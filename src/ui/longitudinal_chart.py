"""
longitudinal_chart.py — Tumour volume trend chart with RANO annotations.

Produces an interactive Plotly line chart showing WT / TC / ET volumes
across multiple timepoints.  RANO category boundaries are drawn as
shaded bands so clinicians can immediately see response classification.

Usage
-----
    from src.ui.longitudinal_chart import build_volume_trend_chart
    fig = build_volume_trend_chart(days=[0, 45, 90, 180], wt=[15000, 12000, 8000, 6000],
                                   tc=[8000, 6000, 4000, 3000], et=[3000, 2500, 1500, 1200])
    fig.show()
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import plotly.graph_objects as go

# Region colour scheme matching the 3D viewer
_REGION_COLOURS = {
    "WT": "#4FC3F7",   # light blue
    "TC": "#FFB74D",   # orange
    "ET": "#EF5350",   # red
}


def build_volume_trend_chart(
    days: List[float],
    wt: List[float],
    tc: List[float],
    et: List[float],
    subject_id: str = "Subject",
    rano_categories: Optional[List[str]] = None,
) -> go.Figure:
    """
    Build a Plotly line chart of tumour sub-region volumes over time.

    Parameters
    ----------
    days            : list of elapsed days from baseline (must be ascending).
    wt, tc, et      : volumes in mm³ for Whole Tumour, Tumour Core, Enhancing Tumour.
    subject_id      : label for the figure title.
    rano_categories : optional list of RANO labels ("CR","PR","SD","PD") per
                      timepoint (same length as days).  Displayed as markers.

    Returns
    -------
    plotly.graph_objects.Figure
    """
    if not (len(days) == len(wt) == len(tc) == len(et)):
        raise ValueError("days, wt, tc, et must all have the same length.")
    if len(days) < 1:
        raise ValueError("At least one timepoint is required.")

    traces = []

    for region_name, values, colour in [
        ("WT (Whole Tumour)", wt, _REGION_COLOURS["WT"]),
        ("TC (Tumour Core)", tc, _REGION_COLOURS["TC"]),
        ("ET (Enhancing)", et, _REGION_COLOURS["ET"]),
    ]:
        traces.append(go.Scatter(
            x=days,
            y=values,
            mode="lines+markers",
            name=region_name,
            line=dict(color=colour, width=2.5),
            marker=dict(size=8, symbol="circle"),
            hovertemplate=f"<b>{region_name}</b><br>Day %{{x}}<br>Volume: %{{y:,.0f}} mm³<extra></extra>",
        ))

    # RANO category annotations as vertical dashed lines
    rano_colours = {"CR": "#66BB6A", "PR": "#42A5F5", "SD": "#FFA726", "PD": "#EF5350"}
    shapes = []
    annotations = []

    if rano_categories and len(rano_categories) == len(days):
        for day, category in zip(days[1:], rano_categories[1:]):  # skip baseline
            col = rano_colours.get(category, "gray")
            shapes.append(dict(
                type="line",
                x0=day, x1=day, y0=0, y1=1,
                xref="x", yref="paper",
                line=dict(color=col, width=1.5, dash="dot"),
            ))
            annotations.append(dict(
                x=day, y=1.02, xref="x", yref="paper",
                text=category, showarrow=False,
                font=dict(color=col, size=11),
            ))

    fig = go.Figure(data=traces)
    fig.update_layout(
        title=dict(
            text=f"Tumour Volume Trend — {subject_id}",
            x=0.5, font=dict(size=15, color="white"),
        ),
        xaxis=dict(
            title="Days from Baseline",
            gridcolor="rgba(255,255,255,0.1)",
            zeroline=False,
            color="white",
        ),
        yaxis=dict(
            title="Volume (mm³)",
            gridcolor="rgba(255,255,255,0.1)",
            zeroline=False,
            color="white",
        ),
        legend=dict(
            bgcolor="rgba(30,30,40,0.8)",
            bordercolor="gray",
            font=dict(color="white"),
        ),
        paper_bgcolor="rgb(15,15,25)",
        plot_bgcolor="rgb(20,20,35)",
        shapes=shapes,
        annotations=annotations,
        hovermode="x unified",
        margin=dict(l=60, r=20, t=60, b=60),
    )
    return fig


def build_rano_summary_bar(
    subjects: List[str],
    categories: List[str],
) -> go.Figure:
    """
    Build a Plotly horizontal bar chart summarising RANO responses across subjects.

    Parameters
    ----------
    subjects   : list of subject IDs.
    categories : list of RANO category strings ("CR","PR","SD","PD").

    Returns
    -------
    plotly.graph_objects.Figure
    """
    if len(subjects) != len(categories):
        raise ValueError("subjects and categories must have the same length.")

    colour_map = {"CR": "#66BB6A", "PR": "#42A5F5", "SD": "#FFA726", "PD": "#EF5350"}
    bar_colours = [colour_map.get(c, "gray") for c in categories]

    # Count per category for the horizontal bars
    order = ["CR", "PR", "SD", "PD"]
    counts = {c: categories.count(c) for c in order}

    fig = go.Figure(go.Bar(
        x=[counts[c] for c in order],
        y=order,
        orientation="h",
        marker_color=[colour_map[c] for c in order],
        text=[counts[c] for c in order],
        textposition="outside",
    ))
    fig.update_layout(
        title=dict(text="RANO Response Summary", x=0.5, font=dict(color="white", size=14)),
        xaxis=dict(title="Number of Subjects", color="white",
                   gridcolor="rgba(255,255,255,0.1)"),
        yaxis=dict(color="white"),
        paper_bgcolor="rgb(15,15,25)",
        plot_bgcolor="rgb(20,20,35)",
        font=dict(color="white"),
        margin=dict(l=60, r=40, t=50, b=40),
        showlegend=False,
    )
    return fig


def build_delta_heatmap(
    subjects: List[str],
    days: List[float],
    wt_series: List[List[float]],
) -> go.Figure:
    """
    Build a heatmap of percentage WT volume change relative to baseline
    across multiple subjects and timepoints.

    Parameters
    ----------
    subjects  : subject IDs (rows).
    days      : elapsed days from baseline (columns, excluding day 0).
    wt_series : list of WT volume lists, one per subject (including baseline at idx 0).

    Returns
    -------
    plotly.graph_objects.Figure
    """
    if len(subjects) != len(wt_series):
        raise ValueError("subjects and wt_series must have the same length.")

    matrix = []
    for vols in wt_series:
        baseline = max(vols[0], 1.0)
        pct_changes = [(v - baseline) / baseline * 100 for v in vols[1:]]
        matrix.append(pct_changes)

    z = np.array(matrix, dtype=float)

    fig = go.Figure(go.Heatmap(
        z=z,
        x=[f"Day {d:.0f}" for d in days],
        y=subjects,
        colorscale=[
            [0.0, "#66BB6A"],   # green (shrinkage)
            [0.5, "#FAFAFA"],   # neutral
            [1.0, "#EF5350"],   # red (growth)
        ],
        zmid=0,
        colorbar=dict(title="ΔWT (%)", tickfont=dict(color="white"),
                      titlefont=dict(color="white")),
        hovertemplate="Subject: %{y}<br>%{x}<br>ΔWT: %{z:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text="Whole Tumour % Change from Baseline", x=0.5,
                   font=dict(color="white", size=14)),
        paper_bgcolor="rgb(15,15,25)",
        plot_bgcolor="rgb(20,20,35)",
        font=dict(color="white"),
        xaxis=dict(color="white"),
        yaxis=dict(color="white"),
        margin=dict(l=80, r=40, t=50, b=40),
    )
    return fig
