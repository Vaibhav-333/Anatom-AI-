"""
report_history.py — SQLite CRUD for AI-interpreted medical reports.

Each report stores the full Gemini interpretation as a JSON blob so that
the history and results pages can render it without re-calling the AI.
File hashes enable deduplication: re-uploading the same file returns the
cached result instantly.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

import aiosqlite

from src.serving.schemas import (
    AnatomicalMappingItem,
    FindingSchema,
    InterpretResponse,
    ReportDetailResponse,
    ReportSummaryResponse,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _safe_col(row: aiosqlite.Row, col: str, default=None):
    """Safely read a column that may not exist in older DB rows."""
    try:
        return row[col]
    except (IndexError, KeyError):
        return default


def _row_to_summary(row: aiosqlite.Row) -> ReportSummaryResponse:
    interp_raw = json.loads(row["interpretation"] or "{}")
    summary_text = interp_raw.get("summary", "")
    snippet = summary_text[:160] + "…" if len(summary_text) > 160 else summary_text
    return ReportSummaryResponse(
        id=row["id"],
        user_id=row["user_id"],
        file_name=row["file_name"],
        file_type=row["file_type"],
        report_type=row["report_type"],
        risk_level=row["risk_level"],
        upload_date=row["upload_date"],
        summary_snippet=snippet,
        affected_regions=json.loads(row["affected_regions"] or "[]"),
        triage_level=_safe_col(row, "triage_level"),
    )


def _row_to_detail(row: aiosqlite.Row) -> ReportDetailResponse:
    summary = _row_to_summary(row)
    interp_raw = json.loads(row["interpretation"] or "{}")
    findings = [
        FindingSchema(
            text=f.get("text", ""),
            severity=f.get("severity", "normal"),
            value=f.get("value"),
            unit=f.get("unit"),
            reference_range=f.get("reference_range"),
        )
        for f in interp_raw.get("findings", [])
    ]
    anat_mapping = [
        AnatomicalMappingItem(
            region_id=m.get("region_id", ""),
            finding_index=int(m.get("finding_index", 0)),
            camera_focus=m.get("camera_focus", [0.0, 0.5, 0.0]),
            severity=m.get("severity", "normal"),
        )
        for m in interp_raw.get("anatomical_mapping", [])
        if isinstance(m, dict)
    ]
    interpretation = InterpretResponse(
        report_id=row["id"],
        summary=interp_raw.get("summary", ""),
        findings=findings,
        affected_regions=interp_raw.get("affected_regions", []),
        confidence=float(interp_raw.get("confidence", 0.0)),
        reasoning=interp_raw.get("reasoning", ""),
        report_type=interp_raw.get("report_type", row["report_type"]),
        risk_level=interp_raw.get("risk_level", row["risk_level"]),
        anatomical_mapping=anat_mapping,
    )
    guidance_raw = row["guidance"]
    guidance = json.loads(guidance_raw) if guidance_raw else None

    triage_raw = _safe_col(row, "triage_data")
    triage = json.loads(triage_raw) if triage_raw else None

    kg_raw = _safe_col(row, "knowledge_graph_data")
    knowledge_graph = json.loads(kg_raw) if kg_raw else None

    pi_raw = _safe_col(row, "personalized_insights")
    personalized_insights = json.loads(pi_raw) if pi_raw else None

    dd_raw = _safe_col(row, "diagnosis_data")
    diagnosis_data = json.loads(dd_raw) if dd_raw else None

    return ReportDetailResponse(
        **summary.model_dump(),
        interpretation=interpretation,
        guidance=guidance,
        triage=triage,
        knowledge_graph=knowledge_graph,
        personalized_insights=personalized_insights,
        diagnosis_data=diagnosis_data,
    )


# ---------------------------------------------------------------------------
# Public CRUD
# ---------------------------------------------------------------------------

async def save_report(
    db: aiosqlite.Connection,
    user_id: str,
    file_name: str,
    file_type: str,
    interp_dict: dict,
    file_hash: str,
) -> str:
    """Persist a new report row and return its UUID."""
    report_id = str(uuid.uuid4())
    now = _now_iso()
    affected = json.dumps(interp_dict.get("affected_regions", []))
    risk = interp_dict.get("risk_level", "low")
    report_type = interp_dict.get("report_type", "unknown")

    await db.execute(
        """
        INSERT INTO reports
            (id, user_id, file_name, file_type, report_type,
             interpretation, affected_regions, risk_level, file_hash, upload_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            report_id, user_id, file_name, file_type, report_type,
            json.dumps(interp_dict), affected, risk, file_hash, now,
        ),
    )
    await db.commit()
    return report_id


async def update_report_enrichment(
    db: aiosqlite.Connection,
    report_id: str,
    triage_data: dict | None = None,
    knowledge_graph_data: dict | None = None,
    personalized_insights: list | None = None,
    diagnosis_data: dict | None = None,
) -> None:
    """
    Persist triage, knowledge graph, personalized insights, and full diagnosis data
    for an existing report. Called after the diagnostic finalization pipeline completes.
    """
    triage_level = triage_data.get("level") if triage_data else None
    await db.execute(
        """
        UPDATE reports
        SET triage_data = ?,
            knowledge_graph_data = ?,
            personalized_insights = ?,
            triage_level = ?,
            diagnosis_data = ?
        WHERE id = ?
        """,
        (
            json.dumps(triage_data) if triage_data is not None else None,
            json.dumps(knowledge_graph_data) if knowledge_graph_data is not None else None,
            json.dumps(personalized_insights) if personalized_insights is not None else "[]",
            triage_level,
            json.dumps(diagnosis_data) if diagnosis_data is not None else None,
            report_id,
        ),
    )
    await db.commit()


async def find_by_hash(
    db: aiosqlite.Connection,
    file_hash: str,
) -> Optional[dict]:
    """Return the stored interpretation dict for a given file hash, or None."""
    async with db.execute(
        "SELECT interpretation FROM reports WHERE file_hash = ? LIMIT 1", (file_hash,)
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        return None
    return json.loads(row[0] or "{}")


async def list_reports(
    db: aiosqlite.Connection,
    user_id: str,
) -> list[ReportSummaryResponse]:
    """Return all reports for a user, newest first."""
    async with db.execute(
        "SELECT * FROM reports WHERE user_id = ? ORDER BY upload_date DESC",
        (user_id,),
    ) as cur:
        rows = await cur.fetchall()
    return [_row_to_summary(r) for r in rows]


async def get_report(
    db: aiosqlite.Connection,
    user_id: str,
    report_id: str,
) -> Optional[ReportDetailResponse]:
    """Return full report detail, or None if not found / wrong user."""
    async with db.execute(
        "SELECT * FROM reports WHERE id = ? AND user_id = ?",
        (report_id, user_id),
    ) as cur:
        row = await cur.fetchone()
    if row is None:
        return None
    return _row_to_detail(row)


async def delete_report(
    db: aiosqlite.Connection,
    user_id: str,
    report_id: str,
) -> bool:
    """Delete a report. Returns True if it existed."""
    async with db.execute(
        "SELECT id FROM reports WHERE id = ? AND user_id = ?",
        (report_id, user_id),
    ) as cur:
        found = await cur.fetchone()
    if not found:
        return False
    await db.execute(
        "DELETE FROM reports WHERE id = ? AND user_id = ?",
        (report_id, user_id),
    )
    await db.commit()
    return True
