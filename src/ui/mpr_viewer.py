"""
mpr_viewer.py — Multi-Planar Reconstruction (MPR) slice viewer.

Renders axial, sagittal, and coronal slices from a 3D MRI volume as a
matplotlib figure.  An optional segmentation overlay is drawn with the BraTS
colour convention using alpha compositing.

BraTS overlay colours
---------------------
    Class 0 (BG)  : transparent
    Class 1 (NCR) : red    (1, 0.2, 0.2)
    Class 2 (ED)  : yellow (0.9, 0.8, 0.1)
    Class 3 (ET)  : cyan   (0.1, 0.8, 0.9)

Usage
-----
    from src.ui.mpr_viewer import build_mpr_figure
    fig = build_mpr_figure(volume, segmentation, slice_fracs=(0.5, 0.5, 0.5))
"""

from __future__ import annotations

from typing import Optional, Tuple

import matplotlib
matplotlib.use("Agg")   # headless — must be set before pyplot import
import matplotlib.pyplot as plt
import matplotlib.figure
import numpy as np

# BraTS RGBA overlay colours (R, G, B, A)
_OVERLAY_COLOURS = {
    0: (0.0, 0.0, 0.0, 0.0),    # Background — transparent
    1: (1.0, 0.2, 0.2, 0.6),    # NCR — red
    2: (0.9, 0.8, 0.1, 0.5),    # ED  — yellow
    3: (0.1, 0.8, 0.9, 0.7),    # ET  — cyan
}

_PLANE_LABELS = ("Axial", "Sagittal", "Coronal")


def _get_slice(
    volume: np.ndarray,
    axis: int,
    idx: int,
) -> np.ndarray:
    """Extract a 2D slice along the given axis, returning (rows, cols)."""
    idx = int(np.clip(idx, 0, volume.shape[axis] - 1))
    slc = np.take(volume, idx, axis=axis)
    # Ensure (H, W) orientation for display
    if axis == 0:
        return slc           # (W, D) → displayed as-is
    if axis == 1:
        return slc.T         # (H, D) → transpose so H is vertical
    return slc               # (H, W) → fine


def _build_overlay(
    seg_slice: np.ndarray,
) -> np.ndarray:
    """Convert a 2D segmentation slice into an RGBA overlay image."""
    H, W = seg_slice.shape
    rgba = np.zeros((H, W, 4), dtype=np.float32)
    for cls_idx, colour in _OVERLAY_COLOURS.items():
        mask = seg_slice == cls_idx
        for ch, val in enumerate(colour):
            rgba[mask, ch] = val
    return rgba


def build_mpr_figure(
    volume: np.ndarray,
    segmentation: Optional[np.ndarray] = None,
    slice_fracs: Tuple[float, float, float] = (0.5, 0.5, 0.5),
    modality_name: str = "MRI",
    figsize: Tuple[float, float] = (14, 5),
    cmap: str = "gray",
) -> matplotlib.figure.Figure:
    """
    Render axial, sagittal, and coronal slices side-by-side.

    Parameters
    ----------
    volume       : (H, W, D) float array — one MRI modality, normalised or raw.
    segmentation : (H, W, D) int array   — BraTS labels (optional overlay).
    slice_fracs  : (axial_frac, sag_frac, cor_frac) ∈ [0,1] — relative slice
                   positions along each axis.
    modality_name: label displayed in figure title.
    figsize      : matplotlib figure size in inches.
    cmap         : matplotlib colourmap for the MRI background.

    Returns
    -------
    matplotlib.figure.Figure
    """
    if volume.ndim != 3:
        raise ValueError(f"volume must be 3D, got shape {volume.shape}")
    if segmentation is not None and segmentation.shape != volume.shape:
        raise ValueError(
            f"segmentation shape {segmentation.shape} must match volume {volume.shape}"
        )

    H, W, D = volume.shape
    axes_sizes = (H, W, D)
    fracs = slice_fracs

    # Normalise for display
    vmin, vmax = float(volume.min()), float(volume.max())
    vol_norm = (volume - vmin) / max(vmax - vmin, 1e-8)

    fig, axs = plt.subplots(1, 3, figsize=figsize, facecolor="#0f0f19")
    fig.suptitle(f"Multi-Planar Reconstruction — {modality_name}", color="white", fontsize=13)

    for ax_idx, (ax, frac, label) in enumerate(zip(axs, fracs, _PLANE_LABELS)):
        dim_size = axes_sizes[ax_idx]
        slice_idx = int(np.clip(frac * dim_size, 0, dim_size - 1))

        img_slice = _get_slice(vol_norm, ax_idx, slice_idx)

        ax.imshow(img_slice, cmap=cmap, interpolation="bilinear", aspect="auto")

        if segmentation is not None:
            seg_slice = _get_slice(segmentation, ax_idx, slice_idx)
            overlay = _build_overlay(seg_slice)
            ax.imshow(overlay, interpolation="nearest", aspect="auto")

        ax.set_title(f"{label}  (slice {slice_idx}/{dim_size - 1})",
                     color="white", fontsize=10)
        ax.axis("off")
        ax.set_facecolor("#0f0f19")

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    return fig


def build_single_slice(
    volume: np.ndarray,
    axis: int,
    slice_idx: int,
    segmentation: Optional[np.ndarray] = None,
    overlay_map: Optional[np.ndarray] = None,
    cmap: str = "gray",
    figsize: Tuple[float, float] = (5, 5),
) -> matplotlib.figure.Figure:
    """
    Render a single slice with optional segmentation and/or continuous overlay.

    Parameters
    ----------
    volume      : (H, W, D) float array.
    axis        : 0=axial, 1=sagittal, 2=coronal.
    slice_idx   : integer slice position.
    segmentation: optional (H, W, D) label array for BraTS colour overlay.
    overlay_map : optional (H, W, D) float array (e.g. entropy) for heatmap overlay.
    cmap        : colourmap for the MRI background.
    figsize     : figure size in inches.

    Returns
    -------
    matplotlib.figure.Figure
    """
    if volume.ndim != 3:
        raise ValueError(f"volume must be 3D, got shape {volume.shape}")

    H, W, D = volume.shape
    vmin, vmax = float(volume.min()), float(volume.max())
    vol_norm = (volume - vmin) / max(vmax - vmin, 1e-8)

    img = _get_slice(vol_norm, axis, slice_idx)

    fig, ax = plt.subplots(figsize=figsize, facecolor="#0f0f19")
    ax.imshow(img, cmap=cmap, interpolation="bilinear", aspect="auto")

    if segmentation is not None:
        seg_sl = _get_slice(segmentation, axis, slice_idx)
        ax.imshow(_build_overlay(seg_sl), interpolation="nearest", aspect="auto")

    if overlay_map is not None:
        ov_sl = _get_slice(overlay_map, axis, slice_idx)
        ov_norm = (ov_sl - ov_sl.min()) / max(ov_sl.max() - ov_sl.min(), 1e-8)
        ax.imshow(ov_norm, cmap="hot", alpha=0.5, interpolation="bilinear", aspect="auto")

    ax.axis("off")
    ax.set_facecolor("#0f0f19")
    plt.tight_layout()
    return fig
