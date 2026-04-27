"""
visualizer.py — Slice-based QC visualizer for the preprocessing pipeline.

Generates a multi-panel matplotlib figure showing Axial, Sagittal, and
Coronal centre slices for all four modalities, with the segmentation label
overlaid in colour. Used to visually verify each preprocessing step.

Output: a PNG file saved to the output directory (no display required —
works in headless server environments).

Colour map for BraTS labels:
    0  = background (transparent)
    1  = necrotic core (red)
    2  = peritumoral edema (yellow)
    3  = enhancing tumour (cyan)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Optional, Tuple

import matplotlib
matplotlib.use("Agg")   # Headless rendering — no display required
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from src.imaging.loader import MRISubject

logger = logging.getLogger(__name__)

# BraTS label colour map (RGBA)
LABEL_COLORS: Dict[int, Tuple[float, float, float, float]] = {
    1: (1.0, 0.2, 0.2, 0.6),   # NCR — red
    2: (1.0, 1.0, 0.0, 0.5),   # ED  — yellow
    3: (0.0, 0.9, 1.0, 0.6),   # ET  — cyan
}

MODALITY_CMAPS = {
    "t1":    "gray",
    "t1ce":  "hot",
    "t2":    "gray",
    "flair": "gray",
}


class SliceVisualizer:
    """
    Generate and save a multi-planar QC figure for an MRISubject.

    Parameters
    ----------
    figure_dpi : int
        DPI of the saved PNG. Default 150 (good for web viewing).
    show_seg_overlay : bool
        If True and subject has a segmentation label, overlay tumour classes.
    """

    def __init__(self, figure_dpi: int = 150, show_seg_overlay: bool = True) -> None:
        self.figure_dpi = figure_dpi
        self.show_seg_overlay = show_seg_overlay

    def save_qc_figure(
        self,
        subject: MRISubject,
        output_path: str | Path,
        title: Optional[str] = None,
    ) -> Path:
        """
        Render a 4 × 3 grid (4 modalities × 3 planes) and save as PNG.

        Parameters
        ----------
        subject     : MRISubject to visualize.
        output_path : File path for the output PNG.
        title       : Optional figure super-title.

        Returns
        -------
        Path to the saved PNG file.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        modalities = subject.modalities
        seg = subject.seg if self.show_seg_overlay else None
        shape = subject.shape
        cx, cy, cz = shape[0] // 2, shape[1] // 2, shape[2] // 2   # Centre slices

        n_rows = len(modalities)   # 4
        n_cols = 3                 # Axial, Sagittal, Coronal
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(n_cols * 4, n_rows * 3 + 1))

        if title is None:
            title = f"QC Preview — {subject.subject_id}"
        fig.suptitle(title, fontsize=14, fontweight="bold", y=0.98)

        for row, (name, volume) in enumerate(modalities.items()):
            slices = [
                ("Axial",    volume[:, :, cz],    seg[:, :, cz]    if seg is not None else None),
                ("Sagittal", volume[cx, :, :],    seg[cx, :, :]    if seg is not None else None),
                ("Coronal",  volume[:, cy, :],    seg[:, cy, :]    if seg is not None else None),
            ]

            for col, (plane_name, img_slice, seg_slice) in enumerate(slices):
                ax = axes[row, col] if n_rows > 1 else axes[col]
                cmap = MODALITY_CMAPS.get(name, "gray")

                # Rotate for anatomical orientation
                img_display = np.rot90(img_slice)
                vmin = float(np.percentile(img_display[img_display != 0], 1)) if (img_display != 0).any() else 0
                vmax = float(np.percentile(img_display[img_display != 0], 99)) if (img_display != 0).any() else 1

                ax.imshow(img_display, cmap=cmap, vmin=vmin, vmax=vmax, origin="lower")

                # Segmentation overlay
                if seg_slice is not None:
                    seg_display = np.rot90(seg_slice)
                    overlay = np.zeros((*seg_display.shape, 4), dtype=np.float32)
                    for label_id, color in LABEL_COLORS.items():
                        mask = seg_display == label_id
                        overlay[mask] = color
                    ax.imshow(overlay, origin="lower")

                if row == 0:
                    ax.set_title(plane_name, fontsize=10)
                ax.set_ylabel(name.upper(), fontsize=9, rotation=90, labelpad=4)
                ax.axis("off")

        # Legend
        legend_patches = [
            mpatches.Patch(color=LABEL_COLORS[1][:3], alpha=0.8, label="NCR (Necrotic Core)"),
            mpatches.Patch(color=LABEL_COLORS[2][:3], alpha=0.8, label="ED (Edema)"),
            mpatches.Patch(color=LABEL_COLORS[3][:3], alpha=0.8, label="ET (Enhancing)"),
        ]
        fig.legend(handles=legend_patches, loc="lower center", ncol=3, fontsize=8,
                   bbox_to_anchor=(0.5, 0.01))

        plt.tight_layout(rect=[0, 0.04, 1, 0.97])
        fig.savefig(str(output_path), dpi=self.figure_dpi, bbox_inches="tight")
        plt.close(fig)

        logger.info("QC figure saved: %s", output_path)
        return output_path

    def compare_before_after(
        self,
        before: MRISubject,
        after: MRISubject,
        modality: str,
        output_path: str | Path,
    ) -> Path:
        """
        Side-by-side comparison of a single modality before and after a pipeline step.

        Useful for visually verifying bias correction, skull stripping, etc.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        shape = before.shape
        cz = shape[2] // 2

        vol_before = before.modalities[modality][:, :, cz]
        vol_after = after.modalities[modality][:, :, cz]

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
        fig.suptitle(f"{modality.upper()} — Before vs After", fontsize=12, fontweight="bold")

        for ax, vol, label in [(ax1, vol_before, "Before"), (ax2, vol_after, "After")]:
            ax.imshow(np.rot90(vol), cmap="gray", origin="lower")
            ax.set_title(label, fontsize=10)
            ax.axis("off")

        plt.tight_layout()
        fig.savefig(str(output_path), dpi=self.figure_dpi, bbox_inches="tight")
        plt.close(fig)

        logger.info("Comparison figure saved: %s", output_path)
        return output_path
