"""
Tests for src/training/metrics.py
"""

import numpy as np
import pytest

from src.training.metrics import SegmentationMetrics, _dice, _sensitivity_precision


class TestDiceFunction:
    def test_perfect_overlap(self):
        mask = np.ones((10, 10, 10), dtype=bool)
        assert _dice(mask, mask) == pytest.approx(1.0, abs=1e-4)

    def test_no_overlap(self):
        pred = np.zeros((10, 10, 10), dtype=bool)
        pred[:5] = True
        target = np.zeros((10, 10, 10), dtype=bool)
        target[5:] = True
        score = _dice(pred, target)
        assert score == pytest.approx(0.0, abs=1e-4)

    def test_both_empty(self):
        # Both empty → perfect agreement by convention
        empty = np.zeros((10, 10, 10), dtype=bool)
        assert _dice(empty, empty) == pytest.approx(1.0, abs=1e-4)

    def test_partial_overlap(self):
        pred = np.zeros((4, 4, 4), dtype=bool)
        target = np.zeros((4, 4, 4), dtype=bool)
        pred[:2, :2, :2] = True   # 8 voxels
        target[:2, :2, :2] = True
        target[2:4, 2:4, 2:4] = True  # additional 8 voxels
        # intersection = 8, pred=8, target=16
        expected = 2 * 8 / (8 + 16)
        assert _dice(pred, target) == pytest.approx(expected, abs=0.01)


class TestSensitivityPrecision:
    def test_perfect(self):
        mask = np.ones((5, 5, 5), dtype=bool)
        sens, prec = _sensitivity_precision(mask, mask)
        assert sens == pytest.approx(1.0, abs=1e-4)
        assert prec == pytest.approx(1.0, abs=1e-4)

    def test_all_false_positive(self):
        pred = np.ones((5, 5, 5), dtype=bool)
        target = np.zeros((5, 5, 5), dtype=bool)
        _, prec = _sensitivity_precision(pred, target)
        assert prec == pytest.approx(0.0, abs=1e-4)

    def test_all_false_negative(self):
        pred = np.zeros((5, 5, 5), dtype=bool)
        target = np.ones((5, 5, 5), dtype=bool)
        sens, _ = _sensitivity_precision(pred, target)
        assert sens == pytest.approx(0.0, abs=1e-4)


class TestSegmentationMetrics:
    def _make_arrays(self, shape=(16, 16, 16)):
        """Create synthetic pred/target arrays with known overlap."""
        target = np.zeros(shape, dtype=np.int32)
        target[4:8, 4:8, 4:8] = 1    # NCR
        target[8:12, 4:8, 4:8] = 2   # ED
        target[4:8, 8:12, 4:8] = 3   # ET

        # Perfect prediction
        pred = target.copy()
        return pred, target

    def test_perfect_dice_equals_one(self):
        pred, target = self._make_arrays()
        metrics = SegmentationMetrics(compute_hd95=False)
        result = metrics.compute(pred, target, "test")

        for cls_name, dsc in result.dice_per_class.items():
            assert dsc == pytest.approx(1.0, abs=1e-3), f"Expected DSC=1.0 for {cls_name}, got {dsc}"

    def test_perfect_wt_tc_et(self):
        pred, target = self._make_arrays()
        metrics = SegmentationMetrics(compute_hd95=False)
        result = metrics.compute(pred, target, "test")

        assert result.dice_wt == pytest.approx(1.0, abs=1e-3)
        assert result.dice_tc == pytest.approx(1.0, abs=1e-3)
        assert result.dice_et == pytest.approx(1.0, abs=1e-3)

    def test_all_background_prediction(self):
        _, target = self._make_arrays()
        pred = np.zeros_like(target)
        metrics = SegmentationMetrics(compute_hd95=False)
        result = metrics.compute(pred, target, "all_bg")

        # All class dice should be 0 (empty pred, non-empty target)
        for cls_name, dsc in result.dice_per_class.items():
            assert dsc == pytest.approx(0.0, abs=0.01), f"{cls_name} should be 0, got {dsc}"

    def test_aggregate_averages_correctly(self):
        pred, target = self._make_arrays()
        metrics = SegmentationMetrics(compute_hd95=False)
        r1 = metrics.compute(pred, target, "sub1")
        r2 = metrics.compute(pred, target, "sub2")

        agg = SegmentationMetrics.aggregate([r1, r2])
        assert "dice_wt" in agg
        assert "dice_tc" in agg
        assert "dice_et" in agg
        # Perfect predictions → aggregated means should also be ~1.0
        assert agg["dice_wt"] == pytest.approx(1.0, abs=1e-3)

    def test_aggregate_empty_returns_empty(self):
        assert SegmentationMetrics.aggregate([]) == {}

    def test_hd95_perfect_prediction_is_zero(self):
        pred, target = self._make_arrays()
        metrics = SegmentationMetrics(compute_hd95=True)
        result = metrics.compute(pred, target, "hd95_test")
        for cls_name, hd in result.hd95_per_class.items():
            assert hd == pytest.approx(0.0, abs=0.01), f"HD95 for {cls_name} should be 0, got {hd}"

    def test_result_subject_id_preserved(self):
        pred, target = self._make_arrays()
        metrics = SegmentationMetrics(compute_hd95=False)
        result = metrics.compute(pred, target, "BraTS-007")
        assert result.subject_id == "BraTS-007"
