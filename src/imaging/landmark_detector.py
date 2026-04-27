"""
landmark_detector.py — Anatomical Landmark Detection via MNI152 Atlas.

Projects canonical MNI152 landmark coordinates (brainstem, ventricles,
corpus callosum, thalamus) into patient space using ANTsPy rigid registration.
Returns a dict of structure name → physical (x,y,z) coordinate in mm, which
the NeuroRenderer renders as labelled spheres in the surgical 3D scene.

Strategy
--------
1. Load canonical MNI landmark coordinates from config/landmarks_mni.yaml.
2. Register patient T1 to MNI152 template using ANTsPy "Rigid" transform
   (~30 s — fast enough for interactive use, avoids full SyN deformable reg).
3. Apply the *inverse* transform to each landmark coordinate, mapping it
   from MNI space → patient voxel space → patient mm space.
4. Return as a dict keyed by landmark name.

Fallback (ANTsPy not available)
--------------------------------
If antspy is not installed, the detector falls back to placing landmarks at
fixed anatomical fractions of the brain bounding box. These are geometrically
plausible for demo purposes but not patient-specific. A warning is raised.

Usage
-----
    from src.imaging.landmark_detector import AnatomicalLandmarkDetector
    detector = AnatomicalLandmarkDetector()
    landmarks = detector.detect(subject, brain_mask, voxel_spacing)
    # landmarks["brainstem"] = np.array([cx_mm, cy_mm, cz_mm])
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import yaml

from src.imaging.loader import MRISubject

logger = logging.getLogger(__name__)

_LANDMARKS_CONFIG = Path(__file__).parent.parent.parent / "config" / "landmarks_mni.yaml"

# Approximate fractional positions within the brain bounding box
# used as fallback when ANTsPy is unavailable.
# (frac_x, frac_y, frac_z) in [0,1] — relative to brain bbox in RAS order.
_FALLBACK_FRACS: Dict[str, Tuple[float, float, float]] = {
    "brainstem":       (0.50, 0.35, 0.18),
    "left_ventricle":  (0.38, 0.52, 0.58),
    "right_ventricle": (0.62, 0.52, 0.58),
    "corpus_callosum": (0.50, 0.55, 0.68),
    "third_ventricle": (0.50, 0.46, 0.52),
    "left_thalamus":   (0.40, 0.44, 0.50),
    "right_thalamus":  (0.60, 0.44, 0.50),
    "left_putamen":    (0.36, 0.52, 0.46),
    "right_putamen":   (0.64, 0.52, 0.46),
}


class AnatomicalLandmarkDetector:
    """
    Detect anatomical landmark positions in patient space.

    Parameters
    ----------
    config_path : Path to landmarks_mni.yaml. Defaults to config/ directory.
    use_ants    : If True (default), attempt ANTsPy registration.
                  If False, always use the geometric fallback.
    visible_only: If True, return only landmarks listed under default_visible
                  in the YAML. If False, return all landmarks.
    """

    def __init__(
        self,
        config_path: Optional[Path] = None,
        use_ants: bool = True,
        visible_only: bool = True,
    ) -> None:
        self.config_path = config_path or _LANDMARKS_CONFIG
        self.use_ants = use_ants
        self.visible_only = visible_only
        self._config = self._load_config()

    def detect(
        self,
        subject: MRISubject,
        brain_mask: Optional[np.ndarray] = None,
        voxel_spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    ) -> Dict[str, np.ndarray]:
        """
        Compute landmark positions in patient mm-space.

        Parameters
        ----------
        subject       : MRISubject — t1 array is used for registration.
        brain_mask    : optional (H,W,D) uint8 — restricts bounding box
                        computation for the fallback method.
        voxel_spacing : (sx,sy,sz) in mm.

        Returns
        -------
        Dict[str, np.ndarray]  — name → [x_mm, y_mm, z_mm].
        """
        landmark_names = self._get_visible_names()

        if self.use_ants:
            try:
                return self._detect_via_ants(
                    subject, voxel_spacing, landmark_names
                )
            except ImportError:
                logger.warning(
                    "ANTsPy not available — using geometric fallback for landmarks. "
                    "Install with: pip install antspy>=0.4.2"
                )
            except Exception as exc:
                logger.warning(
                    "ANTsPy registration failed (%s) — using geometric fallback.", exc
                )

        return self._detect_fallback(subject, brain_mask, voxel_spacing, landmark_names)

    # ── Private: ANTsPy registration path ────────────────────────────────────

    def _detect_via_ants(
        self,
        subject: MRISubject,
        voxel_spacing: Tuple[float, float, float],
        landmark_names: List[str],
    ) -> Dict[str, np.ndarray]:
        """Register T1 to MNI152, inverse-project landmark coordinates."""
        import ants

        logger.info("Running ANTsPy Rigid registration to MNI152 template…")

        # Convert T1 numpy array → ANTs image
        t1 = subject.t1.astype(np.float32)
        t1_ants = ants.from_numpy(
            t1,
            spacing=list(voxel_spacing),
            origin=[0.0, 0.0, 0.0],
            direction=np.eye(3),
        )

        # Load MNI152 template bundled with ANTsPy
        mni_template = ants.image_read(ants.get_ants_data("mni"))

        # Rigid registration: ~25–45 s on CPU
        reg = ants.registration(
            fixed=mni_template,
            moving=t1_ants,
            type_of_transform="Rigid",
            verbose=False,
        )
        # reg["fwdtransforms"] maps T1 → MNI
        # reg["invtransforms"] maps MNI → T1 (what we need)
        inv_transforms = reg["invtransforms"]

        landmarks: Dict[str, np.ndarray] = {}
        config_lms = self._config.get("landmarks", {})

        for name in landmark_names:
            if name not in config_lms:
                continue
            mni_coord = config_lms[name]["mni_ras"]
            mni_pt = ants.from_numpy(
                np.zeros((1, 1, 1), dtype=np.float32),
                spacing=[1.0, 1.0, 1.0],
                origin=list(mni_coord),
            )
            try:
                patient_pt = ants.apply_transforms_to_points(
                    dim=3,
                    points=np.array([mni_coord], dtype=np.float64),
                    transformlist=inv_transforms,
                )
                coord_mm = np.array(
                    [patient_pt["x"][0], patient_pt["y"][0], patient_pt["z"][0]],
                    dtype=np.float32,
                )
                landmarks[name] = coord_mm
                logger.debug("Landmark '%s': MNI%s → patient%s", name, mni_coord, coord_mm)
            except Exception as exc:
                logger.warning("Could not project landmark '%s': %s", name, exc)

        logger.info("ANTsPy landmark detection complete — %d landmarks found.", len(landmarks))
        return landmarks

    # ── Private: geometric fallback ───────────────────────────────────────────

    def _detect_fallback(
        self,
        subject: MRISubject,
        brain_mask: Optional[np.ndarray],
        voxel_spacing: Tuple[float, float, float],
        landmark_names: List[str],
    ) -> Dict[str, np.ndarray]:
        """
        Place landmarks at fixed anatomical fractions of the brain bounding box.

        Not patient-specific, but anatomically plausible for demo and as a
        graceful degradation when ANTsPy is unavailable.
        """
        logger.info("Using geometric fallback for landmark detection.")

        # Compute brain bounding box from T1 or mask
        if brain_mask is not None:
            brain_vox = np.argwhere(brain_mask > 0)
        else:
            brain_vox = np.argwhere(subject.t1 > subject.t1.max() * 0.05)

        if len(brain_vox) == 0:
            # Last resort: use full volume dims
            H, W, D = subject.t1.shape
            min_vox = np.array([0, 0, 0])
            max_vox = np.array([H, W, D])
        else:
            min_vox = brain_vox.min(axis=0)
            max_vox = brain_vox.max(axis=0)

        span = (max_vox - min_vox).astype(np.float32)
        sx, sy, sz = voxel_spacing

        landmarks: Dict[str, np.ndarray] = {}
        for name in landmark_names:
            fracs = _FALLBACK_FRACS.get(name)
            if fracs is None:
                continue
            vox = min_vox + span * np.array(fracs, dtype=np.float32)
            mm = np.array([vox[0] * sx, vox[1] * sy, vox[2] * sz], dtype=np.float32)
            landmarks[name] = mm

        return landmarks

    # ── Config helpers ────────────────────────────────────────────────────────

    def _load_config(self) -> dict:
        if not self.config_path.exists():
            logger.warning("Landmark config not found at %s", self.config_path)
            return {}
        with open(self.config_path, "r") as f:
            return yaml.safe_load(f) or {}

    def _get_visible_names(self) -> List[str]:
        if not self.visible_only:
            return list(self._config.get("landmarks", {}).keys())
        return self._config.get(
            "default_visible",
            list(_FALLBACK_FRACS.keys()),
        )

    def get_proximity_threshold(self) -> float:
        """Return the landmark proximity warning distance in mm."""
        return float(self._config.get("proximity_warning_mm", 8.0))

    def get_landmark_metadata(self, name: str) -> dict:
        """Return the full metadata dict for a landmark by name."""
        return self._config.get("landmarks", {}).get(name, {})
