"""Shared accent-gradient panel styles for all Release Dashboard pages."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import streamlit as st

DEFAULT_ACCENT = "#448aff"

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.append(str(_ROOT))


def _theme_value(*names: str) -> str | None:
    try:
        theme = st.context.theme
        for name in names:
            val = getattr(theme, name, None)
            if val:
                return str(val)
    except (AttributeError, RuntimeError, TypeError):
        pass
    return None


def _parse_rgb(color: str) -> tuple[int, int, int] | None:
    color = color.strip().lower()
    if color.startswith("#"):
        h = color.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        if len(h) >= 6:
            return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    match = re.match(r"rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", color)
    if match:
        return int(match.group(1)), int(match.group(2)), int(match.group(3))
    return None


def _color_is_dark(color: str) -> bool:
    rgb = _parse_rgb(color)
    if rgb is None:
        return False
    r, g, b = rgb
    lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return lum < 0.45


def is_dark_theme() -> bool:
    base = _theme_value("base")
    if base and base.lower() == "dark":
        return True
    bg = _theme_value("backgroundColor", "background_color")
    if bg and _color_is_dark(bg):
        return True
    try:
        option_base = st.get_option("theme.base")
        if option_base and str(option_base).lower() == "dark":
            return True
    except Exception:
        pass
    return False


def accent_gradient_style(accent: str = DEFAULT_ACCENT, *, dark: bool | None = None) -> str:
    """Inline CSS: accent-tinted gradient background + matching border (option 1)."""
    rgb = _parse_rgb(accent) or (68, 138, 255)
    r, g, b = rgb
    dark = is_dark_theme() if dark is None else dark
    if dark:
        bg = (
            f"linear-gradient(135deg, rgba({r},{g},{b},0.26) 0%, "
            f"rgba({r},{g},{b},0.10) 42%, rgba({r},{g},{b},0.03) 100%)"
        )
        border = f"rgba({r},{g},{b},0.40)"
    else:
        bg = (
            f"linear-gradient(135deg, rgba({r},{g},{b},0.17) 0%, "
            f"rgba({r},{g},{b},0.06) 42%, rgba(255,255,255,0) 100%)"
        )
        border = f"rgba({r},{g},{b},0.28)"
    return f"background:{bg}; border-color:{border};"


def content_palette() -> dict[str, str]:
    """Text colors for panels (backgrounds come from accent_gradient_style)."""
    if is_dark_theme():
        return {
            "label": "#90caf9",
            "value": "#ffffff",
            "body": "#f5f5f5",
            "section": "#82b1ff",
            "heading": "#fafafa",
            "shadow": "0 2px 10px rgba(0,0,0,0.35)",
        }
    return {
        "label": "#5c6bc0",
        "value": "#1a237e",
        "body": "#283593",
        "section": "#1565c0",
        "heading": "#31333f",
        "shadow": "0 2px 10px rgba(21, 101, 192, 0.10)",
    }


def _gradient_css(r: int, g: int, b: int, *, dark: bool, strong: float = 1.0) -> str:
    if dark:
        return (
            f"linear-gradient(135deg, rgba({r},{g},{b},{0.22 * strong}) 0%, "
            f"rgba({r},{g},{b},{0.07 * strong}) 48%, transparent 100%)"
        )
    return (
        f"linear-gradient(135deg, rgba({r},{g},{b},{0.14 * strong}) 0%, "
        f"rgba({r},{g},{b},{0.04 * strong}) 48%, transparent 100%)"
    )


def inject_global_styles() -> None:
    """Accent-gradient styling for custom panels and native Streamlit widgets."""
    dark = is_dark_theme()
    p = content_palette()
    r, g, b = 68, 138, 255  # default blue
    panel_bg = _gradient_css(r, g, b, dark=dark)
    panel_border = f"rgba({r},{g},{b},{0.38 if dark else 0.22})"

    # Semantic alert accents
    info = _parse_rgb("#448aff") or (68, 138, 255)
    ok = _parse_rgb("#00e676") or (0, 230, 118)
    warn = _parse_rgb("#ff9100") or (255, 145, 0)
    err = _parse_rgb("#ff1744") or (255, 23, 68)

    st.markdown(
        f"""
        <style>
            .app-accent-panel {{
                border-radius: 12px;
                border: 1px solid {panel_border};
                border-left: 5px solid var(--accent, {DEFAULT_ACCENT});
                box-shadow: {p["shadow"]};
            }}

            [data-testid="stMetric"] {{
                background: {_gradient_css(r, g, b, dark=dark, strong=0.85)};
                border: 1px solid {panel_border};
                border-radius: 10px;
                padding: 0.55rem 0.75rem;
            }}

            [data-testid="stExpander"] details {{
                background: {panel_bg};
                border: 1px solid {panel_border};
                border-radius: 10px;
            }}

            [data-testid="stExpander"] summary {{
                border-radius: 10px;
            }}

            div[data-testid="stAlert"][data-baseweb="notification"] {{
                border-radius: 10px;
                border-width: 1px;
                border-style: solid;
            }}

            div[data-testid="stAlert"][kind="info"] {{
                background: {_gradient_css(*info, dark=dark)} !important;
                border-color: rgba({info[0]},{info[1]},{info[2]},{0.35 if dark else 0.25}) !important;
            }}
            div[data-testid="stAlert"][kind="success"] {{
                background: {_gradient_css(*ok, dark=dark)} !important;
                border-color: rgba({ok[0]},{ok[1]},{ok[2]},{0.35 if dark else 0.25}) !important;
            }}
            div[data-testid="stAlert"][kind="warning"] {{
                background: {_gradient_css(*warn, dark=dark)} !important;
                border-color: rgba({warn[0]},{warn[1]},{warn[2]},{0.35 if dark else 0.25}) !important;
            }}
            div[data-testid="stAlert"][kind="error"] {{
                background: {_gradient_css(*err, dark=dark)} !important;
                border-color: rgba({err[0]},{err[1]},{err[2]},{0.35 if dark else 0.25}) !important;
            }}

            [data-testid="stForm"] {{
                background: {_gradient_css(r, g, b, dark=dark, strong=0.6)};
                border: 1px solid {panel_border};
                border-radius: 12px;
                padding: 0.75rem 1rem;
            }}

            .stCodeBlock, [data-testid="stCodeBlock"] {{
                border-radius: 10px;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )
