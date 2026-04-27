"""
Tests for src/analytics/volumetrics.py
"""

import numpy as np
import pytest

from src.analytics.volumetrics import VolumetricAnalyzer, VolumetricResult


SPACING = (1.0, 1.0, 1.0)   # 1 mm³ per voxel → count == volume
SHAPE = (20, 20, 20)


def _make_seg(ncr_box, ed_box, et_box, shape=SHAPE):
    """
    Build a segmentation with labeled boxes.
    ncr_box etc. are (slice, slice, slice) tuples.
    """
    seg = np.zeros(shape, dtype=np.int32)
    if ncr_box:
        seg[ncr_box] = 1
    if ed_box:
        seg[ed_box] = 2
    if et_box:
        seg[et_box] = 3
    return seg


class TestVolumetricAnalyzerBasic:
    def test_all_background_returns_zero_tumor(self):
        seg = np.zeros(SHAPE, dtype=np.int32)
        result = VolumetricAnalyzer().compute(seg, SPACING, "bg_only")
        assert result.wt_mm3 == pytest.approx(0.0)
        assert result.tc_mm3 == pytest.approx(0.0)
        assert result.et_mm3 == pytest.approx(0.0)
        assert result.total_tumor_mm3 == pytest.approx(0.0)

    def test_pure_ncr_volume_correct(self):
        seg = np.zeros(SHAPE, dtype=np.int32)
        seg[5:10, 5:10, 5:10] = 1     # 5×5×5 = 125 voxels
        result = VolumetricAnalyzer().compute(seg, SPACING, "ncr_only")
        assert result.volumes_mm3["NCR"] == pytest.approx(125.0)
        assert result.volumes_mm3["ED"] == pytest.approx(0.0)
        assert result.volumes_mm3["ET"] == pytest.approx(0.0)

    def test_pure_ed_volume_correct(self):
        seg = np.zeros(SHAPE, dtype=np.int32)
        seg[0:4, 0:4, 0:4] = 2     # 4×4×4 = 64 voxels
        result = VolumetricAnalyzer().compute(seg, SPACING, "ed_only")
        assert result.volumes_mm3["ED"] == pytest.approx(64.0)

    def test_pure_et_volume_correct(self):
        seg = np.zeros(SHAPE, dtype=np.int32)
        seg[0:3, 0:3, 0:3] = 3     # 3×3×3 = 27 voxels
        result = VolumetricAnalyzer().compute(seg, SPACING, "et_only")
        assert result.volumes_mm3["ET"] == pytest.approx(27.0)
        assert result.et_mm3 == pytest.approx(27.0)


class TestBraTSRegions:
    """WT = NCR+ED+ET, TC = NCR+ET, ET = ET."""

    def _make_full(self):
        seg = np.zeros(SHAPE, dtype=np.int32)
        seg[0:2, 0:2, 0:2] = 1     # NCR: 8 voxels
        seg[2:4, 0:2, 0:2] = 2     # ED:  8 voxels
        seg[4:6, 0:2, 0:2] = 3     # ET:  8 voxels
        return seg

    def test_wt_is_sum_of_all_classes(self):
        seg = self._make_full()
        result = VolumetricAnalyzer().compute(seg, SPACING, "full")
        assert result.wt_mm3 == pytest.approx(24.0)   # 8+8+8

    def test_tc_excludes_ed(self):
        seg = self._make_full()
        result = VolumetricAnalyzer().compute(seg, SPACING, "full")
        assert result.tc_mm3 == pytest.approx(16.0)   # NCR + ET = 8+8

    def test_et_is_only_et_class(self):
        seg = self._make_full()
        result = VolumetricAnalyzer().compute(seg, SPACING, "full")
        assert result.et_mm3 == pytest.approx(8.0)


class TestVoxelSpacing:
    def test_anisotropic_spacing_scales_volume(self):
        seg = np.zeros((10, 10, 10), dtype=np.int32)
        seg[0:2, 0:2, 0:2] = 1    # 8 voxels
        spacing = (2.0, 2.0, 1.0)  # 4 mm³ per voxel
        result = VolumetricAnalyzer().compute(seg, spacing, "aniso")
        assert result.volumes_mm3["NCR"] == pytest.approx(8 * 4.0)

    def test_voxel_volume_stored_correctly(self):
        seg = np.zeros(SHAPE, dtype=np.int32)
        spacing = (0.5, 0.5, 2.0)
        result = VolumetricAnalyzer().compute(seg, spacing, "vox")
        assert result.voxel_volume_mm3 == pytest.approx(0.5 * 0.5 * 2.0)


class TestFractions:
    def test_fractions_between_zero_and_one(self):
        seg = np.zeros(SHAPE, dtype=np.int32)
        seg[0:5, 0:5, 0:5] = 1
        seg[5:8, 0:5, 0:5] = 2
        result = VolumetricAnalyzer().compute(seg, SPACING, "frac")
        for name, frac in result.fractions.items():
            assert 0.0 <= frac <= 1.0, f"Fraction out of range for {name}: {frac}"

    def test_all_background_fractions_finite(self):
        seg = np.zeros(SHAPE, dtype=np.int32)
        result = VolumetricAnalyzer().compute(seg, SPACING, "bg")
        # Should not raise ZeroDivisionError; all fractions = 0
        for frac in result.fractions.values():
            assert np.isfinite(frac)


class TestSubjectId:
    def test_subject_id_preserved(self):
        seg = np.zeros(SHAPE, dtype=np.int32)
        result = VolumetricAnalyzer().compute(seg, SPACING, "BraTS-007")
        assert result.subject_id == "BraTS-007"


class TestAggregate:
    def _make_result(self, wt, tc, et, sid="s"):
        r = VolumetricResult(subject_id=sid, voxel_volume_mm3=1.0)
        r.wt_mm3 = wt
        r.tc_mm3 = tc
        r.et_mm3 = et
        return r

    def test_aggregate_empty_returns_empty(self):
        assert VolumetricAnalyzer.aggregate([]) == {}

    def test_aggregate_mean_correct(self):
        r1 = self._make_result(100, 60, 30)
        r2 = self._make_result(200, 120, 60)
        agg = VolumetricAnalyzer.aggregate([r1, r2])
        assert agg["mean_wt_mm3"] == pytest.approx(150.0)
        assert agg["mean_tc_mm3"] == pytest.approx(90.0)
        assert agg["mean_et_mm3"] == pytest.approx(45.0)

    def test_aggregate_std_zero_for_identical(self):
        r1 = self._make_result(100, 50, 25)
        r2 = self._make_result(100, 50, 25)
        agg = VolumetricAnalyzer.aggregate([r1, r2])
        assert agg["std_wt_mm3"] == pytest.approx(0.0, abs=1e-6)

    def test_aggregate_n_subjects(self):
        results = [self._make_result(i, i, i) for i in range(5)]
        agg = VolumetricAnalyzer.aggregate(results)
        assert agg["n_subjects"] == 5


class TestInputValidation:
    def test_non_3d_input_raises(self):
        seg = np.zeros((10, 10), dtype=np.int32)
        with pytest.raises(ValueError, match="3D"):
            VolumetricAnalyzer().compute(seg, SPACING)
