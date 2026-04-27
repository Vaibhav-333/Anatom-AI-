"""
Tests for src/analytics/explainability.py

All tests run on CPU with a tiny UNet3D (base_channels=4) to keep them fast.
No GPU required.
"""

import pytest
import torch
import numpy as np

from src.models.unet3d import UNet3D
from src.analytics.explainability import GradCAM3D, UncertaintyEstimator, UncertaintyResult

# Small spatial size so tests are fast
SPATIAL = (16, 16, 16)
B, C, NUM_CLASSES = 1, 4, 4


def _tiny_model(deep_supervision=True):
    return UNet3D(
        in_channels=C,
        num_classes=NUM_CLASSES,
        base_channels=4,
        deep_supervision=deep_supervision,
        dropout_p=0.5,   # High dropout so MC variance is detectable
    )


def _make_input():
    return torch.randn(B, C, *SPATIAL)


# ---------------------------------------------------------------------------
# UncertaintyEstimator tests
# ---------------------------------------------------------------------------

class TestUncertaintyEstimator:
    def test_mean_probs_shape(self):
        model = _tiny_model()
        est = UncertaintyEstimator(n_samples=3)
        result = est.estimate(model, _make_input())
        assert result.mean_probs.shape == (NUM_CLASSES, *SPATIAL)

    def test_variance_shape(self):
        model = _tiny_model()
        result = UncertaintyEstimator(n_samples=3).estimate(model, _make_input())
        assert result.variance.shape == (NUM_CLASSES, *SPATIAL)

    def test_entropy_shape(self):
        model = _tiny_model()
        result = UncertaintyEstimator(n_samples=3).estimate(model, _make_input())
        assert result.entropy.shape == SPATIAL

    def test_predicted_class_shape(self):
        model = _tiny_model()
        result = UncertaintyEstimator(n_samples=3).estimate(model, _make_input())
        assert result.predicted_class.shape == SPATIAL

    def test_mean_probs_sum_to_one(self):
        model = _tiny_model()
        result = UncertaintyEstimator(n_samples=3).estimate(model, _make_input())
        prob_sum = result.mean_probs.sum(axis=0)   # sum over classes
        np.testing.assert_allclose(prob_sum, np.ones(SPATIAL), atol=1e-5)

    def test_variance_nonnegative(self):
        model = _tiny_model()
        result = UncertaintyEstimator(n_samples=3).estimate(model, _make_input())
        assert np.all(result.variance >= 0.0)

    def test_entropy_nonnegative(self):
        model = _tiny_model()
        result = UncertaintyEstimator(n_samples=3).estimate(model, _make_input())
        assert np.all(result.entropy >= 0.0)

    def test_n_samples_stored(self):
        model = _tiny_model()
        result = UncertaintyEstimator(n_samples=7).estimate(model, _make_input())
        assert result.n_samples == 7

    def test_model_returns_to_eval_after(self):
        model = _tiny_model()
        model.eval()
        UncertaintyEstimator(n_samples=3).estimate(model, _make_input())
        # Model should be restored to eval (was_training=False)
        assert not model.training

    def test_model_returns_to_train_after(self):
        model = _tiny_model()
        model.train()
        UncertaintyEstimator(n_samples=3).estimate(model, _make_input())
        # Model should be restored to train mode
        assert model.training

    def test_batch_size_1_required(self):
        model = _tiny_model()
        x_batch = torch.randn(2, C, *SPATIAL)
        with pytest.raises(ValueError, match="batch_size=1"):
            UncertaintyEstimator(n_samples=3).estimate(model, x_batch)

    def test_n_samples_must_be_at_least_2(self):
        with pytest.raises(ValueError):
            UncertaintyEstimator(n_samples=1)

    def test_high_dropout_produces_nonzero_variance(self):
        # With dropout_p=0.5 and 20 samples, variance must be detectable.
        # Seed both weight-init and input so the result is deterministic
        # regardless of which tests ran before this one.
        torch.manual_seed(7)
        model = _tiny_model(deep_supervision=False)
        torch.manual_seed(7)
        result = UncertaintyEstimator(n_samples=20).estimate(model, _make_input())
        assert result.variance.max() > 0.0

    def test_works_without_deep_supervision(self):
        model = _tiny_model(deep_supervision=False)
        result = UncertaintyEstimator(n_samples=3).estimate(model, _make_input())
        assert result.mean_probs.shape == (NUM_CLASSES, *SPATIAL)


# ---------------------------------------------------------------------------
# GradCAM3D tests
# ---------------------------------------------------------------------------

class TestGradCAM3D:
    def test_saliency_map_shape(self):
        model = _tiny_model(deep_supervision=False)
        cam = GradCAM3D(model, target_layer=model.dec0)
        saliency = cam.generate(_make_input(), target_class=0)
        cam.remove_hooks()
        assert saliency.shape == SPATIAL

    def test_saliency_values_in_0_1(self):
        model = _tiny_model(deep_supervision=False)
        cam = GradCAM3D(model, target_layer=model.dec0)
        saliency = cam.generate(_make_input(), target_class=1)
        cam.remove_hooks()
        assert saliency.min() >= 0.0
        assert saliency.max() <= 1.0

    def test_saliency_max_equals_one(self):
        """Normalisation should ensure max == 1.0 when saliency is non-trivial."""
        model = _tiny_model(deep_supervision=False)
        cam = GradCAM3D(model, target_layer=model.dec0)
        saliency = cam.generate(_make_input(), target_class=2)
        cam.remove_hooks()
        # If any activation exists, max should be 1
        if saliency.max() > 0:
            assert saliency.max() == pytest.approx(1.0, abs=1e-5)

    def test_different_target_classes_produce_different_maps(self):
        # Fixed seed ensures the random model weights produce distinct per-class gradients.
        torch.manual_seed(42)
        model = _tiny_model(deep_supervision=False)
        model.eval()
        torch.manual_seed(0)
        x = _make_input()
        cam = GradCAM3D(model, target_layer=model.dec0)
        s0 = cam.generate(x, target_class=0)
        s3 = cam.generate(x, target_class=3)
        cam.remove_hooks()
        # Different class targets must not produce bit-for-bit identical saliency maps.
        assert not np.array_equal(s0, s3)

    def test_hook_cleanup_removes_hooks(self):
        model = _tiny_model(deep_supervision=False)
        cam = GradCAM3D(model, target_layer=model.dec0)
        cam.remove_hooks()
        # After removal, internal state should remain but hooks are detached
        # (No assertion on internals — just verify remove_hooks() does not raise)

    def test_batch_size_1_required(self):
        model = _tiny_model(deep_supervision=False)
        cam = GradCAM3D(model, target_layer=model.dec0)
        x_batch = torch.randn(2, C, *SPATIAL)
        with pytest.raises(ValueError, match="batch_size=1"):
            cam.generate(x_batch, target_class=0)
        cam.remove_hooks()

    def test_works_with_encoder_target_layer(self):
        """Grad-CAM should work when targeting an encoder block too."""
        model = _tiny_model(deep_supervision=False)
        cam = GradCAM3D(model, target_layer=model.enc3)
        saliency = cam.generate(_make_input(), target_class=1)
        cam.remove_hooks()
        assert saliency.shape == SPATIAL

    def test_saliency_is_numpy_array(self):
        model = _tiny_model(deep_supervision=False)
        cam = GradCAM3D(model, target_layer=model.dec0)
        saliency = cam.generate(_make_input(), target_class=0)
        cam.remove_hooks()
        assert isinstance(saliency, np.ndarray)
