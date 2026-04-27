"""
dataset.py — PyTorch Dataset for BraTS multi-modal MRI segmentation.

Two dataset modes
-----------------
BraTSDataset (training/validation)
    Scans a root directory of preprocessed subject folders.
    Returns tumour-biased 3D patches of shape (4, Ph, Pw, Pd) with
    corresponding integer label maps (Ph, Pw, Pd).

BraTSInferenceDataset (full-volume inference)
    Returns the complete 4-channel volume for a single subject without
    patching. Used in the prediction / evaluation pipeline.

Expected directory layout (output of Phase 1 pipeline)
-------------------------------------------------------
    processed_root/
        BraTS-001/
            BraTS-001_t1.nii.gz
            BraTS-001_t1ce.nii.gz
            BraTS-001_t2.nii.gz
            BraTS-001_flair.nii.gz
            BraTS-001_seg.nii.gz      ← optional in inference mode
        BraTS-002/
            ...
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import nibabel as nib
import numpy as np
import torch
from torch.utils.data import Dataset

from src.utils.patch_extractor import PatchExtractor

logger = logging.getLogger(__name__)

MODALITY_KEYS = ["t1", "t1ce", "t2", "flair"]


class BraTSDataset(Dataset):
    """
    Patch-based training dataset for preprocessed BraTS subjects.

    Each __getitem__ call returns one randomly sampled 3D patch from a
    randomly chosen subject, with tumour-biased sampling (see PatchExtractor).

    Parameters
    ----------
    subject_dirs : list of paths to preprocessed subject directories.
    patch_size   : 3D patch size in voxels. Default (128, 128, 128).
    patches_per_subject : number of patches to sample per subject per epoch.
    overlap      : patch overlap fraction for tumour-biased sampling.
    tumor_sample_prob : probability of forcing a tumour-containing patch.
    augment      : if True, apply basic 3D flips on-the-fly.
    seed         : random seed for reproducibility.
    """

    def __init__(
        self,
        subject_dirs: List[Path],
        patch_size: Tuple[int, int, int] = (128, 128, 128),
        patches_per_subject: int = 2,
        overlap: float = 0.5,
        tumor_sample_prob: float = 0.5,
        augment: bool = True,
        seed: Optional[int] = None,
    ) -> None:
        self.subject_dirs = [Path(d) for d in subject_dirs]
        self.patch_size = patch_size
        self.patches_per_subject = patches_per_subject
        self.augment = augment
        self.rng = np.random.default_rng(seed)

        self.extractor = PatchExtractor(
            patch_size=patch_size,
            overlap=overlap,
            tumor_sample_prob=tumor_sample_prob,
            seed=seed,
        )

        # Pre-cache volume paths (no actual loading at init — lazy load)
        self._subject_paths = self._discover_subjects()
        logger.info(
            "BraTSDataset: %d subjects × %d patches = %d total samples",
            len(self._subject_paths), patches_per_subject,
            len(self._subject_paths) * patches_per_subject,
        )

    def __len__(self) -> int:
        return len(self._subject_paths) * self.patches_per_subject

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Returns
        -------
        image : (4, Ph, Pw, Pd) float32 tensor — normalised multi-modal MRI.
        label : (Ph, Pw, Pd) int64 tensor — BraTS class labels [0–3].
        """
        subject_idx = idx // self.patches_per_subject
        subject_dir = self._subject_paths[subject_idx]

        volumes, seg = self._load_subject(subject_dir)

        # Build a lightweight MRISubject-compatible object for PatchExtractor
        from src.imaging.loader import MRISubject
        subject = MRISubject(
            subject_id=subject_dir.name,
            t1=volumes[0], t1ce=volumes[1], t2=volumes[2], flair=volumes[3],
            seg=seg,
        )

        patches = self.extractor.sample(subject, n_patches=1)
        patch = patches[0]

        image = torch.from_numpy(patch.data.astype(np.float32))    # (4, Ph, Pw, Pd)
        label = torch.from_numpy(patch.label.astype(np.int64)) if patch.label is not None \
            else torch.zeros(self.patch_size, dtype=torch.int64)

        if self.augment:
            image, label = self._random_flip(image, label)

        return image, label

    def _load_subject(
        self, subject_dir: Path
    ) -> Tuple[List[np.ndarray], Optional[np.ndarray]]:
        """Load all 4 modalities and optional segmentation from NIfTI files."""
        sid = subject_dir.name
        volumes = []
        for key in MODALITY_KEYS:
            path = subject_dir / f"{sid}_{key}.nii.gz"
            if not path.exists():
                raise FileNotFoundError(
                    f"Missing modality file: {path}. "
                    "Run the Phase 1 pipeline first."
                )
            vol = nib.load(str(path)).get_fdata(dtype=np.float32)
            volumes.append(vol)

        seg = None
        seg_path = subject_dir / f"{sid}_seg.nii.gz"
        if seg_path.exists():
            seg = nib.load(str(seg_path)).get_fdata().astype(np.int16)

        return volumes, seg

    def _discover_subjects(self) -> List[Path]:
        """Return all subject directories that have at least one modality file."""
        valid = []
        for d in self.subject_dirs:
            sid = d.name
            probe = d / f"{sid}_t1.nii.gz"
            if probe.exists():
                valid.append(d)
            else:
                logger.warning("Subject directory '%s' missing t1 file — skipping.", d)
        return valid

    def _random_flip(
        self, image: torch.Tensor, label: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """Apply random axis flips (label-preserving)."""
        for dim in [1, 2, 3]:   # H, W, D of the (4, H, W, D) image
            if self.rng.random() > 0.5:
                image = torch.flip(image, [dim])
                label = torch.flip(label, [dim - 1])   # label is (H, W, D) — no channel
        return image, label

    @classmethod
    def from_root(
        cls,
        root: str | Path,
        pattern: str = "BraTS*",
        **kwargs,
    ) -> "BraTSDataset":
        """Convenience constructor: discover all subject dirs under root."""
        root = Path(root)
        subject_dirs = sorted([d for d in root.glob(pattern) if d.is_dir()])
        if not subject_dirs:
            raise FileNotFoundError(
                f"No subject directories matching '{pattern}' found in {root}."
            )
        return cls(subject_dirs, **kwargs)


class BraTSInferenceDataset(Dataset):
    """
    Full-volume inference dataset — one item = one complete 4-channel volume.

    Used for evaluation and prediction. Does NOT patch; the caller is
    responsible for patch-based inference if needed.

    Parameters
    ----------
    subject_dirs : list of preprocessed subject directory paths.
    """

    def __init__(self, subject_dirs: List[Path]) -> None:
        self.subject_dirs = [Path(d) for d in subject_dirs]

    def __len__(self) -> int:
        return len(self.subject_dirs)

    def __getitem__(
        self, idx: int
    ) -> Tuple[torch.Tensor, Optional[torch.Tensor], str]:
        """
        Returns
        -------
        image      : (4, H, W, D) float32 tensor.
        label      : (H, W, D) int64 tensor or None if no seg file.
        subject_id : str identifier.
        """
        subject_dir = self.subject_dirs[idx]
        sid = subject_dir.name
        volumes = []

        for key in MODALITY_KEYS:
            path = subject_dir / f"{sid}_{key}.nii.gz"
            vol = nib.load(str(path)).get_fdata(dtype=np.float32)
            volumes.append(vol)

        image = torch.from_numpy(np.stack(volumes, axis=0))  # (4, H, W, D)

        seg_path = subject_dir / f"{sid}_seg.nii.gz"
        label = None
        if seg_path.exists():
            label = torch.from_numpy(
                nib.load(str(seg_path)).get_fdata().astype(np.int64)
            )

        return image, label, sid
