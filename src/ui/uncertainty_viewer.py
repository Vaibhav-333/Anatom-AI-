"""
uncertainty_viewer.py — Uncertainty and Grad-CAM overlay visualisation.

Renders per-voxel entropy or Grad-CAM saliency maps on top of MRI slices
using a "hot" heatmap with alpha compositing.

Usage
-----
    from src.ui.uncertainty_viewer import build_uncertainty_panel
    fig = build_uncertainty_panel(volume, entropy_map, segmentation)
    fig.savefig("uncertainty.png", dpi=150)
"""

from __future__ import annotations

from typing import Optional, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.figure
import matplotlib.colors as mcolors
import numpy as np

from .mpr_viewer import _build_overlay, _get_slice


def build_uncertainty_panel(
    volume: np.ndarray,
    uncertainty_map: np.ndarray,
    segmentation: Optional[np.ndarray] = None,
    axis: int = 0,
    slice_frac: float = 0.5,
    cmap: str = "hot",
    figsize: Tuple[float, float] = (14, 5),
    title: str = "Predictive Uncertainty (MC Dropout)",
) -> matplotlib.figure.Figure:
    """
    Render three panels: MRI only | uncertainty overlay | side-by-side diff.

    Parameters
    ----------
    volume          : (H, W, D) float — MRI modality.
    uncertainty_map : (H, W, D) float — per-voxel entropy or variance.
    segmentation    : (H, W, D) int   — BraTS labels (optional overlay).
    axis            : 0=axial, 1=sagittal, 2=coronal.
    slice_frac      : ∈ [0, 1] — relative slice position.
    cmap            : matplotlib colourmap for the uncertainty overlay.
    figsize         : figure size.
    title           : figure title.

    Returns
    -------
    matplotlib.figure.Figure with three subplots.
    """
    if volume.ndim != 3:
        raise ValueError(f"volume must be 3D, got shape {volume.shape}")
    if uncertainty_map.shape != volume.shape:
        raise ValueError(
            f"uncertainty_map {uncertainty_map.shape} must match volume {volume.shape}"
        )

    dim_size = volume.shape[axis]
    slice_idx = int(np.clip(slice_frac * dim_size, 0, dim_size - 1))

    # Normalise MRI
    vmin, vmax = float(volume.min()), float(volume.max())
    vol_norm = (volume - vmin) / max(vmax - vmin, 1e-8)
    mri_slice = _get_slice(vol_norm, axis, slice_idx)

    # Normalise uncertainty to [0, 1]
    u_slice = _get_slice(uncertainty_map, axis, slice_idx)
    u_norm = (u_slice - u_slice.min()) / max(u_slice.max() - u_slice.min(), 1e-8)

    fig, axs = plt.subplots(1, 3, figsize=figsize, facecolor="#0f0f19")
    fig.suptitle(title, color="white", fontsize=13)

    plane_names = ("Axial", "Sagittal", "Coronal")
    plane_name = plane_names[axis]

    # Panel 1: MRI + segmentation
    axs[0].imshow(mri_slice, cmap="gray", aspect="auto")
    if segmentation is not None:
        seg_sl = _get_slice(segmentation, axis, slice_idx)
        axs[0].imshow(_build_overlay(seg_sl), aspect="auto")
    axs[0].set_title(f"{plane_name} — Segmentation", color="white", fontsize=10)
    axs[0].axis("off")

    # Panel 2: MRI + uncertainty heatmap
    axs[1].imshow(mri_slice, cmap="gray", aspect="auto")
    im = axs[1].imshow(u_norm, cmap=cmap, alpha=0.6, aspect="auto", vmin=0, vmax=1)
    axs[1].set_title(f"{plane_name} — Uncertainty", color="white", fontsize=10)
    axs[1].axis("off")
    cbar = fig.colorbar(im, ax=axs[1], fraction=0.04, pad=0.02)
    cbar.set_label("Normalised entropy", color="white", fontsize=8)
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")

    # Panel 3: High-uncertainty regions (top 20%) highlighted
    threshold = np.percentile(u_norm, 80)
    high_u = (u_norm >= threshold).astype(float)
    axs[2].imshow(mri_slice, cmap="gray", aspect="auto")
    masked = np.ma.masked_where(high_u == 0, high_u)
    axs[2].imshow(masked, cmap="Reds", alpha=0.7, aspect="auto", vmin=0, vmax=1)
    axs[2].set_title(f"{plane_name} — High-uncertainty voxels (top 20%)",
                     color="white", fontsize=10)
    axs[2].axis("off")

    for ax in axs:
        ax.set_facecolor("#0f0f19")

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    return fig


def build_gradcam_panel(
    volume: np.ndarray,
    saliency: np.ndarray,
    segmentation: Optional[np.ndarray] = None,
    axis: int = 0,
    slice_frac: float = 0.5,
    target_class_name: str = "ET (class 3)",
    figsize: Tuple[float, float] = (10, 5),
) -> matplotlib.figure.Figure:
    """
    Render a two-panel Grad-CAM figure: MRI | saliency overlay.

    Parameters
    ----------
    volume          : (H, W, D) float — MRI modality.
    saliency        : (H, W, D) float ∈ [0, 1] — Grad-CAM saliency map.
    segmentation    : (H, W, D) int — BraTS labels (optional).
    axis            : 0=axial, 1=sagittal, 2=coronal.
    slice_frac      : ∈ [0, 1].
    target_class_name: label for the figure title.
    figsize         : figure size.

    Returns
    -------
    matplotlib.figure.Figure with two subplots.
    """
    if volume.ndim != 3:
        raise ValueError(f"volume must be 3D, got shape {volume.shape}")
    if saliency.shape != volume.shape:
        raise ValueError(f"saliency {saliency.shape} must match volume {volume.shape}")

    dim_size = volume.shape[axis]
    slice_idx = int(np.clip(slice_frac * dim_size, 0, dim_size - 1))

    vmin, vmax = float(volume.min()), float(volume.max())
    vol_norm = (volume - vmin) / max(vmax - vmin, 1e-8)
    mri_slice = _get_slice(vol_norm, axis, slice_idx)
    sal_slice = _get_slice(saliency, axis, slice_idx)

    fig, axs = plt.subplots(1, 2, figsize=figsize, facecolor="#0f0f19")
    fig.suptitle(f"Grad-CAM — {target_class_name}", color="white", fontsize=13)

    plane_names = ("Axial", "Sagittal", "Coronal")
    plane = plane_names[axis]

    # Panel 1: MRI + optional segmentation
    axs[0].imshow(mri_slice, cmap="gray", aspect="auto")
    if segmentation is not None:
        seg_sl = _get_slice(segmentation, axis, slice_idx)
        axs[0].imshow(_build_overlay(seg_sl), aspect="auto")
    axs[0].set_title(f"{plane} — Ground Truth / Prediction", color="white", fontsize=10)
    axs[0].axis("off")

    # Panel 2: Grad-CAM overlay
    axs[1].imshow(mri_slice, cmap="gray", aspect="auto")
    im = axs[1].imshow(sal_slice, cmap="jet", alpha=0.55, aspect="auto", vmin=0, vmax=1)
    axs[1].set_title(f"{plane} — Grad-CAM Saliency", color="white", fontsize=10)
    axs[1].axis("off")
    cbar = fig.colorbar(im, ax=axs[1], fraction=0.04, pad=0.02)
    cbar.set_label("Saliency", color="white", fontsize=8)
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")

    for ax in axs:
        ax.set_facecolor("#0f0f19")

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    return fig


def uncertainty_stats(uncertainty_map: np.ndarray, segmentation: Optional[np.ndarray] = None) -> dict:
    """
    Compute summary statistics of an uncertainty map.

    Parameters
    ----------
    uncertainty_map : (H, W, D) float — entropy or variance map.
    segmentation    : optional (H, W, D) int — if provided, compute per-region stats.

    Returns
    -------
    dict with global stats and optional per-region stats.
    """
    stats = {
        "mean": float(uncertainty_map.mean()),
        "max": float(uncertainty_map.max()),
        "p90": float(np.percentile(uncertainty_map, 90)),
        "p95": float(np.percentile(uncertainty_map, 95)),
    }
    if segmentation is not None:
        for cls_idx, name in {1: "NCR", 2: "ED", 3: "ET"}.items():
            mask = segmentation == cls_idx
            if mask.sum() > 0:
                stats[f"{name}_mean"] = float(uncertainty_map[mask].mean())
                stats[f"{name}_max"] = float(uncertainty_map[mask].max())
            else:
                stats[f"{name}_mean"] = 0.0
                stats[f"{name}_max"] = 0.0
    return stats
