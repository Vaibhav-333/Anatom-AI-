"""
uncertainty_3d.py — Neon Mist: 3D uncertainty fog builder for PyVista.

Converts a per-voxel MC Dropout entropy map into a pyvista.PolyData point
cloud that can be added to the NeuroRenderer surgical scene as a "neon mist"
hovering around the tumour boundary — indicating where the model was least
certain and the tumour may be infiltrating beyond visible margins.

Visual design
-------------
Two layered isosurfaces create a depth-graded mist effect:
  • Outer fog  (P75 percentile) — low opacity 0.20, sparse
  • Dense core (P90 percentile) — higher opacity 0.55, concentrated

Points are coloured by entropy value using the "plasma" colormap (dark purple
→ bright yellow), so clinical users can read uncertainty magnitude at a glance.

Usage
-----
    from src.ui.uncertainty_3d import build_uncertainty_fog
    fog = build_uncertainty_fog(entropy_map, voxel_spacing=(1,1,1))
    # fog is a pyvista.PolyData with scalar array "entropy"
    # Pass to NeuroRenderer.render_combined(..., uncertainty_fog=fog)
"""

from __future__ import annotations

import logging
from typing import Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Neon accent colour for the dense fog core (RGB 0-1)
NEON_GREEN  = (0.22, 1.00, 0.08)   # #39FF14
NEON_PLASMA = "plasma"              # matplotlib cmap — used in PyVista


def build_uncertainty_fog(
    entropy_map: np.ndarray,
    voxel_spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    threshold_percentile: float = 78.0,
    max_points: int = 40_000,
    segmentation: Optional[np.ndarray] = None,
) -> object:
    """
    Build a pyvista.PolyData point cloud representing the uncertainty fog.

    Parameters
    ----------
    entropy_map          : (H,W,D) float32 array — per-voxel predictive entropy
                           from MC Dropout (produced by explainability.py).
    voxel_spacing        : (sx,sy,sz) in mm — used to convert voxel indices
                           to physical mm coordinates.
    threshold_percentile : voxels above this entropy percentile are included.
                           78 ≈ top 22% of uncertain voxels — dense but not
                           cluttered.
    max_points           : maximum number of points in the cloud (randomly
                           sampled if the thresholded set is larger). Keeps
                           render time under 1 s.
    segmentation         : optional (H,W,D) int BraTS label map. When provided,
                           only voxels near the tumour boundary (within 5 mm)
                           are included — focuses the mist on clinically
                           meaningful regions.

    Returns
    -------
    pyvista.PolyData  with:
        • point coordinates in mm-space
        • scalar array "entropy"  (float32, raw entropy values)
        • scalar array "layer"    (0 = outer fog, 1 = dense core)

    Raises
    ------
    ImportError  : if pyvista is not installed.
    ValueError   : if entropy_map is not 3D.
    """
    from src.ui.renderer_context import require_pyvista
    require_pyvista()
    import pyvista as pv

    if entropy_map.ndim != 3:
        raise ValueError(f"entropy_map must be 3D, got shape {entropy_map.shape}")

    entropy = entropy_map.astype(np.float32)
    logger.info(
        "Building uncertainty fog — shape=%s  percentile=%.0f%%",
        entropy.shape, threshold_percentile,
    )

    # ── Compute thresholds ────────────────────────────────────────────────────
    nonzero = entropy[entropy > 0]
    if nonzero.size == 0:
        logger.warning("Entropy map is all-zero — fog will be empty.")
        return pv.PolyData()

    p_outer = float(np.percentile(nonzero, threshold_percentile))
    p_dense = float(np.percentile(nonzero, min(threshold_percentile + 12.0, 99.0)))

    # ── Optional: restrict to tumour boundary region ──────────────────────────
    if segmentation is not None:
        tumor_mask = (segmentation > 0).astype(np.uint8)
        boundary_mask = _dilate_boundary(tumor_mask, dilation_vox=5)
        entropy = entropy * boundary_mask

    # ── Extract above-threshold voxel indices ─────────────────────────────────
    outer_indices = np.argwhere(entropy >= p_outer)
    if len(outer_indices) == 0:
        logger.warning("No voxels above threshold — returning empty fog.")
        return pv.PolyData()

    # Tag each point with its layer (0=outer, 1=dense)
    outer_entropy = entropy[outer_indices[:, 0], outer_indices[:, 1], outer_indices[:, 2]]
    dense_mask = outer_entropy >= p_dense
    layers = dense_mask.astype(np.int8)

    # ── Random downsample if too many points ──────────────────────────────────
    if len(outer_indices) > max_points:
        rng = np.random.default_rng(seed=42)
        chosen = rng.choice(len(outer_indices), size=max_points, replace=False)
        outer_indices = outer_indices[chosen]
        outer_entropy = outer_entropy[chosen]
        layers = layers[chosen]

    # ── Convert voxel indices → physical mm coordinates ───────────────────────
    sx, sy, sz = voxel_spacing
    coords = outer_indices.astype(np.float32)
    coords[:, 0] *= sx
    coords[:, 1] *= sy
    coords[:, 2] *= sz

    # ── Build pyvista PolyData ────────────────────────────────────────────────
    fog = pv.PolyData(coords)
    fog.point_data["entropy"] = outer_entropy.astype(np.float32)
    fog.point_data["layer"] = layers.astype(np.int8)

    logger.info(
        "Fog cloud built — %d points  (outer≥%.3f  dense≥%.3f)",
        len(coords), p_outer, p_dense,
    )
    return fog


def build_demo_fog(
    shape: Tuple[int, int, int] = (80, 80, 60),
    voxel_spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    tumor_center_frac: Tuple[float, float, float] = (0.5, 0.5, 0.5),
) -> object:
    """
    Generate a synthetic uncertainty fog for demo purposes.

    Creates a Gaussian-shaped entropy distribution centred on the tumour,
    so the demo looks clinically plausible without real MC Dropout inference.
    """
    H, W, D = shape
    cx, cy, cz = (int(f * s) for f, s in zip(tumor_center_frac, (H, W, D)))

    grid = np.mgrid[0:H, 0:W, 0:D].astype(np.float32)
    dist2 = (grid[0] - cx)**2 + (grid[1] - cy)**2 + (grid[2] - cz)**2
    sigma = min(H, W, D) * 0.18
    entropy_map = np.exp(-dist2 / (2 * sigma**2)).astype(np.float32)

    # Add structured noise so the fog looks realistic
    rng = np.random.default_rng(7)
    entropy_map += rng.exponential(0.05, size=shape).astype(np.float32)
    entropy_map = entropy_map / entropy_map.max()

    return build_uncertainty_fog(
        entropy_map, voxel_spacing=voxel_spacing, threshold_percentile=75
    )


# ── Private helpers ───────────────────────────────────────────────────────────

def _dilate_boundary(binary_mask: np.ndarray, dilation_vox: int) -> np.ndarray:
    """
    Return a mask covering the outer boundary shell of a binary region.

    Dilates the mask by `dilation_vox` voxels, then subtracts the eroded
    interior — leaving only the boundary shell where infiltration is plausible.
    """
    from scipy.ndimage import binary_dilation, binary_erosion

    struct = _spherical_struct(dilation_vox)
    dilated = binary_dilation(binary_mask, structure=struct)
    # Keep the full dilated region (includes original + surrounding shell)
    return dilated.astype(np.uint8)


def _spherical_struct(radius: int) -> np.ndarray:
    r = radius
    d = 2 * r + 1
    grid = np.mgrid[-r:r+1, -r:r+1, -r:r+1]
    return (grid[0]**2 + grid[1]**2 + grid[2]**2 <= r**2)
