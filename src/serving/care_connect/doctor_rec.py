"""Doctor recommendation scoring engine."""
from __future__ import annotations

import json
from typing import Any

from src.serving.care_connect.symptom_map import resolve_specialization


def _parse_doctor(row) -> dict[str, Any]:
    """Convert a DB row to a doctor dict."""
    return {
        "id": row["id"],
        "name": row["name"],
        "specialization": row["specialization"],
        "subspecialties": json.loads(row["subspecialties"] or "[]"),
        "experience_years": row["experience_years"] or 0,
        "rating": float(row["rating"] or 4.0),
        "review_count": row["review_count"] or 0,
        "consultation_fee": row["consultation_fee"] or 500,
        "mode": row["mode"] or "both",
        "hospital": row["hospital"] or "",
        "city": row["city"] or "Delhi",
        "latitude": float(row["latitude"] or 28.6139),
        "longitude": float(row["longitude"] or 77.2090),
        "availability": json.loads(row["availability"] or "{}"),
        "verified": bool(row["verified"]),
        "profile_image": row["profile_image"],
        "degrees": json.loads(row["degrees"] or "[]"),
        "languages": json.loads(row["languages"] or '["Hindi","English"]'),
        "about": row["about"] or "",
    }


def _score_doctor(
    doctor: dict,
    target_specialization: str,
    max_fee: int | None,
    mode_pref: str | None,
) -> float:
    """Compute a 0–100 relevance score for a doctor."""
    score = 0.0

    # Specialization match (40 points)
    if doctor["specialization"].lower() == target_specialization.lower():
        score += 40
    elif any(target_specialization.lower() in s.lower() for s in doctor["subspecialties"]):
        score += 20
    elif "general physician" in target_specialization.lower():
        score += 10

    # Rating (25 points) — normalized over 5.0
    score += (doctor["rating"] / 5.0) * 25

    # Experience (15 points) — cap at 20 years
    exp_norm = min(doctor["experience_years"] / 20.0, 1.0)
    score += exp_norm * 15

    # Mode preference (10 points)
    if mode_pref:
        if doctor["mode"] == mode_pref or doctor["mode"] == "both":
            score += 10
    else:
        score += 5  # neutral

    # Budget fit (10 points)
    if max_fee is not None:
        if doctor["consultation_fee"] <= max_fee:
            score += 10
        elif doctor["consultation_fee"] <= max_fee * 1.2:
            score += 5
    else:
        score += 5  # neutral

    return round(score, 2)


async def get_recommended_doctors(
    db,
    symptoms: list[str],
    conditions: list[str],
    specialization: str | None = None,
    max_fee: int | None = None,
    mode: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Fetch and rank doctors by relevance."""
    target_spec = specialization or resolve_specialization(symptoms, conditions)

    async with db.execute("SELECT * FROM doctors") as cur:
        rows = await cur.fetchall()

    doctors = [_parse_doctor(row) for row in rows]

    # Score and rank
    for doc in doctors:
        doc["relevance_score"] = _score_doctor(doc, target_spec, max_fee, mode)

    doctors.sort(key=lambda d: d["relevance_score"], reverse=True)
    return doctors[:limit]


async def get_all_doctors(
    db,
    specialization: str | None = None,
    mode: str | None = None,
    max_fee: int | None = None,
    min_rating: float | None = None,
) -> list[dict]:
    """Fetch all doctors with optional filters."""
    query = "SELECT * FROM doctors WHERE 1=1"
    params: list = []

    if specialization:
        query += " AND LOWER(specialization) = LOWER(?)"
        params.append(specialization)
    if mode and mode != "all":
        query += " AND (mode = ? OR mode = 'both')"
        params.append(mode)
    if max_fee:
        query += " AND consultation_fee <= ?"
        params.append(max_fee)
    if min_rating:
        query += " AND rating >= ?"
        params.append(min_rating)

    query += " ORDER BY rating DESC, review_count DESC"

    async with db.execute(query, params) as cur:
        rows = await cur.fetchall()

    return [_parse_doctor(row) for row in rows]


async def get_doctor_by_id(db, doctor_id: str) -> dict | None:
    """Fetch a single doctor by ID."""
    async with db.execute("SELECT * FROM doctors WHERE id = ?", (doctor_id,)) as cur:
        row = await cur.fetchone()
    if not row:
        return None
    return _parse_doctor(row)
