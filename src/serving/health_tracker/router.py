"""
Health Tracker Router — symptom logs, medications, insights, scores, export, share.
Prefix: /health-tracker
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from src.serving.database import get_db
from src.serving.health_tracker.models import (
    AdherenceStats,
    CalendarHeatmapPoint,
    HealthTrackerShareRequest,
    HealthTrackerShareResponse,
    InsightsResponse,
    MedLogCreate,
    MedLogResponse,
    MedicationCreate,
    MedicationResponse,
    SymptomLogCreate,
    SymptomLogResponse,
    SymptomTrendPoint,
    WeeklyScoreResponse,
)
from src.serving.health_tracker import insights_engine
from src.serving.health_tracker.pdf_gen import generate_health_tracker_pdf

router = APIRouter(prefix="/health-tracker", tags=["Health Tracker"])


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def _date_key(dt: Optional[datetime] = None) -> str:
    d = dt or datetime.now(timezone.utc)
    return d.strftime("%Y-%m-%d")


def _row_to_symptom(row) -> SymptomLogResponse:
    return SymptomLogResponse(
        id=row["id"],
        user_id=row["user_id"],
        logged_at=row["logged_at"],
        date_key=row["date_key"],
        pain_level=row["pain_level"],
        fever_celsius=row["fever_celsius"],
        fatigue=row["fatigue"],
        mood=row["mood"],
        sleep_hours=row["sleep_hours"],
        custom_symptoms=json.loads(row["custom_symptoms"] or "[]"),
        notes=row["notes"],
    )


def _row_to_medication(row) -> MedicationResponse:
    return MedicationResponse(
        id=row["id"],
        user_id=row["user_id"],
        name=row["name"],
        dosage=row["dosage"],
        frequency=row["frequency"],
        duration_days=row["duration_days"],
        start_date=row["start_date"],
        end_date=row["end_date"],
        active=bool(row["active"]),
    )


def _row_to_medlog(row) -> MedLogResponse:
    return MedLogResponse(
        id=row["id"],
        medication_id=row["medication_id"],
        user_id=row["user_id"],
        scheduled_for=row["scheduled_for"],
        taken_at=row["taken_at"],
        status=row["status"],
        date_key=row["date_key"],
    )


# ── Symptom Logs ──────────────────────────────────────────────────────────────

@router.post("/symptoms", response_model=SymptomLogResponse, tags=["Health Tracker"])
async def log_symptom(body: SymptomLogCreate):
    log_id = f"sl-{uuid.uuid4().hex[:12]}"
    logged_at = body.logged_at or datetime.now(timezone.utc)
    logged_at_str = logged_at.strftime("%Y-%m-%dT%H:%M:%S")
    date_key = _date_key(logged_at)

    # Convert Fahrenheit to Celsius if provided
    fever_c = body.fever_celsius
    if fever_c is None and body.fever_fahrenheit is not None:
        fever_c = round((body.fever_fahrenheit - 32) * 5 / 9, 2)

    async with get_db() as db:
        await db.execute(
            """INSERT INTO ht_symptom_logs
               (id, user_id, logged_at, date_key, pain_level, fever_celsius,
                fatigue, mood, sleep_hours, custom_symptoms, notes)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (log_id, body.user_id, logged_at_str, date_key, body.pain_level,
             fever_c, body.fatigue, body.mood, body.sleep_hours,
             json.dumps(body.custom_symptoms), body.notes),
        )
        await db.commit()
        row = await (await db.execute(
            "SELECT * FROM ht_symptom_logs WHERE id=?", (log_id,)
        )).fetchone()
    return _row_to_symptom(row)


@router.get("/symptoms/{user_id}", response_model=list[SymptomLogResponse])
async def get_symptoms(
    user_id: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    limit: int = Query(100, le=500),
):
    query = "SELECT * FROM ht_symptom_logs WHERE user_id=?"
    params: list = [user_id]
    if start:
        query += " AND date_key >= ?"
        params.append(start)
    if end:
        query += " AND date_key <= ?"
        params.append(end)
    query += " ORDER BY logged_at DESC LIMIT ?"
    params.append(limit)
    async with get_db() as db:
        rows = await (await db.execute(query, params)).fetchall()
    return [_row_to_symptom(r) for r in rows]


@router.get("/symptoms/{user_id}/trends", response_model=list[SymptomTrendPoint])
async def get_symptom_trends(
    user_id: str,
    period: str = Query("weekly", regex="^(weekly|monthly)$"),
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    if not start:
        days = 30 if period == "monthly" else 7
        start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    if not end:
        end = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    async with get_db() as db:
        rows = await (await db.execute(
            """SELECT date_key,
                      AVG(pain_level) as avg_pain,
                      AVG(mood) as avg_mood,
                      AVG(sleep_hours) as avg_sleep,
                      AVG(fever_celsius) as avg_fever,
                      COUNT(*) as entry_count
               FROM ht_symptom_logs
               WHERE user_id=? AND date_key BETWEEN ? AND ?
               GROUP BY date_key ORDER BY date_key""",
            (user_id, start, end),
        )).fetchall()

    return [
        SymptomTrendPoint(
            date=r["date_key"],
            avg_pain=round(r["avg_pain"], 2) if r["avg_pain"] is not None else None,
            avg_mood=round(r["avg_mood"], 2) if r["avg_mood"] is not None else None,
            avg_sleep=round(r["avg_sleep"], 2) if r["avg_sleep"] is not None else None,
            avg_fever=round(r["avg_fever"], 2) if r["avg_fever"] is not None else None,
            entry_count=r["entry_count"],
        )
        for r in rows
    ]


@router.get("/symptoms/{user_id}/heatmap", response_model=list[CalendarHeatmapPoint])
async def get_symptom_heatmap(
    user_id: str,
    year: int = Query(datetime.now().year),
    month: int = Query(datetime.now().month, ge=1, le=12),
):
    month_str = f"{year}-{month:02d}"
    async with get_db() as db:
        rows = await (await db.execute(
            """SELECT date_key,
                      AVG(COALESCE(pain_level, 5)) as pain_avg,
                      AVG(CASE fatigue WHEN 'high' THEN 1 WHEN 'medium' THEN 0.5 ELSE 0 END) as fatigue_avg
               FROM ht_symptom_logs
               WHERE user_id=? AND date_key LIKE ?
               GROUP BY date_key""",
            (user_id, f"{month_str}-%"),
        )).fetchall()

    result = []
    for r in rows:
        raw = (r["pain_avg"] / 10.0 * 0.7) + (r["fatigue_avg"] * 0.3)
        result.append(CalendarHeatmapPoint(date=r["date_key"], intensity=round(min(1.0, raw), 3)))
    return result


@router.delete("/symptoms/{log_id}")
async def delete_symptom_log(log_id: str):
    async with get_db() as db:
        await db.execute("DELETE FROM ht_symptom_logs WHERE id=?", (log_id,))
        await db.commit()
    return {"status": "deleted", "id": log_id}


# ── Medications ───────────────────────────────────────────────────────────────

@router.post("/medications", response_model=MedicationResponse)
async def add_medication(body: MedicationCreate):
    med_id = f"med-{uuid.uuid4().hex[:12]}"
    end_date = None
    if body.duration_days:
        start = datetime.strptime(body.start_date, "%Y-%m-%d")
        end_date = (start + timedelta(days=body.duration_days)).strftime("%Y-%m-%d")

    async with get_db() as db:
        await db.execute(
            """INSERT INTO ht_medications
               (id, user_id, name, dosage, frequency, duration_days, start_date, end_date, active)
               VALUES (?,?,?,?,?,?,?,?,1)""",
            (med_id, body.user_id, body.name, body.dosage,
             body.frequency, body.duration_days, body.start_date, end_date),
        )
        await db.commit()
        row = await (await db.execute(
            "SELECT * FROM ht_medications WHERE id=?", (med_id,)
        )).fetchone()
    return _row_to_medication(row)


@router.get("/medications/{user_id}", response_model=list[MedicationResponse])
async def get_medications(user_id: str, active_only: bool = True):
    query = "SELECT * FROM ht_medications WHERE user_id=?"
    params: list = [user_id]
    if active_only:
        query += " AND active=1"
    query += " ORDER BY created_at DESC"
    async with get_db() as db:
        rows = await (await db.execute(query, params)).fetchall()
    return [_row_to_medication(r) for r in rows]


@router.patch("/medications/{med_id}/deactivate")
async def deactivate_medication(med_id: str):
    async with get_db() as db:
        await db.execute("UPDATE ht_medications SET active=0 WHERE id=?", (med_id,))
        await db.commit()
    return {"status": "deactivated", "id": med_id}


@router.delete("/medications/{med_id}")
async def delete_medication(med_id: str):
    async with get_db() as db:
        await db.execute("DELETE FROM ht_medications WHERE id=?", (med_id,))
        await db.commit()
    return {"status": "deleted", "id": med_id}


# ── Medication Logs ───────────────────────────────────────────────────────────

@router.post("/medication-logs", response_model=MedLogResponse)
async def log_medication_dose(body: MedLogCreate):
    log_id = f"ml-{uuid.uuid4().hex[:12]}"
    taken_at = body.taken_at or (_now_iso() if body.status == "taken" else None)
    date_key = body.scheduled_for[:10]

    async with get_db() as db:
        await db.execute(
            """INSERT INTO ht_medication_logs
               (id, medication_id, user_id, scheduled_for, taken_at, status, date_key)
               VALUES (?,?,?,?,?,?,?)""",
            (log_id, body.medication_id, body.user_id,
             body.scheduled_for, taken_at, body.status, date_key),
        )
        await db.commit()
        row = await (await db.execute(
            "SELECT * FROM ht_medication_logs WHERE id=?", (log_id,)
        )).fetchone()
    return _row_to_medlog(row)


@router.get("/medication-logs/{user_id}/adherence", response_model=list[AdherenceStats])
async def get_adherence_stats(
    user_id: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    if not start:
        start = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end:
        end = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    async with get_db() as db:
        meds = await (await db.execute(
            "SELECT * FROM ht_medications WHERE user_id=?", (user_id,)
        )).fetchall()

        stats = []
        for med in meds:
            logs = await (await db.execute(
                """SELECT * FROM ht_medication_logs
                   WHERE medication_id=? AND date_key BETWEEN ? AND ?""",
                (med["id"], start, end),
            )).fetchall()

            total = len(logs)
            taken = sum(1 for l in logs if l["status"] == "taken")
            missed = sum(1 for l in logs if l["status"] == "missed")
            adherence_pct = round(taken / total * 100, 1) if total > 0 else 0.0

            last_7 = [
                {"date": l["date_key"], "status": l["status"]}
                for l in sorted(logs, key=lambda x: x["date_key"])[-7:]
            ]

            stats.append(AdherenceStats(
                medication_id=med["id"],
                medication_name=med["name"],
                total_doses=total,
                taken=taken,
                missed=missed,
                adherence_pct=adherence_pct,
                last_7_days=last_7,
            ))
    return stats


@router.get("/medication-logs/{user_id}/calendar")
async def get_med_calendar(
    user_id: str,
    year: int = Query(datetime.now().year),
    month: int = Query(datetime.now().month, ge=1, le=12),
):
    month_str = f"{year}-{month:02d}"
    async with get_db() as db:
        rows = await (await db.execute(
            """SELECT date_key,
                      SUM(CASE WHEN status='taken' THEN 1 ELSE 0 END) as taken_count,
                      SUM(CASE WHEN status='missed' THEN 1 ELSE 0 END) as missed_count
               FROM ht_medication_logs
               WHERE user_id=? AND date_key LIKE ?
               GROUP BY date_key ORDER BY date_key""",
            (user_id, f"{month_str}-%"),
        )).fetchall()
    return [{"date": r["date_key"], "taken_count": r["taken_count"], "missed_count": r["missed_count"]} for r in rows]


# ── AI Insights ───────────────────────────────────────────────────────────────

@router.get("/insights/{user_id}", response_model=InsightsResponse)
async def get_insights(user_id: str, days: int = Query(14, ge=3, le=90)):
    start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    async with get_db() as db:
        symptom_rows = await (await db.execute(
            "SELECT * FROM ht_symptom_logs WHERE user_id=? AND date_key >= ? ORDER BY date_key",
            (user_id, start),
        )).fetchall()
        med_rows = await (await db.execute(
            "SELECT * FROM ht_medication_logs WHERE user_id=? AND date_key >= ?",
            (user_id, start),
        )).fetchall()
        score_row = await (await db.execute(
            "SELECT * FROM ht_weekly_scores WHERE user_id=? ORDER BY computed_at DESC LIMIT 1",
            (user_id,),
        )).fetchone()

    s_logs = [dict(r) for r in symptom_rows]
    m_logs = [dict(r) for r in med_rows]
    s_row = dict(score_row) if score_row else None
    return await insights_engine.compute_insights(s_logs, m_logs, s_row)


# ── Weekly Scores ─────────────────────────────────────────────────────────────

@router.get("/scores/{user_id}", response_model=list[WeeklyScoreResponse])
async def get_weekly_scores(user_id: str, weeks: int = Query(8, ge=1, le=52)):
    async with get_db() as db:
        rows = await (await db.execute(
            "SELECT * FROM ht_weekly_scores WHERE user_id=? ORDER BY week_key DESC LIMIT ?",
            (user_id, weeks),
        )).fetchall()
    return [
        WeeklyScoreResponse(
            id=r["id"], user_id=r["user_id"], week_key=r["week_key"],
            score=r["score"], symptom_avg=r["symptom_avg"],
            adherence_pct=r["adherence_pct"], sleep_avg=r["sleep_avg"],
            trend=r["trend"], streak_days=r["streak_days"],
            badges=json.loads(r["badges"] or "[]"),
        )
        for r in rows
    ]


@router.post("/scores/{user_id}/compute", response_model=WeeklyScoreResponse)
async def compute_weekly_score(user_id: str):
    week_key = datetime.now(timezone.utc).strftime("%Y-W%W")
    start = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")

    async with get_db() as db:
        s_rows = await (await db.execute(
            "SELECT * FROM ht_symptom_logs WHERE user_id=? AND date_key >= ?",
            (user_id, start),
        )).fetchall()
        m_rows = await (await db.execute(
            "SELECT * FROM ht_medication_logs WHERE user_id=? AND date_key >= ?",
            (user_id, start),
        )).fetchall()

    s_logs = [dict(r) for r in s_rows]
    m_logs = [dict(r) for r in m_rows]
    pain_vals = [r["pain_level"] for r in s_logs if r.get("pain_level") is not None]
    sleep_vals = [r["sleep_hours"] for r in s_logs if r.get("sleep_hours") is not None]
    trend = insights_engine.classify_trend(pain_vals)
    score, badges = insights_engine.compute_weekly_score(s_logs, m_logs, trend)

    total = len(m_logs)
    taken = sum(1 for m in m_logs if m.get("status") == "taken")
    adherence_pct = round(taken / total * 100, 1) if total > 0 else 100.0
    avg_pain = round(sum(pain_vals) / len(pain_vals), 2) if pain_vals else None
    avg_sleep = round(sum(sleep_vals) / len(sleep_vals), 2) if sleep_vals else None
    date_keys = sorted({r["date_key"] for r in s_logs})
    streak = insights_engine._compute_streak(date_keys)
    score_id = f"ws-{uuid.uuid4().hex[:12]}"

    async with get_db() as db:
        await db.execute(
            """INSERT INTO ht_weekly_scores
               (id, user_id, week_key, score, symptom_avg, adherence_pct,
                sleep_avg, trend, streak_days, badges)
               VALUES (?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(user_id, week_key) DO UPDATE SET
                 score=excluded.score, symptom_avg=excluded.symptom_avg,
                 adherence_pct=excluded.adherence_pct, sleep_avg=excluded.sleep_avg,
                 trend=excluded.trend, streak_days=excluded.streak_days,
                 badges=excluded.badges, computed_at=CURRENT_TIMESTAMP""",
            (score_id, user_id, week_key, score, avg_pain, adherence_pct,
             avg_sleep, trend, streak, json.dumps(badges)),
        )
        await db.commit()

    return WeeklyScoreResponse(
        id=score_id, user_id=user_id, week_key=week_key,
        score=score, symptom_avg=avg_pain, adherence_pct=adherence_pct,
        sleep_avg=avg_sleep, trend=trend, streak_days=streak, badges=badges,
    )


# ── PDF Export ────────────────────────────────────────────────────────────────

@router.get("/export/{user_id}/pdf")
async def export_pdf(
    user_id: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
):
    if not start:
        start = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end:
        end = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    async with get_db() as db:
        s_rows = await (await db.execute(
            "SELECT * FROM ht_symptom_logs WHERE user_id=? AND date_key BETWEEN ? AND ? ORDER BY date_key",
            (user_id, start, end),
        )).fetchall()
        trend_rows = await (await db.execute(
            """SELECT date_key,
                      AVG(pain_level) as avg_pain, AVG(mood) as avg_mood,
                      AVG(sleep_hours) as avg_sleep, AVG(fever_celsius) as avg_fever,
                      COUNT(*) as entry_count
               FROM ht_symptom_logs
               WHERE user_id=? AND date_key BETWEEN ? AND ?
               GROUP BY date_key ORDER BY date_key""",
            (user_id, start, end),
        )).fetchall()
        meds = await (await db.execute(
            "SELECT * FROM ht_medications WHERE user_id=?", (user_id,)
        )).fetchall()
        adh_list = []
        for med in meds:
            logs = await (await db.execute(
                "SELECT * FROM ht_medication_logs WHERE medication_id=? AND date_key BETWEEN ? AND ?",
                (med["id"], start, end),
            )).fetchall()
            total = len(logs)
            taken = sum(1 for l in logs if l["status"] == "taken")
            adh_list.append({
                "medication_name": med["name"],
                "total_doses": total,
                "taken": taken,
                "missed": total - taken,
                "adherence_pct": round(taken / total * 100, 1) if total else 0,
            })
        score_row = await (await db.execute(
            "SELECT * FROM ht_weekly_scores WHERE user_id=? ORDER BY computed_at DESC LIMIT 1",
            (user_id,),
        )).fetchone()

    s_logs = [dict(r) for r in s_rows]
    trend_data = [dict(r) for r in trend_rows]
    score_dict = dict(score_row) if score_row else {}
    pain_vals = [r["pain_level"] for r in s_logs if r.get("pain_level") is not None]
    m_logs_all = []
    insights = await insights_engine.compute_insights(s_logs, m_logs_all, score_dict or None)
    pdf_bytes = generate_health_tracker_pdf(
        user_id=user_id,
        symptom_logs=s_logs,
        trend_data=trend_data,
        adherence_stats=adh_list,
        insights=insights.model_dump(),
        date_range=(start, end),
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="health_report_{user_id}_{end}.pdf"'},
    )


# ── Share ─────────────────────────────────────────────────────────────────────

@router.post("/share", response_model=HealthTrackerShareResponse)
async def share_health_report(body: HealthTrackerShareRequest):
    import secrets
    token = secrets.token_urlsafe(24)
    report_id = f"ht:{body.user_id}"
    expires_at = (
        datetime.now(timezone.utc) + timedelta(hours=body.expiry_hours)
    ).strftime("%Y-%m-%dT%H:%M:%S")

    async with get_db() as db:
        await db.execute(
            "INSERT INTO shared_reports (token, report_id, expires_at) VALUES (?,?,?)",
            (token, report_id, expires_at),
        )
        await db.commit()

    return HealthTrackerShareResponse(
        token=token,
        share_url=f"/health-tracker/share/{token}",
        expires_at=expires_at,
    )


@router.get("/share/{token}")
async def view_shared_health_report(token: str):
    async with get_db() as db:
        row = await (await db.execute(
            "SELECT * FROM shared_reports WHERE token=?", (token,)
        )).fetchone()
        if not row:
            raise HTTPException(404, "Share token not found")
        if row["is_revoked"]:
            raise HTTPException(410, "This share link has been revoked")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        if row["expires_at"] < now:
            raise HTTPException(410, "This share link has expired")

        report_id: str = row["report_id"]
        if not report_id.startswith("ht:"):
            raise HTTPException(400, "Invalid share token type")
        user_id = report_id[3:]

        score_row = await (await db.execute(
            "SELECT * FROM ht_weekly_scores WHERE user_id=? ORDER BY computed_at DESC LIMIT 1",
            (user_id,),
        )).fetchone()
        start = (datetime.now(timezone.utc) - timedelta(days=14)).strftime("%Y-%m-%d")
        s_rows = await (await db.execute(
            "SELECT * FROM ht_symptom_logs WHERE user_id=? AND date_key >= ? ORDER BY date_key",
            (user_id, start),
        )).fetchall()
        await db.execute(
            "UPDATE shared_reports SET view_count=view_count+1, last_viewed_at=? WHERE token=?",
            (now, token),
        )
        await db.commit()

    s_logs = [dict(r) for r in s_rows]
    score = dict(score_row) if score_row else {}
    insights = await insights_engine.compute_insights(s_logs, [], score or None)
    return {
        "user_id": user_id,
        "trend": insights.trend,
        "weekly_score": insights.weekly_score,
        "alerts": [a.model_dump() for a in insights.alerts],
        "suggestions": insights.suggestions,
    }
