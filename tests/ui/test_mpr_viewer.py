"""
Tests for src/ui/mpr_viewer.py
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.figure
import numpy as np
import pytest

from src.ui.mpr_viewer import build_mpr_figure, build_single_slice

SHAPE = (32, 32, 24)
RNG = np.random.default_rng(7)


def _vol():
    return RNG.normal(500, 80, SHAPE).clip(1, None).astype(np.float32)


def _seg():
    seg = np.zeros(SHAPE, dtype=np.int32)
    seg[8:20, 8:20, 6:18] = 2
    seg[11:17, 11:17, 9:15] = 1
    seg[13:15, 13:15, 11:13] = 3
    return seg


class TestBuildMprFigure:
    def test_returns_matplotlib_figure(self):
        fig = build_mpr_figure(_vol())
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_has_three_axes(self):
        fig = build_mpr_figure(_vol())
        assert len(fig.axes) == 3

    def test_with_segmentation_overlay(self):
        """Should not raise when segmentation provided."""
        fig = build_mpr_figure(_vol(), segmentation=_seg())
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_mismatched_shapes_raises(self):
        vol = _vol()
        seg = np.zeros((10, 10, 10), dtype=np.int32)
        with pytest.raises(ValueError, match="shape"):
            build_mpr_figure(vol, segmentation=seg)

    def test_non_3d_volume_raises(self):
        with pytest.raises(ValueError):
            build_mpr_figure(np.zeros((10, 10)))

    def test_slice_fracs_clamped_at_zero(self):
        """slice_fracs=0.0 should not raise IndexError."""
        fig = build_mpr_figure(_vol(), slice_fracs=(0.0, 0.0, 0.0))
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_slice_fracs_clamped_at_one(self):
        """slice_fracs=1.0 should not raise IndexError."""
        fig = build_mpr_figure(_vol(), slice_fracs=(1.0, 1.0, 1.0))
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_custom_modality_name_in_title(self):
        fig = build_mpr_figure(_vol(), modality_name="FLAIR")
        title = fig.texts[0].get_text()
        assert "FLAIR" in title

    def test_constant_volume_does_not_crash(self):
        """All-constant volume: normalisation denominator = 0 must be handled."""
        vol = np.ones(SHAPE, dtype=np.float32) * 500.0
        fig = build_mpr_figure(vol)
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_no_segmentation_still_three_axes(self):
        fig = build_mpr_figure(_vol(), segmentation=None)
        assert len(fig.axes) == 3


class TestBuildSingleSlice:
    def test_returns_matplotlib_figure(self):
        fig = build_single_slice(_vol(), axis=0, slice_idx=10)
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_axis_0_axial(self):
        fig = build_single_slice(_vol(), axis=0, slice_idx=15)
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_axis_1_sagittal(self):
        fig = build_single_slice(_vol(), axis=1, slice_idx=10)
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_axis_2_coronal(self):
        fig = build_single_slice(_vol(), axis=2, slice_idx=8)
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_with_segmentation_overlay(self):
        fig = build_single_slice(_vol(), axis=0, slice_idx=10, segmentation=_seg())
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_with_continuous_overlay_map(self):
        rng = np.random.default_rng(99)
        overlay = rng.uniform(0, 1, SHAPE).astype(np.float32)
        fig = build_single_slice(_vol(), axis=0, slice_idx=10, overlay_map=overlay)
        assert isinstance(fig, matplotlib.figure.Figure)

    def test_non_3d_raises(self):
        with pytest.raises(ValueError):
            build_single_slice(np.zeros((10, 10)), axis=0, slice_idx=5)

    def test_out_of_bounds_slice_clamped(self):
        """slice_idx beyond volume depth should be silently clamped."""
        vol = _vol()
        fig = build_single_slice(vol, axis=2, slice_idx=9999)
        assert isinstance(fig, matplotlib.figure.Figure)
