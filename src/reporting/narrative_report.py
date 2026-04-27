"""
narrative_report.py — AI Clinical Impression Generator for Anatom AI.

Renders a structured 3–5 paragraph clinical narrative from volumetric,
radiomic, and longitudinal data using a Jinja2 template.

The output is plain text suitable for:
  • Displaying in the Streamlit UI (inside a styled monospace panel)
  • Embedding in the PDF report via PDFReportBuilder._narrative_section()
  • Attaching to DICOM SR documents

Usage
-----
    from src.reporting.narrative_report import NarrativeReportBuilder
    from src.analytics.volumetrics import VolumetricResult

    builder = NarrativeReportBuilder()
    text = builder.render(
        vol_result=result,
        radiomic_features=features,   # optional
        longitudinal_report=long_rep, # optional
        risk_estimate=risk,           # optional
        subject_id="BraTS-001",
        scan_date="2026-04-14",
        institution="Anatom AI",
    )
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_TEMPLATE_PATH = Path(__file__).parent.parent.parent / "templates" / "narrative_report.j2"


class NarrativeReportBuilder:
    """
    Render an AI clinical narrative from Anatom AI analytics results.

    Requires `jinja2` (listed in requirements.txt). Falls back to a minimal
    plaintext summary if Jinja2 is unavailable.
    """

    def __init__(self, template_path: Optional[Path] = None) -> None:
        self._template_path = Path(template_path or _TEMPLATE_PATH)
        self._jinja_available = False
        try:
            from jinja2 import Environment, FileSystemLoader  # noqa: F401
            self._jinja_available = True
        except ImportError:
            logger.warning("Jinja2 not installed — using fallback plaintext narrative.")

    def render(
        self,
        vol_result,
        subject_id: str = "Unknown",
        scan_date: str = "",
        institution: str = "Anatom AI",
        radiomic_features: Optional[Dict] = None,
        longitudinal_report=None,
        risk_estimate=None,
    ) -> str:
        """
        Render the clinical narrative.

        Parameters
        ----------
        vol_result         : VolumetricResult
        subject_id         : patient / subject identifier
        scan_date          : ISO date string
        institution        : reporting institution name
        radiomic_features  : dict from RadiomicsExtractor.extract() (optional)
        longitudinal_report: LongitudinalReport (optional)
        risk_estimate      : RiskEstimate from RecurrenceRiskEstimator (optional)

        Returns
        -------
        str — the rendered narrative text.
        """
        ctx = self._build_context(
            vol_result, subject_id, scan_date, institution,
            radiomic_features, longitudinal_report, risk_estimate,
        )

        if self._jinja_available:
            return self._render_jinja(ctx)
        return self._render_fallback(ctx)

    # ── Context builder ───────────────────────────────────────────────────────

    def _build_context(
        self, vol_result, subject_id, scan_date, institution,
        radiomic_features, longitudinal_report, risk_estimate,
    ) -> dict:
        vols = vol_result.volumes_mm3
        ctx: dict = {
            "subject_id":    subject_id,
            "scan_date":     scan_date or "N/A",
            "institution":   institution,
            "wt_mm3":        vol_result.wt_mm3,
            "tc_mm3":        vol_result.tc_mm3,
            "et_mm3":        vol_result.et_mm3,
            "ncr_mm3":       vols.get("NCR", 0.0),
            "ed_mm3":        vols.get("ED",  0.0),
            "rano_category": None,
            "rano_pct_change": None,
            "days_elapsed":  None,
            "risk_score":    None,
            "risk_interp":   None,
            "top_factors":   None,
            "sphericity":    None,
            "has_longitudinal": False,
            "has_risk":      False,
            "has_radiomics": False,
        }

        if longitudinal_report is not None:
            ctx["has_longitudinal"] = True
            ctx["rano_category"]    = longitudinal_report.rano_category
            ctx["rano_pct_change"]  = longitudinal_report.rano_pct_change
            ctx["days_elapsed"]     = longitudinal_report.days_elapsed

        if risk_estimate is not None:
            ctx["has_risk"]      = True
            ctx["risk_score"]    = risk_estimate.score
            ctx["risk_interp"]   = risk_estimate.interpretation
            ctx["top_factors"]   = risk_estimate.top_factors

        if radiomic_features is not None:
            ctx["has_radiomics"] = True
            et_feats = radiomic_features.get("ET", {})
            sph = et_feats.get("sphericity", 0.0)
            if sph > 0:
                ctx["sphericity"] = sph

        # Section numbering for the Impression section
        section_num = 4
        if ctx["has_radiomics"]:
            section_num += 1
        if ctx["has_risk"]:
            section_num += 1
        ctx["loop_section"] = section_num

        return ctx

    # ── Jinja2 renderer ───────────────────────────────────────────────────────

    def _render_jinja(self, ctx: dict) -> str:
        from jinja2 import Environment, FileSystemLoader, select_autoescape

        env = Environment(
            loader=FileSystemLoader(str(self._template_path.parent)),
            autoescape=select_autoescape([]),   # plain text — no HTML escaping
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True,
        )
        template = env.get_template(self._template_path.name)
        return template.render(**ctx)

    # ── Fallback plaintext renderer ───────────────────────────────────────────

    def _render_fallback(self, ctx: dict) -> str:
        lines = [
            "ANATOM AI — AI CLINICAL IMPRESSION",
            f"Subject: {ctx['subject_id']}   Date: {ctx['scan_date']}",
            "",
            "FINDINGS SUMMARY",
            f"  Whole Tumour (WT): {ctx['wt_mm3']:,.1f} mm³",
            f"  Tumour Core (TC):  {ctx['tc_mm3']:,.1f} mm³",
            f"  Enhancing (ET):    {ctx['et_mm3']:,.1f} mm³",
            f"  Necrotic Core:     {ctx['ncr_mm3']:,.1f} mm³",
            f"  Edema (ED):        {ctx['ed_mm3']:,.1f} mm³",
        ]
        if ctx["has_longitudinal"] and ctx["rano_category"]:
            lines += ["", f"RANO Response: {ctx['rano_category']}"]
            if ctx["rano_pct_change"] is not None:
                lines.append(f"  Volume change: {ctx['rano_pct_change']:+.1f}%")
        if ctx["has_risk"]:
            lines += ["", f"Recurrence Risk: {ctx['risk_score']}/100 — {ctx['risk_interp']}"]
        lines += ["", "DISCLAIMER: Investigational use only. Not for clinical decisions."]
        return "\n".join(lines)
