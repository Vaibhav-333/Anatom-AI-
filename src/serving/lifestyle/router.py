"""
Lifestyle Planner Router — AI-generated diet, exercise, and preventive care plans.
Prefix: /lifestyle
"""
from __future__ import annotations

import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.serving.database import get_db
from src.serving.lifestyle.models import (
    LifestylePlanRequest,
    LifestylePlanResponse,
    LifestylePlanSummary,
    LifestyleShareRequest,
    LifestyleShareResponse,
    MealEntry,
    ExerciseEntry,
    NutritionInfo,
)
from src.serving.lifestyle.lifestyle_ai import generate_lifestyle_plan

router = APIRouter(prefix="/lifestyle", tags=["Lifestyle Planner"])


def _parse_plan_row(row) -> LifestylePlanResponse:
    meal_raw = json.loads(row["meal_plan"] or "{}")
    exercise_raw = json.loads(row["exercise_plan"] or "[]")
    avoid = json.loads(row["avoid_list"] or "[]")
    preventive = json.loads(row["preventive_care"] or "[]")

    meals: dict = {}
    for slot, entries in meal_raw.items():
        meals[slot] = [MealEntry(**e) for e in entries] if entries else []

    exercises = [ExerciseEntry(**e) for e in exercise_raw] if exercise_raw else []

    # Compute daily nutrition from meals
    total_cal = total_pro = total_carb = total_fat = total_fib = 0.0
    for slot_entries in meals.values():
        for entry in slot_entries:
            n = entry.nutrition
            total_cal += n.calories
            total_pro += n.protein_g
            total_carb += n.carbs_g
            total_fat += n.fat_g
            total_fib += n.fiber_g

    return LifestylePlanResponse(
        id=row["id"],
        user_id=row["user_id"],
        goal=row["goal"],
        dietary_pref=row["dietary_pref"],
        activity_level=row["activity_level"],
        plan_date=row["plan_date"],
        meals=meals,
        daily_nutrition=NutritionInfo(
            calories=int(total_cal), protein_g=round(total_pro, 1),
            carbs_g=round(total_carb, 1), fat_g=round(total_fat, 1), fiber_g=round(total_fib, 1),
        ),
        exercises=exercises,
        avoid_list=avoid,
        preventive_care=preventive,
        ai_notes=row["ai_notes"],
        auto_adjusted=False,
    )


# ── Generate Plan ─────────────────────────────────────────────────────────────

@router.post("/generate", response_model=LifestylePlanResponse)
async def generate_plan(body: LifestylePlanRequest):
    plan_date = body.plan_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Fetch symptom trend from insights engine if not provided
    symptom_trend = body.symptom_trend
    avg_pain = body.avg_pain
    if symptom_trend is None:
        try:
            from src.serving.health_tracker import insights_engine
            start = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%d")
            async with get_db() as db:
                s_rows = await (await db.execute(
                    "SELECT * FROM ht_symptom_logs WHERE user_id=? AND date_key >= ? ORDER BY date_key",
                    (body.user_id, start),
                )).fetchall()
            s_logs = [dict(r) for r in s_rows]
            pain_vals = [r["pain_level"] for r in s_logs if r.get("pain_level") is not None]
            symptom_trend = insights_engine.classify_trend(pain_vals)
            avg_pain = round(sum(pain_vals) / len(pain_vals), 1) if pain_vals else None
        except Exception:
            symptom_trend = "stable"

    # Fetch user profile for personalisation
    user_profile = None
    try:
        async with get_db() as db:
            p_row = await (await db.execute(
                "SELECT * FROM profiles WHERE id=?", (body.user_id,)
            )).fetchone()
        if p_row:
            user_profile = dict(p_row)
    except Exception:
        pass

    plan_dict, auto_adjusted = await generate_lifestyle_plan(
        goal=body.goal,
        dietary_pref=body.dietary_pref,
        restrictions=body.restrictions,
        activity_level=body.activity_level,
        symptom_trend=symptom_trend,
        avg_pain=avg_pain,
        user_profile=user_profile,
    )

    plan_id = f"lp-{uuid.uuid4().hex[:12]}"
    meal_plan = plan_dict.get("meals", {})
    exercise_plan = plan_dict.get("exercises", [])
    avoid_list = plan_dict.get("avoid_list", [])
    preventive_care = plan_dict.get("preventive_care", [])
    ai_notes = plan_dict.get("ai_notes", "")
    daily_nutrition_raw = plan_dict.get("daily_nutrition", {})

    async with get_db() as db:
        await db.execute(
            """INSERT INTO ht_lifestyle_plans
               (id, user_id, goal, dietary_pref, restrictions, activity_level,
                plan_date, meal_plan, exercise_plan, avoid_list, preventive_care, ai_notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (plan_id, body.user_id, body.goal, body.dietary_pref,
             json.dumps(body.restrictions), body.activity_level, plan_date,
             json.dumps(meal_plan), json.dumps(exercise_plan),
             json.dumps(avoid_list), json.dumps(preventive_care), ai_notes),
        )
        await db.commit()

    # Build response
    meals_parsed: dict = {}
    for slot, entries in meal_plan.items():
        meals_parsed[slot] = [MealEntry(**e) for e in entries] if isinstance(entries, list) else []

    exercises_parsed = [ExerciseEntry(**e) for e in exercise_plan] if isinstance(exercise_plan, list) else []

    total_cal = daily_nutrition_raw.get("calories", 0)
    daily_nutrition = NutritionInfo(
        calories=int(total_cal),
        protein_g=daily_nutrition_raw.get("protein_g", 0),
        carbs_g=daily_nutrition_raw.get("carbs_g", 0),
        fat_g=daily_nutrition_raw.get("fat_g", 0),
        fiber_g=daily_nutrition_raw.get("fiber_g", 0),
    )

    return LifestylePlanResponse(
        id=plan_id,
        user_id=body.user_id,
        goal=body.goal,
        dietary_pref=body.dietary_pref,
        activity_level=body.activity_level,
        plan_date=plan_date,
        meals=meals_parsed,
        daily_nutrition=daily_nutrition,
        exercises=exercises_parsed,
        avoid_list=avoid_list,
        preventive_care=preventive_care,
        ai_notes=ai_notes,
        auto_adjusted=auto_adjusted,
    )


@router.get("/{user_id}/latest", response_model=LifestylePlanResponse)
async def get_latest_plan(user_id: str):
    async with get_db() as db:
        row = await (await db.execute(
            "SELECT * FROM ht_lifestyle_plans WHERE user_id=? ORDER BY generated_at DESC LIMIT 1",
            (user_id,),
        )).fetchone()
    if not row:
        raise HTTPException(404, "No lifestyle plan found for this user")
    return _parse_plan_row(row)


@router.get("/{user_id}/history", response_model=list[LifestylePlanSummary])
async def get_plan_history(user_id: str, limit: int = Query(7, le=30)):
    async with get_db() as db:
        rows = await (await db.execute(
            "SELECT id, plan_date, goal, activity_level FROM ht_lifestyle_plans WHERE user_id=? ORDER BY generated_at DESC LIMIT ?",
            (user_id, limit),
        )).fetchall()
    return [
        LifestylePlanSummary(id=r["id"], plan_date=r["plan_date"],
                             goal=r["goal"], activity_level=r["activity_level"],
                             auto_adjusted=False)
        for r in rows
    ]


@router.get("/{user_id}/recommendations")
async def get_recommendations(user_id: str):
    async with get_db() as db:
        row = await (await db.execute(
            "SELECT preventive_care FROM ht_lifestyle_plans WHERE user_id=? ORDER BY generated_at DESC LIMIT 1",
            (user_id,),
        )).fetchone()
    if not row:
        return {"recommendations": []}
    return {"recommendations": json.loads(row["preventive_care"] or "[]")}


# ── Share ─────────────────────────────────────────────────────────────────────

@router.post("/share", response_model=LifestyleShareResponse)
async def share_lifestyle_plan(body: LifestyleShareRequest):
    token = secrets.token_urlsafe(24)
    report_id = f"lp:{body.user_id}"
    expires_at = (
        datetime.now(timezone.utc) + timedelta(hours=body.expiry_hours)
    ).strftime("%Y-%m-%dT%H:%M:%S")

    async with get_db() as db:
        await db.execute(
            "INSERT INTO shared_reports (token, report_id, expires_at) VALUES (?,?,?)",
            (token, report_id, expires_at),
        )
        await db.commit()

    return LifestyleShareResponse(
        token=token,
        share_url=f"/lifestyle/share/{token}",
        expires_at=expires_at,
    )


@router.get("/share/{token}")
async def view_shared_lifestyle_plan(token: str):
    async with get_db() as db:
        row = await (await db.execute(
            "SELECT * FROM shared_reports WHERE token=?", (token,)
        )).fetchone()
        if not row:
            raise HTTPException(404, "Share token not found")
        if row["is_revoked"]:
            raise HTTPException(410, "This share link has been revoked")
        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        if row["expires_at"] < now_str:
            raise HTTPException(410, "This share link has expired")

        report_id: str = row["report_id"]
        if not report_id.startswith("lp:"):
            raise HTTPException(400, "Invalid share token type")
        user_id = report_id[3:]

        plan_row = await (await db.execute(
            "SELECT * FROM ht_lifestyle_plans WHERE user_id=? ORDER BY generated_at DESC LIMIT 1",
            (user_id,),
        )).fetchone()
        await db.execute(
            "UPDATE shared_reports SET view_count=view_count+1, last_viewed_at=? WHERE token=?",
            (now_str, token),
        )
        await db.commit()

    if not plan_row:
        return {"user_id": user_id, "message": "No lifestyle plan found"}
    plan = _parse_plan_row(plan_row)
    return {
        "user_id": user_id,
        "goal": plan.goal,
        "plan_date": plan.plan_date,
        "avoid_list": plan.avoid_list,
        "preventive_care": plan.preventive_care,
        "ai_notes": plan.ai_notes,
    }
