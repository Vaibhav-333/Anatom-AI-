"""
qc_validator.py — Quality Control for MRI preprocessing pipeline.

Two validation checkpoints:

validate_pre()  — Called BEFORE any processing.
    Checks: files exist, shapes are 3D, no NaN/Inf, all 4 modalities present,
    voxel range is physically plausible (not all zeros, not all identical).

validate_post() — Called AFTER full preprocessing.
    Checks: brain mask coverage is within expected range, normalised values
    are z-score-like (mean ≈ 0, std ≈ 1), no NaN/Inf introduced by pipeline.

Results are returned as a QCReport dataclass. A failed report raises in the
pipeline — a subject with critical QC failures never enters the training set.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

import numpy as np

from src.imaging.loader import MRISubject

logger = logging.getLogger(__name__)


@dataclass
class QCReport:
    """Structured result of a QC check."""
    subject_id: str
    stage: str                          # "pre" or "post"
    passed: bool = True
    failures: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def add_failure(self, msg: str) -> None:
        self.failures.append(msg)
        self.passed = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def save(self, output_dir: str | Path) -> None:
        path = Path(output_dir) / f"qc_{self.stage}_{self.subject_id}.json"
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)
        logger.debug("QC report saved: %s", path)


class QCValidator:
    """
    Validates MRISubject objects at the pre- and post-processing stages.

    Parameters
    ----------
    min_brain_coverage : float
        Post-processing: minimum fraction of volume that should be brain tissue.
    max_brain_coverage : float
        Post-processing: warn if brain mask is suspiciously large (>60% usually wrong).
    expected_modalities : list[str]
        Pre-processing: all of these must be present and non-zero.
    """

    def __init__(
        self,
        min_brain_coverage: float = 0.05,
        max_brain_coverage: float = 0.60,
        expected_modalities: Optional[List[str]] = None,
    ) -> None:
        self.min_brain_coverage = min_brain_coverage
        self.max_brain_coverage = max_brain_coverage
        self.expected_modalities = expected_modalities or ["t1", "t1ce", "t2", "flair"]

    def validate_pre(self, subject: MRISubject) -> QCReport:
        """
        Run pre-processing QC checks on a freshly loaded MRISubject.

        Fails on: missing modalities, NaN/Inf, all-zero volumes, shape mismatches.
        Warns on: unusual voxel intensity ranges.
        """
        report = QCReport(subject_id=subject.subject_id, stage="pre")

        for name in self.expected_modalities:
            volume = subject.modalities.get(name)
            if volume is None:
                report.add_failure(f"Missing modality: '{name}'")
                continue

            # Shape check
            if volume.ndim != 3:
                report.add_failure(f"'{name}' is not 3D — ndim={volume.ndim}")

            # NaN / Inf
            if np.isnan(volume).any():
                report.add_failure(f"'{name}' contains NaN values.")
            if np.isinf(volume).any():
                report.add_failure(f"'{name}' contains Inf values.")

            # Non-zero content
            nonzero_frac = float((volume != 0).mean())
            if nonzero_frac < 0.001:
                report.add_failure(f"'{name}' is effectively all zeros (nonzero={nonzero_frac:.4f}).")

            # Intensity range sanity
            v_min, v_max = float(volume.min()), float(volume.max())
            report.stats[f"{name}_min"] = round(v_min, 4)
            report.stats[f"{name}_max"] = round(v_max, 4)

            if v_max == v_min:
                report.add_failure(f"'{name}' has zero intensity range — constant volume.")

            if v_max < 0:
                report.add_warning(f"'{name}' maximum is negative — unusual for raw MRI.")

        if report.passed:
            logger.info("Pre-QC PASSED for '%s'", subject.subject_id)
        else:
            logger.error("Pre-QC FAILED for '%s': %s", subject.subject_id, report.failures)

        return report

    def validate_post(self, subject: MRISubject) -> QCReport:
        """
        Run post-processing QC checks after the full preprocessing pipeline.

        Checks: no NaN/Inf introduced, normalised statistics are plausible,
        brain coverage is within expected bounds.
        """
        report = QCReport(subject_id=subject.subject_id, stage="post")

        for name, volume in subject.modalities.items():
            # NaN / Inf (pipeline may introduce these via division errors)
            if np.isnan(volume).any():
                report.add_failure(f"Post-processing introduced NaN in '{name}'.")
            if np.isinf(volume).any():
                report.add_failure(f"Post-processing introduced Inf in '{name}'.")

            brain_mask = volume != 0
            brain_frac = float(brain_mask.mean())

            report.stats[f"{name}_brain_coverage"] = round(brain_frac, 4)

            if brain_frac < self.min_brain_coverage:
                report.add_failure(
                    f"'{name}' brain coverage {brain_frac:.3f} < min {self.min_brain_coverage}."
                )
            if brain_frac > self.max_brain_coverage:
                report.add_warning(
                    f"'{name}' brain coverage {brain_frac:.3f} > expected max {self.max_brain_coverage}."
                )

            if brain_mask.any():
                mu = float(volume[brain_mask].mean())
                std = float(volume[brain_mask].std())
                report.stats[f"{name}_mean"] = round(mu, 4)
                report.stats[f"{name}_std"] = round(std, 4)

                # z-score sanity: mean should be near 0, std near 1
                if abs(mu) > 5.0:
                    report.add_warning(f"'{name}' mean={mu:.2f} deviates from expected ~0 (z-score).")
                if std < 0.1 or std > 10.0:
                    report.add_warning(f"'{name}' std={std:.2f} is outside expected range [0.1, 10].")

        if report.passed:
            logger.info("Post-QC PASSED for '%s'", subject.subject_id)
        else:
            logger.error("Post-QC FAILED for '%s': %s", subject.subject_id, report.failures)

        return report
