"""
longitudinal.py — Registration-free longitudinal tumor growth tracking.

Compares two volumetric results from different timepoints and produces:
  - Absolute volume delta (mm3) per sub-region
  - Growth rate (mm3/day)
  - RANO (Response Assessment in Neuro-Oncology) category

RANO Volume-Based Criteria (approximation from bidimensional RANO standard)
---------------------------------------------------------------------------
    CR (Complete Response)   : WT volume < 500 mm3  OR  ≥95% reduction
    PR (Partial Response)    : WT volume decreased ≥ 50%
    PD (Progressive Disease) : WT volume increased  ≥ 25%  OR new lesions detected
    SD (Stable Disease)      : everything else

These thresholds are a volumetric approximation of the bidimensional RANO
criteria (which measure the longest diameter and its perpendicular). Refer to
clinical literature before using in a medical context.

Reference
---------
Wen PY et al., "Updated Response Assessment Criteria for High-Grade Gliomas:
Response Assessment in Neuro-Oncology Working Group", J Clin Oncol 2010.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import numpy as np

from .volumetrics import VolumetricAnalyzer, VolumetricResult

logger = logging.getLogger(__name__)

# Volumetric RANO thresholds (mm3 / percentage)
_CR_VOLUME_THRESHOLD_MM3 = 500.0     # Near-complete response
_CR_REDUCTION_THRESHOLD = 0.95       # 95% reduction qualifies as CR
_PR_REDUCTION_THRESHOLD = 0.50       # ≥50% decrease → Partial Response
_PD_INCREASE_THRESHOLD = 0.25        # ≥25% increase  → Progressive Disease


@dataclass
class LongitudinalReport:
    """
    Longitudinal tumor growth analysis between two timepoints.

    Attributes
    ----------
    subject_id      : patient/subject identifier.
    days_elapsed    : time between T1 and T2 scans (days). Can be fractional.
    volumes_t1      : volumes in mm3 at baseline (T1).
    volumes_t2      : volumes in mm3 at follow-up (T2).
    delta_mm3       : absolute volume change (T2 - T1) per region.
    rate_mm3_per_day: growth rate per region.  Positive = growth, negative = regression.
    pct_change      : percentage change per region relative to T1.
    rano_category   : "CR" | "PR" | "SD" | "PD" based on WT volume change.
    rano_pct_change : % WT volume change used for RANO classification.
    """

    subject_id: str
    days_elapsed: float

    volumes_t1: Dict[str, float] = field(default_factory=dict)
    volumes_t2: Dict[str, float] = field(default_factory=dict)

    delta_mm3: Dict[str, float] = field(default_factory=dict)
    rate_mm3_per_day: Dict[str, float] = field(default_factory=dict)
    pct_change: Dict[str, float] = field(default_factory=dict)

    rano_category: str = "SD"
    rano_pct_change: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "subject_id": self.subject_id,
            "days_elapsed": self.days_elapsed,
            "volumes_t1_mm3": self.volumes_t1,
            "volumes_t2_mm3": self.volumes_t2,
            "delta_mm3": self.delta_mm3,
            "rate_mm3_per_day": self.rate_mm3_per_day,
            "pct_change": self.pct_change,
            "rano_category": self.rano_category,
            "rano_pct_change": self.rano_pct_change,
        }


class LongitudinalTracker:
    """
    Compare volumetric results across two timepoints and apply RANO criteria.

    Typical usage
    -------------
    Option A — from pre-computed VolumetricResult objects:

        tracker = LongitudinalTracker()
        report = tracker.compare(result_t1, result_t2, days_elapsed=90.0)

    Option B — directly from segmentation arrays:

        report = LongitudinalTracker.from_segmentations(
            seg_t1, seg_t2,
            voxel_spacing=(1.0, 1.0, 1.0),
            days_elapsed=90.0,
            subject_id="BraTS-007",
        )
    """

    def compare(
        self,
        result_t1: VolumetricResult,
        result_t2: VolumetricResult,
        days_elapsed: float,
    ) -> LongitudinalReport:
        """
        Generate a LongitudinalReport from two VolumetricResult objects.

        Parameters
        ----------
        result_t1    : VolumetricResult at baseline.
        result_t2    : VolumetricResult at follow-up.
        days_elapsed : time between scans in days (must be > 0).

        Returns
        -------
        LongitudinalReport
        """
        if days_elapsed <= 0:
            raise ValueError(f"days_elapsed must be positive, got {days_elapsed}.")

        subject_id = result_t1.subject_id

        # Collect region volumes from both timepoints
        regions = ("WT", "TC", "ET")
        t1_vols = {
            "WT": result_t1.wt_mm3,
            "TC": result_t1.tc_mm3,
            "ET": result_t1.et_mm3,
        }
        t2_vols = {
            "WT": result_t2.wt_mm3,
            "TC": result_t2.tc_mm3,
            "ET": result_t2.et_mm3,
        }

        delta: Dict[str, float] = {}
        rate: Dict[str, float] = {}
        pct: Dict[str, float] = {}

        for region in regions:
            v1, v2 = t1_vols[region], t2_vols[region]
            delta[region] = v2 - v1
            rate[region] = (v2 - v1) / days_elapsed
            # % change relative to T1 (avoid division by zero — use 1.0 as floor)
            pct[region] = (v2 - v1) / max(v1, 1.0)

        # RANO classification based on WT
        rano_category = self._classify_rano(t1_vols["WT"], t2_vols["WT"])
        rano_pct = pct["WT"] * 100.0  # convert to percentage points

        report = LongitudinalReport(
            subject_id=subject_id,
            days_elapsed=days_elapsed,
            volumes_t1=t1_vols,
            volumes_t2=t2_vols,
            delta_mm3=delta,
            rate_mm3_per_day=rate,
            pct_change={k: v * 100.0 for k, v in pct.items()},
            rano_category=rano_category,
            rano_pct_change=rano_pct,
        )

        logger.info(
            "Subject %s - RANO: %s  WT D=%.1f mm3 (%.1f%%/day)  over %.0f days",
            subject_id, rano_category, delta["WT"], rate["WT"], days_elapsed,
        )
        return report

    @staticmethod
    def from_segmentations(
        seg_t1: np.ndarray,
        seg_t2: np.ndarray,
        voxel_spacing: Tuple[float, float, float],
        days_elapsed: float,
        subject_id: str = "unknown",
    ) -> LongitudinalReport:
        """
        Convenience method: compute volumes from raw segmentations and compare.

        Parameters
        ----------
        seg_t1, seg_t2   : integer label arrays of shape (H, W, D).
        voxel_spacing    : (sx, sy, sz) in mm.
        days_elapsed     : time between scans in days.
        subject_id       : patient identifier.

        Returns
        -------
        LongitudinalReport
        """
        analyzer = VolumetricAnalyzer()
        r1 = analyzer.compute(seg_t1, voxel_spacing, subject_id=subject_id)
        r2 = analyzer.compute(seg_t2, voxel_spacing, subject_id=subject_id)
        return LongitudinalTracker().compare(r1, r2, days_elapsed)

    # ------------------------------------------------------------------ RANO
    @staticmethod
    def _classify_rano(wt_t1: float, wt_t2: float) -> str:
        """
        Classify RANO response based on Whole Tumour volume change.

        Returns one of: "CR", "PR", "SD", "PD".
        """
        # Complete response: near-zero residual tumour
        if wt_t2 < _CR_VOLUME_THRESHOLD_MM3:
            return "CR"

        # Fractional change (positive = growth, negative = shrinkage)
        safe_t1 = max(wt_t1, 1.0)
        frac_change = (wt_t2 - wt_t1) / safe_t1

        # Complete response via ≥95% reduction (even if absolute vol > 500 mm3)
        if frac_change <= -_CR_REDUCTION_THRESHOLD:
            return "CR"

        # Partial response: ≥50% decrease
        if frac_change <= -_PR_REDUCTION_THRESHOLD:
            return "PR"

        # Progressive disease: ≥25% increase
        if frac_change >= _PD_INCREASE_THRESHOLD:
            return "PD"

        # Stable disease
        return "SD"
