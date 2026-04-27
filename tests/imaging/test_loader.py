"""
Tests for src/imaging/loader.py

All tests use synthetic in-memory NIfTI files — no real patient data required.
"""

import io
import tempfile
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest

from src.imaging.loader import MRISubject, NIfTILoader, MODALITY_SUFFIXES


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_nifti(shape=(64, 64, 32), dtype=np.float32) -> nib.Nifti1Image:
    data = np.random.rand(*shape).astype(dtype)
    affine = np.eye(4)
    return nib.Nifti1Image(data, affine)


def _write_subject(tmp_path: Path, subject_id: str, include_seg: bool = True) -> Path:
    """Write a synthetic BraTS 2024-format subject to tmp_path."""
    subject_dir = tmp_path / subject_id
    subject_dir.mkdir()

    for modality, suffix in MODALITY_SUFFIXES.items():
        if modality == "seg" and not include_seg:
            continue
        img = _make_nifti(shape=(64, 64, 32))
        nib.save(img, str(subject_dir / f"{subject_id}{suffix}"))

    return subject_dir


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestNIfTILoader:
    def test_loads_all_modalities(self, tmp_path):
        subject_dir = _write_subject(tmp_path, "BraTS-001")
        loader = NIfTILoader(require_seg=True)
        subject = loader.load(subject_dir)

        assert subject.subject_id == "BraTS-001"
        assert subject.t1.shape == (64, 64, 32)
        assert subject.t1ce.shape == (64, 64, 32)
        assert subject.t2.shape == (64, 64, 32)
        assert subject.flair.shape == (64, 64, 32)
        assert subject.seg is not None

    def test_modalities_are_float32(self, tmp_path):
        subject_dir = _write_subject(tmp_path, "BraTS-002")
        subject = NIfTILoader().load(subject_dir)

        for name, vol in subject.modalities.items():
            assert vol.dtype == np.float32, f"Expected float32 for '{name}', got {vol.dtype}"

    def test_seg_is_int16(self, tmp_path):
        subject_dir = _write_subject(tmp_path, "BraTS-003")
        subject = NIfTILoader().load(subject_dir)
        assert subject.seg.dtype == np.int16

    def test_stack_returns_4_channels(self, tmp_path):
        subject_dir = _write_subject(tmp_path, "BraTS-004")
        subject = NIfTILoader().load(subject_dir)
        stacked = subject.stack()
        assert stacked.shape == (4, 64, 64, 32)

    def test_missing_modality_raises(self, tmp_path):
        # Write only 3 modalities (missing t1)
        subject_id = "BraTS-005"
        subject_dir = tmp_path / subject_id
        subject_dir.mkdir()
        for modality, suffix in MODALITY_SUFFIXES.items():
            if modality == "t1":
                continue
            img = _make_nifti()
            nib.save(img, str(subject_dir / f"{subject_id}{suffix}"))

        with pytest.raises(FileNotFoundError, match="t1"):
            NIfTILoader().load(subject_dir)

    def test_missing_seg_ok_when_not_required(self, tmp_path):
        subject_dir = _write_subject(tmp_path, "BraTS-006", include_seg=False)
        subject = NIfTILoader(require_seg=False).load(subject_dir)
        assert subject.seg is None

    def test_nonexistent_dir_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            NIfTILoader().load(tmp_path / "does_not_exist")

    def test_metadata_contains_spacing(self, tmp_path):
        subject_dir = _write_subject(tmp_path, "BraTS-007")
        subject = NIfTILoader().load(subject_dir)
        assert "t1" in subject.metadata
        assert len(subject.metadata["t1"].voxel_spacing_mm) == 3

    def test_shape_mismatch_raises(self, tmp_path):
        subject_id = "BraTS-008"
        subject_dir = tmp_path / subject_id
        subject_dir.mkdir()

        for modality, suffix in MODALITY_SUFFIXES.items():
            # Give t2 a different shape
            shape = (64, 64, 32) if modality != "t2" else (64, 64, 48)
            img = _make_nifti(shape=shape)
            nib.save(img, str(subject_dir / f"{subject_id}{suffix}"))

        with pytest.raises(ValueError, match="Shape mismatch"):
            NIfTILoader().load(subject_dir)


class TestMRISubject:
    def _make_subject(self) -> MRISubject:
        shape = (10, 10, 10)
        return MRISubject(
            subject_id="test",
            t1=np.ones(shape, dtype=np.float32),
            t1ce=np.ones(shape, dtype=np.float32) * 2,
            t2=np.ones(shape, dtype=np.float32) * 3,
            flair=np.ones(shape, dtype=np.float32) * 4,
            seg=np.zeros(shape, dtype=np.int16),
        )

    def test_modalities_dict(self):
        subject = self._make_subject()
        assert set(subject.modalities.keys()) == {"t1", "t1ce", "t2", "flair"}

    def test_shape_property(self):
        subject = self._make_subject()
        assert subject.shape == (10, 10, 10)
