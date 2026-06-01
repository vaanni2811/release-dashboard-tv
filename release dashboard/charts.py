"""Plotly chart builders for the Home command center."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
from plotly.subplots import make_subplots

import dashboard_config as dash_config
from theme import is_dark_theme, plotly_gauge_axis_color, plotly_layout_defaults, plotly_outside_text_color


def _grid_color() -> str:
    return "rgba(255,255,255,0.14)" if is_dark_theme() else "rgba(0,0,0,0.06)"


def _slice_line_color() -> str:
    return "rgba(255,255,255,0.35)" if is_dark_theme() else "#ffffff"


def _bar_line_color() -> str:
    return "rgba(255,255,255,0.12)" if is_dark_theme() else "rgba(0,0,0,0.08)"


def _base_layout(**overrides: Any) -> dict:
    layout = plotly_layout_defaults()
    layout.update(overrides)
    return layout


def _apply_layout(fig: go.Figure, **overrides: Any) -> None:
    """Apply layout as a single dict (avoids duplicate-kw errors in Plotly)."""
    fig.update_layout(_base_layout(**overrides))


def status_pie_chart(status_counts: dict[str, int]) -> go.Figure:
    labels = [k for k, v in status_counts.items() if v > 0]
    values = [status_counts[k] for k in labels]
    colors = [dash_config.STATUS_PIE_COLORS.get(k, dash_config.CHART_PALETTE[i % 10]) for i, k in enumerate(labels)]

    outside = plotly_outside_text_color()
    slice_line = _slice_line_color()
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.52,
                marker={"colors": colors, "line": {"color": slice_line, "width": 2}},
                textinfo="label+percent",
                textposition="outside",
                textfont={"color": outside, "size": 12},
                pull=[0.03 if lab == "Blocked" else 0 for lab in labels],
                hovertemplate="<b>%{label}</b><br>%{value} patches<br>%{percent}<extra></extra>",
            )
        ]
    )
    _apply_layout(fig, title="Patch Status", showlegend=False, height=dash_config.CHART_HEIGHT)
    return fig


def side_donut_chart(side_counts: dict[str, int]) -> go.Figure:
    labels = [k for k, v in side_counts.items() if v > 0]
    values = [side_counts[k] for k in labels]
    colors = [dash_config.SIDE_DONUT_COLORS.get(k, dash_config.CHART_PALETTE[i]) for i, k in enumerate(labels)]

    outside = plotly_outside_text_color()
    slice_line = _slice_line_color()
    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.58,
                marker={"colors": colors, "line": {"color": slice_line, "width": 2}},
                textinfo="label+value",
                textfont={"color": outside, "size": 12},
                hovertemplate="<b>%{label}</b><br>%{value} patches<extra></extra>",
            )
        ]
    )
    _apply_layout(fig, title="FC vs WM Distribution", showlegend=True, height=dash_config.CHART_HEIGHT)
    return fig


def pending_action_bar(pending: dict[str, int]) -> go.Figure:
    items = sorted(pending.items(), key=lambda x: x[1], reverse=True)
    labels = [k for k, v in items if v > 0] or ["No pending actions"]
    values = [pending[k] for k in labels] if items else [0]
    colors = [dash_config.COLOR_ORANGE if v >= 5 else dash_config.COLOR_YELLOW for v in values]

    text_color = plotly_outside_text_color()
    fig = go.Figure(
        data=[
            go.Bar(
                x=values,
                y=labels,
                orientation="h",
                marker={
                    "color": colors,
                    "line": {"color": _bar_line_color(), "width": 1},
                },
                text=values,
                textposition="outside",
                textfont={"color": text_color},
                hovertemplate="<b>%{y}</b><br>%{x} patches<extra></extra>",
            )
        ]
    )
    _apply_layout(
        fig,
        title="Pending Actions",
        height=dash_config.CHART_HEIGHT,
        xaxis={"title": "Patches", "gridcolor": _grid_color(), "zeroline": False},
        yaxis={"autorange": "reversed", "gridcolor": "rgba(0,0,0,0)"},
    )
    return fig


def patch_type_bar(type_counts: dict[str, int]) -> go.Figure:
    labels = list(type_counts.keys())
    values = [type_counts[k] for k in labels]
    short = [lab.replace(" Patch", "").replace(" Hotfix", "") for lab in labels]

    text_color = plotly_outside_text_color()
    fig = go.Figure(
        data=[
            go.Bar(
                x=short,
                y=values,
                marker={
                    "color": values,
                    "colorscale": [[0, "#90caf9"], [0.5, "#42a5f5"], [1, "#1565c0"]],
                    "line": {"color": _bar_line_color(), "width": 1},
                    "cornerradius": 6,
                },
                text=values,
                textposition="outside",
                textfont={"color": text_color},
                hovertemplate="<b>%{x}</b><br>%{y} patches<extra></extra>",
            )
        ]
    )
    _apply_layout(
        fig,
        title="Patches by Type",
        height=dash_config.CHART_HEIGHT,
        yaxis={"title": "Count", "gridcolor": _grid_color()},
        xaxis={"tickangle": -20},
    )
    return fig


def weekly_trend_chart(created: dict[str, int], closed: dict[str, int]) -> go.Figure:
    weeks = list(created.keys())
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=weeks,
            y=[created[w] for w in weeks],
            mode="lines+markers",
            name="Created",
            line={"color": dash_config.COLOR_BLUE, "width": 3, "shape": "spline"},
            marker={"size": 8, "line": {"width": 2, "color": "#fff"}},
            fill="tozeroy",
            fillcolor="rgba(21, 101, 192, 0.12)",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=weeks,
            y=[closed[w] for w in weeks],
            mode="lines+markers",
            name="Closed",
            line={"color": dash_config.COLOR_GREEN, "width": 3, "shape": "spline"},
            marker={"size": 8, "line": {"width": 2, "color": "#fff"}},
            fill="tozeroy",
            fillcolor="rgba(46, 125, 50, 0.10)",
        )
    )
    _apply_layout(
        fig,
        title="Weekly Patch Trend",
        height=dash_config.CHART_HEIGHT,
        hovermode="x unified",
        yaxis={"title": "Patches", "gridcolor": _grid_color()},
        xaxis={"title": "Week starting"},
    )
    return fig


def developer_workload_chart(
    total: dict[str, int],
    open_counts: dict[str, int],
    blocked: dict[str, int],
) -> go.Figure:
    devs = sorted(total.keys(), key=lambda d: total.get(d, 0), reverse=True)[:10]
    if not devs:
        devs = ["Unassigned"]

    total_color = "#607d8b" if is_dark_theme() else "#cfd8dc"
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="Open",
            x=devs,
            y=[open_counts.get(d, 0) for d in devs],
            marker={"color": dash_config.COLOR_BLUE, "cornerradius": 4},
        )
    )
    fig.add_trace(
        go.Bar(
            name="Blocked",
            x=devs,
            y=[blocked.get(d, 0) for d in devs],
            marker={"color": dash_config.COLOR_RED, "cornerradius": 4},
        )
    )
    fig.add_trace(
        go.Bar(
            name="Total in scope",
            x=devs,
            y=[total.get(d, 0) for d in devs],
            marker={"color": total_color, "cornerradius": 4},
        )
    )
    _apply_layout(
        fig,
        title="Developer Workload",
        barmode="group",
        height=dash_config.CHART_HEIGHT,
        yaxis={"title": "Patches", "gridcolor": _grid_color()},
        xaxis={"tickangle": -25},
    )
    return fig


def aging_chart(buckets: dict[str, int]) -> go.Figure:
    order = ["0–2 days", "3–5 days", "6–10 days", "10+ days"]
    values = [buckets.get(k, 0) for k in order]
    colors = [dash_config.COLOR_GREEN, dash_config.COLOR_YELLOW, dash_config.COLOR_ORANGE, dash_config.COLOR_RED]

    text_color = plotly_outside_text_color()
    fig = go.Figure(
        data=[
            go.Bar(
                x=order,
                y=values,
                marker={"color": colors, "cornerradius": 8, "line": {"width": 0}},
                text=values,
                textposition="outside",
                textfont={"color": text_color},
                hovertemplate="<b>%{x}</b><br>%{y} open patches<extra></extra>",
            )
        ]
    )
    _apply_layout(
        fig,
        title="Open Patch Aging",
        height=320,
        yaxis={"title": "Open patches", "gridcolor": _grid_color()},
    )
    return fig


def readiness_gauge(
    title: str,
    value: float,
    *,
    bar_color: str | None = None,
) -> go.Figure:
    color = bar_color or (dash_config.COLOR_GREEN if value >= 85 else dash_config.COLOR_ORANGE if value >= 60 else dash_config.COLOR_RED)
    label_color = plotly_outside_text_color()
    axis_color = plotly_gauge_axis_color()
    gauge_bg = "rgba(255,255,255,0.06)" if is_dark_theme() else "rgba(0,0,0,0.04)"
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=value,
            number={"suffix": "%", "font": {"size": 28, "color": label_color}},
            title={"text": title, "font": {"size": 14, "color": label_color}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 1, "tickcolor": axis_color},
                "bar": {"color": color, "thickness": 0.75},
                "bgcolor": gauge_bg,
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 60], "color": "rgba(229, 57, 53, 0.22)"},
                    {"range": [60, 85], "color": "rgba(255, 179, 0, 0.22)"},
                    {"range": [85, 100], "color": "rgba(67, 160, 71, 0.25)"},
                ],
                "threshold": {
                    "line": {"color": axis_color, "width": 2},
                    "thickness": 0.8,
                    "value": value,
                },
            },
        )
    )
    _apply_layout(
        fig,
        margin={"l": 30, "r": 30, "t": 60, "b": 10},
        height=260,
    )
    return fig


def readiness_row_gauges(release_pct: float, uat_pct: float, stage_pct: float) -> go.Figure:
    fig = make_subplots(
        rows=1,
        cols=3,
        specs=[[{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}]],
        subplot_titles=("Release Readiness", "UAT Readiness", "Stage Readiness"),
    )
    for col, (title, val) in enumerate(
        [("Release", release_pct), ("UAT", uat_pct), ("Stage", stage_pct)], start=1
    ):
        color = dash_config.COLOR_GREEN if val >= 85 else dash_config.COLOR_ORANGE if val >= 60 else dash_config.COLOR_RED
        fig.add_trace(
            go.Indicator(
                mode="gauge+number",
                value=val,
                number={"suffix": "%"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": color},
                    "bgcolor": "rgba(0,0,0,0.04)",
                    "borderwidth": 0,
                },
            ),
            row=1,
            col=col,
        )
    _apply_layout(fig, title="Release Readiness", height=280, showlegend=False)
    return fig
