"""
trajectory_planner.py — Surgical Trajectory Planning.

Computes the top-3 optimal approach trajectories from the skull surface to
the tumour centroid. Each trajectory is scored on:

  • Path length     (shorter = better — less brain tissue disruption)
  • Safety margin   (penalty for passing within warning radius of critical structures)
  • Normal alignment (reward for entering cortex perpendicular to its surface —
                      reduces cortical damage)

Algorithm
---------
1. Sample N candidate entry points from the pial surface mesh vertices
   (evenly spaced via a spatial grid to cover the full surface).
2. For each candidate, build the straight-line segment to the tumour centroid.
3. Score each segment using the weighted criteria above.
4. Return the top-3 highest-scoring trajectories as TrajectoryResult objects.

Landmark avoidance uses trimesh ray-mesh intersection to test whether the
trajectory line passes through each landmark's exclusion sphere.

Usage
-----
    from src.analytics.trajectory_planner import SurgicalTrajectoryPlanner
    planner = SurgicalTrajectoryPlanner()
    results = planner.plan(cortex_mesh, tumor_centroid, landmarks)
    # results[0] is the best trajectory
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Default proximity warning radius per landmark type (mm)
_DEFAULT_EXCLUSION_RADIUS: Dict[str, float] = {
    "brainstem":       14.0,
    "left_ventricle":  10.0,
    "right_ventricle": 10.0,
    "corpus_callosum": 8.0,
    "third_ventricle": 8.0,
    "left_thalamus":   10.0,
    "right_thalamus":  10.0,
    "left_putamen":    7.0,
    "right_putamen":   7.0,
}

# Scoring weights
_W_LENGTH   = 0.30   # reward shorter paths
_W_SAFETY   = 0.55   # penalise landmark proximity
_W_NORMAL   = 0.15   # reward surface-normal alignment at entry point


@dataclass
class TrajectoryResult:
    """A single ranked surgical trajectory."""
    rank: int                                     # 0 = best
    entry_point: np.ndarray                       # (3,) mm — skull entry
    target_point: np.ndarray                      # (3,) mm — tumour centroid
    path_length_mm: float
    safety_score: float                           # 0.0–1.0 (higher = safer)
    warnings: List[str] = field(default_factory=list)
    landmark_distances: Dict[str, float] = field(default_factory=dict)
    normal_alignment: float = 0.0                 # dot product with cortex normal


class SurgicalTrajectoryPlanner:
    """
    Plan optimal surgical approach trajectories to a brain tumour.

    Parameters
    ----------
    n_candidates : int
        Number of surface points to evaluate as candidate entry points.
        Higher = better coverage but slower. Default 800 gives good results.
    proximity_warning_mm : float
        Distance (mm) below which a landmark triggers a warning.
    n_results : int
        Number of top trajectories to return (default 3).
    """

    def __init__(
        self,
        n_candidates: int = 800,
        proximity_warning_mm: float = 8.0,
        n_results: int = 3,
    ) -> None:
        self.n_candidates = n_candidates
        self.proximity_warning_mm = proximity_warning_mm
        self.n_results = n_results

    def plan(
        self,
        cortex_mesh,
        tumor_centroid: Tuple[float, float, float],
        landmarks: Optional[Dict[str, np.ndarray]] = None,
        excluded_landmarks: Optional[List[str]] = None,
    ) -> List[TrajectoryResult]:
        """
        Compute top-N surgical trajectories.

        Parameters
        ----------
        cortex_mesh      : pyvista.PolyData — pial surface.
                           Falls back to a synthetic hemisphere if None.
        tumor_centroid   : (x,y,z) mm — target point.
        landmarks        : dict of name→(x,y,z) mm from AnatomicalLandmarkDetector.
        excluded_landmarks: landmark names to treat as hard exclusions (not just
                           scored penalties). Defaults to ["brainstem"].

        Returns
        -------
        List[TrajectoryResult] sorted by safety_score descending (best first).
        """
        if excluded_landmarks is None:
            excluded_landmarks = ["brainstem"]

        target = np.asarray(tumor_centroid, dtype=np.float64)
        landmarks = landmarks or {}

        # ── Step 1: Sample candidate entry points from cortex ────────────
        entry_points, normals = self._sample_surface(cortex_mesh, self.n_candidates)
        logger.info(
            "Evaluating %d trajectory candidates to centroid %s",
            len(entry_points), np.round(target, 1),
        )

        # ── Step 2: Score each candidate ─────────────────────────────────
        scores: List[Tuple[float, int, dict]] = []
        for i, (entry, normal) in enumerate(zip(entry_points, normals)):
            result = self._score_trajectory(
                entry, target, normal, landmarks, excluded_landmarks
            )
            scores.append((result["total"], i, result))

        # ── Step 3: Sort and take top N ───────────────────────────────────
        scores.sort(key=lambda x: x[0], reverse=True)
        top = scores[: self.n_results]

        results: List[TrajectoryResult] = []
        for rank, (total_score, idx, detail) in enumerate(top):
            entry = entry_points[idx]
            path_len = float(np.linalg.norm(target - entry))
            warnings = detail["warnings"]
            lm_dists = detail["lm_dists"]

            results.append(TrajectoryResult(
                rank=rank,
                entry_point=entry,
                target_point=target,
                path_length_mm=path_len,
                safety_score=round(total_score, 3),
                warnings=warnings,
                landmark_distances=lm_dists,
                normal_alignment=detail["normal_align"],
            ))

        logger.info(
            "Top trajectory: length=%.1f mm  safety=%.2f  warnings=%d",
            results[0].path_length_mm if results else 0,
            results[0].safety_score if results else 0,
            len(results[0].warnings) if results else 0,
        )
        return results

    # ── Private: surface sampling ─────────────────────────────────────────

    def _sample_surface(
        self,
        cortex_mesh,
        n_candidates: int,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Return (n_candidates, 3) arrays of surface entry points and normals.

        Uses spatial grid subsampling for even distribution across the cortex.
        Falls back to random vertex sampling if trimesh is unavailable.
        """
        if cortex_mesh is None:
            return self._synthetic_hemisphere(n_candidates)

        try:
            import trimesh
            verts = np.array(cortex_mesh.points, dtype=np.float64)
            faces_flat = np.array(cortex_mesh.faces, dtype=np.int32)

            # Reshape pyvista face array [n, v0, v1, v2] → (N,3)
            # PyVista stores: [3, i, j, k, 3, i, j, k, ...]
            n_faces = len(faces_flat) // 4
            faces = faces_flat.reshape(n_faces, 4)[:, 1:]

            tm = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
            tm.fix_normals()

            # Sample evenly on surface
            pts, face_idx = trimesh.sample.sample_surface_even(tm, n_candidates)
            norms = tm.face_normals[face_idx]

            return pts.astype(np.float64), norms.astype(np.float64)

        except Exception as exc:
            logger.warning("trimesh surface sampling failed (%s) — using vertex subset.", exc)
            verts = np.array(cortex_mesh.points, dtype=np.float64)
            if len(verts) > n_candidates:
                idx = np.random.choice(len(verts), n_candidates, replace=False)
                verts = verts[idx]
            normals = np.zeros_like(verts)
            normals[:, 2] = 1.0   # approximate upward normal
            return verts, normals

    def _synthetic_hemisphere(
        self, n: int
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Generate a synthetic hemisphere surface for demo mode."""
        rng = np.random.default_rng(42)
        phi = rng.uniform(0, np.pi, n)
        theta = rng.uniform(0, 2 * np.pi, n)
        r = 90.0  # approximate brain radius in mm
        x = r * np.sin(phi) * np.cos(theta) + 120
        y = r * np.sin(phi) * np.sin(theta) + 120
        z = r * np.cos(phi) + 80
        pts = np.stack([x, y, z], axis=1)
        norms = pts / (np.linalg.norm(pts, axis=1, keepdims=True) + 1e-8)
        return pts, norms

    # ── Private: scoring ──────────────────────────────────────────────────

    def _score_trajectory(
        self,
        entry: np.ndarray,
        target: np.ndarray,
        normal: np.ndarray,
        landmarks: Dict[str, np.ndarray],
        excluded: List[str],
    ) -> dict:
        """Compute composite score for one trajectory."""
        direction = target - entry
        length = float(np.linalg.norm(direction))
        if length < 1e-6:
            return {"total": 0.0, "warnings": [], "lm_dists": {}, "normal_align": 0.0}

        dir_unit = direction / length

        # ── Normal alignment score ────────────────────────────────────────
        norm_unit = normal / (np.linalg.norm(normal) + 1e-8)
        normal_align = float(np.dot(dir_unit, -norm_unit))   # -1 to 1; 1=perpendicular entry
        normal_score = max(0.0, normal_align)

        # ── Length score ──────────────────────────────────────────────────
        # Normalise against typical skull-to-tumour range 20–180 mm
        length_score = 1.0 - np.clip((length - 20) / 160, 0, 1)

        # ── Landmark safety score ─────────────────────────────────────────
        lm_dists: Dict[str, float] = {}
        warnings: List[str] = []
        penalty = 0.0

        for name, coords in landmarks.items():
            lm_pt = np.asarray(coords, dtype=np.float64)
            # Distance from landmark to closest point on trajectory segment
            dist = _point_to_segment_distance(lm_pt, entry, target)
            lm_dists[name] = round(dist, 1)

            excl_r = _DEFAULT_EXCLUSION_RADIUS.get(name, self.proximity_warning_mm)
            warn_r = self.proximity_warning_mm

            if name in excluded and dist < excl_r:
                penalty += 1.0   # hard exclusion — near-zero score
                warnings.append(f"Passes through {name.replace('_',' ').title()} ({dist:.1f} mm)")
            elif dist < warn_r:
                pen = (1 - dist / warn_r) ** 2 * 0.6
                penalty = max(penalty, pen)
                warnings.append(f"{dist:.1f} mm from {name.replace('_',' ').title()}")

        safety_score = max(0.0, 1.0 - penalty)

        total = (
            _W_LENGTH  * length_score +
            _W_SAFETY  * safety_score +
            _W_NORMAL  * normal_score
        )

        return {
            "total":        round(total, 4),
            "length_score": length_score,
            "safety_score": safety_score,
            "normal_align": round(normal_align, 3),
            "warnings":     warnings,
            "lm_dists":     lm_dists,
        }


# ── Utility ───────────────────────────────────────────────────────────────────

def _point_to_segment_distance(
    point: np.ndarray,
    seg_start: np.ndarray,
    seg_end: np.ndarray,
) -> float:
    """Minimum distance from `point` to the line segment [seg_start, seg_end]."""
    d = seg_end - seg_start
    len_sq = float(np.dot(d, d))
    if len_sq < 1e-12:
        return float(np.linalg.norm(point - seg_start))
    t = np.clip(np.dot(point - seg_start, d) / len_sq, 0.0, 1.0)
    proj = seg_start + t * d
    return float(np.linalg.norm(point - proj))
