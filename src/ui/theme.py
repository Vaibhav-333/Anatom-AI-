"""
theme.py — Anatom AI Medical-Grade UI Theme System.

Injects a complete CSS + JavaScript overhaul that transforms Streamlit into
a clinical neurosurgical workstation aesthetic:

  • Dark holographic palette inspired by Brainlab Elements / 3D Slicer
  • Glassmorphism panels with neon border glow
  • Rajdhani + JetBrains Mono typography (Google Fonts)
  • Animated scanline, pulsing status indicators, corner bracket decorators
  • Hides ALL default Streamlit chrome (header, footer, hamburger menu)
  • Custom sidebar with icon navigation
  • Status bar: patient ID · session timestamp · system status

Call inject_theme() once at the top of app.py before any other st calls.
"""

from __future__ import annotations

import streamlit as st

# ── Colour tokens ─────────────────────────────────────────────────────────────
COLORS = {
    "bg_base":         "#030810",
    "bg_surface":      "rgba(4, 18, 38, 0.92)",
    "bg_surface2":     "rgba(6, 26, 54, 0.85)",
    "bg_glass":        "rgba(0, 180, 255, 0.04)",
    "border":          "rgba(0, 210, 255, 0.18)",
    "border_bright":   "rgba(0, 210, 255, 0.55)",
    "accent_cyan":     "#00D4FF",
    "accent_green":    "#00FF85",
    "accent_amber":    "#FFB800",
    "accent_red":      "#FF3B3B",
    "accent_purple":   "#B06EFF",
    "text_primary":    "#D8EEF8",
    "text_secondary":  "rgba(160, 200, 225, 0.72)",
    "text_dim":        "rgba(100, 150, 180, 0.55)",
    "ncr_color":       "#FF4C4C",
    "ed_color":        "#FFD700",
    "et_color":        "#00E5FF",
}

_CSS = """
/* ═══════════════════════════════════════════════════════════════════════════
   ANATOM AI — MEDICAL WORKSTATION CSS
   ═══════════════════════════════════════════════════════════════════════════ */

/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;500&family=Inter:wght@300;400;500;600&display=swap');

/* ── Root variables ── */
:root {
    --bg-base:        #030810;
    --bg-surface:     rgba(4, 18, 38, 0.92);
    --bg-surface2:    rgba(6, 26, 54, 0.85);
    --bg-glass:       rgba(0, 180, 255, 0.04);
    --border:         rgba(0, 210, 255, 0.18);
    --border-bright:  rgba(0, 210, 255, 0.55);
    --cyan:           #00D4FF;
    --green:          #00FF85;
    --amber:          #FFB800;
    --red:            #FF3B3B;
    --purple:         #B06EFF;
    --text:           #D8EEF8;
    --text-dim:       rgba(160, 200, 225, 0.72);
    --font-ui:        'Rajdhani', 'Inter', sans-serif;
    --font-mono:      'JetBrains Mono', 'Courier New', monospace;
    --radius:         4px;
    --radius-lg:      8px;
    --glow-cyan:      0 0 12px rgba(0, 212, 255, 0.35), 0 0 32px rgba(0, 212, 255, 0.12);
    --glow-green:     0 0 12px rgba(0, 255, 133, 0.35), 0 0 32px rgba(0, 255, 133, 0.12);
    --glow-red:       0 0 12px rgba(255, 59, 59, 0.35), 0 0 32px rgba(255, 59, 59, 0.12);
}

/* ── Global reset ── */
*, *::before, *::after { box-sizing: border-box; }

html, body, [data-testid="stAppViewContainer"], [data-testid="stApp"] {
    background: var(--bg-base) !important;
    font-family: var(--font-ui) !important;
    color: var(--text) !important;
}

/* ── Animated grid background ── */
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed;
    inset: 0;
    background-image:
        linear-gradient(rgba(0, 212, 255, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0, 212, 255, 0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    z-index: 0;
}

/* ── Scanline animation ── */
[data-testid="stAppViewContainer"]::after {
    content: '';
    position: fixed;
    top: -100%;
    left: 0;
    width: 100%;
    height: 2px;
    background: linear-gradient(90deg, transparent, var(--cyan), transparent);
    opacity: 0.15;
    animation: scanline 6s linear infinite;
    pointer-events: none;
    z-index: 1;
}

@keyframes scanline {
    0%   { top: -2px; }
    100% { top: 100%; }
}

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"],
.stDeployButton { display: none !important; }

/* ── Main content area ── */
[data-testid="stMain"] {
    background: transparent !important;
    padding-top: 0 !important;
}

.main .block-container {
    padding: 1.2rem 1.8rem 2rem 1.8rem !important;
    max-width: 100% !important;
    background: transparent !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: rgba(2, 10, 22, 0.97) !important;
    border-right: 1px solid var(--border-bright) !important;
    box-shadow: 4px 0 24px rgba(0, 212, 255, 0.08) !important;
}

[data-testid="stSidebar"] > div:first-child {
    padding-top: 0 !important;
}

/* ── Radio buttons → Nav items ── */
[data-testid="stSidebar"] .stRadio > div {
    gap: 2px !important;
}

[data-testid="stSidebar"] .stRadio label {
    font-family: var(--font-ui) !important;
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    color: var(--text-dim) !important;
    padding: 8px 14px !important;
    border-radius: var(--radius) !important;
    border: 1px solid transparent !important;
    transition: all 0.18s ease !important;
    cursor: pointer !important;
    display: flex !important;
    align-items: center !important;
    width: 100% !important;
}

[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(0, 212, 255, 0.06) !important;
    border-color: var(--border) !important;
    color: var(--cyan) !important;
}

[data-testid="stSidebar"] .stRadio [aria-checked="true"] + label,
[data-testid="stSidebar"] .stRadio label[data-baseweb="radio"]:has(input:checked) {
    background: rgba(0, 212, 255, 0.10) !important;
    border-color: var(--cyan) !important;
    color: var(--cyan) !important;
    box-shadow: var(--glow-cyan) !important;
}

/* ── Headings ── */
h1, h2, h3, h4 {
    font-family: var(--font-ui) !important;
    font-weight: 600 !important;
    letter-spacing: 0.05em !important;
    color: var(--text) !important;
}

h1 { font-size: 1.55rem !important; color: var(--cyan) !important; }
h2 { font-size: 1.25rem !important; }
h3 { font-size: 1.05rem !important; color: var(--cyan) !important; }

/* ── Metric tiles ── */
[data-testid="stMetric"] {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-lg) !important;
    padding: 14px 18px !important;
    position: relative !important;
    overflow: hidden !important;
    transition: border-color 0.2s !important;
}

[data-testid="stMetric"]:hover {
    border-color: var(--border-bright) !important;
    box-shadow: var(--glow-cyan) !important;
}

[data-testid="stMetric"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
    background: var(--cyan);
    box-shadow: var(--glow-cyan);
}

[data-testid="stMetricLabel"] {
    font-family: var(--font-ui) !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase !important;
    color: var(--text-dim) !important;
}

[data-testid="stMetricValue"] {
    font-family: var(--font-mono) !important;
    font-size: 1.5rem !important;
    font-weight: 500 !important;
    color: var(--cyan) !important;
}

/* ── Buttons ── */
.stButton > button {
    font-family: var(--font-ui) !important;
    font-size: 0.8rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    background: transparent !important;
    border: 1px solid var(--border-bright) !important;
    color: var(--cyan) !important;
    border-radius: var(--radius) !important;
    padding: 8px 20px !important;
    transition: all 0.18s ease !important;
}

.stButton > button:hover {
    background: rgba(0, 212, 255, 0.10) !important;
    box-shadow: var(--glow-cyan) !important;
    border-color: var(--cyan) !important;
}

.stButton > button:active {
    background: rgba(0, 212, 255, 0.20) !important;
    transform: scale(0.98) !important;
}

/* ── Download button ── */
[data-testid="stDownloadButton"] > button {
    font-family: var(--font-ui) !important;
    font-size: 0.78rem !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    background: rgba(0, 255, 133, 0.08) !important;
    border: 1px solid var(--green) !important;
    color: var(--green) !important;
    border-radius: var(--radius) !important;
    transition: all 0.18s ease !important;
}

[data-testid="stDownloadButton"] > button:hover {
    background: rgba(0, 255, 133, 0.18) !important;
    box-shadow: var(--glow-green) !important;
}

/* ── Sliders ── */
[data-testid="stSlider"] > div {
    padding: 4px 0 !important;
}

[data-testid="stSlider"] [data-baseweb="slider"] div[role="slider"] {
    background: var(--cyan) !important;
    border: 2px solid var(--bg-base) !important;
    box-shadow: var(--glow-cyan) !important;
}

[data-testid="stSlider"] [data-baseweb="slider"] [data-testid="stTickBarMin"],
[data-testid="stSlider"] [data-baseweb="slider"] [data-testid="stTickBarMax"] {
    font-family: var(--font-mono) !important;
    font-size: 0.7rem !important;
    color: var(--text-dim) !important;
}

/* ── Selectbox / dropdowns ── */
[data-baseweb="select"] > div {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    font-family: var(--font-ui) !important;
    font-size: 0.85rem !important;
    color: var(--text) !important;
    transition: border-color 0.18s !important;
}

[data-baseweb="select"] > div:hover {
    border-color: var(--border-bright) !important;
}

[data-baseweb="select"] > div:focus-within {
    border-color: var(--cyan) !important;
    box-shadow: var(--glow-cyan) !important;
}

/* ── Dropdowns menu ── */
[data-baseweb="popover"] {
    background: rgba(4, 14, 32, 0.98) !important;
    border: 1px solid var(--border-bright) !important;
    border-radius: var(--radius-lg) !important;
    backdrop-filter: blur(12px) !important;
}

/* ── Text inputs ── */
[data-baseweb="input"] {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    font-family: var(--font-mono) !important;
    font-size: 0.84rem !important;
    color: var(--text) !important;
}

[data-baseweb="input"]:focus-within {
    border-color: var(--cyan) !important;
    box-shadow: var(--glow-cyan) !important;
}

/* ── Expanders ── */
[data-testid="stExpander"] {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-lg) !important;
    overflow: hidden !important;
}

[data-testid="stExpander"] summary {
    font-family: var(--font-ui) !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    color: var(--cyan) !important;
    padding: 12px 16px !important;
    background: var(--bg-surface2) !important;
}

[data-testid="stExpander"] summary:hover {
    background: rgba(0, 212, 255, 0.06) !important;
}

/* ── Checkboxes ── */
[data-testid="stCheckbox"] {
    font-family: var(--font-ui) !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.04em !important;
    color: var(--text) !important;
}

[data-testid="stCheckbox"] span {
    border-color: var(--border-bright) !important;
    border-radius: 2px !important;
}

[data-testid="stCheckbox"] input:checked + span {
    background: var(--cyan) !important;
    border-color: var(--cyan) !important;
}

/* ── Dividers ── */
hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent, var(--border-bright), transparent) !important;
    margin: 1.2rem 0 !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: var(--bg-surface) !important;
    border: 1px dashed var(--border-bright) !important;
    border-radius: var(--radius-lg) !important;
    padding: 12px !important;
}

[data-testid="stFileUploader"] label {
    font-family: var(--font-ui) !important;
    font-size: 0.8rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.08em !important;
    text-transform: uppercase !important;
    color: var(--text-dim) !important;
}

/* ── Info / warning / error boxes ── */
[data-testid="stInfo"] {
    background: rgba(0, 212, 255, 0.07) !important;
    border: 1px solid rgba(0, 212, 255, 0.30) !important;
    border-left: 3px solid var(--cyan) !important;
    border-radius: var(--radius) !important;
    font-family: var(--font-ui) !important;
    font-size: 0.85rem !important;
    color: var(--text) !important;
}

[data-testid="stWarning"] {
    background: rgba(255, 184, 0, 0.07) !important;
    border: 1px solid rgba(255, 184, 0, 0.30) !important;
    border-left: 3px solid var(--amber) !important;
    border-radius: var(--radius) !important;
    font-family: var(--font-ui) !important;
    font-size: 0.85rem !important;
}

[data-testid="stError"] {
    background: rgba(255, 59, 59, 0.07) !important;
    border: 1px solid rgba(255, 59, 59, 0.30) !important;
    border-left: 3px solid var(--red) !important;
    border-radius: var(--radius) !important;
    font-family: var(--font-ui) !important;
    font-size: 0.85rem !important;
}

/* ── Dataframes / tables ── */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-lg) !important;
    overflow: hidden !important;
    font-family: var(--font-mono) !important;
    font-size: 0.82rem !important;
}

[data-testid="stDataFrame"] th {
    background: var(--bg-surface2) !important;
    color: var(--cyan) !important;
    font-family: var(--font-ui) !important;
    font-size: 0.75rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.1em !important;
    text-transform: uppercase !important;
    border-bottom: 1px solid var(--border-bright) !important;
}

[data-testid="stDataFrame"] td {
    background: var(--bg-surface) !important;
    color: var(--text) !important;
    border-bottom: 1px solid var(--border) !important;
}

[data-testid="stDataFrame"] tr:hover td {
    background: rgba(0, 212, 255, 0.05) !important;
}

/* ── Number inputs ── */
[data-baseweb="input"] input {
    font-family: var(--font-mono) !important;
    font-size: 0.9rem !important;
    color: var(--text) !important;
    background: transparent !important;
}

/* ── Spinner ── */
[data-testid="stSpinner"] {
    font-family: var(--font-ui) !important;
    font-size: 0.85rem !important;
    letter-spacing: 0.06em !important;
    color: var(--cyan) !important;
}

/* ── Caption / small text ── */
[data-testid="stCaptionContainer"] {
    font-family: var(--font-ui) !important;
    font-size: 0.75rem !important;
    letter-spacing: 0.04em !important;
    color: var(--text-dim) !important;
}

/* ── Plotly charts ── */
.js-plotly-plot {
    border-radius: var(--radius-lg) !important;
    overflow: hidden !important;
}

/* ── Image display ── */
[data-testid="stImage"] img {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-lg) !important;
    box-shadow: 0 0 40px rgba(0, 212, 255, 0.10) !important;
}

/* ── Number inputs ── */
[data-testid="stNumberInput"] {
    font-family: var(--font-mono) !important;
}

/* ── Columns ── */
[data-testid="stHorizontalBlock"] {
    gap: 1rem !important;
}

/* ── Pulse animation ── */
@keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 6px rgba(0,212,255,0.3); }
    50%       { box-shadow: 0 0 18px rgba(0,212,255,0.7); }
}

@keyframes pulse-dot {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: 0.5; transform: scale(0.8); }
}

@keyframes fade-in-up {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ── Corner bracket mixin (applied via custom HTML) ── */
.nm-card {
    position: relative;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 20px;
    animation: fade-in-up 0.3s ease;
}

.nm-card::before, .nm-card::after {
    content: '';
    position: absolute;
    width: 12px; height: 12px;
    border-color: var(--cyan);
    border-style: solid;
}

.nm-card::before {
    top: -1px; left: -1px;
    border-width: 2px 0 0 2px;
}

.nm-card::after {
    bottom: -1px; right: -1px;
    border-width: 0 2px 2px 0;
}

/* Custom scrollbar */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--bg-base); }
::-webkit-scrollbar-thumb {
    background: var(--border-bright);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover { background: var(--cyan); }

/* ── Hide collapsed radio / widget labels ── */
[data-testid="stWidgetLabel"]:has(+ [data-testid="stRadioGroup"]) {
    display: none !important;
}
/* Broader fallback: any widget label that is marked collapsed */
label[data-visibility="collapsed"],
[data-testid="stWidgetLabel"][data-visibility="collapsed"] {
    display: none !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
}
/* Hide the raw label text for sidebar radio groups specifically */
[data-testid="stSidebar"] .stRadio > label,
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] {
    display: none !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}
"""

_SIDEBAR_HEADER_HTML = """
<div style="
    padding: 20px 16px 12px 16px;
    border-bottom: 1px solid rgba(0,210,255,0.18);
    margin-bottom: 12px;
">
    <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px;">
        <div style="
            width: 32px; height: 32px;
            background: rgba(0,212,255,0.12);
            border: 1px solid rgba(0,212,255,0.5);
            border-radius: 6px;
            display: flex; align-items: center; justify-content: center;
            font-size: 18px;
        ">🧠</div>
        <div>
            <div style="
                font-family: 'Rajdhani', sans-serif;
                font-size: 1.1rem;
                font-weight: 700;
                letter-spacing: 0.12em;
                color: #00D4FF;
                line-height: 1.1;
            ">ANATOM AI</div>
            <div style="
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.60rem;
                color: rgba(0,212,255,0.5);
                letter-spacing: 0.15em;
                text-transform: uppercase;
            ">SURGICAL PLANNING v4.0</div>
        </div>
    </div>
    <div style="
        display: flex; align-items: center; gap: 6px;
        margin-top: 8px;
    ">
        <div style="
            width: 7px; height: 7px;
            background: #00FF85;
            border-radius: 50%;
            animation: pulse-dot 2s ease-in-out infinite;
        "></div>
        <span style="
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.65rem;
            color: #00FF85;
            letter-spacing: 0.1em;
            text-transform: uppercase;
        ">SYSTEM NOMINAL</span>
    </div>
</div>
<style>
@keyframes pulse-dot {
    0%,100% { opacity:1; box-shadow: 0 0 6px #00FF85; }
    50% { opacity:0.4; box-shadow: 0 0 2px #00FF85; }
}
</style>
"""

_NAV_SECTION_HTML = """
<div style="
    padding: 6px 16px 4px 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.60rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: rgba(0,212,255,0.35);
    margin-top: 8px;
">{label}</div>
"""


def inject_theme() -> None:
    """Inject the complete Anatom AI medical UI theme into Streamlit."""
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)


def sidebar_header() -> None:
    """Render the Anatom AI logo + status header in the sidebar."""
    st.sidebar.markdown(_SIDEBAR_HEADER_HTML, unsafe_allow_html=True)


def nav_section(label: str) -> None:
    """Render a navigation section label in the sidebar."""
    st.sidebar.markdown(_NAV_SECTION_HTML.format(label=label), unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "", icon: str = "") -> None:
    """Render a styled page header with optional subtitle and icon."""
    icon_part = f"{icon}&nbsp;&nbsp;" if icon else ""
    st.markdown(f"""
<div style="
    padding: 16px 0 4px 0;
    border-bottom: 1px solid rgba(0,210,255,0.18);
    margin-bottom: 20px;
">
    <div style="
        font-family: 'Rajdhani', sans-serif;
        font-size: 1.45rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #00D4FF;
    ">{icon_part}{title}</div>
    {f'<div style="font-family: Rajdhani, sans-serif; font-size:0.82rem; letter-spacing:0.06em; color:rgba(160,200,225,0.6); margin-top:4px;">{subtitle}</div>' if subtitle else ''}
</div>
""", unsafe_allow_html=True)


def panel(content_fn, title: str = "", accent: str = "cyan") -> None:
    """
    Wrap content_fn() output in a styled glassmorphism panel.
    Call like: panel(lambda: st.write("hello"), title="Data")
    """
    accent_color = {
        "cyan": "#00D4FF", "green": "#00FF85",
        "amber": "#FFB800", "red": "#FF3B3B", "purple": "#B06EFF",
    }.get(accent, "#00D4FF")

    if title:
        st.markdown(f"""
<div style="
    font-family:'Rajdhani',sans-serif;
    font-size:0.72rem;
    font-weight:700;
    letter-spacing:0.18em;
    text-transform:uppercase;
    color:{accent_color};
    padding: 0 0 6px 2px;
    border-bottom: 1px solid rgba(0,210,255,0.12);
    margin-bottom: 12px;
">{title}</div>
""", unsafe_allow_html=True)
    content_fn()


def metric_row(metrics: list[dict]) -> None:
    """
    Render a row of custom metric tiles.

    Each dict: {"label": str, "value": str, "unit": str, "accent": str}
    accent options: "cyan" | "green" | "amber" | "red" | "purple"
    """
    accent_map = {
        "cyan":   ("#00D4FF", "rgba(0,212,255,0.08)"),
        "green":  ("#00FF85", "rgba(0,255,133,0.08)"),
        "amber":  ("#FFB800", "rgba(255,184,0,0.08)"),
        "red":    ("#FF3B3B", "rgba(255,59,59,0.08)"),
        "purple": ("#B06EFF", "rgba(176,110,255,0.08)"),
    }
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        accent = m.get("accent", "cyan")
        color, bg = accent_map.get(accent, accent_map["cyan"])
        unit = m.get("unit", "")
        with col:
            st.markdown(f"""
<div style="
    background:{bg};
    border:1px solid {color}30;
    border-left:3px solid {color};
    border-radius:6px;
    padding:14px 16px;
    position:relative;
    overflow:hidden;
">
    <div style="
        font-family:'Rajdhani',sans-serif;
        font-size:0.68rem;
        font-weight:700;
        letter-spacing:0.16em;
        text-transform:uppercase;
        color:{color}99;
        margin-bottom:6px;
    ">{m['label']}</div>
    <div style="
        font-family:'JetBrains Mono',monospace;
        font-size:1.45rem;
        font-weight:500;
        color:{color};
        line-height:1.1;
    ">{m['value']}<span style="font-size:0.75rem; margin-left:4px; opacity:0.7;">{unit}</span></div>
</div>
""", unsafe_allow_html=True)


def status_badge(label: str, state: str = "active") -> str:
    """Return HTML for a status badge. state: active|warning|error|inactive"""
    colors = {
        "active":   ("#00FF85", "rgba(0,255,133,0.12)"),
        "warning":  ("#FFB800", "rgba(255,184,0,0.12)"),
        "error":    ("#FF3B3B", "rgba(255,59,59,0.12)"),
        "inactive": ("rgba(160,200,225,0.4)", "rgba(160,200,225,0.05)"),
    }
    color, bg = colors.get(state, colors["active"])
    dot = f'<span style="display:inline-block;width:6px;height:6px;background:{color};border-radius:50%;margin-right:5px;"></span>' if state != "inactive" else ""
    return f"""<span style="
        font-family:'Rajdhani',sans-serif;
        font-size:0.72rem;
        font-weight:600;
        letter-spacing:0.10em;
        text-transform:uppercase;
        color:{color};
        background:{bg};
        border:1px solid {color}40;
        border-radius:4px;
        padding:3px 10px;
        display:inline-flex;
        align-items:center;
    ">{dot}{label}</span>"""


def section_divider(label: str = "") -> None:
    """Render a styled section divider with optional centered label."""
    if label:
        st.markdown(f"""
<div style="
    display:flex; align-items:center; gap:12px;
    margin: 20px 0 16px 0;
">
    <div style="flex:1; height:1px; background:linear-gradient(90deg,transparent,rgba(0,210,255,0.25));"></div>
    <div style="
        font-family:'JetBrains Mono',monospace;
        font-size:0.65rem;
        letter-spacing:0.18em;
        text-transform:uppercase;
        color:rgba(0,210,255,0.45);
        white-space:nowrap;
    ">{label}</div>
    <div style="flex:1; height:1px; background:linear-gradient(90deg,rgba(0,210,255,0.25),transparent);"></div>
</div>
""", unsafe_allow_html=True)
    else:
        st.markdown("""
<div style="height:1px; background:linear-gradient(90deg,transparent,rgba(0,210,255,0.20),transparent); margin:16px 0;"></div>
""", unsafe_allow_html=True)


def alert_box(message: str, kind: str = "info") -> None:
    """Render a styled alert box. kind: info|warning|error|success"""
    configs = {
        "info":    ("#00D4FF", "rgba(0,212,255,0.07)", "ℹ"),
        "warning": ("#FFB800", "rgba(255,184,0,0.07)", "⚠"),
        "error":   ("#FF3B3B", "rgba(255,59,59,0.07)", "✕"),
        "success": ("#00FF85", "rgba(0,255,133,0.07)", "✓"),
    }
    color, bg, icon = configs.get(kind, configs["info"])
    st.markdown(f"""
<div style="
    background:{bg};
    border:1px solid {color}40;
    border-left:3px solid {color};
    border-radius:4px;
    padding:12px 16px;
    display:flex;
    align-items:flex-start;
    gap:12px;
    margin:8px 0;
">
    <span style="color:{color};font-size:1rem;flex-shrink:0;">{icon}</span>
    <span style="
        font-family:'Rajdhani',sans-serif;
        font-size:0.88rem;
        letter-spacing:0.03em;
        color:rgba(216,238,248,0.90);
        line-height:1.5;
    ">{message}</span>
</div>
""", unsafe_allow_html=True)


def trajectory_card(rank: int, entry: tuple, target: tuple,
                    length_mm: float, score: float, warnings: list) -> None:
    """Render a single surgical trajectory card."""
    rank_colors = ["#00FF85", "#FFB800", "#FF3B3B"]
    rank_labels = ["PRIMARY", "SECONDARY", "TERTIARY"]
    color = rank_colors[min(rank, 2)]
    label = rank_labels[min(rank, 2)]
    score_pct = int(score * 100)
    warn_html = "".join(
        f'<div style="font-size:0.73rem;color:#FFB800;margin-top:3px;">⚠ {w}</div>'
        for w in warnings
    ) if warnings else '<div style="font-size:0.73rem;color:#00FF85;">✓ No critical structures in path</div>'

    st.markdown(f"""
<div style="
    background:rgba(4,18,38,0.90);
    border:1px solid {color}30;
    border-left:3px solid {color};
    border-radius:6px;
    padding:14px 18px;
    margin-bottom:10px;
    position:relative;
">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <div style="
            font-family:'Rajdhani',sans-serif;
            font-size:0.72rem;
            font-weight:700;
            letter-spacing:0.18em;
            color:{color};
        ">TRAJECTORY {rank+1} — {label}</div>
        <div style="
            font-family:'JetBrains Mono',monospace;
            font-size:0.78rem;
            color:{color};
        ">SCORE {score_pct}/100</div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:10px;">
        <div>
            <div style="font-family:'Rajdhani',sans-serif;font-size:0.65rem;letter-spacing:0.12em;text-transform:uppercase;color:rgba(0,212,255,0.45);margin-bottom:3px;">PATH LENGTH</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:1.1rem;color:#D8EEF8;">{length_mm:.1f}<span style="font-size:0.75rem;opacity:0.6;"> mm</span></div>
        </div>
        <div>
            <div style="font-family:'Rajdhani',sans-serif;font-size:0.65rem;letter-spacing:0.12em;text-transform:uppercase;color:rgba(0,212,255,0.45);margin-bottom:3px;">SAFETY</div>
            <div style="height:6px;background:rgba(255,255,255,0.08);border-radius:3px;overflow:hidden;margin-top:6px;">
                <div style="width:{score_pct}%;height:100%;background:{color};border-radius:3px;"></div>
            </div>
        </div>
    </div>
    <div style="border-top:1px solid rgba(0,212,255,0.10);padding-top:8px;">
        {warn_html}
    </div>
</div>
""", unsafe_allow_html=True)
