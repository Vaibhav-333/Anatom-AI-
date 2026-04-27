"""
recurrence_risk.py — Heuristic Recurrence Risk Estimation for Glioma.

Computes a 0–100 recurrence risk score from volumetric and radiomic features
using a clinically-grounded weighted model.  This is a research prototype —
NOT validated for clinical use.

Scoring is based on published glioma prognostic factors:
  • ET volume:           larger enhancing core → higher risk
  • Sphericity:         irregular / non-spherical boundary → infiltrative → higher risk
  • ED / WT ratio:      high edema fraction → active invasion → higher risk
  • TC / WT ratio:      large necrotic/enhancing core → aggressive phenotype
  • RANO category:      PD = very high, SD = moderate, PR/CR = lower risk

Feature contributions are returned as SHAP-style additive attribution so the
UI can display "why" the model flagged a case.

Usage
-----
    from src.analytics.recurrence_risk import RecurrenceRiskEstimator
    from src.analytics.volumetrics import VolumetricResult

    estimator = RecurrenceRiskEstimator()
    risk = estimator.estimate(vol_result, radiomic_features, rano_category="SD")
    print(risk.score)           # 0–100 int
    print(risk.contributions)   # list of (feature, delta, direction)
    print(risk.interpretation)  # "Moderate" | "High" | "Very High" | "Low"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from src.analytics.volumetrics import VolumetricResult


@dataclass
class RiskContribution:
    """A single feature's additive contribution to the risk score."""
    feature: str          # human-readable name
    value: float          # raw feature value
    delta: float          # risk score delta (+/-)
    direction: str        # "increasing" | "decreasing"
    description: str      # plain-English explanation


@dataclass
class RiskEstimate:
    """Full recurrence risk estimate for one subject."""
    score: int                                   # 0–100
    interpretation: str                          # Low / Moderate / High / Very High
    contributions: List[RiskContribution] = field(default_factory=list)
    top_factors: List[str]               = field(default_factory=list)
    disclaimer: str = (
        "RESEARCH PROTOTYPE — Not validated for clinical decision-making. "
        "This score must not be used to guide treatment without independent "
        "review by a qualified neuro-oncologist."
    )


class RecurrenceRiskEstimator:
    """
    Estimate glioma recurrence risk from volumetric + radiomic features.

    The model is intentionally transparent: every point in the final score
    is traceable to a specific clinical feature and its literature basis.

    Parameters
    ----------
    baseline_score : int
        Starting risk before any features are applied (default 35 — reflects
        the ~30–40% baseline recurrence rate for treated GBM).
    """

    def __init__(self, baseline_score: int = 35) -> None:
        self.baseline_score = baseline_score

    def estimate(
        self,
        vol_result: VolumetricResult,
        radiomic_features: Optional[Dict[str, Dict[str, float]]] = None,
        rano_category: Optional[str] = None,
    ) -> RiskEstimate:
        """
        Compute recurrence risk score.

        Parameters
        ----------
        vol_result         : VolumetricResult from VolumetricAnalyzer.
        radiomic_features  : dict from RadiomicsExtractor.extract().
                             Enables shape/texture contributions.
        rano_category      : RANO response string ("CR","PR","SD","PD") or None.

        Returns
        -------
        RiskEstimate
        """
        score = float(self.baseline_score)
        contributions: List[RiskContribution] = []

        # ── 1. Enhancing tumour volume ────────────────────────────────────────
        et_mm3 = vol_result.et_mm3
        et_delta, et_desc = _et_volume_contribution(et_mm3)
        score += et_delta
        contributions.append(RiskContribution(
            feature="Enhancing Tumour Volume",
            value=round(et_mm3, 1),
            delta=round(et_delta, 1),
            direction="increasing" if et_delta > 0 else "decreasing",
            description=et_desc,
        ))

        # ── 2. ED / WT ratio (invasion indicator) ────────────────────────────
        ed_mm3 = vol_result.volumes_mm3.get("ED", 0.0)
        wt_mm3 = vol_result.wt_mm3
        ed_ratio = ed_mm3 / (wt_mm3 + 1.0)
        ed_delta, ed_desc = _edema_ratio_contribution(ed_ratio)
        score += ed_delta
        contributions.append(RiskContribution(
            feature="Edema / Whole Tumour Ratio",
            value=round(ed_ratio, 3),
            delta=round(ed_delta, 1),
            direction="increasing" if ed_delta > 0 else "decreasing",
            description=ed_desc,
        ))

        # ── 3. TC / WT ratio (aggressive core) ───────────────────────────────
        tc_mm3 = vol_result.tc_mm3
        tc_ratio = tc_mm3 / (wt_mm3 + 1.0)
        tc_delta, tc_desc = _core_ratio_contribution(tc_ratio)
        score += tc_delta
        contributions.append(RiskContribution(
            feature="Tumour Core / Whole Tumour Ratio",
            value=round(tc_ratio, 3),
            delta=round(tc_delta, 1),
            direction="increasing" if tc_delta > 0 else "decreasing",
            description=tc_desc,
        ))

        # ── 4. Sphericity (from radiomics if available) ───────────────────────
        if radiomic_features:
            et_feats = radiomic_features.get("ET", {})
            sphericity = et_feats.get("sphericity", None)
            if sphericity is not None and sphericity > 0:
                sph_delta, sph_desc = _sphericity_contribution(sphericity)
                score += sph_delta
                contributions.append(RiskContribution(
                    feature="ET Sphericity",
                    value=round(sphericity, 3),
                    delta=round(sph_delta, 1),
                    direction="increasing" if sph_delta > 0 else "decreasing",
                    description=sph_desc,
                ))

            # ── 5. GLCM texture heterogeneity ─────────────────────────────────
            glcm_contrast = et_feats.get("glcm_contrast", None)
            if glcm_contrast is not None:
                tex_delta, tex_desc = _texture_contribution(glcm_contrast)
                score += tex_delta
                contributions.append(RiskContribution(
                    feature="ET Texture Heterogeneity (GLCM Contrast)",
                    value=round(glcm_contrast, 4),
                    delta=round(tex_delta, 1),
                    direction="increasing" if tex_delta > 0 else "decreasing",
                    description=tex_desc,
                ))

        # ── 6. RANO category adjustment ───────────────────────────────────────
        if rano_category:
            rano_delta, rano_desc = _rano_contribution(rano_category)
            score += rano_delta
            contributions.append(RiskContribution(
                feature="RANO Response Category",
                value=0.0,
                delta=round(rano_delta, 1),
                direction="increasing" if rano_delta > 0 else "decreasing",
                description=rano_desc,
            ))

        # ── Clamp and interpret ───────────────────────────────────────────────
        score_int = int(np.clip(round(score), 0, 100))
        interpretation = _interpret(score_int)

        # Top-3 factors by absolute delta
        top = sorted(contributions, key=lambda c: abs(c.delta), reverse=True)[:3]
        top_factors = [c.feature for c in top]

        return RiskEstimate(
            score=score_int,
            interpretation=interpretation,
            contributions=contributions,
            top_factors=top_factors,
        )


# ── Feature scoring functions ─────────────────────────────────────────────────

def _et_volume_contribution(et_mm3: float) -> Tuple[float, str]:
    """ET > 10 cm³ → high risk. Refs: Ellingson et al. 2017."""
    if et_mm3 < 1_000:
        return -5.0, f"Small ET volume ({et_mm3/1000:.1f} cm³) — favourable."
    elif et_mm3 < 5_000:
        return +5.0, f"Moderate ET volume ({et_mm3/1000:.1f} cm³) — intermediate risk."
    elif et_mm3 < 10_000:
        return +15.0, f"Large ET volume ({et_mm3/1000:.1f} cm³) — elevated risk."
    else:
        return +25.0, f"Very large ET volume ({et_mm3/1000:.1f} cm³) — high risk marker."


def _edema_ratio_contribution(ratio: float) -> Tuple[float, str]:
    """High edema fraction suggests active tumour invasion."""
    if ratio < 0.30:
        return -5.0, f"Low edema fraction ({ratio:.0%}) — contained growth."
    elif ratio < 0.55:
        return +5.0, f"Moderate edema fraction ({ratio:.0%}) — some perilesional invasion."
    else:
        return +12.0, f"High edema fraction ({ratio:.0%}) — extensive perilesional invasion."


def _core_ratio_contribution(ratio: float) -> Tuple[float, str]:
    """Large necrotic/enhancing core relative to total tumour → aggressive."""
    if ratio < 0.40:
        return +2.0, f"Moderate core/WT ratio ({ratio:.0%})."
    elif ratio < 0.70:
        return +8.0, f"Elevated core/WT ratio ({ratio:.0%}) — active tumour phenotype."
    else:
        return +15.0, f"Very high core/WT ratio ({ratio:.0%}) — aggressive necrotic core."


def _sphericity_contribution(sphericity: float) -> Tuple[float, str]:
    """
    Low sphericity = irregular boundary = possible infiltration.
    Sphericity 1.0 = perfect sphere.
    """
    if sphericity > 0.80:
        return -8.0, f"High sphericity ({sphericity:.2f}) — well-circumscribed boundary, lower invasion risk."
    elif sphericity > 0.55:
        return +3.0, f"Moderate sphericity ({sphericity:.2f}) — slightly irregular boundary."
    else:
        return +12.0, f"Low sphericity ({sphericity:.2f}) — highly irregular boundary, possible infiltration."


def _texture_contribution(contrast: float) -> Tuple[float, str]:
    """High GLCM contrast in ET region → heterogeneous cellularity → aggressive."""
    if contrast < 0.05:
        return -3.0, f"Low texture contrast ({contrast:.4f}) — homogeneous lesion."
    elif contrast < 0.15:
        return +4.0, f"Moderate texture contrast ({contrast:.4f}) — mixed cellularity."
    else:
        return +10.0, f"High texture contrast ({contrast:.4f}) — heterogeneous tumour, likely aggressive."


def _rano_contribution(rano: str) -> Tuple[float, str]:
    """RANO response category directly adjusts risk."""
    adjustments = {
        "CR": (-20.0, "Complete Response — markedly lower recurrence risk."),
        "PR": (-10.0, "Partial Response — reduced tumour burden."),
        "SD": (  0.0, "Stable Disease — no significant change in risk."),
        "PD": (+20.0, "Progressive Disease — significantly elevated recurrence risk."),
    }
    return adjustments.get(rano.upper(), (0.0, f"RANO category '{rano}' — no adjustment."))


def _interpret(score: int) -> str:
    if score < 30:
        return "Low"
    elif score < 55:
        return "Moderate"
    elif score < 75:
        return "High"
    else:
        return "Very High"
