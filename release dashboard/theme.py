"""Detect Streamlit theme and return chart/CSS tokens for light vs dark."""

from __future__ import annotations

from typing import Any

import dashboard_config as dash_config
from ui_styles import content_palette, is_dark_theme


def plotly_text_color() -> str:
    """Primary chart text — follows Streamlit theme when available."""
    try:
        import streamlit as st

        theme = st.context.theme
        for name in ("textColor", "text_color"):
            val = getattr(theme, name, None)
            if val:
                return str(val)
    except (AttributeError, RuntimeError, TypeError):
        pass
    return "#fafafa" if is_dark_theme() else "#263238"


def plotly_layout_defaults() -> dict[str, Any]:
    """Base Plotly layout tuned for the active Streamlit theme."""
    text = plotly_text_color()
    title = text if is_dark_theme() else "#263238"
    grid = "rgba(255,255,255,0.14)" if is_dark_theme() else "rgba(0,0,0,0.06)"
    axis_title = {"text": "", "font": {"color": title}}
    axis = {
        "gridcolor": grid,
        "zerolinecolor": grid,
        "tickfont": {"color": text},
        "title": axis_title,
    }
    return {
        "font": {"family": dash_config.CHART_FONT, "size": 13, "color": text},
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "margin": {"l": 24, "r": 24, "t": 48, "b": 24},
        "title": {"text": "", "font": {"size": 16, "color": title}},
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1,
            "font": {"color": text},
        },
        "xaxis": dict(axis),
        "yaxis": dict(axis),
    }


def plotly_outside_text_color() -> str:
    return plotly_text_color()


def plotly_gauge_axis_color() -> str:
    if is_dark_theme():
        return "#b0b8c4"
    return "#546e7a"


def dashboard_palette() -> dict[str, str]:
    """Text palette for home dashboard panels."""
    return content_palette()
