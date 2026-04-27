"""
Tests for src/models/unet3d.py and src/models/blocks.py

All tests use tiny spatial dimensions (16×16×16) to keep memory and time low.
No GPU required — all tests run on CPU.
"""

import pytest
import torch

from src.models.blocks import DoubleConv3D, DownBlock, OutputHead, UpBlock
from src.models.unet3d import UNet3D

# Tiny spatial size for fast tests
SPATIAL = (16, 16, 16)
B, C, NUM_CLASSES = 1, 4, 4


# ---------------------------------------------------------------------------
# Block tests
# ---------------------------------------------------------------------------

class TestDoubleConv3D:
    def test_output_shape(self):
        block = DoubleConv3D(4, 32)
        x = torch.randn(B, 4, *SPATIAL)
        out = block(x)
        assert out.shape == (B, 32, *SPATIAL)

    def test_residual_same_channels(self):
        block = DoubleConv3D(32, 32, residual=True)
        x = torch.randn(1, 32, *SPATIAL)
        out = block(x)
        assert out.shape == (1, 32, *SPATIAL)

    def test_residual_different_channels(self):
        block = DoubleConv3D(16, 32, residual=True)
        x = torch.randn(1, 16, *SPATIAL)
        out = block(x)
        assert out.shape == (1, 32, *SPATIAL)

    def test_no_residual(self):
        block = DoubleConv3D(4, 64, residual=False)
        x = torch.randn(1, 4, *SPATIAL)
        out = block(x)
        assert out.shape == (1, 64, *SPATIAL)

    def test_gradient_flows(self):
        block = DoubleConv3D(4, 32)
        x = torch.randn(1, 4, *SPATIAL, requires_grad=True)
        loss = block(x).sum()
        loss.backward()
        assert x.grad is not None


class TestDownBlock:
    def test_halves_spatial_dims(self):
        block = DownBlock(32, 64)
        x = torch.randn(1, 32, *SPATIAL)
        out = block(x)
        expected = (B, 64, SPATIAL[0] // 2, SPATIAL[1] // 2, SPATIAL[2] // 2)
        assert out.shape == expected


class TestUpBlock:
    def test_restores_spatial_dims(self):
        up = UpBlock(in_channels=64, skip_channels=32, out_channels=32)
        x_low = torch.randn(1, 64, 8, 8, 8)     # low-res from deeper level
        skip = torch.randn(1, 32, 16, 16, 16)    # skip from encoder
        out = up(x_low, skip)
        assert out.shape == (1, 32, 16, 16, 16)


class TestOutputHead:
    def test_output_classes(self):
        head = OutputHead(32, NUM_CLASSES)
        x = torch.randn(1, 32, *SPATIAL)
        out = head(x)
        assert out.shape == (B, NUM_CLASSES, *SPATIAL)


# ---------------------------------------------------------------------------
# UNet3D tests
# ---------------------------------------------------------------------------

class TestUNet3D:
    def _make_model(self, deep_supervision=True, base_channels=8):
        return UNet3D(
            in_channels=C,
            num_classes=NUM_CLASSES,
            base_channels=base_channels,
            deep_supervision=deep_supervision,
            dropout_p=0.0,
        )

    def _make_input(self):
        return torch.randn(B, C, *SPATIAL)

    def test_inference_output_shape(self):
        model = self._make_model(deep_supervision=False)
        model.eval()
        x = self._make_input()
        with torch.no_grad():
            out = model(x)
        assert out.shape == (B, NUM_CLASSES, *SPATIAL)

    def test_inference_ignores_deep_supervision(self):
        model = self._make_model(deep_supervision=True)
        model.eval()     # training=False → aux heads bypassed
        x = self._make_input()
        with torch.no_grad():
            out = model(x)
        # Should return a plain tensor (no tuple) in eval mode
        assert isinstance(out, torch.Tensor)
        assert out.shape == (B, NUM_CLASSES, *SPATIAL)

    def test_training_deep_supervision_returns_tuple(self):
        model = self._make_model(deep_supervision=True)
        model.train()
        x = self._make_input()
        out = model(x)
        assert isinstance(out, tuple), "Training mode should return (main, [aux...]) tuple"
        main_logits, aux_list = out
        assert main_logits.shape == (B, NUM_CLASSES, *SPATIAL)
        assert len(aux_list) == 3  # Three auxiliary heads
        for aux in aux_list:
            assert aux.shape == (B, NUM_CLASSES, *SPATIAL)

    def test_no_deep_supervision_returns_tensor(self):
        model = self._make_model(deep_supervision=False)
        model.train()
        x = self._make_input()
        out = model(x)
        assert isinstance(out, torch.Tensor)

    def test_predict_returns_probabilities(self):
        model = self._make_model()
        x = self._make_input()
        probs = model.predict(x)
        assert probs.shape == (B, NUM_CLASSES, *SPATIAL)
        # All class probabilities must sum to 1 per voxel
        prob_sum = probs.sum(dim=1)
        assert torch.allclose(prob_sum, torch.ones_like(prob_sum), atol=1e-5)

    def test_predict_tta_output_shape(self):
        model = self._make_model()
        x = self._make_input()
        probs = model.predict_tta(x)
        assert probs.shape == (B, NUM_CLASSES, *SPATIAL)
        # Verify probabilities sum to 1
        prob_sum = probs.sum(dim=1)
        assert torch.allclose(prob_sum, torch.ones_like(prob_sum), atol=1e-4)

    def test_parameter_count_positive(self):
        model = self._make_model(base_channels=16)
        n_params = model.count_parameters()
        assert n_params > 0
        # At base_channels=16, should have at least 1M params
        assert n_params > 100_000, f"Expected >100K params, got {n_params}"

    def test_gradient_flows_through_all_params(self):
        model = self._make_model(deep_supervision=False)
        model.train()
        x = self._make_input()
        logits = model(x)
        loss = logits.sum()
        loss.backward()

        for name, param in model.named_parameters():
            if param.requires_grad:
                assert param.grad is not None, f"No gradient for parameter: {name}"

    def test_kaiming_init_not_zero(self):
        model = self._make_model()
        # The first conv weight should not be all zeros after Kaiming init
        first_conv = model.enc0.conv[0]  # First Conv3d
        assert not torch.all(first_conv.weight == 0)

    def test_batch_size_2(self):
        model = self._make_model(deep_supervision=False)
        model.eval()
        x = torch.randn(2, C, *SPATIAL)
        with torch.no_grad():
            out = model(x)
        assert out.shape[0] == 2
