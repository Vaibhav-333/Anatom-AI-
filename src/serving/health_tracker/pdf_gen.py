"""
pdf_gen.py — ReportLab PDF generator for Health Tracker reports.

Mirrors the colour palette and structure of care_connect/pdf_gen.py.
"""
from __future__ import annotations

import io
from datetime import datetime
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Brand colours ─────────────────────────────────────────────────────────────
BRAND_DARK  = colors.HexColor("#0A0F1E")
BRAND_NAVY  = colors.HexColor("#0D1627")
BRAND_CYAN  = colors.HexColor("#00D4FF")
BRAND_GREEN = colors.HexColor("#00FF88")
BRAND_AMBER = colors.HexColor("#FFB800")
BRAND_RED   = colors.HexColor("#FF3B3B")
BRAND_GRAY  = colors.HexColor("#8899AA")
WHITE       = colors.white


def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"],
                                fontSize=20, textColor=BRAND_CYAN, spaceAfter=4),
        "subtitle": ParagraphStyle("subtitle", parent=base["Normal"],
                                   fontSize=10, textColor=BRAND_GRAY, spaceAfter=12),
        "heading": ParagraphStyle("heading", parent=base["Heading2"],
                                  fontSize=13, textColor=BRAND_CYAN, spaceBefore=14, spaceAfter=6),
        "body": ParagraphStyle("body", parent=base["Normal"],
                               fontSize=9, textColor=colors.black, spaceAfter=4),
        "bullet": ParagraphStyle("bullet", parent=base["Normal"],
                                 fontSize=9, textColor=colors.black,
                                 leftIndent=12, spaceAfter=3),
        "disclaimer": ParagraphStyle("disclaimer", parent=base["Normal"],
                                     fontSize=7, textColor=BRAND_GRAY,
                                     spaceBefore=20, spaceAfter=0),
    }


def _section_table(rows: list[list], col_widths: list[float]) -> Table:
    t = Table(rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), BRAND_CYAN),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F8FF")]),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, BRAND_GRAY),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def generate_health_tracker_pdf(
    user_id: str,
    symptom_logs: list[dict],
    trend_data: list[dict],
    adherence_stats: list[dict],
    insights: dict,
    date_range: tuple[str, str],
) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
    )
    s = _styles()
    story = []
    W = A4[0] - 36 * mm  # usable width

    # ── Header ────────────────────────────────────────────────────────────────
    story.append(Paragraph("Anatom AI | Health Symptom Report", s["title"]))
    story.append(Paragraph(
        f"User: {user_id}  &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"Period: {date_range[0]} — {date_range[1]}  &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        s["subtitle"],
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=BRAND_CYAN))
    story.append(Spacer(1, 8))

    # ── Health Summary ────────────────────────────────────────────────────────
    story.append(Paragraph("Health Summary", s["heading"]))
    weekly_score = insights.get("weekly_score", 0)
    trend = insights.get("trend", "stable")
    trend_colour = {"improving": "green", "worsening": "red"}.get(trend, "gray")
    summary_rows = [
        ["Metric", "Value"],
        ["Weekly Health Score", f"{weekly_score}/100"],
        ["Overall Trend", trend.capitalize()],
        ["Total Log Entries", str(len(symptom_logs))],
        ["Date Range", f"{date_range[0]} to {date_range[1]}"],
    ]
    story.append(_section_table(summary_rows, [W * 0.5, W * 0.5]))
    story.append(Spacer(1, 10))

    # ── Symptom Overview ──────────────────────────────────────────────────────
    if trend_data:
        story.append(Paragraph("Symptom Trends (Daily Averages)", s["heading"]))
        trend_rows = [["Date", "Avg Pain", "Avg Mood", "Avg Sleep (h)", "Entries"]]
        for pt in trend_data[-14:]:
            trend_rows.append([
                pt.get("date", ""),
                f"{pt['avg_pain']:.1f}" if pt.get("avg_pain") is not None else "—",
                f"{pt['avg_mood']:.1f}" if pt.get("avg_mood") is not None else "—",
                f"{pt['avg_sleep']:.1f}" if pt.get("avg_sleep") is not None else "—",
                str(pt.get("entry_count", 0)),
            ])
        story.append(_section_table(trend_rows, [W * 0.22, W * 0.18, W * 0.18, W * 0.22, W * 0.2]))
        story.append(Spacer(1, 10))

    # ── Medication Adherence ──────────────────────────────────────────────────
    if adherence_stats:
        story.append(Paragraph("Medication Adherence", s["heading"]))
        adh_rows = [["Medication", "Dosage", "Total Doses", "Taken", "Missed", "Adherence %"]]
        for stat in adherence_stats:
            adh_rows.append([
                stat.get("medication_name", ""),
                "",
                str(stat.get("total_doses", 0)),
                str(stat.get("taken", 0)),
                str(stat.get("missed", 0)),
                f"{stat.get('adherence_pct', 0):.0f}%",
            ])
        story.append(_section_table(adh_rows, [W*0.28, W*0.12, W*0.15, W*0.12, W*0.12, W*0.21]))
        story.append(Spacer(1, 10))

    # ── AI Insights ───────────────────────────────────────────────────────────
    story.append(Paragraph("AI Health Insights", s["heading"]))
    alerts = insights.get("alerts", [])
    if alerts:
        story.append(Paragraph("<b>Alerts:</b>", s["body"]))
        for alert in alerts:
            sev = alert.get("severity", "info")
            col = {"critical": "red", "warning": "orange"}.get(sev, "gray")
            story.append(Paragraph(
                f'<font color="{col}">▲</font> <b>{alert.get("title","")}</b>: {alert.get("message","")}',
                s["bullet"],
            ))
    suggestions = insights.get("suggestions", [])
    if suggestions:
        story.append(Spacer(1, 6))
        story.append(Paragraph("<b>Recommendations:</b>", s["body"]))
        for sug in suggestions:
            story.append(Paragraph(f"• {sug}", s["bullet"]))
    story.append(Spacer(1, 10))

    # ── Disclaimer ────────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_GRAY))
    story.append(Paragraph(
        "⚠ DISCLAIMER: This report is generated by an AI system for informational purposes only. "
        "It does not constitute medical advice, diagnosis, or treatment. "
        "Always consult a qualified healthcare professional for medical decisions.",
        s["disclaimer"],
    ))

    doc.build(story)
    return buf.getvalue()
