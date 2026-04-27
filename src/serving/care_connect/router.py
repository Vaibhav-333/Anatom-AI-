"""CareConnect AI — FastAPI router with all endpoints."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from src.serving.database import get_db
from src.serving.care_connect.models import (
    CareReport,
    CareReportSummary,
    Doctor,
    DoctorRecommendRequest,
    GenerateReportRequest,
    GenerateReportResponse,
    PublicReportResponse,
    ProbableCondition,
    SaveDoctorRequest,
    ShareReportRequest,
    ShareReportResponse,
)
from src.serving.care_connect import report_gen, doctor_rec, share_mgr
from src.serving.care_connect.pdf_gen import generate_care_report_pdf
from src.serving.care_connect.seed_doctors import seed_doctors_if_empty
from src.serving.care_connect.symptom_map import resolve_specialization

router = APIRouter(prefix="/care-connect", tags=["CareConnect AI"])


def _now_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_to_report(row) -> CareReport:
    return CareReport(
        id=row["id"],
        user_id=row["user_id"],
        created_at=row["created_at"],
        symptoms=json.loads(row["symptoms"] or "[]"),
        user_age=row["user_age"],
        user_gender=row["user_gender"],
        medical_history=json.loads(row["medical_history"] or "[]"),
        severity=row["severity"],
        duration_days=row["duration_days"],
        probable_conditions=[
            ProbableCondition(**c)
            for c in json.loads(row["probable_conditions"] or "[]")
        ],
        affected_organs=json.loads(row["affected_organs"] or "[]"),
        risk_level=row["risk_level"],
        red_flags=json.loads(row["red_flags"] or "[]"),
        next_steps=json.loads(row["next_steps"] or "[]"),
        treatment_suggestions=json.loads(row["treatment_suggestions"] or "[]"),
        recommended_specialization=row["recommended_specialization"] or "General Physician",
        pdf_path=row["pdf_path"],
    )


def _dict_to_doctor(d: dict) -> Doctor:
    return Doctor(**d)


# ---------------------------------------------------------------------------
# Seed endpoint (called once on startup via lifespan)
# ---------------------------------------------------------------------------

async def ensure_seeded():
    """Call this from app lifespan to seed doctor data."""
    async with get_db() as db:
        await seed_doctors_if_empty(db)


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------

@router.post("/report/generate", response_model=GenerateReportResponse)
async def generate_report(req: GenerateReportRequest):
    """Generate an AI medical report from symptoms and patient data."""
    # Call Gemini AI
    ai_data = await report_gen.generate_care_report(
        symptoms=req.symptoms,
        age=req.age,
        gender=req.gender,
        medical_history=req.medical_history,
        severity=req.severity,
        duration_days=req.duration_days,
    )

    report_id = f"cr-{uuid.uuid4().hex[:12]}"
    now = _now_str()

    conditions = ai_data.get("probable_conditions", [])
    condition_names = [c.get("name", "") for c in conditions]
    specialization = ai_data.get(
        "recommended_specialization",
        resolve_specialization(req.symptoms, condition_names),
    )

    async with get_db() as db:
        await db.execute(
            """INSERT INTO care_reports
               (id, user_id, created_at, symptoms, user_age, user_gender,
                medical_history, severity, duration_days, probable_conditions,
                affected_organs, risk_level, red_flags, next_steps,
                treatment_suggestions, recommended_specialization, ai_raw_response)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                report_id, req.user_id, now,
                json.dumps(req.symptoms),
                req.age, req.gender,
                json.dumps(req.medical_history),
                req.severity, req.duration_days,
                json.dumps(conditions),
                json.dumps(ai_data.get("affected_organs", [])),
                ai_data.get("risk_level", "medium"),
                json.dumps(ai_data.get("red_flags", [])),
                json.dumps(ai_data.get("next_steps", [])),
                json.dumps(ai_data.get("treatment_suggestions", [])),
                specialization,
                json.dumps(ai_data),
            ),
        )
        await db.commit()

        # Seed doctors if empty
        await seed_doctors_if_empty(db)

        # Get recommended doctors
        rec_docs = await doctor_rec.get_recommended_doctors(
            db,
            symptoms=req.symptoms,
            conditions=condition_names,
            specialization=specialization,
            limit=6,
        )

        # Re-fetch the saved report
        async with db.execute(
            "SELECT * FROM care_reports WHERE id = ?", (report_id,)
        ) as cur:
            row = await cur.fetchone()

    report = _row_to_report(row)
    doctors = [_dict_to_doctor(d) for d in rec_docs]

    return GenerateReportResponse(
        report_id=report_id,
        report=report,
        recommended_doctors=doctors,
    )


# ---------------------------------------------------------------------------
# Report CRUD
# ---------------------------------------------------------------------------

@router.get("/reports/{user_id}", response_model=list[CareReportSummary])
async def list_reports(user_id: str):
    """List all CareConnect reports for a user, newest first."""
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM care_reports WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()

    results = []
    for row in rows:
        results.append(CareReportSummary(
            id=row["id"],
            created_at=row["created_at"],
            symptoms=json.loads(row["symptoms"] or "[]"),
            risk_level=row["risk_level"],
            recommended_specialization=row["recommended_specialization"] or "General Physician",
            probable_conditions=[
                ProbableCondition(**c)
                for c in json.loads(row["probable_conditions"] or "[]")
            ],
        ))
    return results


@router.get("/report/{report_id}", response_model=GenerateReportResponse)
async def get_report(report_id: str):
    """Get a single report with recommended doctors."""
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM care_reports WHERE id = ?", (report_id,)
        ) as cur:
            row = await cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Report not found.")

        report = _row_to_report(row)
        condition_names = [c.name for c in report.probable_conditions]

        await seed_doctors_if_empty(db)
        rec_docs = await doctor_rec.get_recommended_doctors(
            db,
            symptoms=report.symptoms,
            conditions=condition_names,
            specialization=report.recommended_specialization,
            limit=6,
        )

    return GenerateReportResponse(
        report_id=report_id,
        report=report,
        recommended_doctors=[_dict_to_doctor(d) for d in rec_docs],
    )


@router.delete("/report/{report_id}")
async def delete_report(report_id: str):
    async with get_db() as db:
        async with db.execute(
            "SELECT id FROM care_reports WHERE id = ?", (report_id,)
        ) as cur:
            row = await cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Report not found.")
        await db.execute("DELETE FROM care_reports WHERE id = ?", (report_id,))
        await db.commit()
    return {"status": "deleted", "report_id": report_id}


# ---------------------------------------------------------------------------
# PDF Export
# ---------------------------------------------------------------------------

@router.get("/report/{report_id}/pdf")
async def download_pdf(report_id: str):
    """Generate and return a professional PDF for a CareConnect report."""
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM care_reports WHERE id = ?", (report_id,)
        ) as cur:
            row = await cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Report not found.")

        report = _row_to_report(row)
        condition_names = [c.name for c in report.probable_conditions]
        await seed_doctors_if_empty(db)
        rec_docs = await doctor_rec.get_recommended_doctors(
            db,
            symptoms=report.symptoms,
            conditions=condition_names,
            specialization=report.recommended_specialization,
            limit=3,
        )

    report_dict = report.model_dump()
    report_dict["probable_conditions"] = [c.model_dump() for c in report.probable_conditions]
    pdf_bytes = generate_care_report_pdf(report_dict, rec_docs)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="care-report-{report_id}.pdf"'},
    )


# ---------------------------------------------------------------------------
# Report Sharing
# ---------------------------------------------------------------------------

@router.post("/report/{report_id}/share", response_model=ShareReportResponse)
async def share_report(report_id: str, req: ShareReportRequest):
    """Create a shareable token-link for a report."""
    async with get_db() as db:
        async with db.execute(
            "SELECT id FROM care_reports WHERE id = ?", (report_id,)
        ) as cur:
            if not await cur.fetchone():
                raise HTTPException(status_code=404, detail="Report not found.")

        result = await share_mgr.create_share_token(db, report_id, req.expiry_hours)

    return ShareReportResponse(**result)


@router.get("/share/{token}", response_model=PublicReportResponse)
async def view_shared_report(token: str, request: Request):
    """Public endpoint — view a report via share token (no auth required)."""
    async with get_db() as db:
        record = await share_mgr.get_share_record(db, token)
        if not record:
            raise HTTPException(status_code=404, detail="Link not found, expired, or revoked.")

        client_ip = request.client.host if request.client else None
        await share_mgr.record_view(db, token, client_ip)

        async with db.execute(
            "SELECT * FROM care_reports WHERE id = ?", (record["report_id"],)
        ) as cur:
            row = await cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Report data not found.")

    report = _row_to_report(row)
    return PublicReportResponse(
        report_id=report.id,
        created_at=report.created_at,
        symptoms=report.symptoms,
        probable_conditions=report.probable_conditions,
        risk_level=report.risk_level,
        red_flags=report.red_flags,
        next_steps=report.next_steps,
        recommended_specialization=report.recommended_specialization,
        expires_at=record["expires_at"],
        view_count=record["view_count"] + 1,
    )


@router.post("/share/{token}/revoke")
async def revoke_share(token: str):
    async with get_db() as db:
        ok = await share_mgr.revoke_token(db, token)
    if not ok:
        raise HTTPException(status_code=404, detail="Token not found.")
    return {"status": "revoked", "token": token}


# ---------------------------------------------------------------------------
# Doctor Recommendation
# ---------------------------------------------------------------------------

@router.post("/doctors/recommend", response_model=list[Doctor])
async def recommend_doctors(req: DoctorRecommendRequest):
    """Rank doctors by relevance to given conditions and preferences."""
    async with get_db() as db:
        await seed_doctors_if_empty(db)
        docs = await doctor_rec.get_recommended_doctors(
            db,
            symptoms=[],
            conditions=req.conditions,
            specialization=req.specialization,
            max_fee=req.max_fee,
            mode=req.mode,
            limit=10,
        )
    return [_dict_to_doctor(d) for d in docs]


@router.get("/doctors", response_model=list[Doctor])
async def list_doctors(
    specialization: str | None = None,
    mode: str | None = None,
    max_fee: int | None = None,
    min_rating: float | None = None,
):
    """List all doctors with optional filters."""
    async with get_db() as db:
        await seed_doctors_if_empty(db)
        docs = await doctor_rec.get_all_doctors(
            db,
            specialization=specialization,
            mode=mode,
            max_fee=max_fee,
            min_rating=min_rating,
        )
    return [_dict_to_doctor(d) for d in docs]


@router.get("/doctors/{doctor_id}", response_model=Doctor)
async def get_doctor(doctor_id: str):
    async with get_db() as db:
        doc = await doctor_rec.get_doctor_by_id(db, doctor_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Doctor not found.")
    return _dict_to_doctor(doc)


# ---------------------------------------------------------------------------
# Saved Doctors
# ---------------------------------------------------------------------------

@router.post("/saved-doctors")
async def save_doctor(req: SaveDoctorRequest):
    async with get_db() as db:
        try:
            await db.execute(
                "INSERT INTO saved_doctors (user_id, doctor_id) VALUES (?, ?)",
                (req.user_id, req.doctor_id),
            )
            await db.commit()
        except Exception:
            pass  # UNIQUE constraint — already saved
    return {"status": "saved", "doctor_id": req.doctor_id}


@router.get("/saved-doctors/{user_id}", response_model=list[Doctor])
async def get_saved_doctors(user_id: str):
    async with get_db() as db:
        await seed_doctors_if_empty(db)
        async with db.execute(
            """SELECT d.* FROM doctors d
               JOIN saved_doctors s ON d.id = s.doctor_id
               WHERE s.user_id = ?
               ORDER BY s.saved_at DESC""",
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
    return [_dict_to_doctor(doctor_rec._parse_doctor(row)) for row in rows]


@router.delete("/saved-doctors/{user_id}/{doctor_id}")
async def unsave_doctor(user_id: str, doctor_id: str):
    async with get_db() as db:
        await db.execute(
            "DELETE FROM saved_doctors WHERE user_id = ? AND doctor_id = ?",
            (user_id, doctor_id),
        )
        await db.commit()
    return {"status": "removed", "doctor_id": doctor_id}
