"""CareConnect AI — PDF report generation using ReportLab + QR code."""
from __future__ import annotations

import io
from datetime import datetime
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Risk level → color mapping
RISK_COLORS = {
    "low": colors.HexColor("#00C896"),
    "medium": colors.HexColor("#F59E0B"),
    "high": colors.HexColor("#EF4444"),
    "critical": colors.HexColor("#7C3AED"),
}

BRAND_CYAN = colors.HexColor("#22D3EE")
BRAND_DARK = colors.HexColor("#0F172A")
BRAND_NAVY = colors.HexColor("#1E293B")
BRAND_GRAY = colors.HexColor("#94A3B8")
WHITE = colors.white


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", fontSize=22, textColor=BRAND_CYAN, fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=4),
        "subtitle": ParagraphStyle("subtitle", fontSize=10, textColor=BRAND_GRAY, fontName="Helvetica", alignment=TA_CENTER, spaceAfter=16),
        "section": ParagraphStyle("section", fontSize=12, textColor=WHITE, fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6),
        "body": ParagraphStyle("body", fontSize=9, textColor=colors.HexColor("#CBD5E1"), fontName="Helvetica", spaceAfter=4, leading=14),
        "bullet": ParagraphStyle("bullet", fontSize=9, textColor=colors.HexColor("#CBD5E1"), fontName="Helvetica", leftIndent=12, spaceAfter=3, bulletIndent=0, leading=13),
        "label": ParagraphStyle("label", fontSize=8, textColor=BRAND_GRAY, fontName="Helvetica"),
        "value": ParagraphStyle("value", fontSize=9, textColor=WHITE, fontName="Helvetica-Bold"),
        "disclaimer": ParagraphStyle("disclaimer", fontSize=7.5, textColor=BRAND_GRAY, fontName="Helvetica-Oblique", alignment=TA_CENTER, leading=11),
        "red_flag": ParagraphStyle("red_flag", fontSize=9, textColor=colors.HexColor("#FCA5A5"), fontName="Helvetica-Bold", spaceAfter=3),
    }


def _qr_flowable(url: str, size: float = 28 * mm):
    """Generate a QR code Image flowable."""
    try:
        import qrcode
        from reportlab.platypus import Image as RLImage

        qr = qrcode.QRCode(box_size=4, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return RLImage(buf, width=size, height=size)
    except ImportError:
        return Spacer(1, size)


def generate_care_report_pdf(
    report: dict[str, Any],
    doctors: list[dict[str, Any]],
    share_url: str | None = None,
) -> bytes:
    """Build and return PDF bytes for a CareConnect report."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
    )

    s = _styles()
    story = []

    # ── Header ──────────────────────────────────────────────
    story.append(Paragraph("ANATOM-AI", s["title"]))
    story.append(Paragraph("CareConnect AI Medical Report", s["subtitle"]))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BRAND_CYAN, spaceAfter=8))

    # ── Report meta ─────────────────────────────────────────
    created = report.get("created_at", datetime.now().isoformat())[:10]
    report_id = report.get("id", "N/A")
    meta_data = [
        [Paragraph("Report ID", s["label"]), Paragraph(report_id, s["value"]),
         Paragraph("Date", s["label"]), Paragraph(created, s["value"])],
        [Paragraph("Age", s["label"]), Paragraph(str(report.get("user_age") or "—"), s["value"]),
         Paragraph("Gender", s["label"]), Paragraph(str(report.get("user_gender") or "—"), s["value"])],
        [Paragraph("Severity", s["label"]), Paragraph(str(report.get("severity", "—")).capitalize(), s["value"]),
         Paragraph("Duration", s["label"]), Paragraph(f"{report.get('duration_days', '—')} day(s)", s["value"])],
    ]
    meta_table = Table(meta_data, colWidths=[30 * mm, 55 * mm, 30 * mm, 55 * mm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_NAVY),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [BRAND_NAVY, colors.HexColor("#151E2D")]),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#334155")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("ROUNDEDCORNERS", [3, 3, 3, 3]),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # ── Symptoms ────────────────────────────────────────────
    story.append(Paragraph("Reported Symptoms", s["section"]))
    symptoms = report.get("symptoms", [])
    for sym in symptoms:
        story.append(Paragraph(f"• {sym}", s["bullet"]))
    history = report.get("medical_history", [])
    if history:
        story.append(Paragraph("Medical History", s["section"]))
        for h in history:
            story.append(Paragraph(f"• {h}", s["bullet"]))

    # ── AI Analysis — Probable Conditions ───────────────────
    story.append(Paragraph("AI Analysis — Probable Conditions", s["section"]))
    conditions = report.get("probable_conditions", [])
    if conditions:
        cond_data = [[
            Paragraph("Condition", ParagraphStyle("h", fontSize=9, textColor=BRAND_CYAN, fontName="Helvetica-Bold")),
            Paragraph("Confidence", ParagraphStyle("h", fontSize=9, textColor=BRAND_CYAN, fontName="Helvetica-Bold")),
            Paragraph("Description", ParagraphStyle("h", fontSize=9, textColor=BRAND_CYAN, fontName="Helvetica-Bold")),
        ]]
        for cond in conditions:
            pct = cond.get("confidence_pct", 0)
            bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
            cond_data.append([
                Paragraph(cond.get("name", "—"), s["value"]),
                Paragraph(f"{pct}%  {bar}", s["body"]),
                Paragraph(cond.get("description", "—"), s["body"]),
            ])
        cond_table = Table(cond_data, colWidths=[48 * mm, 38 * mm, 84 * mm])
        cond_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F2744")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [BRAND_NAVY, colors.HexColor("#151E2D")]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#334155")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(cond_table)
    story.append(Spacer(1, 6))

    # ── Risk Level ──────────────────────────────────────────
    risk = report.get("risk_level", "low")
    risk_color = RISK_COLORS.get(risk, BRAND_GRAY)
    risk_label_style = ParagraphStyle("risk", fontSize=11, textColor=risk_color, fontName="Helvetica-Bold", alignment=TA_CENTER)
    risk_table = Table([[Paragraph(f"Risk Level: {risk.upper()}", risk_label_style)]], colWidths=["100%"])
    risk_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("BOX", (0, 0), (-1, -1), 1.5, risk_color),
    ]))
    story.append(risk_table)
    story.append(Spacer(1, 8))

    # ── Red Flags ───────────────────────────────────────────
    red_flags = report.get("red_flags", [])
    if red_flags:
        story.append(Paragraph("⚠ Red Flag Warnings", ParagraphStyle("rf_title", fontSize=11, textColor=colors.HexColor("#EF4444"), fontName="Helvetica-Bold", spaceAfter=4)))
        for flag in red_flags:
            story.append(Paragraph(f"⚠ {flag}", s["red_flag"]))
        story.append(Spacer(1, 4))

    # ── Next Steps ──────────────────────────────────────────
    story.append(Paragraph("Recommended Next Steps", s["section"]))
    for i, step in enumerate(report.get("next_steps", []), 1):
        story.append(Paragraph(f"{i}. {step}", s["bullet"]))

    # ── Treatment Suggestions ───────────────────────────────
    story.append(Paragraph("General Treatment Approach", s["section"]))
    for sug in report.get("treatment_suggestions", []):
        story.append(Paragraph(f"• {sug}", s["bullet"]))
    story.append(Paragraph(
        "⚠ DISCLAIMER: The above are general wellness suggestions only and do NOT constitute medical prescriptions or clinical advice.",
        ParagraphStyle("disc2", fontSize=8, textColor=colors.HexColor("#F59E0B"), fontName="Helvetica-Oblique", spaceBefore=4),
    ))

    # ── Suggested Doctors ───────────────────────────────────
    if doctors:
        story.append(Paragraph("Suggested Specialists", s["section"]))
        top3 = doctors[:3]
        for doc in top3:
            doc_data = [
                [Paragraph(doc.get("name", ""), ParagraphStyle("dn", fontSize=10, textColor=BRAND_CYAN, fontName="Helvetica-Bold")),
                 Paragraph(f"⭐ {doc.get('rating', 4.0)}", s["value"])],
                [Paragraph(f"{doc.get('specialization', '')} | {doc.get('experience_years', 0)} yrs exp", s["body"]),
                 Paragraph(f"₹{doc.get('consultation_fee', 0)}", s["value"])],
                [Paragraph(doc.get("hospital", ""), s["body"]),
                 Paragraph(doc.get("mode", "").capitalize(), s["label"])],
            ]
            doc_table = Table(doc_data, colWidths=[130 * mm, 40 * mm])
            doc_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), BRAND_NAVY),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#334155")),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(doc_table)
            story.append(Spacer(1, 4))

    # ── QR Code ─────────────────────────────────────────────
    qr_url = share_url or f"https://anatom.ai/care-connect/report/{report.get('id', '')}"
    qr_table = Table(
        [[_qr_flowable(qr_url), Paragraph(f"Scan to view this report online\n{qr_url}", ParagraphStyle("qr", fontSize=8, textColor=BRAND_GRAY, fontName="Helvetica", leading=12))]],
        colWidths=[32 * mm, 138 * mm],
    )
    qr_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (0, 0), (-1, -1), BRAND_NAVY),
    ]))
    story.append(Spacer(1, 8))
    story.append(qr_table)

    # ── Footer Disclaimer ───────────────────────────────────
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#334155")))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "This report was generated by Anatom-AI CareConnect and is intended for informational purposes only. "
        "It does not replace professional medical diagnosis, treatment, or advice. "
        "Always consult a qualified healthcare professional before making any health decisions.",
        s["disclaimer"],
    ))
    story.append(Paragraph("© Anatom-AI | anatom.ai", s["disclaimer"]))

    # ── Background canvas ───────────────────────────────────
    def _bg(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(BRAND_DARK)
        canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
        canvas.restoreState()

    doc.build(story, onFirstPage=_bg, onLaterPages=_bg)
    return buf.getvalue()
