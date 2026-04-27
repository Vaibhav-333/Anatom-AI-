"""
Tests for src/ui/viewer3d.py

All tests run CPU-only; no GPU or display required.
"""

import numpy as np
import pytest
import plotly.graph_objects as go

from src.ui.viewer3d import build_tumor_mesh, build_brain_slice_traces

SHAPE = (30, 30, 30)
SPACING = (1.0, 1.0, 1.0)


def _seg_with_classes(*class_ids, shape=SHAPE):
    seg = np.zeros(shape, dtype=np.int32)
    for cls_id, sl in zip(class_ids, [
        np.s_[5:15, 5:15, 5:15],
        np.s_[16:24, 5:15, 5:15],
        np.s_[5:12, 16:24, 5:15],
    ]):
        seg[sl] = cls_id
    return seg


class TestBuildTumorMesh:
    def test_returns_figure(self):
        seg = _seg_with_classes(1, 2, 3)
        fig = build_tumor_mesh(seg, SPACING)
        assert isinstance(fig, go.Figure)

    def test_one_trace_per_present_class(self):
        seg = _seg_with_classes(1, 2, 3)
        fig = build_tumor_mesh(seg, SPACING, classes=[1, 2, 3])
        assert len(fig.data) == 3

    def test_only_present_classes_generate_traces(self):
        # Only NCR (1) and ET (3) placed; request all three
        seg = np.zeros(SHAPE, dtype=np.int32)
        seg[5:15, 5:15, 5:15] = 1
        seg[16:25, 5:15, 5:15] = 3
        fig = build_tumor_mesh(seg, SPACING, classes=[1, 2, 3])
        names = {t.name for t in fig.data}
        assert "NCR" in names
        assert "ET" in names
        assert "ED" not in names

    def test_all_background_returns_empty_figure(self):
        seg = np.zeros(SHAPE, dtype=np.int32)
        fig = build_tumor_mesh(seg, SPACING)
        assert len(fig.data) == 0

    def test_single_class_requested(self):
        seg = _seg_with_classes(1, 2, 3)
        fig = build_tumor_mesh(seg, SPACING, classes=[3])
        assert len(fig.data) == 1
        assert fig.data[0].name == "ET"

    def test_traces_are_mesh3d(self):
        seg = _seg_with_classes(1, 2, 3)
        fig = build_tumor_mesh(seg, SPACING)
        for trace in fig.data:
            assert isinstance(trace, go.Mesh3d)

    def test_mesh_has_vertices(self):
        seg = np.zeros(SHAPE, dtype=np.int32)
        seg[5:20, 5:20, 5:20] = 1
        fig = build_tumor_mesh(seg, SPACING, classes=[1])
        assert len(fig.data) == 1
        assert len(fig.data[0].x) > 0

    def test_voxel_spacing_scales_coordinates(self):
        """Doubling spacing should double max vertex coordinate."""
        seg = np.zeros(SHAPE, dtype=np.int32)
        seg[5:15, 5:15, 5:15] = 1
        fig1 = build_tumor_mesh(seg, (1.0, 1.0, 1.0), classes=[1])
        fig2 = build_tumor_mesh(seg, (2.0, 2.0, 2.0), classes=[1])
        if fig1.data and fig2.data:
            max1 = max(fig1.data[0].x)
            max2 = max(fig2.data[0].x)
            assert max2 == pytest.approx(max1 * 2.0, rel=0.05)

    def test_non_3d_input_raises(self):
        seg = np.zeros((10, 10), dtype=np.int32)
        with pytest.raises(ValueError):
            build_tumor_mesh(seg, SPACING)

    def test_title_in_layout(self):
        seg = _seg_with_classes(1)
        fig = build_tumor_mesh(seg, SPACING, title="Custom Title")
        assert "Custom Title" in fig.layout.title.text

    def test_small_region_handled_gracefully(self):
        """Fewer than 8 voxels — marching cubes skipped, no trace for that class."""
        seg = np.zeros(SHAPE, dtype=np.int32)
        seg[5, 5, 5] = 1   # single voxel
        fig = build_tumor_mesh(seg, SPACING, classes=[1])
        # Should return a figure without crashing (trace may or may not be present)
        assert isinstance(fig, go.Figure)


class TestBuildBrainSliceTraces:
    def test_returns_figure(self):
        vol = np.random.default_rng(0).normal(500, 80, SHAPE).astype(np.float32)
        fig = build_brain_slice_traces(vol, SPACING)
        assert isinstance(fig, go.Figure)

    def test_has_three_surface_traces(self):
        vol = np.random.default_rng(0).normal(500, 80, SHAPE).astype(np.float32)
        fig = build_brain_slice_traces(vol, SPACING)
        assert len(fig.data) == 3

    def test_all_traces_are_surface(self):
        vol = np.random.default_rng(0).normal(500, 80, SHAPE).astype(np.float32)
        fig = build_brain_slice_traces(vol, SPACING)
        for trace in fig.data:
            assert isinstance(trace, go.Surface)

    def test_non_3d_input_raises(self):
        with pytest.raises(ValueError):
            build_brain_slice_traces(np.zeros((10, 10)), SPACING)
