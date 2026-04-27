"""
skull_stripper.py — Brain mask generation for 3D MRI volumes.

Strategy (slice-by-slice Otsu, then 3D morphological refinement):
  1. For each axial slice: Otsu threshold → binary mask.
  2. Morphological closing (fill holes) per slice.
  3. Retain only the largest connected component across 3D volume.
  4. Final 3D closing pass to seal small gaps.
  5. Apply mask to all four modalities simultaneously.

This approach is GPU-free, dependency-light, and robust on clean BraTS data.
For extreme edge cases (massive edema touching skull), switch to HD-BET as
an external preprocessor before running this pipeline.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

import cv2
import numpy as np
from scipy import ndimage

from .loader import MRISubject

logger = logging.getLogger(__name__)


class SkullStripper:
    """
    Generates a 3D binary brain mask and applies it to all MRI modalities.

    Parameters
    ----------
    threshold_method : str
        Thresholding algorithm for each axial slice.
        "otsu"     — Otsu's method (default, best for bimodal histograms).
        "triangle" — Triangle algorithm (better for skewed distributions).
    closing_radius : int
        Radius (voxels) for morphological closing. Larger values fill bigger
        holes but may dilate the mask into non-brain tissue.
    min_brain_coverage : float
        Minimum fraction of the volume that must be labelled as brain.
        Subjects below this threshold fail QC.
    reference_modality : str
        Modality used to compute the mask (T1ce has highest tissue contrast).
    """

    def __init__(
        self,
        threshold_method: str = "otsu",
        closing_radius: int = 5,
        min_brain_coverage: float = 0.05,
        reference_modality: str = "t1ce",
    ) -> None:
        self.threshold_method = threshold_method
        self.closing_radius = closing_radius
        self.min_brain_coverage = min_brain_coverage
        self.reference_modality = reference_modality

    def strip(self, subject: MRISubject) -> Tuple[MRISubject, np.ndarray]:
        """
        Compute brain mask and apply to all modalities in subject.

        Parameters
        ----------
        subject : MRISubject with raw (unmasked) float32 arrays.

        Returns
        -------
        masked_subject : MRISubject with skull-stripped arrays.
        brain_mask    : Binary uint8 array, shape (H, W, D), values 0 or 1.

        Raises
        ------
        ValueError : if brain mask coverage is below min_brain_coverage.
        """
        reference = subject.modalities[self.reference_modality]
        logger.info("Computing brain mask from '%s'  shape=%s", self.reference_modality, reference.shape)

        # Step 1: Per-slice thresholding → 2D binary masks stacked into 3D
        raw_mask = self._threshold_volume(reference)

        # Step 2: Per-slice morphological closing
        closed_mask = self._close_slices(raw_mask)

        # Step 3: Largest 3D connected component
        brain_mask = self._largest_component_3d(closed_mask)

        # Step 4: Final 3D closing (binary_closing is isotropic)
        struct = _spherical_structuring_element(self.closing_radius)
        brain_mask = ndimage.binary_closing(brain_mask, structure=struct).astype(np.uint8)

        # Step 5: QC coverage check
        coverage = brain_mask.mean()
        logger.info("Brain mask coverage: %.2f%%", coverage * 100)
        if coverage < self.min_brain_coverage:
            raise ValueError(
                f"Brain mask coverage {coverage:.3f} is below the minimum "
                f"threshold {self.min_brain_coverage}. Skull stripping likely failed."
            )

        # Step 6: Apply mask to all modalities
        masked_subject = self._apply_mask(subject, brain_mask)
        return masked_subject, brain_mask

    def _threshold_volume(self, volume: np.ndarray) -> np.ndarray:
        """Apply slice-wise Otsu/Triangle thresholding in the axial plane."""
        h, w, d = volume.shape
        mask = np.zeros((h, w, d), dtype=np.uint8)

        # Normalise to 8-bit for OpenCV
        v_min, v_max = volume.min(), volume.max()
        if v_max == v_min:
            logger.warning("Reference volume has zero intensity range — skull stripping skipped.")
            return mask

        vol_8bit = ((volume - v_min) / (v_max - v_min) * 255).astype(np.uint8)

        flag = (
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
            if self.threshold_method == "otsu"
            else cv2.THRESH_BINARY + cv2.THRESH_TRIANGLE
        )

        for z in range(d):
            slc = vol_8bit[:, :, z]
            if slc.max() == 0:
                continue
            _, binary = cv2.threshold(slc, 0, 1, flag)
            mask[:, :, z] = binary

        return mask

    def _close_slices(self, mask: np.ndarray) -> np.ndarray:
        """Per-axial-slice morphological closing to fill intra-brain holes."""
        h, w, d = mask.shape
        closed = np.zeros_like(mask)
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE,
            (self.closing_radius * 2 + 1, self.closing_radius * 2 + 1),
        )
        for z in range(d):
            slc = mask[:, :, z].astype(np.uint8)
            closed[:, :, z] = cv2.morphologyEx(slc, cv2.MORPH_CLOSE, kernel)
        return closed

    def _largest_component_3d(self, mask: np.ndarray) -> np.ndarray:
        """Retain only the largest connected component across the 3D volume."""
        labelled, n_components = ndimage.label(mask)
        if n_components == 0:
            return mask.astype(np.uint8)

        sizes = ndimage.sum(mask, labelled, range(1, n_components + 1))
        largest_label = int(np.argmax(sizes)) + 1
        return (labelled == largest_label).astype(np.uint8)

    def _apply_mask(self, subject: MRISubject, brain_mask: np.ndarray) -> MRISubject:
        """Zero-out all voxels outside the brain mask for every modality."""
        mask_bool = brain_mask.astype(bool)
        return MRISubject(
            subject_id=subject.subject_id,
            t1=_mask_array(subject.t1, mask_bool),
            t1ce=_mask_array(subject.t1ce, mask_bool),
            t2=_mask_array(subject.t2, mask_bool),
            flair=_mask_array(subject.flair, mask_bool),
            seg=subject.seg,  # Labels are not masked — retain original extent
            metadata=subject.metadata,
        )


def _mask_array(arr: np.ndarray, mask: np.ndarray) -> np.ndarray:
    out = arr.copy()
    out[~mask] = 0.0
    return out


def _spherical_structuring_element(radius: int) -> np.ndarray:
    """Create a 3D spherical binary structuring element."""
    diameter = 2 * radius + 1
    grid = np.mgrid[-radius:radius + 1, -radius:radius + 1, -radius:radius + 1]
    sphere = (grid[0] ** 2 + grid[1] ** 2 + grid[2] ** 2) <= radius ** 2
    return sphere.astype(bool)
