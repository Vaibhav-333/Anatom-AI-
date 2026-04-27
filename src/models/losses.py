"""
losses.py — Loss functions for 3D brain tumour segmentation.

Class imbalance in BraTS is severe:
    Background : ~85–90% of voxels
    Edema      : ~5–8%
    NCR        : ~2–3%
    ET         : ~1–2%

Strategy
--------
1. DiceLoss         — Class-wise soft Dice, averaged over foreground classes.
                       Dice is inherently recall-biased and handles imbalance
                       without explicit class weighting.

2. FocalCELoss      — Cross-entropy with focal modulation (γ=2). Downweights
                       easy background voxels and focuses learning on hard,
                       misclassified voxels near tumour boundaries.

3. CombinedLoss     — Weighted sum: α*Dice + (1-α)*FocalCE.
                       Default α=0.5. This is the primary training loss.

4. DeepSupervisionLoss — Wraps CombinedLoss. Applies it to the main output
                         and each auxiliary head, with geometrically decaying
                         weights. Implements Elite Feature A.

All losses accept:
    pred  : (B, C, H, W, D) raw logits (NOT softmax/sigmoid applied)
    target: (B, H, W, D)    integer class labels [0, C-1]
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import List, Optional


class DiceLoss(nn.Module):
    """
    Soft multi-class Dice loss.

    Computes per-class Dice and returns 1 - mean_dice over the specified
    class subset. Background (class 0) is excluded by default since it
    dominates and makes the metric trivially high.

    Parameters
    ----------
    include_background : bool
        If False (default), class 0 is excluded from the Dice average.
    smooth : float
        Laplace smoothing to prevent division by zero on empty label maps.
    """

    def __init__(self, include_background: bool = False, smooth: float = 1e-5) -> None:
        super().__init__()
        self.include_background = include_background
        self.smooth = smooth

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        """
        Parameters
        ----------
        pred   : (B, C, H, W, D) — raw logits.
        target : (B, H, W, D)    — integer class labels.

        Returns
        -------
        Scalar Dice loss (1 - mean soft Dice over foreground classes).
        """
        num_classes = pred.shape[1]
        pred_soft = torch.softmax(pred, dim=1)

        # One-hot encode target: (B, C, H, W, D)
        target_one_hot = F.one_hot(target.long(), num_classes).permute(0, 4, 1, 2, 3).float()

        start_class = 0 if self.include_background else 1
        dice_scores = []

        for c in range(start_class, num_classes):
            p = pred_soft[:, c]      # (B, H, W, D)
            g = target_one_hot[:, c] # (B, H, W, D)

            intersection = (p * g).sum()
            union = p.sum() + g.sum()

            dice = (2.0 * intersection + self.smooth) / (union + self.smooth)
            dice_scores.append(dice)

        mean_dice = torch.stack(dice_scores).mean()
        return 1.0 - mean_dice


class FocalCELoss(nn.Module):
    """
    Focal Cross-Entropy loss (Lin et al. 2017).

    Modulates the standard cross-entropy so that well-classified (easy)
    examples contribute less to the gradient. Focuses the network on the
    hard, misclassified voxels — typically the tumour boundary.

    L_focal = -α_t * (1 - p_t)^γ * log(p_t)

    Parameters
    ----------
    gamma : float
        Focusing parameter. 0 = standard CE. 2 is the canonical default.
    class_weights : Tensor | None
        Per-class weights (C,) for additional class balancing. If None,
        weights are uniform.
    """

    def __init__(
        self,
        gamma: float = 2.0,
        class_weights: Optional[torch.Tensor] = None,
    ) -> None:
        super().__init__()
        self.gamma = gamma
        self.register_buffer("class_weights", class_weights)

    def forward(self, pred: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
        """
        Parameters
        ----------
        pred   : (B, C, H, W, D) raw logits.
        target : (B, H, W, D) integer labels.

        Returns
        -------
        Scalar focal loss.
        """
        # Standard log-softmax for numerical stability
        log_probs = F.log_softmax(pred, dim=1)  # (B, C, H, W, D)
        probs = torch.exp(log_probs)

        # Gather per-voxel log-prob and prob for the true class
        target_long = target.long()
        log_pt = log_probs.gather(1, target_long.unsqueeze(1)).squeeze(1)  # (B, H, W, D)
        pt = probs.gather(1, target_long.unsqueeze(1)).squeeze(1)

        focal_weight = (1.0 - pt) ** self.gamma
        loss = -focal_weight * log_pt

        # Apply class weights
        if self.class_weights is not None:
            w = self.class_weights.to(pred.device)
            per_voxel_weight = w[target_long]
            loss = loss * per_voxel_weight

        return loss.mean()


class CombinedLoss(nn.Module):
    """
    Primary training loss: α * DiceLoss + (1-α) * FocalCELoss.

    The Dice term handles global class imbalance; the Focal CE term sharpens
    learning on hard voxels. Together they are more robust than either alone.

    Parameters
    ----------
    dice_weight : float
        Weight for the Dice component (α). Default 0.5.
    focal_gamma : float
        Focal parameter for FocalCELoss. Default 2.0.
    class_weights : Tensor | None
        Per-class weights for the CE component.
    include_background_in_dice : bool
        Typically False — background Dice is trivially high.
    """

    def __init__(
        self,
        dice_weight: float = 0.5,
        focal_gamma: float = 2.0,
        class_weights: Optional[torch.Tensor] = None,
        include_background_in_dice: bool = False,
    ) -> None:
        super().__init__()
        self.dice_weight = dice_weight
        self.ce_weight = 1.0 - dice_weight
        self.dice_loss = DiceLoss(include_background=include_background_in_dice)
        self.focal_loss = FocalCELoss(gamma=focal_gamma, class_weights=class_weights)

    def forward(
        self, pred: torch.Tensor, target: torch.Tensor
    ) -> tuple[torch.Tensor, dict]:
        """
        Returns
        -------
        total_loss : Scalar combined loss tensor.
        breakdown  : Dict with individual loss values for logging.
        """
        d_loss = self.dice_loss(pred, target)
        f_loss = self.focal_loss(pred, target)
        total = self.dice_weight * d_loss + self.ce_weight * f_loss
        return total, {"dice_loss": d_loss.item(), "focal_loss": f_loss.item()}


class DeepSupervisionLoss(nn.Module):
    """
    Wraps CombinedLoss with geometrically weighted auxiliary outputs.

    During training the 3D U-Net returns:
        (main_logits, [aux3_logits, aux2_logits, aux1_logits])

    Loss is computed at each level and combined:
        total = Σ_i  w_i * CombinedLoss(output_i, target)

    Weights [1.0, 0.5, 0.25, 0.125] decay by 0.5 from main → coarsest.
    This keeps the main output dominant while regularising auxiliary levels.

    Parameters
    ----------
    base_loss : CombinedLoss instance (shared across all levels).
    ds_weights : list of floats, one per auxiliary level (coarsest → finest).
                 Main output always has weight 1.0.
    """

    def __init__(
        self,
        base_loss: Optional[CombinedLoss] = None,
        ds_weights: Optional[List[float]] = None,
    ) -> None:
        super().__init__()
        self.base_loss = base_loss or CombinedLoss()
        self.ds_weights = ds_weights or [0.5, 0.25, 0.125]

    def forward(
        self,
        pred_main: torch.Tensor,
        pred_aux: List[torch.Tensor],
        target: torch.Tensor,
    ) -> tuple[torch.Tensor, dict]:
        """
        Parameters
        ----------
        pred_main : (B, C, H, W, D) — main decoder output logits.
        pred_aux  : list of (B, C, H, W, D) — auxiliary head logits (all at full res).
        target    : (B, H, W, D) — integer class labels.

        Returns
        -------
        total_loss : Scalar.
        breakdown  : Dict with main + auxiliary loss values.
        """
        main_loss, main_breakdown = self.base_loss(pred_main, target)
        total = main_loss
        breakdown = {"main": main_loss.item(), **{f"main_{k}": v for k, v in main_breakdown.items()}}

        for i, (aux_pred, w) in enumerate(zip(pred_aux, self.ds_weights)):
            aux_loss, _ = self.base_loss(aux_pred, target)
            total = total + w * aux_loss
            breakdown[f"aux{i}_loss"] = aux_loss.item()

        breakdown["total"] = total.item()
        return total, breakdown


def build_class_weights(
    label_counts: List[int],
    num_classes: int,
    device: torch.device,
) -> torch.Tensor:
    """
    Compute inverse-frequency class weights from voxel count statistics.

    Parameters
    ----------
    label_counts : list of voxel counts per class across the training set.
    num_classes  : total number of classes.
    device       : target device.

    Returns
    -------
    weights : (C,) float tensor, normalised so sum = num_classes.
    """
    counts = torch.tensor(label_counts, dtype=torch.float32)
    counts = counts.clamp(min=1)                   # Avoid zero division
    weights = 1.0 / counts
    weights = weights / weights.sum() * num_classes
    return weights.to(device)
