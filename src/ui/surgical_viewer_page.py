"""
surgical_viewer_page.py — Surgical 3D Viewer Streamlit page.

This module is imported by app.py and renders as the "Surgical 3D Viewer"
navigation entry. It provides:

  Phase 1 — Biological Realism
    • Cortical pial surface rendered with sulcal depth shading
    • Tumour sub-regions (NCR / ED / ET) in BraTS colours

  Phase 2 — Virtual Craniotomy
    • "Zoom Depth" slider: expands a spherical clipping region centred on
      the tumour centroid, progressively removing the cortex to reveal the
      tumour in its anatomical context
    • Render mode toggle: Standard Brain / Craniotomy View / X-Ray Mode
    • Camera preset buttons: Default / Axial / Sagittal / Coronal
    • Per-region opacity sliders

Usage (from app.py)
-------------------
    from src.ui.surgical_viewer_page import render_surgical_viewer_page
    render_surgical_viewer_page(data)   # data dict from sidebar()
"""

from __future__ import annotations

import hashlib
import io
import logging
from typing import Optional, Tuple

import numpy as np
import streamlit as st

from src.ui.theme import (
    alert_box,
    metric_row,
    page_header,
    section_divider,
    trajectory_card,
)

logger = logging.getLogger(__name__)

# ── PyVista availability guard ────────────────────────────────────────────────
try:
    from src.ui.renderer_context import PYVISTA_AVAILABLE
except ImportError:
    PYVISTA_AVAILABLE = False


def render_surgical_viewer_page(data: dict) -> None:
    """
    Main entry point called by app.py for the Surgical 3D Viewer page.

    Parameters
    ----------
    data : dict  — produced by sidebar() in app.py. Keys:
        "seg"           : np.ndarray (H,W,D) int32 or None
        "vol"           : np.ndarray (H,W,D) float32 or None
        "voxel_spacing" : (sx,sy,sz) tuple of floats
        "subject_id"    : str
        "nifti_subject" : MRISubject or None (populated when NIfTI uploaded)
        "brain_mask"    : np.ndarray (H,W,D) uint8 or None
    """
    page_header(
        "Surgical 3D Viewer",
        "Cortical pial surface · tumour anatomy · PyVista cinematic rendering",
        "🔬",
    )

    if not PYVISTA_AVAILABLE:
        alert_box(
            "PyVista is not installed. Install with: "
            "pip install pyvista>=0.44.0 vtk>=9.3.0",
            "error",
        )
        return

    seg = data.get("seg")
    subject = data.get("nifti_subject")   # MRISubject or None
    brain_mask = data.get("brain_mask")
    voxel_spacing = data.get("voxel_spacing", (1.0, 1.0, 1.0))
    subject_id = data.get("subject_id", "subject")

    if seg is None and subject is None:
        alert_box(
            "Upload a segmentation (.npy) in the sidebar for tumour-only view, "
            "or a BraTS NIfTI folder for full cortex + tumour rendering.",
            "info",
        )
        _render_demo(voxel_spacing)
        return

    # ── Control panel ─────────────────────────────────────────────────────────
    with st.expander("⚙️ Render Controls", expanded=True):
        col_mode, col_cam = st.columns(2)

        render_mode = col_mode.selectbox(
            "Render Mode",
            ["Standard Brain", "Craniotomy View", "X-Ray Mode"],
            index=0,
            key="sv_render_mode",
        )
        camera_preset = col_cam.selectbox(
            "Camera",
            ["Default", "Axial", "Sagittal", "Coronal"],
            index=0,
            key="sv_camera",
        )

        # Craniotomy depth slider (only visible in craniotomy mode)
        clip_radius = 0.0
        if render_mode == "Craniotomy View":
            clip_radius = st.slider(
                "Craniotomy Depth (mm) — 0 = closed, higher = more revealed",
                min_value=0.0,
                max_value=80.0,
                value=30.0,
                step=2.0,
                key="sv_clip_radius",
                help="Expands a spherical window centred on the tumour centroid.",
            )

        # Per-region opacity
        col_o1, col_o2, col_o3, col_o4 = st.columns(4)
        cortex_opacity = col_o1.slider("Cortex α", 0.05, 0.60, 0.22, 0.01, key="sv_cortex_alpha")
        ncr_opacity    = col_o2.slider("NCR α",    0.10, 1.00, 0.90, 0.05, key="sv_ncr_alpha")
        ed_opacity     = col_o3.slider("ED α",     0.10, 1.00, 0.55, 0.05, key="sv_ed_alpha")
        et_opacity     = col_o4.slider("ET α",     0.10, 1.00, 0.95, 0.05, key="sv_et_alpha")

        section_divider("overlays")

        # ── Phase 3 overlays ─────────────────────────────────────────────
        col_f, col_l = st.columns(2)
        show_fog       = col_f.checkbox(
            "🌫️ Show Uncertainty Fog",
            value=False,
            key="sv_show_fog",
            help="Neon mist overlay showing regions of high predictive uncertainty "
                 "(MC Dropout entropy). Bright = model is less confident = possible "
                 "tumour infiltration beyond visible margin.",
        )
        show_landmarks = col_l.checkbox(
            "📍 Show Anatomical Landmarks",
            value=False,
            key="sv_show_landmarks",
            help="Coloured spheres at key structures: brainstem (orange), "
                 "lateral ventricles (blue), thalami (gold), corpus callosum (purple).",
        )

    # ── Build render params ───────────────────────────────────────────────────
    mode_map = {
        "Standard Brain":   "standard",
        "Craniotomy View":  "craniotomy",
        "X-Ray Mode":       "xray",
    }
    cam_map = {
        "Default": "default", "Axial": "axial",
        "Sagittal": "sagittal", "Coronal": "coronal",
    }

    from src.ui.pyvista_renderer import RenderParams, NeuroRenderer
    params = RenderParams(
        mode=mode_map[render_mode],
        clip_radius=clip_radius,
        cortex_opacity=cortex_opacity,
        camera_preset=cam_map[camera_preset],
        show_uncertainty_fog=show_fog,
        show_landmarks=show_landmarks,
    )

    # Override per-class opacity
    import src.ui.pyvista_renderer as _pyr
    _pyr._TUMOR_CONFIG[1]["opacity"] = ncr_opacity
    _pyr._TUMOR_CONFIG[2]["opacity"] = ed_opacity
    _pyr._TUMOR_CONFIG[3]["opacity"] = et_opacity

    # ── Cache key (avoid re-rendering unchanged params) ───────────────────────
    cache_key = _make_cache_key(subject_id, seg, params, clip_radius)
    if cache_key in st.session_state.get("pyvista_render_cache", {}):
        png_bytes = st.session_state["pyvista_render_cache"][cache_key]
        _display_render(png_bytes, subject_id, render_mode)
        _show_volume_summary(seg, voxel_spacing)
        return

    # ── Extract cortical surface (if NIfTI subject available) ────────────────
    cortex_mesh = None
    if subject is not None:
        with st.spinner("Extracting cortical pial surface…"):
            cortex_mesh = _get_cortex_mesh(subject, brain_mask, voxel_spacing)

    # ── Compute tumour centroid ───────────────────────────────────────────────
    tumor_centroid = None
    if seg is not None:
        from src.analytics.volumetrics import compute_tumor_centroid
        tumor_centroid = compute_tumor_centroid(seg, voxel_spacing)

    # ── Build uncertainty fog (Phase 3) ──────────────────────────────────────
    uncertainty_fog = None
    if show_fog:
        with st.spinner("Building uncertainty fog…"):
            uncertainty_fog = _build_fog(data, seg, voxel_spacing)

    # ── Detect anatomical landmarks (Phase 3) ─────────────────────────────────
    landmarks = None
    if show_landmarks and subject is not None:
        with st.spinner("Detecting anatomical landmarks (MNI atlas)…"):
            landmarks = _detect_landmarks(subject, brain_mask, voxel_spacing)
    elif show_landmarks and subject is None:
        alert_box(
            "Upload a BraTS NIfTI folder for patient-specific landmark detection. "
            "Showing estimated positions based on brain geometry.",
            "warning",
        )
        landmarks = _fallback_landmarks(seg, voxel_spacing)

    # ── Render ────────────────────────────────────────────────────────────────
    renderer = NeuroRenderer(width=1200, height=900)

    with st.spinner("Rendering surgical scene… (first render may take a moment)"):
        try:
            if render_mode == "Craniotomy View" and tumor_centroid is not None:
                png_bytes = renderer.render_craniotomy(
                    cortex_mesh=cortex_mesh,
                    segmentation=seg,
                    voxel_spacing=voxel_spacing,
                    tumor_centroid=tumor_centroid,
                    clip_radius=clip_radius,
                    params=params,
                )
            else:
                png_bytes = renderer.render_combined(
                    cortex_mesh=cortex_mesh,
                    segmentation=seg,
                    voxel_spacing=voxel_spacing,
                    params=params,
                    tumor_centroid=tumor_centroid,
                    uncertainty_fog=uncertainty_fog,
                    landmarks=landmarks,
                )
        except Exception as exc:
            alert_box(f"Render failed: {exc}", "error")
            logger.exception("PyVista render error")
            return

    # Cache result
    if "pyvista_render_cache" not in st.session_state:
        st.session_state["pyvista_render_cache"] = {}
    st.session_state["pyvista_render_cache"][cache_key] = png_bytes

    _display_render(png_bytes, subject_id, render_mode)
    _show_volume_summary(seg, voxel_spacing)

    # ── Landmark proximity table ──────────────────────────────────────────────
    if show_landmarks and landmarks and tumor_centroid is not None:
        _show_landmark_proximity(landmarks, tumor_centroid)


# ── Helper functions ──────────────────────────────────────────────────────────

def _display_render(png_bytes: bytes, subject_id: str, mode: str) -> None:
    """Display the rendered PNG and download button."""
    st.image(png_bytes, caption=f"{subject_id} — {mode}", use_container_width=True)

    col_dl, _ = st.columns([1, 3])
    col_dl.download_button(
        label="⬇️ Download render",
        data=png_bytes,
        file_name=f"anatomai_{subject_id}_{mode.lower().replace(' ','_')}.png",
        mime="image/png",
    )


def _show_volume_summary(seg: Optional[np.ndarray], voxel_spacing: tuple) -> None:
    """Show a compact volumetric summary beneath the render."""
    if seg is None:
        return

    from src.analytics.volumetrics import VolumetricAnalyzer
    analyzer = VolumetricAnalyzer()
    result = analyzer.compute(seg, voxel_spacing, subject_id="")

    section_divider("Volumetric Summary")
    metric_row([
        {"label": "NCR — Necrotic Core", "value": f"{result.volumes_mm3.get('NCR', 0):,.0f}", "unit": "mm³", "accent": "red"},
        {"label": "ED — Edema",          "value": f"{result.volumes_mm3.get('ED',  0):,.0f}", "unit": "mm³", "accent": "amber"},
        {"label": "ET — Enhancing",      "value": f"{result.volumes_mm3.get('ET',  0):,.0f}", "unit": "mm³", "accent": "cyan"},
    ])
    metric_row([
        {"label": "Whole Tumour (WT)", "value": f"{result.wt_mm3:,.0f}", "unit": "mm³", "accent": "purple"},
        {"label": "Tumour Core (TC)",  "value": f"{result.tc_mm3:,.0f}", "unit": "mm³", "accent": "purple"},
        {"label": "Enhancing (ET)",    "value": f"{result.et_mm3:,.0f}", "unit": "mm³", "accent": "cyan"},
    ])


@st.cache_resource(show_spinner=False)
def _get_cortex_mesh(subject, brain_mask, voxel_spacing):
    """Cache the cortex extraction — expensive, runs only once per subject."""
    from src.imaging.cortex_extractor import CortexExtractor
    extractor = CortexExtractor(smooth_sigma_mm=1.5, target_faces=80_000)
    try:
        return extractor.extract(subject, brain_mask, voxel_spacing)
    except Exception as exc:
        logger.warning("Cortex extraction failed: %s — rendering tumour only.", exc)
        return None


def _build_fog(data: dict, seg: Optional[np.ndarray], voxel_spacing: tuple):
    """
    Build the uncertainty fog cloud from an uploaded entropy map or a demo.

    Checks st.session_state for an entropy map uploaded via the sidebar
    uncertainty uploader. Falls back to a synthetic demo fog.
    """
    from src.ui.uncertainty_3d import build_uncertainty_fog, build_demo_fog

    entropy = data.get("entropy")
    if entropy is not None and seg is not None:
        try:
            return build_uncertainty_fog(
                entropy, voxel_spacing=voxel_spacing, segmentation=seg
            )
        except Exception as exc:
            logger.warning("Fog build failed with real entropy: %s — using demo.", exc)

    # Demo fog centred on tumour
    if seg is not None:
        H, W, D = seg.shape
        fracs = (0.5, 0.5, 0.5)
        tumor_vox = np.argwhere(seg > 0)
        if len(tumor_vox):
            mean_vox = tumor_vox.mean(axis=0)
            fracs = tuple(float(mean_vox[i] / seg.shape[i]) for i in range(3))
        return build_demo_fog(shape=(H, W, D), voxel_spacing=voxel_spacing,
                               tumor_center_frac=fracs)

    return build_demo_fog(voxel_spacing=voxel_spacing)


@st.cache_resource(show_spinner=False)
def _detect_landmarks(subject, brain_mask, voxel_spacing):
    """Cache landmark detection — ANTsPy registration runs only once per subject."""
    from src.imaging.landmark_detector import AnatomicalLandmarkDetector
    detector = AnatomicalLandmarkDetector(use_ants=True, visible_only=True)
    try:
        return detector.detect(subject, brain_mask, voxel_spacing)
    except Exception as exc:
        logger.warning("Landmark detection failed: %s", exc)
        return {}


def _fallback_landmarks(
    seg: Optional[np.ndarray],
    voxel_spacing: tuple,
) -> dict:
    """Geometric landmark fallback when no NIfTI subject is available."""
    if seg is None:
        return {}
    from src.imaging.landmark_detector import AnatomicalLandmarkDetector
    from src.imaging.loader import MRISubject
    import numpy as _np
    # Construct a minimal subject with a zero T1 — only the mask matters
    dummy_t1 = _np.zeros(seg.shape, dtype=_np.float32)
    dummy_subject = MRISubject(
        subject_id="fallback", t1=dummy_t1, t1ce=dummy_t1,
        t2=dummy_t1, flair=dummy_t1, seg=seg,
    )
    detector = AnatomicalLandmarkDetector(use_ants=False, visible_only=True)
    return detector.detect(dummy_subject, voxel_spacing=voxel_spacing)


def _show_landmark_proximity(
    landmarks: dict,
    tumor_centroid: Tuple[float, float, float],
) -> None:
    """Show a table of each landmark's distance from the tumour centroid."""
    section_divider("Landmark Proximity to Tumour Centroid")

    centroid = np.asarray(tumor_centroid, dtype=float)
    rows = []
    for name, coords in landmarks.items():
        dist_mm = float(np.linalg.norm(np.asarray(coords) - centroid))
        risk = "🔴 Critical" if dist_mm < 10 else ("🟡 Caution" if dist_mm < 20 else "🟢 Clear")
        rows.append({
            "Structure": name.replace("_", " ").title(),
            "Distance (mm)": f"{dist_mm:.1f}",
            "Proximity Alert": risk,
        })

    if rows:
        import pandas as pd
        st.dataframe(
            pd.DataFrame(rows).sort_values("Distance (mm)"),
            use_container_width=True,
            hide_index=True,
        )


def _render_demo(voxel_spacing: tuple) -> None:
    """Render a synthetic demo scene when no data is uploaded."""
    alert_box("Showing synthetic demo — upload real data for clinical rendering.", "info")

    seg_demo = np.zeros((60, 60, 50), dtype=np.int32)
    seg_demo[15:45, 18:42, 12:38] = 2   # ED shell
    seg_demo[22:38, 24:36, 18:32] = 1   # NCR core
    seg_demo[28:32, 28:32, 23:27] = 3   # ET centre

    from src.ui.pyvista_renderer import NeuroRenderer, RenderParams
    renderer = NeuroRenderer(width=900, height=600)
    params = RenderParams(mode="standard", cortex_opacity=0.0)

    with st.spinner("Rendering demo scene…"):
        try:
            png = renderer.render_combined(
                cortex_mesh=None,
                segmentation=seg_demo,
                voxel_spacing=voxel_spacing,
                params=params,
            )
            st.image(png, caption="Demo — Synthetic Tumour (NCR=red, ED=yellow, ET=cyan)")
        except Exception as exc:
            alert_box(f"Demo render unavailable: {exc}", "warning")


def _make_cache_key(
    subject_id: str,
    seg: Optional[np.ndarray],
    params: "RenderParams",
    clip_radius: float,
) -> str:
    """Build a hashable cache key from render parameters."""
    seg_hash = ""
    if seg is not None:
        seg_hash = hashlib.md5(seg.tobytes(), usedforsecurity=False).hexdigest()[:8]
    return f"{subject_id}_{seg_hash}_{params.mode}_{params.camera_preset}_{clip_radius:.1f}_{params.cortex_opacity:.2f}"
