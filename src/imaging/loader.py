"""
loader.py — NIfTI file loader for multi-modal BraTS MRI data.

Loads all four BraTS modalities (T1, T1ce, T2, FLAIR) and the ground-truth
segmentation label into a typed MRISubject dataclass. All file paths are
validated before loading; missing modalities raise descriptive errors rather
than silent failures.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Tuple

import nibabel as nib
import numpy as np

logger = logging.getLogger(__name__)

# BraTS 2024/2025 standard filename suffixes
MODALITY_SUFFIXES: Dict[str, str] = {
    "t1":    "-t1n.nii.gz",
    "t1ce":  "-t1c.nii.gz",
    "t2":    "-t2w.nii.gz",
    "flair": "-t2f.nii.gz",
    "seg":   "-seg.nii.gz",
}

# Fallback legacy BraTS suffixes (2020–2023 format)
MODALITY_SUFFIXES_LEGACY: Dict[str, str] = {
    "t1":    "_t1.nii.gz",
    "t1ce":  "_t1ce.nii.gz",
    "t2":    "_t2.nii.gz",
    "flair": "_flair.nii.gz",
    "seg":   "_seg.nii.gz",
}


@dataclass
class VolumeMetadata:
    """Spatial metadata extracted from a NIfTI header."""
    shape: Tuple[int, ...]
    voxel_spacing_mm: Tuple[float, ...]   # (x, y, z) spacing in millimetres
    affine: np.ndarray                    # 4×4 world-space affine matrix
    data_dtype: str
    file_path: str


@dataclass
class MRISubject:
    """
    Container for all modalities of a single BraTS subject.

    Arrays are stored as float32 numpy arrays with shape (H, W, D).
    The segmentation label uses int16 with BraTS class encoding:
        0 = background
        1 = necrotic core (NCR)
        2 = peritumoral edema (ED)
        3 = GD-enhancing tumour (ET)
    """
    subject_id: str
    t1:    np.ndarray
    t1ce:  np.ndarray
    t2:    np.ndarray
    flair: np.ndarray
    seg:   Optional[np.ndarray] = None      # None for inference-only data
    metadata: Dict[str, VolumeMetadata] = field(default_factory=dict)

    @property
    def modalities(self) -> Dict[str, np.ndarray]:
        """Return image modalities as a name → array mapping."""
        return {"t1": self.t1, "t1ce": self.t1ce, "t2": self.t2, "flair": self.flair}

    @property
    def shape(self) -> Tuple[int, ...]:
        return self.t1.shape

    def stack(self) -> np.ndarray:
        """Return all four modalities stacked on a new leading channel axis → (4, H, W, D)."""
        return np.stack([self.t1, self.t1ce, self.t2, self.flair], axis=0)


class NIfTILoader:
    """
    Loads a BraTS subject directory into an MRISubject.

    Supports both BraTS 2024/2025 (hyphen) and legacy 2020–2023 (underscore)
    naming conventions. Auto-detects the convention from the directory contents.

    Parameters
    ----------
    require_seg : bool
        If True (default), raise FileNotFoundError when the segmentation
        label is absent. Set to False for inference on unlabelled data.
    """

    def __init__(self, require_seg: bool = True) -> None:
        self.require_seg = require_seg

    def load(self, subject_dir: str | Path) -> MRISubject:
        """
        Load all modalities from a subject directory.

        Parameters
        ----------
        subject_dir : path to directory containing the NIfTI files.

        Returns
        -------
        MRISubject with float32 arrays and attached metadata.

        Raises
        ------
        FileNotFoundError  : if any required modality file is missing.
        ValueError         : if shapes across modalities are inconsistent.
        """
        subject_dir = Path(subject_dir)
        if not subject_dir.is_dir():
            raise FileNotFoundError(f"Subject directory not found: {subject_dir}")

        subject_id = subject_dir.name
        suffixes = self._detect_naming_convention(subject_dir, subject_id)

        volumes: Dict[str, np.ndarray] = {}
        metadata: Dict[str, VolumeMetadata] = {}

        for modality, suffix in suffixes.items():
            filepath = subject_dir / f"{subject_id}{suffix}"

            if not filepath.exists():
                if modality == "seg" and not self.require_seg:
                    logger.info("Segmentation label not found — skipping (inference mode).")
                    continue
                raise FileNotFoundError(
                    f"Missing modality '{modality}' for subject '{subject_id}'. "
                    f"Expected: {filepath}"
                )

            array, meta = self._load_nifti(filepath, modality)
            volumes[modality] = array
            metadata[modality] = meta
            logger.debug("Loaded %s  shape=%s  spacing=%s", modality, meta.shape, meta.voxel_spacing_mm)

        self._validate_shapes(volumes, subject_id)

        return MRISubject(
            subject_id=subject_id,
            t1=volumes["t1"],
            t1ce=volumes["t1ce"],
            t2=volumes["t2"],
            flair=volumes["flair"],
            seg=volumes.get("seg"),
            metadata=metadata,
        )

    def _load_nifti(self, filepath: Path, modality: str) -> Tuple[np.ndarray, VolumeMetadata]:
        """Load a single NIfTI file, return (float32 array, metadata)."""
        img = nib.load(str(filepath))
        data = np.asarray(img.dataobj)

        if modality == "seg":
            array = data.astype(np.int16)
        else:
            array = data.astype(np.float32)

        header = img.header
        voxel_spacing = tuple(float(v) for v in header.get_zooms()[:3])

        meta = VolumeMetadata(
            shape=array.shape,
            voxel_spacing_mm=voxel_spacing,
            affine=np.array(img.affine),
            data_dtype=str(array.dtype),
            file_path=str(filepath),
        )
        return array, meta

    def _detect_naming_convention(
        self, subject_dir: Path, subject_id: str
    ) -> Dict[str, str]:
        """Auto-detect BraTS 2024 vs legacy naming by probing for a t1 file."""
        probe_2024 = subject_dir / f"{subject_id}{MODALITY_SUFFIXES['t1']}"
        if probe_2024.exists():
            logger.debug("Detected BraTS 2024/2025 naming convention.")
            return MODALITY_SUFFIXES

        probe_legacy = subject_dir / f"{subject_id}{MODALITY_SUFFIXES_LEGACY['t1']}"
        if probe_legacy.exists():
            logger.debug("Detected legacy BraTS naming convention.")
            return MODALITY_SUFFIXES_LEGACY

        # Return 2024 convention; missing files will produce clear error messages.
        logger.warning(
            "Could not auto-detect naming convention for '%s'. Defaulting to BraTS 2024.",
            subject_id,
        )
        return MODALITY_SUFFIXES

    def _validate_shapes(self, volumes: Dict[str, np.ndarray], subject_id: str) -> None:
        """Ensure all image modalities share the same spatial shape."""
        image_modalities = {k: v for k, v in volumes.items() if k != "seg"}
        shapes = {k: v.shape for k, v in image_modalities.items()}
        unique_shapes = set(shapes.values())

        if len(unique_shapes) > 1:
            raise ValueError(
                f"Shape mismatch in subject '{subject_id}': {shapes}. "
                "All modalities must have the same spatial dimensions."
            )

        if "seg" in volumes:
            seg_shape = volumes["seg"].shape
            image_shape = next(iter(unique_shapes))
            if seg_shape != image_shape:
                raise ValueError(
                    f"Segmentation shape {seg_shape} does not match image shape "
                    f"{image_shape} for subject '{subject_id}'."
                )
