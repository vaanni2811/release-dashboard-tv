"""Detect Streamlit theme and return chart/CSS tokens for light vs dark."""

from __future__ import annotations

from typing import Any

import streamlit as st

import dashboard_config as dash_config


def is_dark_theme() -> bool:
    """True when Streamlit is using dark base theme."""
    try:
        theme = st.context.theme
        base = getattr(theme, "base", None)
        if base and str(base).lower() == "dark":
            return True
    except (AttributeError, RuntimeError, TypeError):
        pass
    try:
        base = st.get_option("theme.base")
        if base and str(base).lower() == "dark":
            return True
    except Exception:
        pass
    return False


def plotly_layout_defaults() -> dict[str, Any]:
    """Base Plotly layout tuned for the active Streamlit theme."""
    if is_dark_theme():
        text = "#e8eaed"
        title = "#fafafa"
        grid = "rgba(255,255,255,0.14)"
        return {
            "font": {"family": dash_config.CHART_FONT, "size": 13, "color": text},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)",
            "margin": {"l": 24, "r": 24, "t": 48, "b": 24},
            "title": {"font": {"size": 16, "color": title}},
            "legend": {
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.02,
                "xanchor": "right",
                "x": 1,
                "font": {"color": text},
            },
            "xaxis": {
                "gridcolor": grid,
                "zerolinecolor": grid,
                "tickfont": {"color": text},
                "title": {"font": {"color": title}},
            },
            "yaxis": {
                "gridcolor": grid,
                "zerolinecolor": grid,
                "tickfont": {"color": text},
                "title": {"font": {"color": title}},
            },
        }
    return dict(dash_config.PLOTLY_LAYOUT_DEFAULTS)


def plotly_outside_text_color() -> str:
    return "#fafafa" if is_dark_theme() else "#263238"


def plotly_gauge_axis_color() -> str:
    return "#b0b8c4" if is_dark_theme() else "#546e7a"
