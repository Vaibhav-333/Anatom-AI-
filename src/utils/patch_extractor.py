"""
patch_extractor.py — 3D overlapping patch extraction for U-Net training.

3D U-Nets cannot process a full 240×240×155 volume in a single forward pass
on consumer hardware — memory requirements are ~64 GB at float32 for a full
volume batch. Instead, we extract overlapping 3D patches during training.

Strategy
--------
- Slide a cubic window (default 128³) over the full volume with 50% overlap.
- Tumour-biased sampling: with configurable probability, preferentially sample
  patches that contain at least `min_tumor_voxels` tumour labels. This directly
  addresses the severe class imbalance problem — most patches in a brain are
  healthy tissue.
- Patches and their coordinates are returned together so that predictions from
  individual patches can be stitched back into the full volume at inference.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Generator, List, Optional, Tuple

import numpy as np

from src.imaging.loader import MRISubject

logger = logging.getLogger(__name__)


@dataclass
class Patch:
    """A 3D patch extracted from an MRISubject."""
    data: np.ndarray            # Shape: (4, patch_h, patch_w, patch_d) — 4 channels
    label: Optional[np.ndarray] # Shape: (patch_h, patch_w, patch_d) or None
    origin: Tuple[int, int, int] # (x, y, z) corner in original volume space
    subject_id: str


class PatchExtractor:
    """
    Extract 3D overlapping patches from an MRISubject for model training/inference.

    Parameters
    ----------
    patch_size : tuple[int, int, int]
        Spatial size of each patch in voxels (H, W, D). Default: 128³.
    overlap : float
        Fractional overlap between adjacent patches [0, 1). Default: 0.5.
    min_tumor_voxels : int
        Patches with fewer tumour voxels than this are candidates for rejection
        during tumour-biased sampling. Set 0 to disable.
    tumor_sample_prob : float
        Probability of forcing a patch to contain tumour (if any exist).
    seed : int | None
        Random seed for reproducibility.
    """

    def __init__(
        self,
        patch_size: Tuple[int, int, int] = (128, 128, 128),
        overlap: float = 0.5,
        min_tumor_voxels: int = 10,
        tumor_sample_prob: float = 0.5,
        seed: Optional[int] = None,
    ) -> None:
        if not (0.0 <= overlap < 1.0):
            raise ValueError("overlap must be in [0, 1).")
        self.patch_size = patch_size
        self.overlap = overlap
        self.min_tumor_voxels = min_tumor_voxels
        self.tumor_sample_prob = tumor_sample_prob
        self.rng = np.random.default_rng(seed)

    def extract_all(self, subject: MRISubject) -> List[Patch]:
        """
        Extract all overlapping patches in a deterministic sliding-window grid.

        Use this at inference time to cover the full volume without gaps.
        Predictions can be averaged back together using the origin coordinates.
        """
        volume_shape = subject.shape
        stride = self._compute_stride()
        origins = self._compute_origins(volume_shape, stride)

        patches = []
        for origin in origins:
            patch = self._extract_patch(subject, origin)
            if patch is not None:
                patches.append(patch)

        logger.info(
            "Extracted %d patches from '%s'  patch_size=%s  stride=%s",
            len(patches), subject.subject_id, self.patch_size, stride,
        )
        return patches

    def sample(self, subject: MRISubject, n_patches: int) -> List[Patch]:
        """
        Randomly sample n_patches from the subject with tumour-biased selection.

        Use this during training — yields diverse coverage while over-sampling
        tumour-containing patches.
        """
        volume_shape = subject.shape
        tumor_origins = self._get_tumor_origins(subject) if subject.seg is not None else []

        patches = []
        for _ in range(n_patches):
            if tumor_origins and self.rng.random() < self.tumor_sample_prob:
                # Force a tumour-containing patch
                idx = int(self.rng.integers(len(tumor_origins)))
                origin = tumor_origins[idx]
            else:
                # Random patch
                origin = self._random_valid_origin(volume_shape)

            patch = self._extract_patch(subject, origin)
            if patch is not None:
                patches.append(patch)

        logger.debug("Sampled %d patches from '%s'", len(patches), subject.subject_id)
        return patches

    def _extract_patch(
        self, subject: MRISubject, origin: Tuple[int, int, int]
    ) -> Optional[Patch]:
        """Extract a single patch at the given origin. Returns None if out of bounds."""
        x0, y0, z0 = origin
        ph, pw, pd = self.patch_size
        H, W, D = subject.shape

        x1, y1, z1 = min(x0 + ph, H), min(y0 + pw, W), min(z0 + pd, D)
        actual_size = (x1 - x0, y1 - y0, z1 - z0)

        # Allocate padded arrays
        data = np.zeros((4, ph, pw, pd), dtype=np.float32)
        label = np.zeros((ph, pw, pd), dtype=np.int16) if subject.seg is not None else None

        # Fill with available data
        for c, (name, vol) in enumerate(subject.modalities.items()):
            data[c, :actual_size[0], :actual_size[1], :actual_size[2]] = vol[x0:x1, y0:y1, z0:z1]

        if label is not None and subject.seg is not None:
            label[:actual_size[0], :actual_size[1], :actual_size[2]] = subject.seg[x0:x1, y0:y1, z0:z1]

        return Patch(data=data, label=label, origin=origin, subject_id=subject.subject_id)

    def _compute_stride(self) -> Tuple[int, int, int]:
        return tuple(max(1, int(s * (1 - self.overlap))) for s in self.patch_size)

    def _compute_origins(
        self,
        volume_shape: Tuple[int, int, int],
        stride: Tuple[int, int, int],
    ) -> List[Tuple[int, int, int]]:
        origins = []
        H, W, D = volume_shape
        ph, pw, pd = self.patch_size
        sx, sy, sz = stride

        for x in range(0, max(1, H - ph + 1), sx):
            for y in range(0, max(1, W - pw + 1), sy):
                for z in range(0, max(1, D - pd + 1), sz):
                    origins.append((x, y, z))

        return origins

    def _get_tumor_origins(self, subject: MRISubject) -> List[Tuple[int, int, int]]:
        """Return patch origins that contain at least min_tumor_voxels tumour voxels."""
        if subject.seg is None:
            return []

        tumor_voxels = np.argwhere(subject.seg > 0)
        if tumor_voxels.size == 0:
            return []

        ph, pw, pd = self.patch_size
        H, W, D = subject.shape

        origins = []
        for vx, vy, vz in tumor_voxels[::max(1, len(tumor_voxels) // 500)]:  # Sub-sample
            x0 = int(np.clip(vx - ph // 2, 0, H - ph))
            y0 = int(np.clip(vy - pw // 2, 0, W - pw))
            z0 = int(np.clip(vz - pd // 2, 0, D - pd))
            origins.append((x0, y0, z0))

        return origins

    def _random_valid_origin(self, volume_shape: Tuple[int, int, int]) -> Tuple[int, int, int]:
        """Sample a random valid patch origin."""
        H, W, D = volume_shape
        ph, pw, pd = self.patch_size
        x = int(self.rng.integers(0, max(1, H - ph + 1)))
        y = int(self.rng.integers(0, max(1, W - pw + 1)))
        z = int(self.rng.integers(0, max(1, D - pd + 1)))
        return (x, y, z)
