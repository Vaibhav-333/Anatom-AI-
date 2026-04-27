"""
radiomics.py — Radiomic Feature Extraction for BraTS segmentation sub-regions.

Extracts IBSI-compliant shape, first-order, and texture features per tumour
sub-region.  Two backends are supported:

  1. PyRadiomics (preferred) — full IBSI feature set via SimpleITK images.
  2. NumPy fallback — a subset of shape + first-order features computed
     directly from numpy arrays (no external dependency required).

Features extracted per region (NCR / ED / ET and composite WT / TC):
  Shape:       sphericity, surface_area_to_volume, elongation, compactness
  First-order: mean_intensity, entropy, kurtosis, skewness, energy
  Texture:     glcm_contrast, glcm_homogeneity, glcm_energy (NumPy approx)

Usage
-----
    from src.analytics.radiomics import RadiomicsExtractor
    extractor = RadiomicsExtractor()
    features = extractor.extract(segmentation, volume=mri_array,
                                  voxel_spacing=(1.0, 1.0, 1.0))
    # features is a dict: {"NCR": {...}, "ED": {...}, "ET": {...}, ...}
"""

from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# BraTS label map
_LABELS = {"NCR": 1, "ED": 2, "ET": 3}
_COMPOSITE = {
    "WT": [1, 2, 3],
    "TC": [1, 3],
}


class RadiomicsExtractor:
    """
    Extract radiomic features from a BraTS integer segmentation mask.

    Parameters
    ----------
    use_pyradiomics : bool
        Try PyRadiomics first (requires `pyradiomics` package). Falls back
        to the numpy backend automatically if unavailable or if extraction
        fails.
    """

    def __init__(self, use_pyradiomics: bool = True) -> None:
        self.use_pyradiomics = use_pyradiomics
        self._pyrad_available = False
        if use_pyradiomics:
            try:
                import radiomics  # noqa: F401
                self._pyrad_available = True
                logger.info("PyRadiomics backend available.")
            except ImportError:
                logger.info("PyRadiomics not installed — using numpy backend.")

    def extract(
        self,
        segmentation: np.ndarray,
        volume: Optional[np.ndarray] = None,
        voxel_spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    ) -> Dict[str, Dict[str, float]]:
        """
        Extract radiomic features for each BraTS sub-region.

        Parameters
        ----------
        segmentation  : (H,W,D) int32 — BraTS label array.
        volume        : (H,W,D) float32 — co-registered MRI intensity
                        (e.g. T1ce). Optional; enables first-order and
                        texture features. Shape features are always computed.
        voxel_spacing : (sx, sy, sz) mm — physical voxel size.

        Returns
        -------
        dict of {region_name: {feature_name: value}}
        """
        results: Dict[str, Dict[str, float]] = {}

        all_regions = list(_LABELS.items()) + [
            (name, labels) for name, labels in _COMPOSITE.items()
        ]

        for region_name, label_or_labels in all_regions:
            if isinstance(label_or_labels, int):
                mask = (segmentation == label_or_labels)
            else:
                mask = np.isin(segmentation, label_or_labels)

            n_voxels = int(mask.sum())
            if n_voxels < 10:
                results[region_name] = _empty_features()
                continue

            if self._pyrad_available and volume is not None:
                feats = self._extract_pyradiomics(mask, volume, voxel_spacing)
            else:
                feats = _extract_numpy(mask, volume, voxel_spacing)

            results[region_name] = feats

        return results

    # ── PyRadiomics backend ───────────────────────────────────────────────────

    def _extract_pyradiomics(
        self,
        mask: np.ndarray,
        volume: np.ndarray,
        voxel_spacing: Tuple[float, float, float],
    ) -> Dict[str, float]:
        """Run PyRadiomics on the given binary mask + intensity volume."""
        try:
            import SimpleITK as sitk
            from radiomics import featureextractor

            img_sitk  = sitk.GetImageFromArray(volume.astype(np.float32))
            mask_sitk = sitk.GetImageFromArray(mask.astype(np.int32))
            img_sitk.SetSpacing(tuple(float(s) for s in voxel_spacing))
            mask_sitk.SetSpacing(tuple(float(s) for s in voxel_spacing))

            settings = {
                "binWidth": 25,
                "resampledPixelSpacing": None,
                "interpolator": sitk.sitkBSpline,
                "enableCExtensions": True,
            }
            extractor = featureextractor.RadiomicsFeatureExtractor(**settings)
            extractor.enableFeaturesByName(
                shape=["Sphericity", "SurfaceVolumeRatio", "Elongation",
                       "Compactness1", "MeshVolume"],
                firstorder=["Mean", "Entropy", "Kurtosis", "Skewness", "Energy"],
                glcm=["Contrast", "Homogeneity2", "JointEnergy"],
            )

            raw = extractor.execute(img_sitk, mask_sitk)
            feats: Dict[str, float] = {}
            key_map = {
                "original_shape_Sphericity":            "sphericity",
                "original_shape_SurfaceVolumeRatio":    "surface_area_to_volume",
                "original_shape_Elongation":            "elongation",
                "original_shape_Compactness1":          "compactness",
                "original_shape_MeshVolume":            "mesh_volume_mm3",
                "original_firstorder_Mean":             "mean_intensity",
                "original_firstorder_Entropy":          "entropy",
                "original_firstorder_Kurtosis":         "kurtosis",
                "original_firstorder_Skewness":         "skewness",
                "original_firstorder_Energy":           "energy",
                "original_glcm_Contrast":               "glcm_contrast",
                "original_glcm_Homogeneity2":           "glcm_homogeneity",
                "original_glcm_JointEnergy":            "glcm_energy",
            }
            for k, short in key_map.items():
                if k in raw:
                    val = raw[k]
                    feats[short] = float(val) if np.isfinite(float(val)) else 0.0

            # Fill missing with numpy fallback values
            np_feats = _extract_numpy(mask, volume, voxel_spacing)
            for k, v in np_feats.items():
                feats.setdefault(k, v)

            return feats

        except Exception as exc:
            logger.warning("PyRadiomics extraction failed (%s) — using numpy.", exc)
            return _extract_numpy(mask, volume, voxel_spacing)


# ── NumPy feature extraction ──────────────────────────────────────────────────

def _extract_numpy(
    mask: np.ndarray,
    volume: Optional[np.ndarray],
    voxel_spacing: Tuple[float, float, float],
) -> Dict[str, float]:
    """Compute a clinically relevant feature subset using numpy only."""
    feats: Dict[str, float] = {}

    sx, sy, sz = voxel_spacing
    voxel_vol = sx * sy * sz
    n_voxels  = int(mask.sum())
    volume_mm3 = n_voxels * voxel_vol

    # ── Shape features ────────────────────────────────────────────────────────
    feats["mesh_volume_mm3"] = volume_mm3

    # Surface area via count of boundary voxels (6-connectivity)
    from scipy.ndimage import binary_erosion
    try:
        eroded       = binary_erosion(mask)
        surface_mask = mask & ~eroded
        surface_voxels = int(surface_mask.sum())
        avg_face_area  = (sx * sy + sx * sz + sy * sz) / 3
        surface_area   = surface_voxels * avg_face_area
    except Exception:
        surface_area = volume_mm3 ** (2 / 3) * 4.84

    feats["surface_area_mm2"] = round(surface_area, 2)

    if surface_area > 0 and volume_mm3 > 0:
        # Sphericity: ratio of sphere with same volume to actual surface area
        r_eq = (3 * volume_mm3 / (4 * np.pi)) ** (1 / 3)
        sphere_sa = 4 * np.pi * r_eq ** 2
        feats["sphericity"] = round(min(sphere_sa / surface_area, 1.0), 4)
        feats["surface_area_to_volume"] = round(surface_area / volume_mm3, 4)
        feats["compactness"] = round(volume_mm3 / (surface_area ** (3 / 2)), 4)
    else:
        feats["sphericity"] = 0.0
        feats["surface_area_to_volume"] = 0.0
        feats["compactness"] = 0.0

    # Elongation: ratio of shortest to longest principal axis (via PCA on voxel coords)
    coords = np.argwhere(mask).astype(np.float32)
    coords *= np.array([[sx, sy, sz]])
    if len(coords) >= 3:
        cov = np.cov(coords.T)
        try:
            eigvals = np.sort(np.linalg.eigvalsh(cov))[::-1]
            eigvals = np.maximum(eigvals, 1e-9)
            feats["elongation"] = round(float(np.sqrt(eigvals[2] / eigvals[0])), 4)
        except Exception:
            feats["elongation"] = 0.5
    else:
        feats["elongation"] = 0.5

    # ── First-order intensity features ────────────────────────────────────────
    if volume is not None:
        vals = volume[mask].astype(np.float64)
        if len(vals) > 0:
            from scipy.stats import kurtosis, skew
            feats["mean_intensity"] = round(float(np.mean(vals)), 4)
            feats["energy"]         = round(float(np.sum(vals ** 2)), 2)
            # Normalised histogram entropy
            hist, _ = np.histogram(vals, bins=64, density=True)
            hist = hist[hist > 0]
            feats["entropy"]   = round(float(-np.sum(hist * np.log2(hist + 1e-12))), 4)
            feats["kurtosis"]  = round(float(kurtosis(vals, fisher=True)), 4)
            feats["skewness"]  = round(float(skew(vals)), 4)

            # Simple GLCM approximation (horizontal neighbour co-occurrence on 2D slice)
            mid_z = mask.shape[2] // 2
            sl = volume[:, :, mid_z] * mask[:, :, mid_z]
            sl_norm = (sl / (sl.max() + 1e-9) * 15).astype(np.int32)
            glcm = _fast_glcm(sl_norm, levels=16)
            feats["glcm_contrast"]   = round(float(_glcm_contrast(glcm)), 4)
            feats["glcm_homogeneity"]= round(float(_glcm_homogeneity(glcm)), 4)
            feats["glcm_energy"]     = round(float(_glcm_energy(glcm)), 4)
        else:
            feats.update(_empty_intensity_features())
    else:
        feats.update(_empty_intensity_features())

    return feats


def _empty_features() -> Dict[str, float]:
    d = _empty_intensity_features()
    d.update({
        "mesh_volume_mm3": 0.0,
        "surface_area_mm2": 0.0,
        "sphericity": 0.0,
        "surface_area_to_volume": 0.0,
        "compactness": 0.0,
        "elongation": 0.0,
    })
    return d


def _empty_intensity_features() -> Dict[str, float]:
    return {
        "mean_intensity": 0.0,
        "energy": 0.0,
        "entropy": 0.0,
        "kurtosis": 0.0,
        "skewness": 0.0,
        "glcm_contrast": 0.0,
        "glcm_homogeneity": 0.0,
        "glcm_energy": 0.0,
    }


# ── Lightweight GLCM ─────────────────────────────────────────────────────────

def _fast_glcm(img: np.ndarray, levels: int = 16) -> np.ndarray:
    glcm = np.zeros((levels, levels), dtype=np.float64)
    for dy, dx in [(0, 1), (1, 0)]:
        s1 = img[:-dy or None, :-dx or None] if dy or dx else img
        s2 = img[dy:, dx:]
        for i, j in zip(s1.ravel(), s2.ravel()):
            if 0 <= i < levels and 0 <= j < levels:
                glcm[i, j] += 1
    total = glcm.sum()
    return glcm / (total + 1e-12)


def _glcm_contrast(glcm: np.ndarray) -> float:
    levels = glcm.shape[0]
    i, j = np.mgrid[0:levels, 0:levels]
    return float(np.sum(glcm * (i - j) ** 2))


def _glcm_homogeneity(glcm: np.ndarray) -> float:
    levels = glcm.shape[0]
    i, j = np.mgrid[0:levels, 0:levels]
    return float(np.sum(glcm / (1 + np.abs(i - j))))


def _glcm_energy(glcm: np.ndarray) -> float:
    return float(np.sum(glcm ** 2))
