"""
api.py — FastAPI REST API for Anatom AI clinical analytics.

Endpoints
---------
GET  /health                — liveness probe.
POST /analyze/volume        — compute tumour sub-region volumes from a segmentation.
POST /analyze/longitudinal  — compute RANO growth metrics from two segmentations.
POST /report/pdf            — generate and return a PDF clinical report.
POST /report/dicom          — generate and return a DICOM SR file.

All segmentation arrays are sent as base64-encoded numpy bytes inside JSON
(see src/serving/schemas.py for the ArrayPayload format).

Running locally
---------------
    uvicorn src.serving.api:app --host 0.0.0.0 --port 8000 --reload
    # or
    python scripts/serve.py
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

# Make project root importable when running from any directory
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Load .env before any other imports so os.environ is populated
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import os

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from src.analytics.volumetrics import VolumetricAnalyzer
from src.analytics.longitudinal import LongitudinalTracker
from src.reporting.pdf_report import PDFReportBuilder, ReportConfig
from src.reporting.dicom_sr import DicomSRWriter
from fastapi import File, Form, UploadFile

from src.serving.database import init_db, get_db
from src.serving import profile_manager, report_history
from src.serving.ai_interpreter import interpret_document, sha256_hex
from src.serving.auth.router import router as auth_router
from src.serving.copilot.router import router as copilot_router
from src.serving.care_navigator import router as care_navigator_router
from src.serving.care_connect.router import router as care_connect_router, ensure_seeded
from src.serving.health_tracker.router import router as health_tracker_router
from src.serving.lifestyle.router import router as lifestyle_router
from src.serving.analyze_report import analyse_text
from src.serving.health_guidance import generate_guidance
from src.serving.diagnostic_engine import generate_next_question, finalize_diagnostic
from src.serving.care_connect.doctor_rec import get_recommended_doctors
from src.serving.triage_service import run_triage
from src.serving.knowledge_graph_service import build_knowledge_graph
from src.serving import report_history as _report_history
from src.serving.schemas import (
    AnalyzeReportRequest,
    AnalyzeReportResponse,
    ConditionResult,
    GuidanceRequest,
    HealthResponse,
    InterpretResponse,
    LongitudinalRequest,
    LongitudinalResponse,
    ProfileRequest,
    ProfileResponse,
    ReportDetailResponse,
    ReportSummaryResponse,
    ReportRequest,
    TrajectoryRequest,
    TrajectoryResponse,
    TrajectoryResultSchema,
    VolumeRequest,
    VolumeResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise the SQLite database and seed data on startup."""
    await init_db()
    await ensure_seeded()
    yield


app = FastAPI(
    title="Anatom AI API",
    description="REST API for 3D brain tumour segmentation, volumetrics, trajectory planning, reporting, and consumer health intelligence.",
    version="5.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── GZip compression — all text responses ≥512 bytes are compressed ──────────
app.add_middleware(GZipMiddleware, minimum_size=512)

# ── CORS — env-driven; falls back to localhost for local dev ──────────────────
_raw_origins = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001",
)
_allowed_origins: list[str] = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",   # covers all Vercel preview URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(copilot_router)
app.include_router(care_navigator_router)
app.include_router(care_connect_router)
app.include_router(health_tracker_router)
app.include_router(lifestyle_router)

_analyzer = VolumetricAnalyzer()
_tracker  = LongitudinalTracker()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health() -> HealthResponse:
    """Liveness probe — returns 200 when the service is ready."""
    return HealthResponse()


@app.get("/health/ai", tags=["System"])
async def health_ai() -> dict:
    """
    Check whether the Gemini AI integration is configured.
    Returns gemini_configured=true when GEMINI_API_KEY is set in the environment.
    """
    import os
    key = os.environ.get("GEMINI_API_KEY", "")
    configured = bool(key and len(key) > 10)
    looks_valid = key.startswith("AIza") if configured else False
    return {
        "gemini_configured": configured,
        "gemini_key_valid_format": looks_valid,
        "hint": (
            "Key is set and looks valid." if looks_valid
            else "Key missing or wrong format. Get a key from https://aistudio.google.com/app/apikey"
        ),
    }


# ---------------------------------------------------------------------------
# Analysis endpoints
# ---------------------------------------------------------------------------

@app.post("/analyze/volume", response_model=VolumeResponse, tags=["Analytics"])
async def analyze_volume(req: VolumeRequest) -> VolumeResponse:
    """
    Compute tumour sub-region volumes (NCR, ED, ET, WT, TC) in mm³
    from a BraTS-format integer segmentation array.

    The segmentation must be a 3D integer array (dtype int32) with
    label values: 0=BG, 1=NCR, 2=ED, 3=ET.
    """
    try:
        seg = req.segmentation.to_numpy().astype(np.int32)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to decode segmentation: {e}")

    if seg.ndim != 3:
        raise HTTPException(status_code=422, detail=f"Segmentation must be 3D, got {seg.ndim}D.")

    result = _analyzer.compute(seg, req.voxel_spacing, subject_id=req.subject_id)

    return VolumeResponse(
        subject_id=result.subject_id,
        voxel_volume_mm3=result.voxel_volume_mm3,
        volumes_mm3=result.volumes_mm3,
        wt_mm3=result.wt_mm3,
        tc_mm3=result.tc_mm3,
        et_mm3=result.et_mm3,
        total_tumor_mm3=result.total_tumor_mm3,
        fractions=result.fractions,
    )


@app.post("/analyze/longitudinal", response_model=LongitudinalResponse, tags=["Analytics"])
async def analyze_longitudinal(req: LongitudinalRequest) -> LongitudinalResponse:
    """
    Compare two segmentations from different timepoints.
    Returns delta volumes, growth rates, and RANO classification.
    """
    try:
        seg_t1 = req.seg_t1.to_numpy().astype(np.int32)
        seg_t2 = req.seg_t2.to_numpy().astype(np.int32)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to decode segmentation: {e}")

    for seg, name in [(seg_t1, "seg_t1"), (seg_t2, "seg_t2")]:
        if seg.ndim != 3:
            raise HTTPException(status_code=422,
                                detail=f"{name} must be 3D, got {seg.ndim}D.")

    report = LongitudinalTracker.from_segmentations(
        seg_t1, seg_t2,
        voxel_spacing=req.voxel_spacing,
        days_elapsed=req.days_elapsed,
        subject_id=req.subject_id,
    )

    return LongitudinalResponse(
        subject_id=report.subject_id,
        days_elapsed=report.days_elapsed,
        volumes_t1=report.volumes_t1,
        volumes_t2=report.volumes_t2,
        delta_mm3=report.delta_mm3,
        rate_mm3_per_day=report.rate_mm3_per_day,
        pct_change=report.pct_change,
        rano_category=report.rano_category,
        rano_pct_change=report.rano_pct_change,
    )


# ---------------------------------------------------------------------------
# Report endpoints
# ---------------------------------------------------------------------------

@app.post("/report/pdf", tags=["Reporting"],
          response_class=Response,
          responses={200: {"content": {"application/pdf": {}}}})
async def report_pdf(req: ReportRequest) -> Response:
    """
    Generate a PDF clinical report and return it as application/pdf bytes.

    Optionally include a longitudinal growth section by providing seg_t1
    and days_elapsed alongside the primary segmentation.
    """
    try:
        seg = req.segmentation.to_numpy().astype(np.int32)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to decode segmentation: {e}")

    result = _analyzer.compute(seg, req.voxel_spacing, subject_id=req.subject_id)

    long_report = None
    if req.seg_t1 is not None and req.days_elapsed is not None:
        try:
            seg_t1 = req.seg_t1.to_numpy().astype(np.int32)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Failed to decode seg_t1: {e}")
        long_report = LongitudinalTracker.from_segmentations(
            seg_t1, seg,
            voxel_spacing=req.voxel_spacing,
            days_elapsed=req.days_elapsed,
            subject_id=req.subject_id,
        )

    cfg = ReportConfig(
        subject_id=req.subject_id,
        scan_date=req.scan_date or str(date.today()),
        institution=req.institution,
    )
    builder = PDFReportBuilder(cfg)
    pdf_bytes = builder.build(result, longitudinal_report=long_report)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="anatomai_{req.subject_id}.pdf"'
        },
    )


@app.post("/report/dicom", tags=["Reporting"],
          response_class=Response,
          responses={200: {"content": {"application/dicom": {}}}})
async def report_dicom(req: ReportRequest) -> Response:
    """
    Generate a DICOM Structured Report and return it as application/dicom bytes.
    """
    import io
    try:
        seg = req.segmentation.to_numpy().astype(np.int32)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to decode segmentation: {e}")

    result = _analyzer.compute(seg, req.voxel_spacing, subject_id=req.subject_id)

    long_report = None
    if req.seg_t1 is not None and req.days_elapsed is not None:
        try:
            seg_t1 = req.seg_t1.to_numpy().astype(np.int32)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Failed to decode seg_t1: {e}")
        long_report = LongitudinalTracker.from_segmentations(
            seg_t1, seg,
            voxel_spacing=req.voxel_spacing,
            days_elapsed=req.days_elapsed,
            subject_id=req.subject_id,
        )

    writer = DicomSRWriter()
    ds = writer.build(result, longitudinal_report=long_report)

    buf = io.BytesIO()
    ds.save_as(buf, enforce_file_format=True)
    dicom_bytes = buf.getvalue()

    return Response(
        content=dicom_bytes,
        media_type="application/dicom",
        headers={
            "Content-Disposition": f'attachment; filename="anatomai_{req.subject_id}.dcm"'
        },
    )


# ---------------------------------------------------------------------------
# Phase 4 — Surgical Trajectory Planning
# ---------------------------------------------------------------------------

@app.post("/plan/trajectory", response_model=TrajectoryResponse, tags=["Surgical Planning"])
async def plan_trajectory(req: TrajectoryRequest) -> TrajectoryResponse:
    """
    Compute top-3 optimal surgical trajectories from skull to tumour centroid.

    Returns trajectories ranked by a composite score of path length, landmark
    safety margin, and cortical surface normal alignment. Landmarks are
    optional; when omitted all trajectories are scored on path length + normal.
    """
    from src.analytics.volumetrics import compute_tumor_centroid
    from src.analytics.trajectory_planner import SurgicalTrajectoryPlanner

    try:
        seg = req.segmentation.to_numpy().astype(np.int32)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to decode segmentation: {e}")

    if seg.ndim != 3:
        raise HTTPException(status_code=422, detail=f"Segmentation must be 3D, got {seg.ndim}D.")

    centroid = compute_tumor_centroid(seg, req.voxel_spacing)

    landmarks_np = {}
    if req.landmarks:
        landmarks_np = {k: np.array(v) for k, v in req.landmarks.items()}

    planner = SurgicalTrajectoryPlanner(n_candidates=req.n_candidates)
    results = planner.plan(
        cortex_mesh=None,   # API mode: no PyVista mesh; uses synthetic hemisphere
        tumor_centroid=centroid,
        landmarks=landmarks_np,
    )

    return TrajectoryResponse(
        subject_id=req.subject_id,
        tumor_centroid=list(centroid),
        trajectories=[
            TrajectoryResultSchema(
                rank=r.rank,
                entry_point=r.entry_point.tolist(),
                target_point=r.target_point.tolist(),
                path_length_mm=r.path_length_mm,
                safety_score=r.safety_score,
                warnings=r.warnings,
                landmark_distances=r.landmark_distances,
                normal_alignment=r.normal_alignment,
            )
            for r in results
        ],
    )


# ---------------------------------------------------------------------------
# Phase 2 — User Health Profile
# ---------------------------------------------------------------------------

@app.post("/profile", response_model=ProfileResponse, tags=["Profile"])
async def create_or_update_profile(req: ProfileRequest) -> ProfileResponse:
    """
    Create or update a user health profile.
    Returns the stored profile with server-computed health_score, bmi, and metabolic_age.
    """
    async with get_db() as db:
        return await profile_manager.upsert_profile(db, req)


@app.get("/profile/{user_id}", response_model=ProfileResponse, tags=["Profile"])
async def read_profile(user_id: str) -> ProfileResponse:
    """Retrieve a user profile by user_id."""
    async with get_db() as db:
        result = await profile_manager.get_profile(db, user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return result


@app.delete("/profile/{user_id}", tags=["Profile"])
async def remove_profile(user_id: str) -> dict:
    """Delete a user profile and all associated health score history."""
    async with get_db() as db:
        deleted = await profile_manager.delete_profile(db, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Profile not found.")
    return {"status": "deleted", "user_id": user_id}


# ---------------------------------------------------------------------------
# Phase 3 — AI Medical Report Interpreter
# ---------------------------------------------------------------------------

@app.post("/interpret", response_model=InterpretResponse, tags=["Reports"])
async def interpret(
    file: UploadFile = File(..., description="PDF or image medical document (max 20 MB)"),
    user_id: str = Form(...),
    mode: str = Form("simple"),
) -> InterpretResponse:
    """
    Analyse a medical document with Gemini 1.5 Flash and persist the result.

    - mode: "simple" (patient-friendly) or "doctor" (clinical terminology)
    - Duplicate files (same SHA-256) return the cached result instantly.
    - Requires GEMINI_API_KEY environment variable.
    """
    if mode not in ("simple", "doctor"):
        mode = "simple"

    file_bytes = await file.read()
    if len(file_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds 20 MB limit.")

    mime_type = file.content_type or "application/octet-stream"
    file_name = file.filename or "upload"
    file_hash = sha256_hex(file_bytes)

    async with get_db() as db:
        # Cache hit — return stored interpretation with a fresh report_id lookup
        cached = await report_history.find_by_hash(db, file_hash)
        if cached:
            cached_reports = await report_history.list_reports(db, user_id)
            for r in cached_reports:
                # Find the matching report for this user by hash
                pass
            # Save a new entry for this user referencing the same analysis
            report_id = await report_history.save_report(
                db, user_id, file_name, mime_type, cached, file_hash
            )
            return InterpretResponse(report_id=report_id, **cached)

        # Fresh analysis
        interp_dict = await interpret_document(file_bytes, mime_type, file_name, mode)  # type: ignore[arg-type]
        report_id = await report_history.save_report(
            db, user_id, file_name, mime_type, interp_dict, file_hash
        )

    return InterpretResponse(report_id=report_id, **interp_dict)


# ---------------------------------------------------------------------------
# AI Text Analysis — accepts raw report text, no file upload needed
# ---------------------------------------------------------------------------

# Map Gemini-returned anatomical organ names → 3D mesh keys
_ORGAN_KEY_MAP: dict[str, str] = {
    "heart":            "heart",
    "cardiac":          "heart",
    "myocardium":       "heart",
    "lungs":            "lung",
    "lung":             "lung",
    "pulmonary":        "lung",
    "brain":            "brain",
    "cerebral":         "brain",
    "neurological":     "brain",
    "liver":            "liver",
    "hepatic":          "liver",
    "kidney":           "kidney",
    "kidneys":          "kidney",
    "renal":            "kidney",
    "stomach":          "stomach",
    "gastric":          "stomach",
    "colon":            "intestine",
    "intestine":        "intestine",
    "intestines":       "intestine",
    "bowel":            "intestine",
    "gut":              "intestine",
    "colorectal":       "intestine",
    "bladder":          "bladder",
    "urinary bladder":  "bladder",
    "pancreas":         "pancreas",
    "pancreatic":       "pancreas",
    "gallbladder":      "gallbladder",
    "gall bladder":     "gallbladder",
    "biliary":          "gallbladder",
    "spleen":           "spleen",
    "splenic":          "spleen",
}

_SEVERITY_ORDER: dict[str, int] = {"severe": 0, "moderate": 1, "mild": 2}


def _resolve_organ_key(name: str) -> str | None:
    return _ORGAN_KEY_MAP.get(name.lower().strip())


@app.post("/analyze-report", response_model=AnalyzeReportResponse, tags=["Reports"])
async def analyze_report(body: AnalyzeReportRequest) -> AnalyzeReportResponse:
    """
    Analyse raw medical report text with Gemini and return structured conditions.

    Returns a list of detected conditions with name, confidence, affected organs,
    severity, and description. Also resolves organ names to 3D mesh keys so the
    frontend can drive the viewer directly.

    No file upload required — send plain text in the JSON body.
    Requires GEMINI_API_KEY environment variable.
    """
    result = await analyse_text(body.text)

    # Resolve organ names → mesh keys, de-duped, most-severe condition first
    seen: set[str] = set()
    organ_keys: list[str] = []
    sorted_conditions = sorted(
        result["conditions"],
        key=lambda c: _SEVERITY_ORDER.get(c.get("severity", "mild"), 3),
    )
    for cond in sorted_conditions:
        for organ in cond.get("affected_organs", []):
            key = _resolve_organ_key(str(organ))
            if key and key not in seen:
                organ_keys.append(key)
                seen.add(key)

    conditions = [
        ConditionResult(
            name=c["name"],
            confidence=c["confidence"],
            affected_organs=c["affected_organs"],
            severity=c["severity"],
            description=c["description"],
        )
        for c in result["conditions"]
    ]

    return AnalyzeReportResponse(
        conditions=conditions,
        summary=result["summary"],
        risk_level=result["risk_level"],
        organ_keys=organ_keys,
    )


@app.get("/history/{user_id}", response_model=list[ReportSummaryResponse], tags=["Reports"])
async def get_history(user_id: str) -> list[ReportSummaryResponse]:
    """List all reports for a user, newest first."""
    async with get_db() as db:
        return await report_history.list_reports(db, user_id)


@app.get(
    "/history/{user_id}/{report_id}",
    response_model=ReportDetailResponse,
    tags=["Reports"],
)
async def get_report_detail(user_id: str, report_id: str) -> ReportDetailResponse:
    """Retrieve full report detail including the complete AI interpretation."""
    async with get_db() as db:
        result = await report_history.get_report(db, user_id, report_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Report not found.")
    return result


@app.delete("/history/{user_id}/{report_id}", tags=["Reports"])
async def delete_report(user_id: str, report_id: str) -> dict:
    """Delete a report from history."""
    async with get_db() as db:
        deleted = await report_history.delete_report(db, user_id, report_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Report not found.")
    return {"status": "deleted", "report_id": report_id}


@app.post("/guidance", tags=["Health"])
async def get_guidance(req: GuidanceRequest) -> dict:
    """
    Generate structured health guidance for a report using Gemini.
    Guidance is persisted to the report row so subsequent calls return the cached result.
    Requires GEMINI_API_KEY environment variable.
    """
    async with get_db() as db:
        detail = await report_history.get_report(db, req.user_id, req.report_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="Report not found.")

        # Return cached guidance if it already exists
        if detail.guidance:
            return detail.guidance

        # Generate fresh guidance — include user profile for personalization
        interp = detail.interpretation
        profile_dict = None
        try:
            profile = await profile_manager.get_profile(db, req.user_id)
            if profile:
                profile_dict = profile.model_dump()
        except Exception:
            pass

        guidance_dict = await generate_guidance(
            summary=interp.summary,
            findings=[f.model_dump() for f in interp.findings],
            affected_regions=interp.affected_regions,
            risk_level=interp.risk_level,
            user_profile=profile_dict,
        )

        # Persist guidance to the report row
        import json as _json
        await db.execute(
            "UPDATE reports SET guidance = ? WHERE id = ? AND user_id = ?",
            (_json.dumps(guidance_dict), req.report_id, req.user_id),
        )
        await db.commit()

    return guidance_dict


@app.get("/profile/{user_id}/scores", tags=["Profile"])
async def get_score_history(user_id: str) -> list:
    """
    Return health score history for a user (last 30 data points).
    Currently returns the current profile score with synthetic trend data
    for the sparkline chart.
    """
    import math
    import random

    async with get_db() as db:
        profile = await profile_manager.get_profile(db, user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found.")

    base_score = float(profile.health_score)
    # Generate 30-day synthetic history centered around the current score
    random.seed(user_id)  # deterministic per user
    history = []
    for i in range(30):
        day_offset = i - 29
        trend = base_score - 4 * math.exp(-i / 12)  # convergence curve
        noise = random.uniform(-2.5, 2.5)
        score = max(0.0, min(100.0, trend + noise))
        history.append({
            "day": day_offset,
            "score": round(score, 1),
        })
    # Last entry is always the true current score
    history[-1]["score"] = round(base_score, 1)
    return history


# ---------------------------------------------------------------------------
# AI Diagnostic Flow — Question engine + finalization
# ---------------------------------------------------------------------------

from pydantic import BaseModel
from typing import Optional as _Opt


class _DiagQuestionReq(BaseModel):
    user_id: _Opt[str] = None
    report_type: str
    summary: str
    findings: list[dict]
    regions: list[str]
    risk_level: str
    qa_history: list[dict] = []


class _DiagFinalizeReq(BaseModel):
    user_id: str
    initial_analysis: dict
    qa_history: list[dict] = []
    user_age: _Opt[int] = None
    user_gender: _Opt[str] = None
    report_id: _Opt[str] = None  # supply to enrich an existing report row


class _TriageReq(BaseModel):
    report_id: str
    user_id: str


class _KnowledgeGraphReq(BaseModel):
    conditions: list[dict]
    user_id: _Opt[str] = None


@app.post("/diagnostic/question", tags=["Diagnostic Flow"])
async def diagnostic_question(req: _DiagQuestionReq) -> dict:
    """
    Given initial report findings and Q&A history, returns the next AI question
    or {"done": true} when enough information has been gathered.
    Fetches user profile (if user_id provided) to personalize questions.
    """
    user_profile = None
    if req.user_id:
        async with get_db() as db:
            prof = await profile_manager.get_profile(db, req.user_id)
            if prof:
                user_profile = prof.model_dump()

    return await generate_next_question(
        report_type=req.report_type,
        summary=req.summary,
        findings=req.findings,
        regions=req.regions,
        risk_level=req.risk_level,
        qa_history=req.qa_history,
        user_profile=user_profile,
    )


@app.post("/diagnostic/finalize", tags=["Diagnostic Flow"])
async def diagnostic_finalize(req: _DiagFinalizeReq) -> dict:
    """
    Finalizes the diagnostic session: generates a comprehensive AI report from
    the initial analysis + full Q&A history, saves to care_reports, runs AI
    triage, builds the medical knowledge graph, and returns the full enriched
    report with recommended doctors.
    """
    import json as _json
    import uuid as _uuid
    from datetime import datetime, timezone

    # ── 1. Fetch user profile for personalization ─────────────────────────
    user_profile = None
    async with get_db() as db:
        prof = await profile_manager.get_profile(db, req.user_id)
        if prof:
            user_profile = prof.model_dump()

    # ── 2. Finalize diagnosis (with profile injected) ─────────────────────
    result = await finalize_diagnostic(
        req.initial_analysis,
        req.qa_history,
        user_profile=user_profile,
    )

    # ── 3. Run triage ─────────────────────────────────────────────────────
    triage_result = await run_triage(
        risk_level=result["risk_level"],
        red_flags=result["red_flags"],
        probable_conditions=result["probable_conditions"],
        summary=req.initial_analysis.get("summary", ""),
        findings=req.initial_analysis.get("findings", []),
        user_profile=user_profile,
    )

    # ── 4. Build knowledge graph ──────────────────────────────────────────
    knowledge_graph = await build_knowledge_graph(result["probable_conditions"])

    personalized_insights = result.get("personalized_insights", [])

    # ── 5. Persist to care_reports table ─────────────────────────────────
    report_id = str(_uuid.uuid4())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    symptoms = [f.get("text", "") for f in req.initial_analysis.get("findings", [])]

    # Build enriched ai_raw_response with all new data
    enriched_response = {
        "qa_history": req.qa_history,
        "triage": triage_result,
        "knowledge_graph": knowledge_graph,
        "personalized_insights": personalized_insights,
    }

    async with get_db() as db:
        await db.execute(
            """INSERT INTO care_reports
               (id, user_id, created_at, symptoms, user_age, user_gender,
                probable_conditions, affected_organs, risk_level, red_flags,
                next_steps, treatment_suggestions, recommended_specialization,
                ai_raw_response)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                report_id,
                req.user_id,
                now,
                _json.dumps(symptoms),
                req.user_age,
                req.user_gender,
                _json.dumps(result["probable_conditions"]),
                _json.dumps(result["affected_organs"]),
                result["risk_level"],
                _json.dumps(result["red_flags"]),
                _json.dumps(result["next_steps"]),
                _json.dumps(result["treatment_suggestions"]),
                result["recommended_specialization"],
                _json.dumps(enriched_response),
            ),
        )
        await db.commit()

        # ── 6. Enrich the source report row (if report_id provided) ───────
        if req.report_id:
            await _report_history.update_report_enrichment(
                db,
                report_id=req.report_id,
                triage_data=triage_result,
                knowledge_graph_data=knowledge_graph,
                personalized_insights=personalized_insights,
                diagnosis_data=result,
            )

        # Get recommended doctors by specialization
        spec = result["recommended_specialization"]
        doctors_raw = await get_recommended_doctors(
            db,
            symptoms=symptoms,
            conditions=[c["name"] for c in result["probable_conditions"]],
            specialization=spec,
            max_fee=5000,
            mode="all",
            limit=4,
        )

    return {
        "report_id": report_id,
        "report": result,
        "triage": triage_result,
        "knowledge_graph": knowledge_graph,
        "personalized_insights": personalized_insights,
        "recommended_doctors": doctors_raw,
    }


@app.post("/triage", tags=["Diagnostic Flow"])
async def triage_report(req: _TriageReq) -> dict:
    """
    Run AI triage for an already-stored report.
    Fetches the report + user profile from the database and returns a
    TriageResult. Also persists the triage result back to the report row.
    """
    async with get_db() as db:
        report = await _report_history.get_report(db, req.user_id, req.report_id)
        if report is None:
            raise HTTPException(status_code=404, detail="Report not found.")
        prof = await profile_manager.get_profile(db, req.user_id)
        user_profile = prof.model_dump() if prof else None

    interp = report.interpretation
    findings = [f.model_dump() for f in interp.findings]

    triage_result = await run_triage(
        risk_level=interp.risk_level,
        red_flags=[],
        probable_conditions=[],
        summary=interp.summary,
        findings=findings,
        user_profile=user_profile,
    )

    # Persist back
    async with get_db() as db:
        await _report_history.update_report_enrichment(
            db,
            report_id=req.report_id,
            triage_data=triage_result,
        )

    return triage_result


@app.post("/knowledge-graph", tags=["Diagnostic Flow"])
async def knowledge_graph_endpoint(req: _KnowledgeGraphReq) -> dict:
    """
    Build a medical knowledge graph for the supplied conditions list.
    Returns nodes, edges, and the primary condition.
    """
    return await build_knowledge_graph(req.conditions)


# ---------------------------------------------------------------------------
# Phase 4 — Brain Render (3D Visualization)
# ---------------------------------------------------------------------------

@app.get("/render/brain/{subject_id}", tags=["Visualization"],
         responses={200: {"content": {"image/png": {}}}})
async def render_brain(subject_id: str, mode: str = "standard") -> StreamingResponse:
    """
    Return a PNG render of the brain segmentation for the given subject.

    Serves a cached render if available at outputs/analytics/{subject_id}/render_combined.png.
    Falls back to on-the-fly rendering via PyVista NeuroRenderer if a segmentation.npy exists.
    Returns 404 when no data is found for the subject.
    """
    import io

    # Sanitise subject_id to prevent path traversal
    safe_id = Path(subject_id).name
    outputs_dir = Path("outputs/analytics") / safe_id

    # Fast path — serve pre-rendered PNG
    cached_png = outputs_dir / "render_combined.png"
    if cached_png.exists():
        return StreamingResponse(cached_png.open("rb"), media_type="image/png")

    # On-the-fly render from saved segmentation
    seg_path = outputs_dir / "segmentation.npy"
    if not seg_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"No segmentation data found for subject '{safe_id}'.",
        )

    try:
        from src.ui.pyvista_renderer import NeuroRenderer
        seg = np.load(str(seg_path))
        renderer = NeuroRenderer()
        png_bytes: bytes = renderer.render_combined(seg)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Rendering failed for subject '{safe_id}': {e}",
        )

    return StreamingResponse(io.BytesIO(png_bytes), media_type="image/png")
