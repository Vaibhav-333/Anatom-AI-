"""
profile_manager.py — CRUD operations and health metric computation for user profiles.

All public functions accept an open aiosqlite.Connection and operate within
the caller's transaction scope.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

from src.serving.schemas import ProfileRequest, ProfileResponse


# ---------------------------------------------------------------------------
# Health metric computations
# ---------------------------------------------------------------------------

def compute_bmi(weight_kg: float, height_cm: float) -> float:
    """Return BMI rounded to one decimal place."""
    if height_cm <= 0:
        return 0.0
    height_m = height_cm / 100.0
    return round(weight_kg / (height_m ** 2), 1)


def compute_health_score(
    age: int,
    bmi: float,
    conditions: list[str],
    medications: list[str],
) -> float:
    """
    Heuristic health score (0–100).

    Formula (from ANATOM_AI_MASTER_PLAN.md Phase 2):
        base = 80
        BMI   : underweight −8 | normal +5 | overweight −6 | obese1 −14 | obese2 −22
        Age   : >60 −6 | >45 −3 | <30 +5
        Conds : −5 per condition
        Meds  : −2 per medication (mild — patient is managing)
        Clamp : [5, 100]
    """
    score = 80.0

    if bmi < 18.5:
        score -= 8
    elif 25 <= bmi < 30:
        score -= 6
    elif 30 <= bmi < 35:
        score -= 14
    elif bmi >= 35:
        score -= 22
    else:
        score += 5  # Normal BMI bonus

    if age > 60:
        score -= 6
    elif age > 45:
        score -= 3
    elif age < 30:
        score += 5

    score -= len(conditions) * 5
    score -= len(medications) * 2

    return max(5.0, min(100.0, round(score, 1)))


def compute_metabolic_age(age: int, bmi: float, conditions: list[str]) -> int:
    """
    Estimated metabolic age based on BMI and chronic conditions.
    Mirrors the client-side calculateMetabolicAge() in utils.ts.
    """
    met_age = float(age)
    if bmi < 18.5:
        met_age += 3
    elif bmi >= 30:
        met_age += 7
    elif bmi >= 25:
        met_age += 3
    else:
        met_age -= 2
    met_age += len(conditions) * 1.5
    return max(18, round(met_age))


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _row_to_response(row: aiosqlite.Row) -> ProfileResponse:
    conditions = json.loads(row["conditions"] or "[]")
    medications = json.loads(row["medications"] or "[]")
    bmi = compute_bmi(row["weight_kg"], row["height_cm"])
    met_age = compute_metabolic_age(row["age"], bmi, conditions)
    return ProfileResponse(
        id=row["id"],
        name=row["name"],
        age=row["age"],
        gender=row["gender"],
        height_cm=row["height_cm"],
        weight_kg=row["weight_kg"],
        blood_type=row["blood_type"],
        conditions=conditions,
        medications=medications,
        health_score=row["health_score"],
        bmi=bmi,
        metabolic_age=met_age,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def upsert_profile(
    db: aiosqlite.Connection,
    payload: ProfileRequest,
) -> ProfileResponse:
    """
    Insert a new profile or update all fields if the user_id already exists.
    Also appends a health_score snapshot row for longitudinal tracking.
    """
    bmi = compute_bmi(payload.weight_kg, payload.height_cm)
    score = compute_health_score(payload.age, bmi, payload.conditions, payload.medications)
    now = _now_iso()
    conditions_json = json.dumps(payload.conditions)
    medications_json = json.dumps(payload.medications)

    # Preserve original created_at if record exists
    async with db.execute(
        "SELECT created_at FROM profiles WHERE id = ?", (payload.user_id,)
    ) as cur:
        existing = await cur.fetchone()

    created_at = existing["created_at"] if existing else now

    await db.execute(
        """
        INSERT INTO profiles
            (id, name, age, gender, height_cm, weight_kg, blood_type,
             conditions, medications, health_score, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name         = excluded.name,
            age          = excluded.age,
            gender       = excluded.gender,
            height_cm    = excluded.height_cm,
            weight_kg    = excluded.weight_kg,
            blood_type   = excluded.blood_type,
            conditions   = excluded.conditions,
            medications  = excluded.medications,
            health_score = excluded.health_score,
            updated_at   = excluded.updated_at
        """,
        (
            payload.user_id, payload.name, payload.age, payload.gender,
            payload.height_cm, payload.weight_kg, payload.blood_type,
            conditions_json, medications_json, score, created_at, now,
        ),
    )

    # Append health score history row
    await db.execute(
        "INSERT INTO health_scores (id, user_id, score, date) VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), payload.user_id, score, now),
    )

    await db.commit()

    met_age = compute_metabolic_age(payload.age, bmi, payload.conditions)
    return ProfileResponse(
        id=payload.user_id,
        name=payload.name,
        age=payload.age,
        gender=payload.gender,
        height_cm=payload.height_cm,
        weight_kg=payload.weight_kg,
        blood_type=payload.blood_type,
        conditions=payload.conditions,
        medications=payload.medications,
        health_score=score,
        bmi=bmi,
        metabolic_age=met_age,
        created_at=created_at,
        updated_at=now,
    )


async def get_profile(
    db: aiosqlite.Connection,
    user_id: str,
) -> Optional[ProfileResponse]:
    """Return the profile for *user_id*, or None if not found."""
    async with db.execute(
        "SELECT * FROM profiles WHERE id = ?", (user_id,)
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        return None
    return _row_to_response(row)


async def delete_profile(
    db: aiosqlite.Connection,
    user_id: str,
) -> bool:
    """Delete profile and all associated health_scores. Returns True if found."""
    async with db.execute(
        "SELECT id FROM profiles WHERE id = ?", (user_id,)
    ) as cur:
        found = await cur.fetchone()
    if not found:
        return False
    await db.execute("DELETE FROM health_scores WHERE user_id = ?", (user_id,))
    await db.execute("DELETE FROM profiles WHERE id = ?", (user_id,))
    await db.commit()
    return True
