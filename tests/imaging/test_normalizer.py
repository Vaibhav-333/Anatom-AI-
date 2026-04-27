"""
Tests for src/imaging/normalizer.py
"""

import numpy as np
import pytest

from src.imaging.loader import MRISubject
from src.imaging.normalizer import Normalizer


def _make_subject(shape=(32, 32, 16), seed=42) -> MRISubject:
    rng = np.random.default_rng(seed)
    return MRISubject(
        subject_id="test",
        t1=rng.normal(500, 200, shape).astype(np.float32).clip(0),
        t1ce=rng.normal(600, 250, shape).astype(np.float32).clip(0),
        t2=rng.normal(700, 300, shape).astype(np.float32).clip(0),
        flair=rng.normal(400, 150, shape).astype(np.float32).clip(0),
        seg=np.zeros(shape, dtype=np.int16),
    )


class TestNormalizer:
    def test_zscore_mean_near_zero(self):
        subject = _make_subject()
        norm = Normalizer(method="zscore")
        result = norm.normalize(subject)

        for name, vol in result.modalities.items():
            brain = vol[vol != 0]
            assert abs(brain.mean()) < 0.5, f"Mean of '{name}' not near 0: {brain.mean():.3f}"

    def test_zscore_std_near_one(self):
        subject = _make_subject()
        norm = Normalizer(method="zscore")
        result = norm.normalize(subject)

        for name, vol in result.modalities.items():
            brain = vol[vol != 0]
            assert 0.5 < brain.std() < 1.5, f"Std of '{name}' not near 1: {brain.std():.3f}"

    def test_minmax_range(self):
        subject = _make_subject()
        norm = Normalizer(method="minmax")
        result = norm.normalize(subject)

        for name, vol in result.modalities.items():
            brain = vol[vol != 0]
            assert brain.min() >= -0.01
            assert brain.max() <= 1.01, f"'{name}' max={brain.max():.4f} exceeds 1.0"

    def test_output_is_float32(self):
        subject = _make_subject()
        result = Normalizer().normalize(subject)
        for name, vol in result.modalities.items():
            assert vol.dtype == np.float32

    def test_seg_label_unchanged(self):
        subject = _make_subject()
        subject.seg[5, 5, 5] = 1
        subject.seg[10, 10, 5] = 2
        result = Normalizer().normalize(subject)
        np.testing.assert_array_equal(result.seg, subject.seg)

    def test_invalid_method_raises(self):
        with pytest.raises(ValueError, match="Unknown normalization method"):
            Normalizer(method="invalid_method")

    def test_all_zero_volume_returned_as_is(self):
        shape = (10, 10, 10)
        subject = MRISubject(
            subject_id="zeros",
            t1=np.zeros(shape, dtype=np.float32),
            t1ce=np.zeros(shape, dtype=np.float32),
            t2=np.zeros(shape, dtype=np.float32),
            flair=np.zeros(shape, dtype=np.float32),
        )
        result = Normalizer().normalize(subject)
        np.testing.assert_array_equal(result.t1, np.zeros(shape))

    def test_percentile_clipping_applied(self):
        # Verify that percentile clipping prevents the outlier from producing
        # an extreme normalised value. With z-score, std is always ~1 by design,
        # but the *maximum absolute value* of individual normalised voxels reveals
        # whether the outlier was constrained.
        rng = np.random.default_rng(7)
        shape = (30, 30, 20)   # 18_000 voxels
        vol = rng.normal(500, 50, shape).astype(np.float32).clip(1)  # All > 0
        vol[0, 0, 0] = 1_000_000    # extreme outlier — ~20_000 σ away

        subject = MRISubject(
            subject_id="outliers",
            t1=vol.copy(), t1ce=vol.copy(), t2=vol.copy(), flair=vol.copy(),
        )

        # Without clipping: the outlier normalises to ~+19_990
        norm_no_clip = Normalizer(method="zscore", clip_percentiles=(0.0, 100.0))
        result_no_clip = norm_no_clip.normalize(subject)
        max_abs_no_clip = float(np.abs(result_no_clip.t1).max())

        # With clipping: the outlier is capped at p99 → normalised value ≤ ~5
        norm_clipped = Normalizer(method="zscore", clip_percentiles=(1.0, 99.0))
        result_clipped = norm_clipped.normalize(subject)
        max_abs_clipped = float(np.abs(result_clipped.t1).max())

        assert max_abs_no_clip > 100, (
            f"Expected large outlier without clipping, got max_abs={max_abs_no_clip:.1f}"
        )
        assert max_abs_clipped < 10, (
            f"Clipping should bound outlier to <10σ, got max_abs={max_abs_clipped:.2f}"
        )

    def test_whitestripe_method_runs(self):
        subject = _make_subject()
        result = Normalizer(method="whitestripe").normalize(subject)
        assert result.t1 is not None
        assert result.t1.dtype == np.float32
