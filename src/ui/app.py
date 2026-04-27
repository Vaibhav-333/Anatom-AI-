"""
app.py — Anatom AI Surgical Planning Platform Dashboard.

Launch:
    streamlit run src/ui/app.py
    python scripts/launch_app.py

UI design: medical workstation aesthetic (Brainlab / 3D Slicer inspired).
Full CSS overhaul via src/ui/theme.py — dark holographic panels, Rajdhani
typography, neon cyan/green accents, animated grid background.

Navigation
----------
  CLINICAL ANALYTICS
    Volume Report       — mm³ breakdown + sub-region bar chart
    Longitudinal Track  — RANO trend chart + response classification

  IMAGING
    MPR Viewer          — axial / sagittal / coronal slice explorer
    Uncertainty Map     — MC Dropout entropy heatmap

  SURGICAL PLANNING  (PyVista — Phase 1–4)
    Surgical 3D Viewer  — cortical surface + virtual craniotomy
    Trajectory Planner  — optimal approach route to tumour

  LEGACY / DEBUG
    3D Viewer (Plotly)  — original interactive Plotly mesh (kept for reference)
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# ── Theme (must be imported before any other st calls after set_page_config) ──
from src.ui.theme import (
    inject_theme, sidebar_header, nav_section,
    page_header, metric_row, section_divider, alert_box, status_badge,
)

# ── Analytics & imaging ──────────────────────────────────────────────────────
from src.analytics.volumetrics import VolumetricAnalyzer
from src.analytics.longitudinal import LongitudinalTracker
from src.ui.viewer3d import build_tumor_mesh
from src.ui.mpr_viewer import build_mpr_figure
from src.ui.longitudinal_chart import build_volume_trend_chart, build_rano_summary_bar
from src.ui.uncertainty_viewer import build_uncertainty_panel, uncertainty_stats

# ── Surgical 3D Viewer ───────────────────────────────────────────────────────
from src.ui.surgical_viewer_page import render_surgical_viewer_page

# ── Page config — must be first Streamlit call ───────────────────────────────
st.set_page_config(
    page_title="Anatom AI · Surgical Planning Platform",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_theme()


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

def sidebar() -> dict:
    """Render the styled sidebar and return uploaded data dict."""
    with st.sidebar:
        sidebar_header()

        # ── Navigation ────────────────────────────────────────────────────
        nav_section("Clinical Analytics")
        analytics_page = st.radio(
            "analytics_nav",
            ["Volume Report", "Longitudinal Track"],
            label_visibility="collapsed",
            key="nav_analytics",
        )

        nav_section("Imaging")
        imaging_page = st.radio(
            "imaging_nav",
            ["MPR Viewer", "Uncertainty Map"],
            label_visibility="collapsed",
            key="nav_imaging",
        )

        nav_section("Surgical Planning")
        surgical_page = st.radio(
            "surgical_nav",
            ["🔬 Surgical 3D Viewer", "📐 Trajectory Planner"],
            label_visibility="collapsed",
            key="nav_surgical",
        )

        nav_section("Reference")
        ref_page = st.radio(
            "ref_nav",
            ["3D Viewer (Plotly)"],
            label_visibility="collapsed",
            key="nav_ref",
        )

        # Determine active page from which radio was last interacted with.
        # We use a session_state flag to track which group is "active".
        _update_active_group()
        page = st.session_state.get("active_page", "🔬 Surgical 3D Viewer")

        section_divider()

        # ── Patient / session ─────────────────────────────────────────────
        st.markdown("""
<div style="font-family:'JetBrains Mono',monospace;font-size:0.62rem;
letter-spacing:0.14em;text-transform:uppercase;color:rgba(0,210,255,0.4);
padding:0 0 6px 2px;">Patient Session</div>
""", unsafe_allow_html=True)
        subject_id = st.text_input(
            "Subject ID", value="BraTS-001", label_visibility="collapsed",
            placeholder="Subject ID",
        )

        col_sx, col_sy, col_sz = st.columns(3)
        sx = col_sx.number_input("X", value=1.0, step=0.1, format="%.2f", label_visibility="visible")
        sy = col_sy.number_input("Y", value=1.0, step=0.1, format="%.2f", label_visibility="visible")
        sz = col_sz.number_input("Z", value=1.0, step=0.1, format="%.2f", label_visibility="visible")

        section_divider()

        # ── Data upload ───────────────────────────────────────────────────
        st.markdown("""
<div style="font-family:'JetBrains Mono',monospace;font-size:0.62rem;
letter-spacing:0.14em;text-transform:uppercase;color:rgba(0,210,255,0.4);
padding:0 0 6px 2px;">Data Inputs</div>
""", unsafe_allow_html=True)
        seg_file     = st.file_uploader("Segmentation (.npy)",    type=["npy"], key="up_seg")
        vol_file     = st.file_uploader("MRI Volume (.npy)",      type=["npy"], key="up_vol")
        entropy_file = st.file_uploader("Uncertainty Map (.npy)", type=["npy"], key="up_ent")

        section_divider()

        # ── NIfTI path (Surgical Viewer) ──────────────────────────────────
        st.markdown("""
<div style="font-family:'JetBrains Mono',monospace;font-size:0.62rem;
letter-spacing:0.14em;text-transform:uppercase;color:rgba(0,210,255,0.4);
padding:0 0 6px 2px;">NIfTI Source (Surgical Viewer)</div>
""", unsafe_allow_html=True)
        nifti_path = st.text_input(
            "BraTS folder path",
            value="",
            placeholder="/data/BraTS-001",
            label_visibility="collapsed",
            key="nifti_path_input",
        )

    # ── Build data dict ───────────────────────────────────────────────────
    data: dict = {
        "page":          page,
        "subject_id":    subject_id,
        "voxel_spacing": (float(sx), float(sy), float(sz)),
        "seg":           None,
        "vol":           None,
        "entropy":       None,
        "nifti_subject": None,
        "brain_mask":    None,
    }

    if seg_file is not None:
        data["seg"] = np.load(io.BytesIO(seg_file.read())).astype(np.int32)
    if vol_file is not None:
        data["vol"] = np.load(io.BytesIO(vol_file.read())).astype(np.float32)
    if entropy_file is not None:
        data["entropy"] = np.load(io.BytesIO(entropy_file.read())).astype(np.float32)

    # NIfTI load + skull strip for Surgical Viewer
    nifti_val = st.session_state.get("nifti_path_input", "").strip()
    if nifti_val:
        try:
            from src.imaging.loader import NIfTILoader
            from src.imaging.skull_stripper import SkullStripper
            loader   = NIfTILoader(require_seg=False)
            subject  = loader.load(nifti_val)
            stripped, brain_mask = SkullStripper().strip(subject)
            data["nifti_subject"] = stripped
            data["brain_mask"]    = brain_mask
            if "t1" in stripped.metadata:
                data["voxel_spacing"] = stripped.metadata["t1"].voxel_spacing_mm
            if stripped.seg is not None and data["seg"] is None:
                data["seg"] = stripped.seg.astype(np.int32)
        except Exception as err:
            st.sidebar.warning(f"NIfTI: {err}")

    return data


def _update_active_group() -> None:
    """Track which nav group was most recently interacted with."""
    # On first load, default to Volume Report.
    if "active_page" not in st.session_state:
        st.session_state["active_page"] = "Volume Report"

    nav_keys = {
        "nav_analytics": st.session_state.get("nav_analytics", "Volume Report"),
        "nav_imaging":   st.session_state.get("nav_imaging",   "MPR Viewer"),
        "nav_surgical":  st.session_state.get("nav_surgical",  "🔬 Surgical 3D Viewer"),
        "nav_ref":       st.session_state.get("nav_ref",       "3D Viewer (Plotly)"),
    }
    # Only detect changes after the first render (prev must be non-empty)
    prev = st.session_state.get("_prev_nav", {})
    if prev:
        for key, val in nav_keys.items():
            if prev.get(key) != val:
                st.session_state["active_page"] = val
    st.session_state["_prev_nav"] = nav_keys


# ─────────────────────────────────────────────────────────────────────────────
# Page: Volume Report
# ─────────────────────────────────────────────────────────────────────────────

def page_volume_report(data: dict) -> None:
    page_header("Volume Report", "Sub-region volumetrics  ·  BraTS label breakdown", "📊")

    seg = data["seg"]
    if seg is None:
        alert_box(
            "Upload a <strong>Segmentation (.npy)</strong> in the sidebar to compute volumes, "
            "or enter a NIfTI folder path for automatic extraction.",
            kind="info",
        )
        _demo_volume_report(data["subject_id"], data["voxel_spacing"])
        return

    analyzer = VolumetricAnalyzer()
    result   = analyzer.compute(seg, data["voxel_spacing"], subject_id=data["subject_id"])

    metric_row([
        {"label": "Whole Tumour",     "value": f"{result.wt_mm3:,.0f}",  "unit": "mm³", "accent": "cyan"},
        {"label": "Tumour Core",      "value": f"{result.tc_mm3:,.0f}",  "unit": "mm³", "accent": "purple"},
        {"label": "Enhancing Tumour", "value": f"{result.et_mm3:,.0f}",  "unit": "mm³", "accent": "green"},
        {"label": "Voxel Volume",     "value": f"{result.voxel_volume_mm3:.3f}", "unit": "mm³", "accent": "amber"},
    ])

    section_divider("Sub-Region Breakdown")

    import plotly.graph_objects as go
    labels  = ["NCR (Necrotic Core)", "ED (Edema)", "ET (Enhancing)"]
    values  = [result.volumes_mm3.get(k, 0) for k in ["NCR", "ED", "ET"]]
    colors  = ["#FF4C4C", "#FFD700", "#00E5FF"]

    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker=dict(
            color=colors,
            line=dict(color=["#FF000030", "#FFD70030", "#00E5FF30"], width=0),
        ),
        text=[f"{v:,.0f} mm³" for v in values],
        textposition="outside",
        textfont=dict(family="JetBrains Mono", size=11, color="#D8EEF8"),
    ))
    fig.update_layout(
        paper_bgcolor="rgba(4,14,32,0.0)",
        plot_bgcolor="rgba(4,14,32,0.0)",
        font=dict(family="Rajdhani", color="#D8EEF8"),
        yaxis=dict(
            title="Volume (mm³)", color="#D8EEF8",
            gridcolor="rgba(0,212,255,0.07)",
            zerolinecolor="rgba(0,212,255,0.15)",
        ),
        xaxis=dict(color="#D8EEF8"),
        margin=dict(t=20, b=20, l=20, r=20),
        bargap=0.35,
    )
    st.plotly_chart(fig, use_container_width=True)

    section_divider("Tumour Burden")
    import pandas as pd
    frac_df = pd.DataFrame([
        {"Region": k, "Volume (mm³)": f"{result.volumes_mm3.get(k, result.__dict__.get(k+'_mm3', 0)):,.0f}",
         "% Brain": f"{v*100:.3f}%"}
        for k, v in result.fractions.items()
        if k not in ("background",)
    ])
    st.dataframe(frac_df, use_container_width=True, hide_index=True)

    # ── Phase 5: Radiomic Analysis ────────────────────────────────────────────
    section_divider("Radiomic Fingerprinting")
    with st.expander("⚗️ Radiomic Feature Extraction", expanded=False):
        vol_arr = data.get("vol")
        with st.spinner("Extracting radiomic features…"):
            from src.analytics.radiomics import RadiomicsExtractor
            extractor = RadiomicsExtractor(use_pyradiomics=True)
            radiomic_feats = extractor.extract(
                seg, volume=vol_arr, voxel_spacing=data["voxel_spacing"]
            )

        _display_radiomic_features(radiomic_feats)
        st.session_state["radiomic_feats"] = radiomic_feats

    # ── Phase 5: Recurrence Risk ──────────────────────────────────────────────
    section_divider("Recurrence Risk Score")
    with st.expander("🧬 AI Recurrence Risk Assessment", expanded=False):
        radiomic_feats = st.session_state.get("radiomic_feats")
        from src.analytics.recurrence_risk import RecurrenceRiskEstimator
        estimator = RecurrenceRiskEstimator()
        risk = estimator.estimate(result, radiomic_features=radiomic_feats)
        _display_risk_estimate(risk)
        st.session_state["risk_estimate"] = risk

    # ── Phase 5: AI Narrative Report ──────────────────────────────────────────
    section_divider("AI Clinical Narrative")
    if st.button("📝 Generate AI Clinical Impression", key="btn_narrative",
                 help="Renders a structured clinical narrative from volumetric + radiomic data."):
        with st.spinner("Composing clinical narrative…"):
            from src.reporting.narrative_report import NarrativeReportBuilder
            builder = NarrativeReportBuilder()
            narrative = builder.render(
                vol_result=result,
                subject_id=data["subject_id"],
                scan_date=str(__import__("datetime").date.today()),
                institution="Anatom AI",
                radiomic_features=st.session_state.get("radiomic_feats"),
                risk_estimate=st.session_state.get("risk_estimate"),
            )
            st.session_state["narrative_text"] = narrative

    if "narrative_text" in st.session_state:
        st.markdown("""
<div style="
    background:rgba(4,14,28,0.95);
    border:1px solid rgba(0,212,255,0.25);
    border-left:3px solid #00D4FF;
    border-radius:6px;
    padding:20px 24px;
    font-family:'JetBrains Mono',monospace;
    font-size:0.75rem;
    line-height:1.7;
    color:rgba(200,230,245,0.90);
    white-space:pre-wrap;
    margin-top:12px;
">{text}</div>""".format(text=st.session_state["narrative_text"]),
            unsafe_allow_html=True,
        )
        st.download_button(
            label="⬇️ Download Narrative (.txt)",
            data=st.session_state["narrative_text"].encode("utf-8"),
            file_name=f"anatomai_narrative_{data['subject_id']}.txt",
            mime="text/plain",
        )


def _display_radiomic_features(feats: dict) -> None:
    """Render a styled radiomic feature table for ET and WT regions."""
    import pandas as pd
    display_regions = ["ET", "NCR", "ED"]
    rows = []
    for region in display_regions:
        f = feats.get(region, {})
        if not f or f.get("mesh_volume_mm3", 0) == 0:
            continue
        rows.append({
            "Region":              region,
            "Volume (mm³)":        f"{f.get('mesh_volume_mm3', 0):,.1f}",
            "Sphericity":          f"{f.get('sphericity', 0):.4f}",
            "SA/V Ratio":          f"{f.get('surface_area_to_volume', 0):.4f}",
            "Elongation":          f"{f.get('elongation', 0):.4f}",
            "Entropy (bits)":      f"{f.get('entropy', 0):.4f}",
            "GLCM Contrast":       f"{f.get('glcm_contrast', 0):.4f}",
            "GLCM Homogeneity":    f"{f.get('glcm_homogeneity', 0):.4f}",
        })

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        # Clinical flags
        et = feats.get("ET", {})
        sph = et.get("sphericity", 0)
        if sph > 0:
            if sph > 0.80:
                alert_box(f"ET Sphericity {sph:.3f} — Well-circumscribed boundary. "
                          "Favourable resectability profile.", "success")
            elif sph < 0.50:
                alert_box(f"ET Sphericity {sph:.3f} — Highly irregular boundary. "
                          "Consider generous surgical margin.", "warning")
    else:
        alert_box("No tumour voxels found for radiomic extraction.", "info")


def _display_risk_estimate(risk) -> None:
    """Render the recurrence risk score card."""
    from src.ui.theme import status_badge
    score = risk.score
    interp = risk.interpretation
    state = {"Low": "active", "Moderate": "warning",
              "High": "error", "Very High": "error"}.get(interp, "inactive")

    col_score, col_bar = st.columns([1, 3])
    col_score.markdown(f"""
<div style="
    background:rgba(4,14,32,0.9);
    border:1px solid rgba(0,212,255,0.2);
    border-radius:8px;
    padding:20px;
    text-align:center;
">
    <div style="font-family:'Rajdhani',sans-serif;font-size:0.65rem;
    letter-spacing:0.18em;text-transform:uppercase;
    color:rgba(0,212,255,0.5);margin-bottom:8px;">RECURRENCE RISK</div>
    <div style="font-family:'JetBrains Mono',monospace;font-size:2.4rem;
    color:#00D4FF;line-height:1;">{score}</div>
    <div style="font-family:'Rajdhani',sans-serif;font-size:0.75rem;
    color:rgba(160,200,225,0.5);">/ 100</div>
    <div style="margin-top:10px;">{status_badge(interp, state)}</div>
</div>
""", unsafe_allow_html=True)

    with col_bar:
        if risk.contributions:
            import pandas as pd
            rows = [
                {"Factor": c.feature,
                 "Delta": f"{c.delta:+.1f}",
                 "Direction": c.direction.title(),
                 "Detail": c.description}
                for c in risk.contributions
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    alert_box(risk.disclaimer, "warning")


def _demo_volume_report(subject_id: str, spacing: tuple) -> None:
    section_divider("Demo Data")
    import plotly.graph_objects as go
    demo = {"NCR (Necrotic Core)": 4200, "ED (Edema)": 11500, "ET (Enhancing)": 2800}
    fig  = go.Figure(go.Bar(
        x=list(demo.keys()), y=list(demo.values()),
        marker_color=["#FF4C4C", "#FFD700", "#00E5FF"],
        text=[f"{v:,.0f} mm³" for v in demo.values()],
        textposition="outside",
        textfont=dict(family="JetBrains Mono", size=11, color="#D8EEF8"),
    ))
    fig.update_layout(
        title=dict(text=f"DEMO — {subject_id}", font=dict(family="Rajdhani", size=14, color="#00D4FF")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Rajdhani", color="#D8EEF8"),
        yaxis=dict(gridcolor="rgba(0,212,255,0.07)", zerolinecolor="rgba(0,212,255,0.15)"),
        margin=dict(t=40, b=20, l=20, r=20),
    )
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# Page: 3D Viewer (legacy Plotly)
# ─────────────────────────────────────────────────────────────────────────────

def page_3d_viewer(data: dict) -> None:
    page_header("3D Tumour Mesh", "Interactive Plotly surface renderer  ·  Legacy view", "🔵")

    seg = data["seg"]
    if seg is None:
        alert_box("Upload a <strong>Segmentation (.npy)</strong> to render the 3D surface.", kind="info")
        _demo_3d(data["voxel_spacing"])
        return

    classes_to_show = st.multiselect(
        "Classes to render",
        options=["NCR (1)", "ED (2)", "ET (3)"],
        default=["NCR (1)", "ED (2)", "ET (3)"],
    )
    class_map = {"NCR (1)": 1, "ED (2)": 2, "ET (3)": 3}
    selected  = [class_map[c] for c in classes_to_show] or [1, 2, 3]

    with st.spinner("Extracting tumour surfaces…"):
        fig = build_tumor_mesh(seg, data["voxel_spacing"], classes=selected,
                               title=f"3D Tumour — {data['subject_id']}")

    if not fig.data:
        alert_box("No tumour voxels found in the selected classes.", kind="warning")
    else:
        st.plotly_chart(fig, use_container_width=True)

    st.caption("Drag to rotate · Scroll to zoom · Right-drag to pan")


def _demo_3d(spacing: tuple) -> None:
    demo_seg = np.zeros((40, 40, 40), dtype=np.int32)
    demo_seg[10:25, 12:28, 14:26] = 2
    demo_seg[14:21, 16:24, 17:23] = 1
    demo_seg[17:20, 18:22, 19:22] = 3
    fig = build_tumor_mesh(demo_seg, spacing, title="Demo — Synthetic Tumour")
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# Page: MPR Viewer
# ─────────────────────────────────────────────────────────────────────────────

def page_mpr_viewer(data: dict) -> None:
    page_header("Multi-Planar Reconstruction", "Axial · Sagittal · Coronal slice explorer", "🔬")

    vol = data["vol"]
    seg = data["seg"]

    if vol is None:
        alert_box("Upload an <strong>MRI Volume (.npy)</strong> to explore slices.", kind="info")
        _demo_mpr(seg)
        return

    show_seg  = st.checkbox("Show segmentation overlay", value=(seg is not None), disabled=(seg is None))
    overlay   = seg if (show_seg and seg is not None) else None

    col_a, col_b, col_c = st.columns(3)
    ax_frac  = col_a.slider("Axial",    0.0, 1.0, 0.5, 0.01)
    sag_frac = col_b.slider("Sagittal", 0.0, 1.0, 0.5, 0.01)
    cor_frac = col_c.slider("Coronal",  0.0, 1.0, 0.5, 0.01)

    fig = build_mpr_figure(vol, segmentation=overlay,
                           slice_fracs=(ax_frac, sag_frac, cor_frac),
                           modality_name=data["subject_id"])
    st.pyplot(fig, use_container_width=True)


def _demo_mpr(seg) -> None:
    rng      = np.random.default_rng(1)
    demo_vol = rng.normal(600, 80, (64, 64, 40)).clip(1, None).astype(np.float32)
    demo_seg = np.zeros((64, 64, 40), dtype=np.int32)
    demo_seg[20:44, 20:44, 12:28] = 2
    demo_seg[26:38, 26:38, 16:24] = 1
    demo_seg[30:34, 30:34, 18:22] = 3
    fig = build_mpr_figure(demo_vol, segmentation=demo_seg if seg is None else seg)
    st.pyplot(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# Page: Uncertainty Map
# ─────────────────────────────────────────────────────────────────────────────

def page_uncertainty_map(data: dict) -> None:
    page_header("Uncertainty Map", "MC Dropout predictive entropy  ·  Model confidence visualisation", "🌡")

    vol = data["vol"]
    seg = data["seg"]

    alert_box(
        "Generate entropy maps via <code>scripts/analyze.py uncertainty</code> "
        "then upload the <code>_entropy.npy</code> file in the sidebar.",
        kind="info",
    )

    if vol is None:
        alert_box("Upload an <strong>MRI Volume (.npy)</strong> to see the overlay.", kind="warning")
        return

    entropy = data.get("entropy")
    if entropy is None:
        st.caption("No entropy map uploaded — showing synthetic demo.")
        rng     = np.random.default_rng(42)
        entropy = rng.exponential(scale=0.3, size=vol.shape).astype(np.float32)

    col_axis, col_frac = st.columns([1, 3])
    axis_label = col_axis.selectbox("Plane", ["Axial (0)", "Sagittal (1)", "Coronal (2)"])
    axis_idx   = int(axis_label.split("(")[1][0])
    frac       = col_frac.slider("Slice position", 0.0, 1.0, 0.5, 0.01)

    if entropy.shape != vol.shape:
        alert_box(f"Shape mismatch: entropy {entropy.shape} vs volume {vol.shape}", kind="error")
        return

    fig = build_uncertainty_panel(vol, entropy, segmentation=seg,
                                  axis=axis_idx, slice_frac=frac,
                                  title=f"Predictive Uncertainty — {data['subject_id']}")
    st.pyplot(fig, use_container_width=True)

    stats = uncertainty_stats(entropy, seg)
    section_divider("Entropy Statistics")
    metric_row([
        {"label": "Mean Entropy", "value": f"{stats['mean']:.4f}", "accent": "cyan"},
        {"label": "Max Entropy",  "value": f"{stats['max']:.4f}",  "accent": "amber"},
        {"label": "P90 Entropy",  "value": f"{stats['p90']:.4f}",  "accent": "amber"},
        {"label": "P95 Entropy",  "value": f"{stats['p95']:.4f}",  "accent": "red"},
    ])


# ─────────────────────────────────────────────────────────────────────────────
# Page: Longitudinal Track
# ─────────────────────────────────────────────────────────────────────────────

def page_longitudinal(data: dict) -> None:
    page_header("Longitudinal Tracking", "RANO volume-based response criteria  ·  Multi-timepoint trend", "📈")

    st.markdown("""
<div style="font-family:'Rajdhani',sans-serif;font-size:0.82rem;
color:rgba(160,200,225,0.7);letter-spacing:0.04em;margin-bottom:12px;">
Enter WT / TC / ET volumes (mm³) for each scan timepoint. Use
<code style="color:#00D4FF;font-family:'JetBrains Mono',monospace;">
scripts/analyze.py volume</code> to compute these from segmentations.
</div>
""", unsafe_allow_html=True)

    if "timepoints" not in st.session_state:
        st.session_state.timepoints = [
            {"day": 0,   "wt": 18000, "tc": 10000, "et": 4000},
            {"day": 45,  "wt": 15500, "tc": 8500,  "et": 3200},
            {"day": 90,  "wt": 9000,  "tc": 5000,  "et": 1800},
            {"day": 180, "wt": 5500,  "tc": 3000,  "et": 900},
        ]

    tps = st.session_state.timepoints
    cols_h = st.columns([1, 2, 2, 2, 0.5])
    for h, label in zip(cols_h, ["Day", "WT (mm³)", "TC (mm³)", "ET (mm³)", ""]):
        h.markdown(f"<div style='font-family:Rajdhani,sans-serif;font-size:0.72rem;"
                   f"font-weight:700;letter-spacing:0.12em;text-transform:uppercase;"
                   f"color:rgba(0,212,255,0.55);'>{label}</div>", unsafe_allow_html=True)

    updated = []
    for i, tp in enumerate(tps):
        c0, c1, c2, c3, c4 = st.columns([1, 2, 2, 2, 0.5])
        day = c0.number_input("", value=tp["day"], key=f"day_{i}", label_visibility="collapsed")
        wt  = c1.number_input("", value=tp["wt"],  key=f"wt_{i}",  label_visibility="collapsed")
        tc  = c2.number_input("", value=tp["tc"],  key=f"tc_{i}",  label_visibility="collapsed")
        et  = c3.number_input("", value=tp["et"],  key=f"et_{i}",  label_visibility="collapsed")
        if c4.button("✕", key=f"del_{i}"):
            continue
        updated.append({"day": day, "wt": wt, "tc": tc, "et": et})
    st.session_state.timepoints = updated

    if st.button("+ Add Timepoint"):
        last = tps[-1]["day"] if tps else 0
        st.session_state.timepoints.append({"day": last + 45, "wt": 0, "tc": 0, "et": 0})
        st.rerun()

    tps  = sorted(st.session_state.timepoints, key=lambda x: x["day"])
    if len(tps) < 2:
        alert_box("Add at least two timepoints to render the trend chart.", kind="warning")
        return

    days = [t["day"] for t in tps]
    wt   = [t["wt"]  for t in tps]
    tc   = [t["tc"]  for t in tps]
    et   = [t["et"]  for t in tps]

    rano_labels = [None]
    for i in range(1, len(tps)):
        cat = LongitudinalTracker._classify_rano(wt[0], wt[i])
        rano_labels.append(cat)

    fig = build_volume_trend_chart(days, wt, tc, et,
                                   subject_id=data["subject_id"],
                                   rano_categories=rano_labels)
    st.plotly_chart(fig, use_container_width=True)

    section_divider("RANO Classification")
    for i in range(1, len(tps)):
        cat    = rano_labels[i]
        states = {"CR": "success", "PR": "active", "SD": "warning", "PD": "error"}
        from src.ui.theme import status_badge
        badge  = status_badge(cat, state=states.get(cat, "inactive"))
        pct    = (wt[i] - wt[0]) / max(wt[0], 1.0) * 100
        elapsed = days[i] - days[0]
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:12px;padding:8px 0;'
            f'border-bottom:1px solid rgba(0,210,255,0.08);">'
            f'{badge}'
            f'<span style="font-family:JetBrains Mono,monospace;font-size:0.82rem;color:#D8EEF8;">'
            f'Day {days[i]}</span>'
            f'<span style="font-family:Rajdhani,sans-serif;font-size:0.82rem;'
            f'color:rgba(160,200,225,0.6);">WT {pct:+.1f}% · {elapsed}d elapsed</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Page: Trajectory Planner
# ─────────────────────────────────────────────────────────────────────────────

def page_trajectory_planner(data: dict) -> None:
    from src.ui.theme import trajectory_card
    page_header(
        "Trajectory Planner",
        "Optimal surgical approach routes  ·  Landmark avoidance  ·  Safety scoring",
        "📐",
    )

    seg            = data["seg"]
    voxel_spacing  = data["voxel_spacing"]
    subject        = data.get("nifti_subject")
    brain_mask     = data.get("brain_mask")

    if seg is None:
        alert_box(
            "Upload a <strong>Segmentation (.npy)</strong> (and optionally a NIfTI "
            "folder for patient-specific cortex and landmarks) to compute trajectories.",
            kind="info",
        )
        return

    col_cfg, col_lm = st.columns(2)
    with col_cfg:
        n_cand = st.slider(
            "Candidate entry points", 200, 2000, 800, 100,
            help="More candidates = better trajectory coverage but slower.",
        )
        show_lm_detection = st.checkbox("Enable landmark avoidance", value=True)

    with col_lm:
        excl = st.multiselect(
            "Hard exclusion zones",
            ["brainstem", "left_thalamus", "right_thalamus",
             "left_ventricle", "right_ventricle"],
            default=["brainstem"],
            help="Trajectories passing through these structures are heavily penalised.",
        )

    from src.analytics.volumetrics import compute_tumor_centroid
    tumor_centroid = compute_tumor_centroid(seg, voxel_spacing)

    # Landmarks
    landmarks = {}
    if show_lm_detection:
        with st.spinner("Loading landmark positions…"):
            if subject is not None:
                from src.imaging.landmark_detector import AnatomicalLandmarkDetector
                det = AnatomicalLandmarkDetector(use_ants=True, visible_only=True)
                try:
                    landmarks = det.detect(subject, brain_mask, voxel_spacing)
                except Exception as e:
                    st.caption(f"Landmark detection: {e} — using geometric fallback.")
                    landmarks = {}
            if not landmarks and seg is not None:
                from src.ui.surgical_viewer_page import _fallback_landmarks
                landmarks = _fallback_landmarks(seg, voxel_spacing)

    # Cortex mesh
    cortex_mesh = None
    if subject is not None:
        with st.spinner("Extracting cortical surface for trajectory sampling…"):
            from src.ui.surgical_viewer_page import _get_cortex_mesh
            cortex_mesh = _get_cortex_mesh(subject, brain_mask, voxel_spacing)

    with st.spinner(f"Evaluating {n_cand} trajectory candidates…"):
        from src.analytics.trajectory_planner import SurgicalTrajectoryPlanner
        planner = SurgicalTrajectoryPlanner(n_candidates=n_cand)
        results = planner.plan(
            cortex_mesh=cortex_mesh,
            tumor_centroid=tumor_centroid,
            landmarks=landmarks,
            excluded_landmarks=excl,
        )

    if not results:
        alert_box("No valid trajectories found. Try increasing candidate count.", kind="warning")
        return

    section_divider("Optimal Trajectories")

    # Metric summary
    best = results[0]
    metric_row([
        {"label": "Best Path Length", "value": f"{best.path_length_mm:.1f}", "unit": "mm",     "accent": "green"},
        {"label": "Safety Score",     "value": f"{int(best.safety_score*100)}", "unit": "/100", "accent": "cyan"},
        {"label": "Landmarks Mapped", "value": str(len(landmarks)),              "unit": "",     "accent": "purple"},
        {"label": "Warnings",         "value": str(len(best.warnings)),          "unit": "",
         "accent": "amber" if best.warnings else "green"},
    ])

    section_divider()

    # Trajectory cards
    for r in results:
        trajectory_card(
            rank=r.rank,
            entry=r.entry_point,
            target=r.target_point,
            length_mm=r.path_length_mm,
            score=r.safety_score,
            warnings=r.warnings,
        )

    # 3D visualisation with trajectories
    if st.button("Render in Surgical 3D Viewer"):
        from src.ui.renderer_context import PYVISTA_AVAILABLE
        if PYVISTA_AVAILABLE:
            from src.ui.pyvista_renderer import NeuroRenderer, RenderParams
            renderer = NeuroRenderer(width=1200, height=800)
            traj_dicts = [
                {"entry_point": r.entry_point, "target_point": r.target_point,
                 "safety_score": r.safety_score}
                for r in results
            ]
            params = RenderParams(mode="craniotomy", clip_radius=45.0, cortex_opacity=0.18)
            with st.spinner("Rendering trajectory scene…"):
                try:
                    png = renderer.render_combined(
                        cortex_mesh=cortex_mesh,
                        segmentation=seg,
                        voxel_spacing=voxel_spacing,
                        params=params,
                        tumor_centroid=tumor_centroid,
                        landmarks=landmarks,
                        trajectories=traj_dicts,
                    )
                    st.image(png, caption="Surgical trajectories overlay", use_container_width=True)
                    st.download_button("⬇ Download render", data=png,
                                       file_name=f"trajectory_{data['subject_id']}.png",
                                       mime="image/png")
                except Exception as exc:
                    alert_box(f"Render error: {exc}", kind="error")

    # Landmark proximity table
    if landmarks:
        section_divider("Landmark Proximity")
        import pandas as pd
        rows = []
        for name, coords in landmarks.items():
            dist = float(np.linalg.norm(np.asarray(coords) - np.asarray(tumor_centroid)))
            risk = "🔴 Critical" if dist < 10 else ("🟡 Caution" if dist < 20 else "🟢 Clear")
            rows.append({"Structure": name.replace("_", " ").title(),
                         "Distance to Tumour (mm)": f"{dist:.1f}", "Alert": risk})
        st.dataframe(pd.DataFrame(rows).sort_values("Distance to Tumour (mm)"),
                     use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    data = sidebar()
    page = data["page"]

    # Route to page
    if page == "Volume Report":
        page_volume_report(data)
    elif page == "3D Viewer (Plotly)":
        page_3d_viewer(data)
    elif page == "MPR Viewer":
        page_mpr_viewer(data)
    elif page == "Uncertainty Map":
        page_uncertainty_map(data)
    elif page == "Longitudinal Track":
        page_longitudinal(data)
    elif page == "🔬 Surgical 3D Viewer":
        render_surgical_viewer_page(data)
    elif page == "📐 Trajectory Planner":
        page_trajectory_planner(data)
    else:
        st.info("Select a page from the sidebar.")


if __name__ == "__main__":
    main()
