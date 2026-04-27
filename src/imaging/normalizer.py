"""
normalizer.py — Intensity normalization for multi-modal MRI volumes.

Normalization is computed ONLY over brain voxels (non-zero under the brain
mask) to avoid the large background region skewing statistics.

Supported methods
-----------------
zscore     : (x - μ) / σ  — recommended for neural network training.
minmax     : (x - min) / (max - min) → [0, 1].
whitestripe: Match intensity histogram to a reference white-matter stripe
             (simplified implementation; full WhiteStripe requires R package).

In all cases, a percentile clipping step (default 1st–99th) is applied first
to suppress scanner-intensity outliers and Gibbs ringing artefacts.
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

import numpy as np

from .loader import MRISubject

logger = logging.getLogger(__name__)


class Normalizer:
    """
    Per-modality intensity normalizer with brain-mask-aware statistics.

    Parameters
    ----------
    method : str
        Normalization method: "zscore" | "minmax" | "whitestripe".
    clip_percentiles : tuple[float, float]
        Lower and upper percentile bounds for pre-clipping.
        Set to (0, 100) to disable clipping.
    brain_mask : np.ndarray | None
        Optional pre-computed brain mask (uint8, shape matches volumes).
        If None, non-zero voxels are used as a proxy for brain tissue.
    """

    SUPPORTED_METHODS = ("zscore", "minmax", "whitestripe")

    def __init__(
        self,
        method: str = "zscore",
        clip_percentiles: Tuple[float, float] = (1.0, 99.0),
        brain_mask: Optional[np.ndarray] = None,
    ) -> None:
        if method not in self.SUPPORTED_METHODS:
            raise ValueError(f"Unknown normalization method '{method}'. Choose from {self.SUPPORTED_METHODS}.")
        self.method = method
        self.clip_percentiles = clip_percentiles
        self.brain_mask = brain_mask

    def normalize(self, subject: MRISubject) -> MRISubject:
        """
        Normalize all four image modalities independently.

        Parameters
        ----------
        subject : MRISubject (post skull-stripping recommended).

        Returns
        -------
        MRISubject with float32 normalized arrays.
        """
        normalized = {}
        for name, volume in subject.modalities.items():
            normalized[name] = self._normalize_volume(volume, name)

        return MRISubject(
            subject_id=subject.subject_id,
            t1=normalized["t1"],
            t1ce=normalized["t1ce"],
            t2=normalized["t2"],
            flair=normalized["flair"],
            seg=subject.seg,
            metadata=subject.metadata,
        )

    def _normalize_volume(self, volume: np.ndarray, name: str) -> np.ndarray:
        """Apply clipping then the chosen normalization to a single modality."""
        mask = self._get_brain_mask(volume)

        if mask.sum() == 0:
            logger.warning("Modality '%s' has no non-zero brain voxels — returning as-is.", name)
            return volume.astype(np.float32)

        # 1. Percentile clipping (on brain voxels only)
        clipped = self._clip(volume, mask)

        # 2. Normalization
        if self.method == "zscore":
            result = self._zscore(clipped, mask)
        elif self.method == "minmax":
            result = self._minmax(clipped, mask)
        else:
            result = self._whitestripe(clipped, mask)

        logger.debug(
            "Normalized '%s' using '%s'  brain_voxels=%d  result_range=[%.3f, %.3f]",
            name, self.method, mask.sum(), result[mask].min(), result[mask].max(),
        )
        return result.astype(np.float32)

    def _get_brain_mask(self, volume: np.ndarray) -> np.ndarray:
        """Return a boolean mask of brain voxels."""
        if self.brain_mask is not None:
            return self.brain_mask.astype(bool)
        # Proxy: all non-zero voxels after skull stripping
        return volume > 0

    def _clip(self, volume: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Clip intensity values to the specified percentile range (brain voxels only)."""
        lo, hi = self.clip_percentiles
        if lo == 0 and hi == 100:
            return volume.copy()

        brain_values = volume[mask]
        p_low = float(np.percentile(brain_values, lo))
        p_high = float(np.percentile(brain_values, hi))

        clipped = volume.copy()
        clipped[mask] = np.clip(brain_values, p_low, p_high)
        return clipped

    def _zscore(self, volume: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Zero-mean, unit-variance normalization over brain voxels."""
        brain_values = volume[mask]
        mu = float(brain_values.mean())
        sigma = float(brain_values.std())

        if sigma < 1e-8:
            logger.warning("Near-zero standard deviation (σ=%.6f) — returning zero volume.", sigma)
            return np.zeros_like(volume)

        result = np.zeros_like(volume, dtype=np.float32)
        result[mask] = (brain_values - mu) / sigma
        return result

    def _minmax(self, volume: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """Scale brain voxels to [0, 1]."""
        brain_values = volume[mask]
        v_min = float(brain_values.min())
        v_max = float(brain_values.max())
        denom = v_max - v_min

        result = np.zeros_like(volume, dtype=np.float32)
        if denom < 1e-8:
            return result

        result[mask] = (brain_values - v_min) / denom
        return result

    def _whitestripe(self, volume: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        Simplified WhiteStripe normalization.

        Identifies the white-matter intensity mode from the histogram of brain
        voxels and normalises so that this mode maps to 1.0. This makes
        intensities comparable across scanners without needing an external
        reference scan.

        Full WhiteStripe (Shinohara et al. 2014) uses a narrower stripe; this
        implementation approximates it via histogram peak detection.
        """
        brain_values = volume[mask]

        # Find WM peak: top 25th–75th percentile of brain intensities
        p25 = float(np.percentile(brain_values, 25))
        p75 = float(np.percentile(brain_values, 75))
        wm_region = brain_values[(brain_values >= p25) & (brain_values <= p75)]

        if wm_region.size == 0:
            logger.warning("White matter stripe empty — falling back to z-score.")
            return self._zscore(volume, mask)

        wm_mean = float(wm_region.mean())
        wm_std = float(wm_region.std())

        if wm_std < 1e-8:
            return self._zscore(volume, mask)

        result = np.zeros_like(volume, dtype=np.float32)
        result[mask] = (brain_values - wm_mean) / wm_std
        return result
