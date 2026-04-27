"""
Tests for src/analytics/longitudinal.py
"""

import numpy as np
import pytest

from src.analytics.longitudinal import LongitudinalTracker, LongitudinalReport
from src.analytics.volumetrics import VolumetricAnalyzer, VolumetricResult

SPACING = (1.0, 1.0, 1.0)


def _make_result(wt_mm3: float, tc_mm3: float, et_mm3: float, sid: str = "s") -> VolumetricResult:
    """Build a minimal VolumetricResult with the given region volumes."""
    r = VolumetricResult(subject_id=sid, voxel_volume_mm3=1.0)
    r.wt_mm3 = wt_mm3
    r.tc_mm3 = tc_mm3
    r.et_mm3 = et_mm3
    return r


class TestRANOClassification:
    """Verify RANO category assignment across boundary conditions."""

    def test_near_zero_wt_is_cr(self):
        r1 = _make_result(50000, 30000, 10000)
        r2 = _make_result(100, 60, 20)    # < 500 mm³ → CR
        report = LongitudinalTracker().compare(r1, r2, days_elapsed=90.0)
        assert report.rano_category == "CR"

    def test_95_percent_reduction_is_cr(self):
        r1 = _make_result(10000, 6000, 2000)
        r2 = _make_result(450, 270, 90)   # 95.5% reduction, but vol > 500
        # 450 < 500 so this hits the absolute CR threshold — let's use a bigger number
        r2 = _make_result(495, 270, 90)   # <500 → CR
        report = LongitudinalTracker().compare(r1, r2, days_elapsed=30.0)
        assert report.rano_category == "CR"

    def test_exactly_50_percent_reduction_is_pr(self):
        r1 = _make_result(10000, 6000, 2000)
        r2 = _make_result(5000, 3000, 1000)   # exactly -50% WT
        report = LongitudinalTracker().compare(r1, r2, days_elapsed=90.0)
        assert report.rano_category == "PR"

    def test_large_reduction_but_above_cr_threshold_is_pr(self):
        r1 = _make_result(20000, 12000, 4000)
        r2 = _make_result(8000, 4000, 2000)   # 60% reduction, > 500 mm³ → PR
        report = LongitudinalTracker().compare(r1, r2, days_elapsed=60.0)
        assert report.rano_category == "PR"

    def test_stable_disease(self):
        r1 = _make_result(10000, 6000, 2000)
        r2 = _make_result(10500, 6300, 2100)   # +5% → SD
        report = LongitudinalTracker().compare(r1, r2, days_elapsed=30.0)
        assert report.rano_category == "SD"

    def test_progressive_disease_25_percent(self):
        r1 = _make_result(10000, 6000, 2000)
        r2 = _make_result(12500, 7500, 2500)   # +25% → PD
        report = LongitudinalTracker().compare(r1, r2, days_elapsed=30.0)
        assert report.rano_category == "PD"

    def test_large_growth_is_pd(self):
        r1 = _make_result(5000, 3000, 1000)
        r2 = _make_result(15000, 9000, 3000)   # +200% → PD
        report = LongitudinalTracker().compare(r1, r2, days_elapsed=180.0)
        assert report.rano_category == "PD"

    def test_negative_days_raises(self):
        r1 = _make_result(5000, 3000, 1000)
        r2 = _make_result(5000, 3000, 1000)
        with pytest.raises(ValueError):
            LongitudinalTracker().compare(r1, r2, days_elapsed=-10)

    def test_zero_days_raises(self):
        r1 = _make_result(5000, 3000, 1000)
        r2 = _make_result(5000, 3000, 1000)
        with pytest.raises(ValueError):
            LongitudinalTracker().compare(r1, r2, days_elapsed=0)


class TestDeltaAndRate:
    def test_delta_mm3_correct(self):
        r1 = _make_result(10000, 6000, 2000)
        r2 = _make_result(12000, 7000, 2500)
        report = LongitudinalTracker().compare(r1, r2, days_elapsed=100.0)
        assert report.delta_mm3["WT"] == pytest.approx(2000.0)
        assert report.delta_mm3["TC"] == pytest.approx(1000.0)
        assert report.delta_mm3["ET"] == pytest.approx(500.0)

    def test_rate_mm3_per_day_correct(self):
        r1 = _make_result(10000, 6000, 2000)
        r2 = _make_result(11000, 6600, 2200)   # +1000 WT over 100 days
        report = LongitudinalTracker().compare(r1, r2, days_elapsed=100.0)
        assert report.rate_mm3_per_day["WT"] == pytest.approx(10.0)

    def test_negative_delta_for_shrinking_tumor(self):
        r1 = _make_result(10000, 6000, 2000)
        r2 = _make_result(8000, 4000, 1500)
        report = LongitudinalTracker().compare(r1, r2, days_elapsed=60.0)
        assert report.delta_mm3["WT"] < 0
        assert report.rate_mm3_per_day["WT"] < 0

    def test_pct_change_correct(self):
        r1 = _make_result(10000, 6000, 2000)
        r2 = _make_result(12000, 6000, 2000)   # +20% WT
        report = LongitudinalTracker().compare(r1, r2, days_elapsed=30.0)
        assert report.pct_change["WT"] == pytest.approx(20.0, abs=0.01)

    def test_rano_pct_change_reported(self):
        r1 = _make_result(10000, 6000, 2000)
        r2 = _make_result(13000, 7800, 2600)   # +30%
        report = LongitudinalTracker().compare(r1, r2, days_elapsed=45.0)
        assert report.rano_pct_change == pytest.approx(30.0, abs=0.01)


class TestFromSegmentations:
    """End-to-end test via raw segmentation arrays."""

    def _seg(self, ncr_count, ed_count, et_count, shape=(30, 30, 30)):
        seg = np.zeros(shape, dtype=np.int32)
        idx = 0
        flat = seg.ravel()
        flat[idx: idx + ncr_count] = 1; idx += ncr_count
        flat[idx: idx + ed_count] = 2;  idx += ed_count
        flat[idx: idx + et_count] = 3
        return flat.reshape(shape)

    def test_from_segmentations_returns_report(self):
        seg1 = self._seg(100, 200, 50)
        seg2 = self._seg(120, 240, 60)
        report = LongitudinalTracker.from_segmentations(
            seg1, seg2, SPACING, days_elapsed=30.0, subject_id="BraTS-001"
        )
        assert isinstance(report, LongitudinalReport)
        assert report.subject_id == "BraTS-001"

    def test_from_segmentations_volumes_consistent(self):
        seg1 = self._seg(100, 200, 50)
        seg2 = self._seg(200, 400, 100)   # doubled
        report = LongitudinalTracker.from_segmentations(
            seg1, seg2, SPACING, days_elapsed=60.0
        )
        # WT T1 = 100+200+50 = 350 mm³; WT T2 = 700 mm³ → +100% → PD
        assert report.rano_category == "PD"

    def test_from_segmentations_delta_correct(self):
        seg1 = self._seg(100, 0, 0)
        seg2 = self._seg(150, 0, 0)
        report = LongitudinalTracker.from_segmentations(
            seg1, seg2, SPACING, days_elapsed=50.0
        )
        assert report.delta_mm3["WT"] == pytest.approx(50.0)


class TestSubjectIdPreserved:
    def test_subject_id_in_report(self):
        r1 = _make_result(5000, 3000, 1000, sid="BraTS-042")
        r2 = _make_result(5500, 3300, 1100)
        report = LongitudinalTracker().compare(r1, r2, days_elapsed=30.0)
        assert report.subject_id == "BraTS-042"


class TestToDict:
    def test_to_dict_has_required_keys(self):
        r1 = _make_result(10000, 6000, 2000)
        r2 = _make_result(12000, 7000, 2500)
        report = LongitudinalTracker().compare(r1, r2, days_elapsed=90.0)
        d = report.to_dict()
        for key in ("subject_id", "days_elapsed", "delta_mm3", "rano_category", "rano_pct_change"):
            assert key in d
