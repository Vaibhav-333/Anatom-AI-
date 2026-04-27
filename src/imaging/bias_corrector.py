"""
bias_corrector.py — N4ITK Bias Field Correction for MRI volumes.

MRI scanners introduce a smooth, low-frequency intensity non-uniformity
("bias field") caused by RF coil inhomogeneity. Without correcting this,
the same tissue type can appear 20–30% brighter near the coil than far
from it — which both confounds intensity normalization and misleads the
segmentation model.

N4BiasFieldCorrection (Tustison et al. 2010) is the clinical gold standard.
It is available via SimpleITK and operates entirely in CPU memory.

Pipeline position: FIRST step, before skull stripping and normalization.
This is critical — accurate skull stripping depends on uniform intensity.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import numpy as np
import SimpleITK as sitk

from .loader import MRISubject

logger = logging.getLogger(__name__)


class BiasCorrector:
    """
    Apply N4ITK bias field correction to all image modalities of an MRISubject.

    Parameters
    ----------
    n_iterations : list[int]
        Number of optimizer iterations at each resolution level.
        Default [50, 50, 50, 50] = 4 levels, 50 iterations each.
        Reduce for speed; increase for accuracy on heavy artefacts.
    convergence_threshold : float
        Early-stop convergence threshold. Default 0.001.
    shrink_factor : int
        Downsampling factor applied before correction for speed.
        Images are upsampled back after. Default 4.
    mask_image : np.ndarray | None
        Optional binary brain mask. If supplied, correction is computed
        only inside the mask (much faster and more accurate).
    modalities_to_correct : list[str] | None
        Which modalities to correct. Defaults to all four.
    """

    def __init__(
        self,
        n_iterations: List[int] = None,
        convergence_threshold: float = 0.001,
        shrink_factor: int = 4,
        mask_image: Optional[np.ndarray] = None,
        modalities_to_correct: Optional[List[str]] = None,
    ) -> None:
        self.n_iterations = n_iterations or [50, 50, 50, 50]
        self.convergence_threshold = convergence_threshold
        self.shrink_factor = shrink_factor
        self.mask_image = mask_image
        self.modalities_to_correct = modalities_to_correct or ["t1", "t1ce", "t2", "flair"]

    def correct(self, subject: MRISubject) -> MRISubject:
        """
        Run N4 bias field correction on each specified modality.

        Parameters
        ----------
        subject : MRISubject with raw float32 arrays.

        Returns
        -------
        MRISubject with bias-corrected float32 arrays.
        """
        corrected_modalities = {}

        for name, volume in subject.modalities.items():
            if name not in self.modalities_to_correct:
                corrected_modalities[name] = volume
                continue

            logger.info("Running N4 bias correction on '%s'  shape=%s", name, volume.shape)
            corrected_modalities[name] = self._correct_volume(volume)

        return MRISubject(
            subject_id=subject.subject_id,
            t1=corrected_modalities["t1"],
            t1ce=corrected_modalities["t1ce"],
            t2=corrected_modalities["t2"],
            flair=corrected_modalities["flair"],
            seg=subject.seg,
            metadata=subject.metadata,
        )

    def _correct_volume(self, volume: np.ndarray) -> np.ndarray:
        """Run N4 on a single 3D numpy array and return the corrected array."""
        # Convert to SimpleITK image (float32 required by N4)
        sitk_img = sitk.GetImageFromArray(volume.astype(np.float32))

        # Build optional mask
        sitk_mask = self._build_sitk_mask(volume)

        # Shrink for speed
        if self.shrink_factor > 1:
            shrunk = sitk.Shrink(
                sitk_img,
                [self.shrink_factor] * sitk_img.GetDimension(),
            )
            shrunk_mask = sitk.Shrink(
                sitk_mask,
                [self.shrink_factor] * sitk_mask.GetDimension(),
            ) if sitk_mask is not None else None
        else:
            shrunk = sitk_img
            shrunk_mask = sitk_mask

        # Configure N4 corrector
        corrector = sitk.N4BiasFieldCorrectionImageFilter()
        corrector.SetMaximumNumberOfIterations(self.n_iterations)
        corrector.SetConvergenceThreshold(self.convergence_threshold)

        # Execute on shrunk image
        if shrunk_mask is not None:
            corrector.Execute(shrunk, shrunk_mask)
        else:
            corrector.Execute(shrunk)

        # Retrieve log bias field and upsample to original resolution
        log_bias_field = corrector.GetLogBiasFieldAsImage(sitk_img)

        # Apply: corrected = original / exp(log_bias_field)
        corrected_sitk = sitk_img / sitk.Exp(log_bias_field)

        corrected = sitk.GetArrayFromImage(corrected_sitk).astype(np.float32)
        logger.debug(
            "N4 complete  original_range=[%.2f, %.2f]  corrected_range=[%.2f, %.2f]",
            float(volume.min()), float(volume.max()),
            float(corrected.min()), float(corrected.max()),
        )
        return corrected

    def _build_sitk_mask(self, volume: np.ndarray) -> Optional[sitk.Image]:
        """Build a SimpleITK binary mask for N4 computation region."""
        if self.mask_image is not None:
            mask_arr = self.mask_image.astype(np.uint8)
        else:
            # Use Otsu threshold as a quick proxy mask
            sitk_tmp = sitk.GetImageFromArray(volume.astype(np.float32))
            otsu_filter = sitk.OtsuThresholdImageFilter()
            otsu_filter.SetInsideValue(0)
            otsu_filter.SetOutsideValue(1)
            return otsu_filter.Execute(sitk_tmp)

        return sitk.GetImageFromArray(mask_arr)
