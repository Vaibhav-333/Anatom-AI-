"""
resampler.py — Spatial resampling to isotropic voxel spacing.

Uses SimpleITK for high-quality interpolation:
  - B-spline (order 3) for continuous image modalities.
  - Nearest-neighbour for integer segmentation labels (preserves class IDs).

After resampling, volumes are padded or cropped to the target canonical size
(default 240 × 240 × 155, matching BraTS 2024 standard) using centre-based
symmetric padding / centre cropping.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import numpy as np
import SimpleITK as sitk

from .loader import MRISubject

logger = logging.getLogger(__name__)

# BraTS 2024 canonical spatial size (x, y, z)
DEFAULT_TARGET_SIZE: Tuple[int, int, int] = (240, 240, 155)
DEFAULT_TARGET_SPACING: Tuple[float, float, float] = (1.0, 1.0, 1.0)


class Resampler:
    """
    Resample all MRI modalities (and segmentation) to a common isotropic grid.

    Parameters
    ----------
    target_spacing : tuple of three floats
        Desired voxel spacing in mm (x, y, z). Default: 1 mm isotropic.
    target_size : tuple of three ints | None
        After resampling, pad/crop to this spatial size. If None, size is
        determined entirely by the resampled voxel grid.
    image_interpolator : str
        SimpleITK interpolator for image modalities.
        "bspline"  — highest quality (default).
        "linear"   — faster, slightly lower quality.
    """

    INTERPOLATORS = {
        "bspline": sitk.sitkBSpline,
        "linear":  sitk.sitkLinear,
        "nearest": sitk.sitkNearestNeighbor,
    }

    def __init__(
        self,
        target_spacing: Tuple[float, float, float] = DEFAULT_TARGET_SPACING,
        target_size: Optional[Tuple[int, int, int]] = DEFAULT_TARGET_SIZE,
        image_interpolator: str = "bspline",
    ) -> None:
        if image_interpolator not in self.INTERPOLATORS:
            raise ValueError(
                f"Unknown interpolator '{image_interpolator}'. "
                f"Choose from {list(self.INTERPOLATORS)}."
            )
        self.target_spacing = target_spacing
        self.target_size = target_size
        self.image_interp = self.INTERPOLATORS[image_interpolator]
        self.label_interp = sitk.sitkNearestNeighbor

    def resample(self, subject: MRISubject) -> MRISubject:
        """
        Resample all modalities in subject to the target spacing and size.

        Parameters
        ----------
        subject : MRISubject with float32 image arrays and optional int16 seg.

        Returns
        -------
        MRISubject with resampled arrays.
        """
        # Infer original spacing from metadata (use t1 as reference)
        original_spacing = self._get_original_spacing(subject)
        logger.info(
            "Resampling '%s'  original_spacing=%s → target_spacing=%s",
            subject.subject_id, original_spacing, self.target_spacing,
        )

        resampled_modalities = {}
        for name, volume in subject.modalities.items():
            resampled_modalities[name] = self._resample_volume(
                volume, original_spacing, is_label=False
            )

        resampled_seg = None
        if subject.seg is not None:
            resampled_seg = self._resample_volume(
                subject.seg.astype(np.float32), original_spacing, is_label=True
            ).astype(np.int16)

        # Pad / crop to canonical size
        if self.target_size is not None:
            resampled_modalities = {
                k: self._pad_or_crop(v) for k, v in resampled_modalities.items()
            }
            if resampled_seg is not None:
                resampled_seg = self._pad_or_crop(resampled_seg.astype(np.float32)).astype(np.int16)

        logger.info(
            "Resampled output shape: %s", next(iter(resampled_modalities.values())).shape
        )

        return MRISubject(
            subject_id=subject.subject_id,
            t1=resampled_modalities["t1"],
            t1ce=resampled_modalities["t1ce"],
            t2=resampled_modalities["t2"],
            flair=resampled_modalities["flair"],
            seg=resampled_seg,
            metadata=subject.metadata,
        )

    def _resample_volume(
        self,
        volume: np.ndarray,
        original_spacing: Tuple[float, float, float],
        is_label: bool,
    ) -> np.ndarray:
        """Resample a single 3D numpy array using SimpleITK."""
        sitk_img = sitk.GetImageFromArray(volume.transpose(2, 1, 0))  # (D,W,H) → ITK convention
        sitk_img.SetSpacing([float(s) for s in original_spacing])

        new_size = self._compute_new_size(sitk_img.GetSize(), original_spacing)
        interpolator = self.label_interp if is_label else self.image_interp

        resampled = sitk.Resample(
            sitk_img,
            new_size,
            sitk.Transform(),
            interpolator,
            sitk_img.GetOrigin(),
            [float(s) for s in self.target_spacing],
            sitk_img.GetDirection(),
            0.0,
            sitk_img.GetPixelID(),
        )

        # Back to numpy: (D,W,H) → (H,W,D)
        return sitk.GetArrayFromImage(resampled).transpose(2, 1, 0).astype(np.float32)

    def _compute_new_size(
        self,
        original_size: Tuple[int, int, int],
        original_spacing: Tuple[float, float, float],
    ) -> List[int]:
        """Compute output size from spacing ratio (preserves physical extent)."""
        return [
            int(round(orig_sz * orig_sp / tgt_sp))
            for orig_sz, orig_sp, tgt_sp in zip(
                original_size, original_spacing, self.target_spacing
            )
        ]

    def _pad_or_crop(self, volume: np.ndarray) -> np.ndarray:
        """Centre-pad or centre-crop volume to self.target_size."""
        assert self.target_size is not None
        result = np.zeros(self.target_size, dtype=volume.dtype)

        for dim in range(3):
            src = volume.shape[dim]
            tgt = self.target_size[dim]
            if src >= tgt:
                volume = _crop_dim(volume, dim, tgt)
            else:
                volume = _pad_dim(volume, dim, tgt)

        # After all three dims are aligned, copy into result buffer
        slices = tuple(slice(0, min(volume.shape[i], self.target_size[i])) for i in range(3))
        result[slices] = volume[slices]
        return result

    def _get_original_spacing(
        self, subject: MRISubject
    ) -> Tuple[float, float, float]:
        """Read voxel spacing from subject metadata (fall back to 1 mm if unavailable)."""
        if "t1" in subject.metadata:
            spacing = subject.metadata["t1"].voxel_spacing_mm
            return tuple(float(s) for s in spacing[:3])
        logger.warning("No metadata found — assuming 1 mm isotropic original spacing.")
        return (1.0, 1.0, 1.0)


def _crop_dim(volume: np.ndarray, dim: int, target: int) -> np.ndarray:
    """Centre-crop along a single dimension."""
    src = volume.shape[dim]
    start = (src - target) // 2
    slices = [slice(None)] * 3
    slices[dim] = slice(start, start + target)
    return volume[tuple(slices)]


def _pad_dim(volume: np.ndarray, dim: int, target: int) -> np.ndarray:
    """Centre-pad along a single dimension with zeros."""
    src = volume.shape[dim]
    pad_total = target - src
    pad_before = pad_total // 2
    pad_after = pad_total - pad_before
    pad_width = [(0, 0)] * 3
    pad_width[dim] = (pad_before, pad_after)
    return np.pad(volume, pad_width, mode="constant", constant_values=0)
