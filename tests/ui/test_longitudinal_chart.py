"""
Tests for src/ui/longitudinal_chart.py
"""

import numpy as np
import pytest
import plotly.graph_objects as go

from src.ui.longitudinal_chart import (
    build_volume_trend_chart,
    build_rano_summary_bar,
    build_delta_heatmap,
)


class TestBuildVolumeTrendChart:
    def _make(self, n=4, **kwargs):
        days = list(range(0, n * 45, 45))
        wt   = [18000 - i * 2000 for i in range(n)]
        tc   = [10000 - i * 1000 for i in range(n)]
        et   = [4000  - i * 500  for i in range(n)]
        return build_volume_trend_chart(days, wt, tc, et, **kwargs)

    def test_returns_figure(self):
        assert isinstance(self._make(), go.Figure)

    def test_has_three_traces(self):
        """One trace for each of WT, TC, ET."""
        fig = self._make()
        assert len(fig.data) == 3

    def test_trace_names_include_regions(self):
        fig = self._make()
        names = [t.name for t in fig.data]
        assert any("WT" in n for n in names)
        assert any("TC" in n for n in names)
        assert any("ET" in n for n in names)

    def test_x_values_match_days(self):
        days = [0, 30, 90, 180]
        wt = [10000, 9000, 7000, 5000]
        tc = [6000, 5000, 4000, 3000]
        et = [2000, 1800, 1400, 1000]
        fig = build_volume_trend_chart(days, wt, tc, et)
        assert list(fig.data[0].x) == days

    def test_subject_id_in_title(self):
        fig = self._make(subject_id="BraTS-007")
        assert "BraTS-007" in fig.layout.title.text

    def test_rano_categories_add_shapes(self):
        days = [0, 45, 90]
        wt = [10000, 8000, 5000]
        tc = [6000, 5000, 3000]
        et = [2000, 1600, 1000]
        rano = [None, "PR", "PR"]
        fig = build_volume_trend_chart(days, wt, tc, et, rano_categories=rano)
        # Should have at least one shape (dashed RANO line)
        assert len(fig.layout.shapes) >= 1

    def test_mismatched_lengths_raise(self):
        with pytest.raises(ValueError):
            build_volume_trend_chart([0, 1], [100], [50, 60], [20, 30])

    def test_single_timepoint_raises(self):
        with pytest.raises(ValueError):
            build_volume_trend_chart([], [], [], [])

    def test_single_timepoint_ok(self):
        """One timepoint is valid (no trend line, just a point)."""
        fig = build_volume_trend_chart([0], [10000], [6000], [2000])
        assert isinstance(fig, go.Figure)

    def test_decreasing_volumes_valid(self):
        """Volume shrinkage (complete response) should not error."""
        fig = build_volume_trend_chart(
            [0, 45, 90, 180],
            [20000, 10000, 2000, 400],
            [12000, 6000, 1200, 200],
            [4000, 2000, 400, 80],
        )
        assert isinstance(fig, go.Figure)


class TestBuildRanoSummaryBar:
    def test_returns_figure(self):
        fig = build_rano_summary_bar(
            ["S1", "S2", "S3", "S4"],
            ["CR", "PR", "SD", "PD"],
        )
        assert isinstance(fig, go.Figure)

    def test_has_one_bar_trace(self):
        fig = build_rano_summary_bar(["A", "B"], ["PR", "SD"])
        assert len(fig.data) == 1

    def test_bar_is_horizontal(self):
        fig = build_rano_summary_bar(["A", "B"], ["PR", "PD"])
        assert fig.data[0].orientation == "h"

    def test_mismatched_lengths_raise(self):
        with pytest.raises(ValueError):
            build_rano_summary_bar(["A", "B"], ["CR"])

    def test_all_same_category(self):
        fig = build_rano_summary_bar(["A", "B", "C"], ["PD", "PD", "PD"])
        assert isinstance(fig, go.Figure)


class TestBuildDeltaHeatmap:
    def _wt_series(self, n_subjects=3, n_timepoints=4):
        rng = np.random.default_rng(5)
        series = []
        for _ in range(n_subjects):
            baseline = rng.uniform(10000, 20000)
            vols = [baseline]
            for _ in range(n_timepoints - 1):
                vols.append(max(vols[-1] * rng.uniform(0.8, 1.2), 0))
            series.append(vols)
        return series

    def test_returns_figure(self):
        series = self._wt_series()
        fig = build_delta_heatmap(
            subjects=["S1", "S2", "S3"],
            days=[45, 90, 135],
            wt_series=series,
        )
        assert isinstance(fig, go.Figure)

    def test_has_heatmap_trace(self):
        series = self._wt_series()
        fig = build_delta_heatmap(["S1", "S2"], [45, 90], series[:2])
        assert isinstance(fig.data[0], go.Heatmap)

    def test_matrix_shape(self):
        series = self._wt_series(n_subjects=2, n_timepoints=4)
        fig = build_delta_heatmap(["S1", "S2"], [45, 90, 135], series)
        z = np.array(fig.data[0].z)
        # 2 subjects × 3 follow-up days
        assert z.shape == (2, 3)

    def test_mismatched_subjects_raises(self):
        with pytest.raises(ValueError):
            build_delta_heatmap(["S1", "S2"], [45], [[1000, 900], [2000, 1800], [3000, 2700]])

    def test_baseline_row_is_zero(self):
        """Percentage change at day 0 (baseline) is always 0%."""
        # Our function only computes follow-up columns, so z has n_days columns.
        # The first column corresponds to days[0], not the baseline itself.
        series = [[10000, 10000]]   # no change → pct = 0
        fig = build_delta_heatmap(["S1"], [45], series)
        z = np.array(fig.data[0].z)
        assert z[0, 0] == pytest.approx(0.0, abs=0.01)
