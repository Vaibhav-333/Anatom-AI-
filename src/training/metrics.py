"""
metrics.py — Segmentation evaluation metrics for BraTS tumour segmentation.

Primary metrics (BraTS challenge standard)
-------------------------------------------
Dice Similarity Coefficient (DSC)
    Measures volumetric overlap between prediction and ground truth.
    DSC = 2|P ∩ G| / (|P| + |G|)
    Reported per class and as mean over foreground classes.

Hausdorff Distance 95th Percentile (HD95)
    Surface distance metric. Robust to outliers compared to standard HD.
    Lower is better (mm). Clinically important — HD95 > 15 mm is typically
    unacceptable for neurosurgical planning.

Sensitivity (Recall) and Precision
    Reported per class for detailed failure analysis.

BraTS Hierarchical Sub-Region Metrics (standard evaluation protocol)
    WT (Whole Tumour)         : classes 1+2+3 vs background
    TC (Tumour Core)          : classes 1+3 vs background
    ET (Enhancing Tumour)     : class 3 vs background

All metrics operate on numpy arrays (CPU) — detach tensors before calling.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# BraTS class names
CLASS_NAMES = ["Background", "NCR", "ED", "ET"]

# BraTS hierarchical sub-regions: (name → set of class indices)
BRATS_REGIONS: Dict[str, List[int]] = {
    "WT": [1, 2, 3],   # Whole Tumour
    "TC": [1, 3],       # Tumour Core
    "ET": [3],          # Enhancing Tumour
}


@dataclass
class SegmentationResult:
    """Per-subject segmentation metrics."""
    subject_id: str
    dice_per_class: Dict[str, float] = field(default_factory=dict)
    hd95_per_class: Dict[str, float] = field(default_factory=dict)
    sensitivity_per_class: Dict[str, float] = field(default_factory=dict)
    precision_per_class: Dict[str, float] = field(default_factory=dict)
    # BraTS hierarchical region metrics
    dice_wt: float = 0.0
    dice_tc: float = 0.0
    dice_et: float = 0.0
    hd95_wt: float = 0.0
    hd95_tc: float = 0.0
    hd95_et: float = 0.0


class SegmentationMetrics:
    """
    Compute standard BraTS segmentation metrics from prediction and ground truth.

    Parameters
    ----------
    num_classes : int
        Total number of classes including background (default 4).
    compute_hd95 : bool
        Whether to compute Hausdorff95. Slow for large volumes — disable
        during training and enable for final evaluation only.
    voxel_spacing_mm : tuple[float, float, float]
        Physical voxel size for Hausdorff distance in mm.
    """

    def __init__(
        self,
        num_classes: int = 4,
        compute_hd95: bool = True,
        voxel_spacing_mm: tuple = (1.0, 1.0, 1.0),
    ) -> None:
        self.num_classes = num_classes
        self.compute_hd95 = compute_hd95
        self.voxel_spacing = np.array(voxel_spacing_mm)

    def compute(
        self,
        pred: np.ndarray,
        target: np.ndarray,
        subject_id: str = "unknown",
    ) -> SegmentationResult:
        """
        Compute all metrics for a single subject.

        Parameters
        ----------
        pred   : (H, W, D) integer array of predicted class labels.
        target : (H, W, D) integer array of ground-truth class labels.
        subject_id : identifier for logging.

        Returns
        -------
        SegmentationResult with all computed metrics.
        """
        assert pred.shape == target.shape, f"Shape mismatch: {pred.shape} vs {target.shape}"

        result = SegmentationResult(subject_id=subject_id)

        # Per-class metrics (skip background class 0)
        for c in range(1, self.num_classes):
            name = CLASS_NAMES[c]
            p_mask = pred == c
            g_mask = target == c

            dsc = _dice(p_mask, g_mask)
            sens, prec = _sensitivity_precision(p_mask, g_mask)

            result.dice_per_class[name] = round(dsc, 4)
            result.sensitivity_per_class[name] = round(sens, 4)
            result.precision_per_class[name] = round(prec, 4)

            if self.compute_hd95:
                hd = _hausdorff95(p_mask, g_mask, self.voxel_spacing)
                result.hd95_per_class[name] = round(hd, 2)

        # BraTS hierarchical regions
        for region_name, class_ids in BRATS_REGIONS.items():
            p_mask = np.isin(pred, class_ids)
            g_mask = np.isin(target, class_ids)

            dsc = _dice(p_mask, g_mask)
            setattr(result, f"dice_{region_name.lower()}", round(dsc, 4))

            if self.compute_hd95:
                hd = _hausdorff95(p_mask, g_mask, self.voxel_spacing)
                setattr(result, f"hd95_{region_name.lower()}", round(hd, 2))

        logger.debug(
            "Metrics %s  WT=%.3f  TC=%.3f  ET=%.3f",
            subject_id, result.dice_wt, result.dice_tc, result.dice_et,
        )
        return result

    @staticmethod
    def aggregate(results: List[SegmentationResult]) -> Dict[str, float]:
        """
        Average metrics across multiple subjects.

        Parameters
        ----------
        results : list of per-subject SegmentationResult.

        Returns
        -------
        dict of metric_name → mean value.
        """
        if not results:
            return {}

        summary: Dict[str, List[float]] = {}

        for r in results:
            for name, val in r.dice_per_class.items():
                summary.setdefault(f"dice_{name}", []).append(val)
            for name, val in r.hd95_per_class.items():
                summary.setdefault(f"hd95_{name}", []).append(val)
            for attr in ["dice_wt", "dice_tc", "dice_et", "hd95_wt", "hd95_tc", "hd95_et"]:
                summary.setdefault(attr, []).append(getattr(r, attr))

        return {k: float(np.mean(v)) for k, v in summary.items()}

    def from_logits(
        self,
        logits: "torch.Tensor",
        target: "torch.Tensor",
        subject_id: str = "unknown",
    ) -> SegmentationResult:
        """
        Convenience wrapper: convert logits/target tensors to numpy and compute.

        Parameters
        ----------
        logits : (B, C, H, W, D) or (C, H, W, D) raw logit tensor.
        target : (B, H, W, D) or (H, W, D) integer label tensor.
        """
        import torch
        if logits.dim() == 5:
            logits = logits[0]       # Take first batch element
            target = target[0]

        pred_np = logits.argmax(dim=0).cpu().numpy().astype(np.int32)
        target_np = target.cpu().numpy().astype(np.int32)
        return self.compute(pred_np, target_np, subject_id)


# ---------------------------------------------------------------------------
# Internal metric functions
# ---------------------------------------------------------------------------

def _dice(pred: np.ndarray, target: np.ndarray, smooth: float = 1e-6) -> float:
    """Dice coefficient between two binary masks."""
    intersection = float((pred & target).sum())
    union = float(pred.sum() + target.sum())
    if union == 0:
        return 1.0   # Both empty → perfect agreement
    return (2.0 * intersection + smooth) / (union + smooth)


def _sensitivity_precision(
    pred: np.ndarray, target: np.ndarray
) -> tuple[float, float]:
    """Sensitivity (recall) and precision for binary masks."""
    tp = float((pred & target).sum())
    fp = float((pred & ~target).sum())
    fn = float((~pred & target).sum())

    sensitivity = tp / (tp + fn + 1e-8) if (tp + fn) > 0 else 1.0
    precision   = tp / (tp + fp + 1e-8) if (tp + fp) > 0 else 1.0
    return sensitivity, precision


def _hausdorff95(
    pred: np.ndarray,
    target: np.ndarray,
    spacing: np.ndarray,
) -> float:
    """
    Compute the 95th-percentile Hausdorff distance in mm.

    Falls back to 0.0 if either mask is empty (avoids inf/NaN in logs).
    Uses scipy distance_transform_edt for efficient surface computation.
    """
    from scipy.ndimage import distance_transform_edt

    if not pred.any() and not target.any():
        return 0.0
    if not pred.any() or not target.any():
        return float("inf")

    # Surface voxels via erosion (border detection)
    pred_surface  = _surface_voxels(pred)
    target_surface = _surface_voxels(target)

    # Distance transforms
    dt_pred   = distance_transform_edt(~pred,   sampling=spacing)
    dt_target = distance_transform_edt(~target, sampling=spacing)

    dist_pred_to_target = dt_target[pred_surface]
    dist_target_to_pred = dt_pred[target_surface]

    all_distances = np.concatenate([dist_pred_to_target, dist_target_to_pred])
    return float(np.percentile(all_distances, 95))


def _surface_voxels(mask: np.ndarray) -> np.ndarray:
    """Return a boolean mask of surface (border) voxels using 6-connectivity erosion."""
    from scipy.ndimage import binary_erosion
    eroded = binary_erosion(mask)
    return mask & ~eroded
