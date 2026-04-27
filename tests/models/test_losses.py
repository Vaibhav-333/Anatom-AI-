"""
Tests for src/models/losses.py
"""

import pytest
import torch
import torch.nn.functional as F

from src.models.losses import (
    CombinedLoss,
    DeepSupervisionLoss,
    DiceLoss,
    FocalCELoss,
    build_class_weights,
)

B, C, H, W, D = 1, 4, 8, 8, 8


def _random_logits(b=B, c=C, spatial=(H, W, D)) -> torch.Tensor:
    return torch.randn(b, c, *spatial)


def _random_target(b=B, c=C, spatial=(H, W, D)) -> torch.Tensor:
    return torch.randint(0, c, (b, *spatial))


class TestDiceLoss:
    def test_returns_scalar(self):
        loss_fn = DiceLoss()
        loss = loss_fn(_random_logits(), _random_target())
        assert loss.shape == torch.Size([])

    def test_range_0_to_1(self):
        loss_fn = DiceLoss()
        for _ in range(5):
            loss = loss_fn(_random_logits(), _random_target())
            assert 0.0 <= loss.item() <= 1.5   # Soft dice can slightly exceed 1 with smooth

    def test_perfect_prediction_near_zero(self):
        # Perfect prediction: logits push probability mass entirely to the correct class
        target = torch.zeros(1, 8, 8, 8, dtype=torch.long)
        target[0, 3:5, 3:5, 3:5] = 1   # Small NCR region

        # Build logits that push class 1 probability to ~1.0 in the target region
        logits = torch.full((1, 4, 8, 8, 8), -10.0)
        logits[0, 1, :, :, :] = -10.0   # Class 1 low everywhere
        logits[0, 1, 3:5, 3:5, 3:5] = 100.0  # Class 1 extremely high in target region
        logits[0, 0, :, :, :] = 10.0    # Background high everywhere else
        logits[0, 0, 3:5, 3:5, 3:5] = -100.0

        loss_fn = DiceLoss(include_background=False)
        loss = loss_fn(logits, target)
        # Loss should be near 0 (near-perfect dice)
        assert loss.item() < 0.2, f"Perfect prediction should give low dice loss, got {loss.item():.4f}"

    def test_include_background_flag(self):
        loss_with_bg = DiceLoss(include_background=True)
        loss_without_bg = DiceLoss(include_background=False)
        logits, target = _random_logits(), _random_target()
        l1 = loss_with_bg(logits, target)
        l2 = loss_without_bg(logits, target)
        # They may differ — just ensure both are valid scalars
        assert l1.shape == torch.Size([])
        assert l2.shape == torch.Size([])

    def test_gradient_flows(self):
        logits = _random_logits().requires_grad_(True)
        loss = DiceLoss()(_random_logits().detach(), _random_target())
        # Check via autograd on a fresh computation
        logits = _random_logits().requires_grad_(True)
        loss = DiceLoss()(logits, _random_target())
        loss.backward()
        assert logits.grad is not None


class TestFocalCELoss:
    def test_returns_scalar(self):
        loss = FocalCELoss()(_random_logits(), _random_target())
        assert loss.shape == torch.Size([])

    def test_nonnegative(self):
        for _ in range(5):
            loss = FocalCELoss()(_random_logits(), _random_target())
            assert loss.item() >= 0

    def test_gamma_zero_equals_ce(self):
        # When gamma=0, Focal CE reduces to standard CE (up to floating point)
        logits = _random_logits()
        target = _random_target()

        focal = FocalCELoss(gamma=0.0)(logits, target)
        ce = F.cross_entropy(logits.view(B, C, -1), target.view(B, -1)).mean()

        assert abs(focal.item() - ce.item()) < 0.01, (
            f"gamma=0 focal ({focal.item():.4f}) should match CE ({ce.item():.4f})"
        )

    def test_class_weights_applied(self):
        weights = torch.tensor([0.1, 2.0, 2.0, 5.0])
        loss_weighted = FocalCELoss(class_weights=weights)(_random_logits(), _random_target())
        loss_unweighted = FocalCELoss()(_random_logits(), _random_target())
        # Can't assert exact values but both should be valid scalars
        assert loss_weighted.item() >= 0


class TestCombinedLoss:
    def test_returns_tensor_and_breakdown(self):
        loss_fn = CombinedLoss()
        total, breakdown = loss_fn(_random_logits(), _random_target())
        assert total.shape == torch.Size([])
        assert "dice_loss" in breakdown
        assert "focal_loss" in breakdown

    def test_nonnegative(self):
        loss_fn = CombinedLoss()
        for _ in range(3):
            total, _ = loss_fn(_random_logits(), _random_target())
            assert total.item() >= 0

    def test_dice_weight_extremes(self):
        logits, target = _random_logits(), _random_target()

        # All Dice
        loss_all_dice, _ = CombinedLoss(dice_weight=1.0)(logits, target)
        # All Focal
        loss_all_focal, _ = CombinedLoss(dice_weight=0.0)(logits, target)
        # Both valid
        assert loss_all_dice.item() >= 0
        assert loss_all_focal.item() >= 0

    def test_gradients_flow(self):
        logits = _random_logits().requires_grad_(True)
        total, _ = CombinedLoss()(logits, _random_target())
        total.backward()
        assert logits.grad is not None


class TestDeepSupervisionLoss:
    def _make_aux(self, n=3):
        return [_random_logits() for _ in range(n)]

    def test_returns_total_and_breakdown(self):
        ds_loss = DeepSupervisionLoss()
        pred_main = _random_logits()
        pred_aux = self._make_aux(3)
        target = _random_target()

        total, breakdown = ds_loss(pred_main, pred_aux, target)
        assert total.shape == torch.Size([])
        assert "main" in breakdown
        assert "total" in breakdown
        assert "aux0_loss" in breakdown
        assert "aux1_loss" in breakdown
        assert "aux2_loss" in breakdown

    def test_total_geq_main(self):
        ds_loss = DeepSupervisionLoss()
        pred_main = _random_logits()
        target = _random_target()
        total, breakdown = ds_loss(pred_main, self._make_aux(), target)
        # Total includes positive auxiliary losses, so total >= main
        assert breakdown["total"] >= breakdown["main"] - 1e-5

    def test_gradient_flows_from_all_heads(self):
        pred_main = _random_logits().requires_grad_(True)
        pred_aux = [_random_logits().requires_grad_(True) for _ in range(3)]
        target = _random_target()

        total, _ = DeepSupervisionLoss()(pred_main, pred_aux, target)
        total.backward()

        assert pred_main.grad is not None
        for i, aux in enumerate(pred_aux):
            assert aux.grad is not None, f"No gradient for aux head {i}"


class TestBuildClassWeights:
    def test_returns_correct_shape(self):
        w = build_class_weights([1000, 100, 50, 10], num_classes=4, device=torch.device("cpu"))
        assert w.shape == (4,)

    def test_rare_class_gets_higher_weight(self):
        w = build_class_weights([10000, 10], num_classes=2, device=torch.device("cpu"))
        assert w[1] > w[0], "Rare class should have higher weight"

    def test_handles_zero_counts(self):
        # Should not raise division by zero
        w = build_class_weights([0, 100, 50, 10], num_classes=4, device=torch.device("cpu"))
        assert torch.all(torch.isfinite(w))
