"""
registrar.py — Multi-modal MRI co-registration.

BraTS data ships pre-registered, but real clinical data almost never is.
This module co-registers T1, T2, and FLAIR to T1ce (the reference modality
with highest tumour contrast) using SimpleITK rigid registration.

Why rigid (not affine/deformable)?
  Multi-modal acquisitions of the same brain in a single session differ only
  due to patient motion between scans — a rigid transform (6 DOF: 3 rotation,
  3 translation) is the correct model. Deformable registration would distort
  anatomy and is inappropriate here.

Transform matrices are saved so that surgical coordinates computed in
Phase 4 can be inverse-mapped to scanner space.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np
import SimpleITK as sitk

from .loader import MRISubject

logger = logging.getLogger(__name__)


class ModalityRegistrar:
    """
    Register all image modalities to a common reference using rigid registration.

    Parameters
    ----------
    reference_modality : str
        The modality all others are registered TO. Default "t1ce".
    interpolator : str
        Interpolation for the final resampling.
        "linear"  — good quality, fast (default).
        "bspline" — highest quality, slower.
        "nearest" — only for labels.
    learning_rate : float
        Gradient descent step size for the registration optimizer.
    n_iterations : int
        Maximum optimizer iterations per resolution level.
    shrink_factors : list[int]
        Multi-resolution pyramid shrink factors (coarse → fine).
    smoothing_sigmas : list[float]
        Gaussian smoothing per resolution level (mm).
    transform_save_dir : Path | None
        If set, save the .tfm transform file for each modality here.
        Useful for inverse-mapping surgical coordinates.
    """

    INTERPOLATORS = {
        "linear":  sitk.sitkLinear,
        "bspline": sitk.sitkBSpline,
        "nearest": sitk.sitkNearestNeighbor,
    }

    def __init__(
        self,
        reference_modality: str = "t1ce",
        interpolator: str = "linear",
        learning_rate: float = 1.0,
        n_iterations: int = 100,
        shrink_factors: Optional[list] = None,
        smoothing_sigmas: Optional[list] = None,
        transform_save_dir: Optional[Path] = None,
    ) -> None:
        if interpolator not in self.INTERPOLATORS:
            raise ValueError(f"Unknown interpolator '{interpolator}'. Choose from {list(self.INTERPOLATORS)}.")
        self.reference_modality = reference_modality
        self.interpolator = self.INTERPOLATORS[interpolator]
        self.learning_rate = learning_rate
        self.n_iterations = n_iterations
        self.shrink_factors = shrink_factors or [4, 2, 1]
        self.smoothing_sigmas = smoothing_sigmas or [2.0, 1.0, 0.0]
        self.transform_save_dir = transform_save_dir

    def register(self, subject: MRISubject) -> Tuple[MRISubject, Dict[str, sitk.Transform]]:
        """
        Co-register all modalities to the reference.

        Parameters
        ----------
        subject : MRISubject with float32 arrays.

        Returns
        -------
        registered_subject : MRISubject with aligned arrays.
        transforms        : dict mapping modality name → SimpleITK Transform.
                            Reference modality maps to the identity transform.
        """
        reference_array = subject.modalities[self.reference_modality]
        fixed_image = _numpy_to_sitk(reference_array)

        transforms: Dict[str, sitk.Transform] = {}
        registered_modalities: Dict[str, np.ndarray] = {}

        for name, volume in subject.modalities.items():
            if name == self.reference_modality:
                registered_modalities[name] = volume
                transforms[name] = sitk.Transform()  # identity
                logger.debug("'%s' is the reference — no registration needed.", name)
                continue

            logger.info("Registering '%s' → '%s'", name, self.reference_modality)
            moving_image = _numpy_to_sitk(volume)

            transform = self._register_pair(fixed_image, moving_image)
            registered_volume = self._apply_transform(fixed_image, moving_image, transform)

            registered_modalities[name] = registered_volume
            transforms[name] = transform

            if self.transform_save_dir is not None:
                self._save_transform(transform, subject.subject_id, name)

        return (
            MRISubject(
                subject_id=subject.subject_id,
                t1=registered_modalities["t1"],
                t1ce=registered_modalities["t1ce"],
                t2=registered_modalities["t2"],
                flair=registered_modalities["flair"],
                seg=subject.seg,
                metadata=subject.metadata,
            ),
            transforms,
        )

    def _register_pair(
        self,
        fixed: sitk.Image,
        moving: sitk.Image,
    ) -> sitk.Transform:
        """Run multi-resolution rigid registration and return the final transform."""
        registration = sitk.ImageRegistrationMethod()

        # Metric: Mattes Mutual Information — standard for multi-modal MRI
        registration.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50)
        registration.SetMetricSamplingStrategy(registration.RANDOM)
        registration.SetMetricSamplingPercentage(0.01)

        # Interpolator
        registration.SetInterpolator(sitk.sitkLinear)

        # Optimizer: gradient descent with line search
        registration.SetOptimizerAsGradientDescent(
            learningRate=self.learning_rate,
            numberOfIterations=self.n_iterations,
            convergenceMinimumValue=1e-6,
            convergenceWindowSize=10,
        )
        registration.SetOptimizerScalesFromPhysicalShift()

        # Initial transform: geometry-based centre alignment
        initial_transform = sitk.CenteredTransformInitializer(
            fixed,
            moving,
            sitk.Euler3DTransform(),
            sitk.CenteredTransformInitializerFilter.GEOMETRY,
        )
        registration.SetInitialTransform(initial_transform, inPlace=False)

        # Multi-resolution pyramid
        registration.SetShrinkFactorsPerLevel(self.shrink_factors)
        registration.SetSmoothingSigmasPerLevel(self.smoothing_sigmas)
        registration.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()

        final_transform = registration.Execute(
            sitk.Cast(fixed, sitk.sitkFloat32),
            sitk.Cast(moving, sitk.sitkFloat32),
        )
        logger.debug(
            "Registration complete  metric=%.6f  iterations=%d",
            registration.GetMetricValue(),
            registration.GetOptimizerIteration(),
        )
        return final_transform

    def _apply_transform(
        self,
        fixed: sitk.Image,
        moving: sitk.Image,
        transform: sitk.Transform,
    ) -> np.ndarray:
        """Resample moving image into fixed image space using the estimated transform."""
        resampled = sitk.Resample(
            moving,
            fixed,
            transform,
            self.interpolator,
            0.0,
            moving.GetPixelID(),
        )
        return sitk.GetArrayFromImage(resampled).astype(np.float32)

    def _save_transform(
        self,
        transform: sitk.Transform,
        subject_id: str,
        modality: str,
    ) -> None:
        """Persist a transform to disk as a SimpleITK .tfm file."""
        self.transform_save_dir.mkdir(parents=True, exist_ok=True)
        tfm_path = self.transform_save_dir / f"{subject_id}_{modality}_to_{self.reference_modality}.tfm"
        sitk.WriteTransform(transform, str(tfm_path))
        logger.debug("Saved transform: %s", tfm_path)


def _numpy_to_sitk(array: np.ndarray) -> sitk.Image:
    """Convert a float32 numpy (H, W, D) array to a SimpleITK image."""
    img = sitk.GetImageFromArray(array.astype(np.float32))
    return img
