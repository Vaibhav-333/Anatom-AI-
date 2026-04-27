"""
Integration tests for src/imaging/pipeline.py

These tests use a minimal in-memory subject to exercise the full pipeline
without requiring real BraTS data or a GPU.

Registration and bias correction are toggled OFF in the test config to keep
tests fast — they depend on SimpleITK which is slow on tiny synthetic volumes.
"""

import json
import tempfile
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest
import yaml

from src.imaging.loader import MODALITY_SUFFIXES
from src.imaging.pipeline import PreprocessingPipeline


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sphere_volume(shape=(64, 64, 32), radius=22, seed=42) -> np.ndarray:
    """Sphere with realistic random intensity variation (not constant) so σ > 0."""
    rng = np.random.default_rng(seed)
    vol = np.zeros(shape, dtype=np.float32)
    cx, cy, cz = shape[0] // 2, shape[1] // 2, shape[2] // 2
    for x in range(shape[0]):
        for y in range(shape[1]):
            for z in range(shape[2]):
                if (x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2 <= radius ** 2:
                    vol[x, y, z] = rng.normal(600, 80)
    return vol.clip(1, None)  # Keep all brain voxels > 0


def _write_brats_subject(subject_dir: Path) -> None:
    subject_dir.mkdir(parents=True, exist_ok=True)
    subject_id = subject_dir.name
    vol = _sphere_volume()
    affine = np.eye(4)
    for modality, suffix in MODALITY_SUFFIXES.items():
        data = vol.copy()
        img = nib.Nifti1Image(data, affine)
        nib.save(img, str(subject_dir / f"{subject_id}{suffix}"))


def _minimal_config(tmp_path: Path, target_size=None) -> dict:
    """Config with registration and bias correction disabled for speed."""
    return {
        "target_spacing": [1.0, 1.0, 1.0],
        "target_size": target_size or [64, 64, 32],
        "clip_percentiles": [1.0, 99.0],
        "normalization_method": "zscore",
        "bias_correction": {"n_iterations": [10, 10], "convergence_threshold": 0.001},
        "skull_strip": {"method": "otsu", "closing_radius": 2, "min_brain_coverage": 0.01},
        "registration": {"reference_modality": "t1ce", "interpolator": "linear"},
        "augmentation": {
            "flips": {"axial": True, "sagittal": False, "coronal": False},
            "rotation_range_deg": 5,
            "gamma_range": [0.9, 1.1],
            "elastic": {"enabled": False},
        },
        "pipeline": {
            "run_qc_pre": True,
            "run_bias_correction": False,   # Disabled for speed
            "run_skull_strip": True,
            "run_registration": False,       # Disabled for speed
            "run_normalization": True,
            "run_resampling": True,
            "run_qc_post": True,
            "log_level": "WARNING",
        },
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPreprocessingPipeline:
    def test_run_produces_output_files(self, tmp_path):
        subject_dir = tmp_path / "BraTS-TEST"
        _write_brats_subject(subject_dir)
        output_dir = tmp_path / "output" / "BraTS-TEST"

        cfg = _minimal_config(tmp_path)
        pipeline = PreprocessingPipeline(cfg)
        pipeline.run(subject_dir, output_dir)

        # At least one processed NIfTI should exist
        nii_files = list(output_dir.glob("*.nii.gz"))
        assert len(nii_files) >= 4, f"Expected ≥4 NIfTI files, found {len(nii_files)}"

    def test_provenance_log_written(self, tmp_path):
        subject_dir = tmp_path / "BraTS-PROV"
        _write_brats_subject(subject_dir)
        output_dir = tmp_path / "output" / "BraTS-PROV"

        pipeline = PreprocessingPipeline(_minimal_config(tmp_path))
        pipeline.run(subject_dir, output_dir)

        prov_file = output_dir / "provenance.json"
        assert prov_file.exists()

        with open(prov_file) as f:
            prov = json.load(f)

        assert prov["subject_id"] == "BraTS-PROV"
        assert prov["qc_passed"] is True
        assert len(prov["steps"]) > 0

    def test_from_yaml(self, tmp_path):
        subject_dir = tmp_path / "BraTS-YAML"
        _write_brats_subject(subject_dir)
        output_dir = tmp_path / "output" / "BraTS-YAML"

        # Write config to YAML file
        config_path = tmp_path / "test_config.yaml"
        with open(config_path, "w") as f:
            yaml.safe_dump(_minimal_config(tmp_path), f)

        pipeline = PreprocessingPipeline.from_yaml(config_path)
        subject = pipeline.run(subject_dir, output_dir)
        assert subject.subject_id == "BraTS-YAML"

    def test_output_subject_has_correct_shape(self, tmp_path):
        subject_dir = tmp_path / "BraTS-SHAPE"
        _write_brats_subject(subject_dir)
        output_dir = tmp_path / "output" / "BraTS-SHAPE"

        target = [64, 64, 32]
        cfg = _minimal_config(tmp_path, target_size=target)
        pipeline = PreprocessingPipeline(cfg)
        subject = pipeline.run(subject_dir, output_dir)

        assert subject.t1.shape == tuple(target), f"Unexpected shape: {subject.t1.shape}"
        assert subject.t1ce.shape == tuple(target)

    def test_no_nan_in_output(self, tmp_path):
        subject_dir = tmp_path / "BraTS-NAN"
        _write_brats_subject(subject_dir)
        output_dir = tmp_path / "output" / "BraTS-NAN"

        pipeline = PreprocessingPipeline(_minimal_config(tmp_path))
        subject = pipeline.run(subject_dir, output_dir)

        for name, vol in subject.modalities.items():
            assert not np.isnan(vol).any(), f"NaN found in '{name}' after pipeline"

    def test_augmentation_changes_values(self, tmp_path):
        subject_dir = tmp_path / "BraTS-AUG"
        _write_brats_subject(subject_dir)
        output_dir = tmp_path / "output" / "BraTS-AUG"

        cfg = _minimal_config(tmp_path)
        pipeline = PreprocessingPipeline(cfg)
        subject_clean = pipeline.run(subject_dir, output_dir)
        subject_aug = pipeline.run(subject_dir, output_dir, apply_augmentation=True)

        # Augmented and clean should differ (flips change the array)
        # This is not guaranteed for all seeds but is highly probable with flips enabled
        # We check at least ONE modality differs
        any_different = any(
            not np.array_equal(subject_clean.modalities[m], subject_aug.modalities[m])
            for m in subject_clean.modalities
        )
        assert any_different, "Augmentation produced identical output — something is wrong."

    def test_missing_subject_dir_raises(self, tmp_path):
        pipeline = PreprocessingPipeline(_minimal_config(tmp_path))
        with pytest.raises((FileNotFoundError, RuntimeError)):
            pipeline.run(tmp_path / "does_not_exist", tmp_path / "out")
