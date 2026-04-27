"""
volumetrics.py — Tumor sub-region volume calculation from segmentation masks.

BraTS Label Encoding
--------------------
    Class 0: Background
    Class 1: Necrotic Core (NCR)
    Class 2: Peritumoral Edema (ED)
    Class 3: Gadolinium-Enhancing Tumour (ET)

BraTS Evaluation Regions
------------------------
    WT (Whole Tumour)    : NCR + ED + ET  (classes 1, 2, 3)
    TC (Tumour Core)     : NCR + ET       (classes 1, 3)
    ET (Enhancing Tumour): ET only        (class 3)

Volume = voxel_count × voxel_spacing[0] × voxel_spacing[1] × voxel_spacing[2] mm3
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# BraTS class definitions
CLASS_NAMES = {0: "background", 1: "NCR", 2: "ED", 3: "ET"}
NUM_CLASSES = 4


@dataclass
class VolumetricResult:
    """Per-subject volumetric measurements in mm3."""

    subject_id: str

    # Physical volume per voxel (mm3)
    voxel_volume_mm3: float

    # Per-class absolute volumes (mm3)
    volumes_mm3: Dict[str, float] = field(default_factory=dict)

    # BraTS composite region volumes (mm3)
    wt_mm3: float = 0.0   # Whole Tumour  (NCR + ED + ET)
    tc_mm3: float = 0.0   # Tumour Core   (NCR + ET)
    et_mm3: float = 0.0   # Enhancing Tumour (ET)

    # Fractions relative to total brain (non-background) volume
    fractions: Dict[str, float] = field(default_factory=dict)

    # Convenience
    total_tumor_mm3: float = 0.0   # Sum of NCR + ED + ET
    total_brain_voxels: int = 0

    def to_dict(self) -> Dict:
        return {
            "subject_id": self.subject_id,
            "voxel_volume_mm3": self.voxel_volume_mm3,
            "volumes_mm3": self.volumes_mm3,
            "wt_mm3": self.wt_mm3,
            "tc_mm3": self.tc_mm3,
            "et_mm3": self.et_mm3,
            "total_tumor_mm3": self.total_tumor_mm3,
            "fractions": self.fractions,
            "total_brain_voxels": self.total_brain_voxels,
        }


class VolumetricAnalyzer:
    """
    Compute tumor sub-region volumes from a discrete segmentation map.

    Parameters
    ----------
    num_classes : int
        Number of label classes (default 4: BG + NCR + ED + ET).
    """

    def __init__(self, num_classes: int = NUM_CLASSES) -> None:
        self.num_classes = num_classes

    def compute(
        self,
        segmentation: np.ndarray,
        voxel_spacing: Tuple[float, float, float],
        subject_id: str = "unknown",
    ) -> VolumetricResult:
        """
        Compute volumes for each class and BraTS composite regions.

        Parameters
        ----------
        segmentation : np.ndarray
            Integer label array of shape (H, W, D), values in [0, num_classes).
        voxel_spacing : (sx, sy, sz) in mm — physical size of one voxel edge.
        subject_id : str — identifier for this subject.

        Returns
        -------
        VolumetricResult with volumes in mm3 and fractions.
        """
        if segmentation.ndim != 3:
            raise ValueError(f"segmentation must be 3D, got shape {segmentation.shape}")

        voxel_vol = float(voxel_spacing[0]) * float(voxel_spacing[1]) * float(voxel_spacing[2])

        # Voxel counts per class
        volumes_mm3: Dict[str, float] = {}
        for cls_idx, cls_name in CLASS_NAMES.items():
            count = int(np.sum(segmentation == cls_idx))
            volumes_mm3[cls_name] = count * voxel_vol

        # Brain = all non-background voxels
        total_brain_voxels = int(np.sum(segmentation != 0))
        brain_vol = total_brain_voxels * voxel_vol

        # BraTS composite regions
        wt_voxels = int(np.sum((segmentation == 1) | (segmentation == 2) | (segmentation == 3)))
        tc_voxels = int(np.sum((segmentation == 1) | (segmentation == 3)))
        et_voxels = int(np.sum(segmentation == 3))

        wt_mm3 = wt_voxels * voxel_vol
        tc_mm3 = tc_voxels * voxel_vol
        et_mm3 = et_voxels * voxel_vol

        total_tumor_mm3 = wt_mm3  # WT = full tumour

        # Fractions relative to brain volume (avoid division by zero)
        safe_brain = max(brain_vol, 1.0)
        fractions: Dict[str, float] = {
            name: vol / safe_brain for name, vol in volumes_mm3.items() if name != "background"
        }
        fractions["WT"] = wt_mm3 / safe_brain
        fractions["TC"] = tc_mm3 / safe_brain
        fractions["ET"] = et_mm3 / safe_brain

        result = VolumetricResult(
            subject_id=subject_id,
            voxel_volume_mm3=voxel_vol,
            volumes_mm3=volumes_mm3,
            wt_mm3=wt_mm3,
            tc_mm3=tc_mm3,
            et_mm3=et_mm3,
            total_tumor_mm3=total_tumor_mm3,
            fractions=fractions,
            total_brain_voxels=total_brain_voxels,
        )

        logger.info(
            "Subject %s — WT=%.1f mm3  TC=%.1f mm3  ET=%.1f mm3",
            subject_id, wt_mm3, tc_mm3, et_mm3,
        )
        return result

    @staticmethod
    def compute_centroid(
        segmentation: np.ndarray,
        voxel_spacing: Tuple[float, float, float],
        classes: Tuple[int, ...] = (1, 2, 3),
    ) -> Tuple[float, float, float]:
        """
        Compute the physical centroid (mm) of the combined tumour mask.

        Parameters
        ----------
        segmentation  : (H,W,D) int array — BraTS labels.
        voxel_spacing : (sx,sy,sz) in mm.
        classes       : which label classes form the tumour (default: all three).

        Returns
        -------
        (cx, cy, cz) in mm — physical centroid of the tumour.
        Returns the centre of the volume if no tumour voxels are found.
        """
        mask = np.zeros_like(segmentation, dtype=bool)
        for c in classes:
            mask |= (segmentation == c)

        coords = np.argwhere(mask)
        if len(coords) == 0:
            # Fallback: geometric centre of the volume
            cx = segmentation.shape[0] / 2.0 * voxel_spacing[0]
            cy = segmentation.shape[1] / 2.0 * voxel_spacing[1]
            cz = segmentation.shape[2] / 2.0 * voxel_spacing[2]
            return (cx, cy, cz)

        mean_vox = coords.mean(axis=0)
        cx = float(mean_vox[0] * voxel_spacing[0])
        cy = float(mean_vox[1] * voxel_spacing[1])
        cz = float(mean_vox[2] * voxel_spacing[2])
        return (cx, cy, cz)

    @staticmethod
    def aggregate(results: list[VolumetricResult]) -> Dict[str, float]:
        """
        Average volumetric metrics across multiple subjects.

        Returns
        -------
        Dict with mean_wt_mm3, mean_tc_mm3, mean_et_mm3, std_wt_mm3, etc.
        """
        if not results:
            return {}

        wt_vals = [r.wt_mm3 for r in results]
        tc_vals = [r.tc_mm3 for r in results]
        et_vals = [r.et_mm3 for r in results]

        return {
            "mean_wt_mm3": float(np.mean(wt_vals)),
            "std_wt_mm3": float(np.std(wt_vals)),
            "mean_tc_mm3": float(np.mean(tc_vals)),
            "std_tc_mm3": float(np.std(tc_vals)),
            "mean_et_mm3": float(np.mean(et_vals)),
            "std_et_mm3": float(np.std(et_vals)),
            "n_subjects": len(results),
        }


# ── Module-level convenience functions ───────────────────────────────────────

def compute_tumor_centroid(
    segmentation: np.ndarray,
    voxel_spacing: Tuple[float, float, float],
) -> Tuple[float, float, float]:
    """
    Return the physical centroid (mm) of all tumour voxels (BraTS classes 1–3).

    Convenience wrapper around VolumetricAnalyzer.compute_centroid().
    Used by the Surgical 3D Viewer for craniotomy clip-sphere positioning.
    """
    return VolumetricAnalyzer.compute_centroid(segmentation, voxel_spacing)
