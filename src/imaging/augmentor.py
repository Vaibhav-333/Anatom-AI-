"""
augmentor.py — Medical-grade 3D data augmentation for MRI brain volumes.

All transforms are label-preserving: the EXACT same spatial transform is
applied to all four image modalities AND the segmentation label simultaneously.
Intensity augmentations (gamma, noise) are applied only to images — not labels.

Augmentation strategy
---------------------
1. Random 3D axis flips (LR / AP / SI)
2. Random rigid transform (rotation + translation)
3. Random elastic deformation (only if enabled — slow but powerful)
4. Gamma intensity augmentation per modality independently

Design note: All operations use numpy + scipy only — no external frameworks
needed at Phase 1. PyTorch-based augmentation (monai.transforms) can replace
this in Phase 2 without changing the MRISubject interface.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np
from scipy.ndimage import affine_transform, gaussian_filter, map_coordinates

from .loader import MRISubject

logger = logging.getLogger(__name__)


@dataclass
class AugmentationConfig:
    """Configuration for the 3D augmentor."""
    # Spatial flips
    flip_axial: bool = True
    flip_sagittal: bool = True
    flip_coronal: bool = True

    # Random rotation
    rotation_range_deg: float = 15.0      # ± degrees per axis
    rotation_prob: float = 0.5

    # Random scaling
    scale_range: Tuple[float, float] = (0.9, 1.1)
    scale_prob: float = 0.3

    # Elastic deformation
    elastic_enabled: bool = True
    elastic_sigma: float = 5.0            # Controls smoothness
    elastic_alpha: float = 40.0           # Controls magnitude
    elastic_prob: float = 0.3

    # Intensity augmentation (images only)
    gamma_range: Tuple[float, float] = (0.7, 1.5)
    gamma_prob: float = 0.5

    # Gaussian noise
    noise_std_range: Tuple[float, float] = (0.0, 0.05)
    noise_prob: float = 0.2

    # Random seed (None = random each call)
    seed: Optional[int] = None


class Augmentor:
    """
    Applies stochastic 3D augmentations to an MRISubject.

    Each call to augment() draws new random parameters, so the same
    subject produces a different augmented view each time — essential for
    training set diversity.

    Parameters
    ----------
    config : AugmentationConfig
        Controls which augmentations are active and their magnitudes.
    """

    def __init__(self, config: Optional[AugmentationConfig] = None) -> None:
        self.config = config or AugmentationConfig()

    def augment(self, subject: MRISubject) -> MRISubject:
        """
        Apply a random augmentation chain to the subject.

        Parameters
        ----------
        subject : MRISubject (post normalisation).

        Returns
        -------
        Augmented MRISubject. Original subject is not modified.
        """
        cfg = self.config
        rng = np.random.default_rng(cfg.seed)

        modalities = {k: v.copy() for k, v in subject.modalities.items()}
        seg = subject.seg.copy() if subject.seg is not None else None

        # 1. Random flips (applied to all channels + seg)
        modalities, seg = self._random_flips(modalities, seg, rng, cfg)

        # 2. Random affine (rotation + scale)
        if rng.random() < cfg.rotation_prob:
            modalities, seg = self._random_affine(modalities, seg, rng, cfg)

        # 3. Elastic deformation
        if cfg.elastic_enabled and rng.random() < cfg.elastic_prob:
            modalities, seg = self._elastic_deform(modalities, seg, rng, cfg)

        # 4. Gamma augmentation (images only)
        for name in list(modalities.keys()):
            if rng.random() < cfg.gamma_prob:
                modalities[name] = self._gamma_augment(modalities[name], rng, cfg)

        # 5. Gaussian noise (images only)
        for name in list(modalities.keys()):
            if rng.random() < cfg.noise_prob:
                modalities[name] = self._add_noise(modalities[name], rng, cfg)

        return MRISubject(
            subject_id=subject.subject_id,
            t1=modalities["t1"],
            t1ce=modalities["t1ce"],
            t2=modalities["t2"],
            flair=modalities["flair"],
            seg=seg,
            metadata=subject.metadata,
        )

    def _random_flips(
        self,
        modalities: dict,
        seg: Optional[np.ndarray],
        rng: np.random.Generator,
        cfg: AugmentationConfig,
    ):
        """Randomly flip along axial (dim 2), sagittal (dim 0), coronal (dim 1)."""
        flip_axes = []
        if cfg.flip_axial and rng.random() > 0.5:
            flip_axes.append(2)
        if cfg.flip_sagittal and rng.random() > 0.5:
            flip_axes.append(0)
        if cfg.flip_coronal and rng.random() > 0.5:
            flip_axes.append(1)

        for axis in flip_axes:
            modalities = {k: np.flip(v, axis=axis).copy() for k, v in modalities.items()}
            if seg is not None:
                seg = np.flip(seg, axis=axis).copy()

        return modalities, seg

    def _random_affine(
        self,
        modalities: dict,
        seg: Optional[np.ndarray],
        rng: np.random.Generator,
        cfg: AugmentationConfig,
    ):
        """Apply random rotation and optional scaling."""
        shape = next(iter(modalities.values())).shape
        centre = np.array(shape) / 2.0

        angles_deg = rng.uniform(-cfg.rotation_range_deg, cfg.rotation_range_deg, 3)
        angles_rad = np.deg2rad(angles_deg)
        scale = rng.uniform(*cfg.scale_range) if rng.random() < cfg.scale_prob else 1.0

        R = _rotation_matrix_3d(*angles_rad) * scale
        offset = centre - R @ centre

        interp_order_img = 3
        interp_order_seg = 0

        modalities = {
            k: affine_transform(v, R, offset=offset, order=interp_order_img, mode="constant", cval=0.0)
            for k, v in modalities.items()
        }
        if seg is not None:
            seg = affine_transform(
                seg.astype(np.float32), R, offset=offset,
                order=interp_order_seg, mode="constant", cval=0.0
            ).astype(np.int16)

        return modalities, seg

    def _elastic_deform(
        self,
        modalities: dict,
        seg: Optional[np.ndarray],
        rng: np.random.Generator,
        cfg: AugmentationConfig,
    ):
        """
        Simoncelli-style elastic deformation.

        Creates a smooth random displacement field by smoothing random noise
        with a Gaussian kernel, then uses it to remap voxel coordinates.
        """
        shape = next(iter(modalities.values())).shape

        # Generate random displacement field
        dx = gaussian_filter(rng.standard_normal(shape).astype(np.float32), sigma=cfg.elastic_sigma)
        dy = gaussian_filter(rng.standard_normal(shape).astype(np.float32), sigma=cfg.elastic_sigma)
        dz = gaussian_filter(rng.standard_normal(shape).astype(np.float32), sigma=cfg.elastic_sigma)

        # Scale displacement
        dx *= cfg.elastic_alpha / dx.std() if dx.std() > 1e-8 else cfg.elastic_alpha
        dy *= cfg.elastic_alpha / dy.std() if dy.std() > 1e-8 else cfg.elastic_alpha
        dz *= cfg.elastic_alpha / dz.std() if dz.std() > 1e-8 else cfg.elastic_alpha

        # Build coordinate map
        x, y, z = np.meshgrid(
            np.arange(shape[0]), np.arange(shape[1]), np.arange(shape[2]), indexing="ij"
        )
        coords = [
            np.clip(x + dx, 0, shape[0] - 1),
            np.clip(y + dy, 0, shape[1] - 1),
            np.clip(z + dz, 0, shape[2] - 1),
        ]

        modalities = {
            k: map_coordinates(v, coords, order=3, mode="constant", cval=0.0).astype(np.float32)
            for k, v in modalities.items()
        }
        if seg is not None:
            seg = map_coordinates(
                seg.astype(np.float32), coords, order=0, mode="constant", cval=0.0
            ).astype(np.int16)

        return modalities, seg

    def _gamma_augment(
        self,
        volume: np.ndarray,
        rng: np.random.Generator,
        cfg: AugmentationConfig,
    ) -> np.ndarray:
        """
        Apply random gamma correction: out = sign(x) * |x|^gamma.

        Works on z-score normalised data (can be negative) via the signed form.
        """
        gamma = rng.uniform(*cfg.gamma_range)
        brain_mask = volume != 0.0
        result = volume.copy()
        v = result[brain_mask]
        result[brain_mask] = np.sign(v) * (np.abs(v) ** gamma)
        return result.astype(np.float32)

    def _add_noise(
        self,
        volume: np.ndarray,
        rng: np.random.Generator,
        cfg: AugmentationConfig,
    ) -> np.ndarray:
        """Add Gaussian noise sampled from the configured std range."""
        std = rng.uniform(*cfg.noise_std_range)
        noise = rng.normal(0, std, volume.shape).astype(np.float32)
        return (volume + noise).astype(np.float32)


def _rotation_matrix_3d(rx: float, ry: float, rz: float) -> np.ndarray:
    """
    Compose a 3D rotation matrix from Euler angles (radians).
    Convention: Rx @ Ry @ Rz (extrinsic XYZ).
    """
    Rx = np.array([
        [1,           0,            0],
        [0,  np.cos(rx), -np.sin(rx)],
        [0,  np.sin(rx),  np.cos(rx)],
    ], dtype=np.float64)

    Ry = np.array([
        [ np.cos(ry), 0, np.sin(ry)],
        [          0, 1,          0],
        [-np.sin(ry), 0, np.cos(ry)],
    ], dtype=np.float64)

    Rz = np.array([
        [np.cos(rz), -np.sin(rz), 0],
        [np.sin(rz),  np.cos(rz), 0],
        [         0,           0, 1],
    ], dtype=np.float64)

    return Rx @ Ry @ Rz
