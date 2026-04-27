"""
viewer3d.py — 3D tumour surface mesh rendering.

Extracts isosurfaces from binary tumour sub-region masks using marching cubes
(scikit-image) and renders them as interactive Plotly Mesh3d traces.

BraTS colour convention
-----------------------
    NCR (class 1) : rgb(220, 60,  60)   — red
    ED  (class 2) : rgb(240, 200, 30)   — yellow
    ET  (class 3) : rgb(60,  200, 220)  — cyan

Usage
-----
    from src.ui.viewer3d import build_tumor_mesh
    fig = build_tumor_mesh(segmentation, voxel_spacing=(1.0, 1.0, 1.0))
    fig.show()
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import plotly.graph_objects as go

# Per-class rendering parameters
_CLASS_CONFIG: Dict[int, Dict] = {
    1: {"name": "NCR", "color": "rgb(220,60,60)",   "opacity": 0.75},
    2: {"name": "ED",  "color": "rgb(240,200,30)",  "opacity": 0.50},
    3: {"name": "ET",  "color": "rgb(60,200,220)",  "opacity": 0.85},
}


def _extract_surface(
    mask: np.ndarray,
    voxel_spacing: Tuple[float, float, float],
) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    """
    Run marching cubes on a binary mask and return (vertices, faces).

    Returns None if the mask is empty or too small to form a surface.
    """
    from skimage.measure import marching_cubes

    if mask.sum() < 8:   # Not enough voxels to triangulate
        return None

    # Pad by 1 voxel so marching cubes can close surfaces at the boundary
    padded = np.pad(mask.astype(np.float32), pad_width=1, mode="constant")
    try:
        verts, faces, _, _ = marching_cubes(padded, level=0.5, spacing=voxel_spacing)
    except (ValueError, RuntimeError):
        return None

    # Offset vertices to account for the 1-voxel padding
    verts -= np.array(voxel_spacing)
    return verts, faces


def build_tumor_mesh(
    segmentation: np.ndarray,
    voxel_spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    classes: Optional[List[int]] = None,
    title: str = "3D Tumour Segmentation",
) -> go.Figure:
    """
    Build an interactive 3D Plotly figure with one surface mesh per tumour class.

    Parameters
    ----------
    segmentation  : (H, W, D) integer array — BraTS label map (0–3).
    voxel_spacing : (sx, sy, sz) in mm — physical voxel dimensions.
    classes       : list of class indices to render; default [1, 2, 3].
    title         : figure title.

    Returns
    -------
    plotly.graph_objects.Figure  with one Mesh3d trace per requested class.
    An empty figure is returned if no surface could be extracted.
    """
    if segmentation.ndim != 3:
        raise ValueError(f"segmentation must be 3D, got shape {segmentation.shape}")

    if classes is None:
        classes = [1, 2, 3]

    traces: List[go.Mesh3d] = []

    for cls_idx in classes:
        cfg = _CLASS_CONFIG.get(cls_idx)
        if cfg is None:
            continue

        mask = segmentation == cls_idx
        result = _extract_surface(mask, voxel_spacing)
        if result is None:
            continue

        verts, faces = result
        trace = go.Mesh3d(
            x=verts[:, 0].tolist(),
            y=verts[:, 1].tolist(),
            z=verts[:, 2].tolist(),
            i=faces[:, 0].tolist(),
            j=faces[:, 1].tolist(),
            k=faces[:, 2].tolist(),
            name=cfg["name"],
            color=cfg["color"],
            opacity=cfg["opacity"],
            showscale=False,
            flatshading=False,
            lighting={"ambient": 0.6, "diffuse": 0.8, "specular": 0.3, "roughness": 0.5},
            lightposition={"x": 100, "y": 200, "z": 0},
        )
        traces.append(trace)

    fig = go.Figure(data=traces)
    H, W, D = [s * sp for s, sp in zip(segmentation.shape, voxel_spacing)]

    fig.update_layout(
        title=dict(text=title, x=0.5, font=dict(size=16)),
        scene=dict(
            xaxis=dict(title="x (mm)", range=[0, H]),
            yaxis=dict(title="y (mm)", range=[0, W]),
            zaxis=dict(title="z (mm)", range=[0, D]),
            aspectmode="data",
            bgcolor="rgb(15,15,25)",
        ),
        paper_bgcolor="rgb(15,15,25)",
        font=dict(color="white"),
        legend=dict(
            bgcolor="rgba(30,30,40,0.8)",
            bordercolor="gray",
            borderwidth=1,
        ),
        margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig


def export_to_pyvista(
    segmentation: np.ndarray,
    voxel_spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    classes: Optional[List[int]] = None,
):
    """
    Export tumour sub-region surfaces as a dict of pyvista.PolyData meshes.

    Shares the same marching-cubes logic as build_tumor_mesh() so both the
    legacy Plotly path and the new PyVista renderer produce identical geometry.

    Parameters
    ----------
    segmentation  : (H, W, D) int array — BraTS label map.
    voxel_spacing : (sx, sy, sz) in mm.
    classes       : class indices to export; default [1, 2, 3].

    Returns
    -------
    Dict[int, pyvista.PolyData]  — one mesh per requested class.
    Requires pyvista to be installed; raises ImportError otherwise.
    """
    from src.ui.renderer_context import get_pyvista
    pv = get_pyvista()

    if classes is None:
        classes = [1, 2, 3]

    meshes = {}
    for cls_idx in classes:
        mask = segmentation == cls_idx
        result = _extract_surface(mask, voxel_spacing)
        if result is None:
            continue
        verts, faces = result
        n_faces = len(faces)
        pv_faces = np.hstack(
            [np.full((n_faces, 1), 3, dtype=np.int32), faces.astype(np.int32)]
        ).ravel()
        meshes[cls_idx] = pv.PolyData(verts.astype(np.float32), pv_faces)

    return meshes


def build_brain_slice_traces(
    volume: np.ndarray,
    voxel_spacing: Tuple[float, float, float] = (1.0, 1.0, 1.0),
    slice_fractions: Tuple[float, float, float] = (0.5, 0.5, 0.5),
) -> go.Figure:
    """
    Add three orthogonal MRI slice planes to a figure for anatomical context.

    Parameters
    ----------
    volume          : (H, W, D) float array — one MRI modality.
    voxel_spacing   : (sx, sy, sz) in mm.
    slice_fractions : (axial_frac, sagittal_frac, coronal_frac) in [0, 1].

    Returns
    -------
    plotly.graph_objects.Figure with three Surface traces (axial, sagittal, coronal).
    """
    if volume.ndim != 3:
        raise ValueError(f"volume must be 3D, got shape {volume.shape}")

    H, W, D = volume.shape
    sx, sy, sz = voxel_spacing

    # Normalise volume to [0, 1] for display
    vmin, vmax = volume.min(), volume.max()
    vol_norm = (volume - vmin) / max(vmax - vmin, 1e-8)

    traces = []

    # Axial (z-plane)
    zi = int(np.clip(slice_fractions[0] * D, 0, D - 1))
    z_val = zi * sz
    xs = np.arange(H) * sx
    ys = np.arange(W) * sy
    traces.append(go.Surface(
        x=xs, y=ys, z=np.full((H, W), z_val),
        surfacecolor=vol_norm[:, :, zi],
        colorscale="gray", showscale=False, opacity=0.8, name="Axial",
    ))

    # Sagittal (x-plane)
    xi = int(np.clip(slice_fractions[1] * H, 0, H - 1))
    x_val = xi * sx
    ys_s = np.arange(W) * sy
    zs_s = np.arange(D) * sz
    traces.append(go.Surface(
        x=np.full((W, D), x_val), y=ys_s[:, None], z=zs_s[None, :],
        surfacecolor=vol_norm[xi, :, :],
        colorscale="gray", showscale=False, opacity=0.8, name="Sagittal",
    ))

    # Coronal (y-plane)
    yi = int(np.clip(slice_fractions[2] * W, 0, W - 1))
    y_val = yi * sy
    xs_c = np.arange(H) * sx
    zs_c = np.arange(D) * sz
    traces.append(go.Surface(
        x=xs_c[:, None], y=np.full((H, D), y_val), z=zs_c[None, :],
        surfacecolor=vol_norm[:, yi, :],
        colorscale="gray", showscale=False, opacity=0.8, name="Coronal",
    ))

    fig = go.Figure(data=traces)
    fig.update_layout(
        scene=dict(aspectmode="data", bgcolor="rgb(15,15,25)"),
        paper_bgcolor="rgb(15,15,25)",
        font=dict(color="white"),
        margin=dict(l=0, r=0, t=0, b=0),
    )
    return fig
