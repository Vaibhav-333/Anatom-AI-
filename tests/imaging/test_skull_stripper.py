"""
Tests for src/imaging/skull_stripper.py

Uses a synthetic "brain-in-box" volume: a sphere of high-intensity voxels
centred in a zero-padded volume, mimicking a skull-stripped ground-truth.
"""

import numpy as np
import pytest

from src.imaging.loader import MRISubject
from src.imaging.skull_stripper import SkullStripper, _spherical_structuring_element


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sphere_volume(shape=(64, 64, 32), radius=20, intensity=500.0) -> np.ndarray:
    """Create a synthetic brain volume: sphere of intensity inside zero background."""
    vol = np.zeros(shape, dtype=np.float32)
    cx, cy, cz = shape[0] // 2, shape[1] // 2, shape[2] // 2
    for x in range(shape[0]):
        for y in range(shape[1]):
            for z in range(shape[2]):
                if (x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2 <= radius ** 2:
                    vol[x, y, z] = intensity
    return vol


def _make_sphere_subject(shape=(64, 64, 32), radius=20) -> MRISubject:
    vol = _sphere_volume(shape, radius)
    seg = np.zeros(shape, dtype=np.int16)
    return MRISubject(
        subject_id="sphere",
        t1=vol.copy(), t1ce=vol.copy(), t2=vol.copy(), flair=vol.copy(),
        seg=seg,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSkullStripper:
    def test_brain_mask_is_binary(self):
        subject = _make_sphere_subject()
        stripper = SkullStripper(closing_radius=2)
        _, brain_mask = stripper.strip(subject)
        unique_vals = set(np.unique(brain_mask))
        assert unique_vals.issubset({0, 1}), f"Non-binary mask values: {unique_vals}"

    def test_brain_mask_shape_matches_volume(self):
        subject = _make_sphere_subject()
        stripper = SkullStripper(closing_radius=2)
        _, brain_mask = stripper.strip(subject)
        assert brain_mask.shape == subject.shape

    def test_background_zeroed_after_masking(self):
        subject = _make_sphere_subject()
        stripper = SkullStripper(closing_radius=2)
        masked_subject, brain_mask = stripper.strip(subject)

        # All voxels outside mask should be zero
        outside = ~brain_mask.astype(bool)
        assert masked_subject.t1[outside].max() == 0.0
        assert masked_subject.t1ce[outside].max() == 0.0

    def test_seg_label_not_masked(self):
        subject = _make_sphere_subject()
        subject.seg[10, 10, 5] = 2
        stripper = SkullStripper(closing_radius=2)
        masked_subject, _ = stripper.strip(subject)
        # Seg is intentionally NOT masked — original labels preserved
        assert masked_subject.seg[10, 10, 5] == 2

    def test_low_coverage_raises(self):
        # A volume that is entirely zeros — skull stripping should flag it
        shape = (32, 32, 16)
        subject = MRISubject(
            subject_id="empty",
            t1=np.zeros(shape, dtype=np.float32),
            t1ce=np.zeros(shape, dtype=np.float32),
            t2=np.zeros(shape, dtype=np.float32),
            flair=np.zeros(shape, dtype=np.float32),
        )
        stripper = SkullStripper(min_brain_coverage=0.05)
        with pytest.raises(ValueError, match="Brain mask coverage"):
            stripper.strip(subject)

    def test_output_modalities_float32(self):
        subject = _make_sphere_subject()
        masked_subject, _ = SkullStripper(closing_radius=2).strip(subject)
        for name, vol in masked_subject.modalities.items():
            assert vol.dtype == np.float32, f"'{name}' dtype={vol.dtype}"

    def test_all_four_modalities_masked(self):
        subject = _make_sphere_subject()
        stripper = SkullStripper(closing_radius=2)
        masked, mask = stripper.strip(subject)

        outside = ~mask.astype(bool)
        for name, vol in masked.modalities.items():
            assert vol[outside].max() == 0.0, f"'{name}' not zeroed outside mask."


class TestSphericalStructuringElement:
    def test_shape_is_cube(self):
        r = 3
        s = _spherical_structuring_element(r)
        assert s.shape == (2 * r + 1, 2 * r + 1, 2 * r + 1)

    def test_centre_is_true(self):
        r = 3
        s = _spherical_structuring_element(r)
        assert s[r, r, r] is np.True_

    def test_corners_are_false(self):
        r = 3
        s = _spherical_structuring_element(r)
        assert not s[0, 0, 0]
