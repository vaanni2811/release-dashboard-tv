"""Home dashboard theme, colors, and layout constants."""

from __future__ import annotations

# Semantic palette — vivid, high-contrast
COLOR_GREEN = "#00e676"
COLOR_YELLOW = "#ffea00"
COLOR_ORANGE = "#ff9100"
COLOR_RED = "#ff1744"
COLOR_BLUE = "#448aff"
COLOR_TEAL = "#00e5ff"
COLOR_PURPLE = "#e040fb"
COLOR_SLATE = "#78909c"
COLOR_PINK = "#ff4081"
COLOR_LIME = "#c6ff00"

CHART_PALETTE: tuple[str, ...] = (
    "#448aff",
    "#00e676",
    "#ff9100",
    "#ff1744",
    "#00e5ff",
    "#ffea00",
    "#e040fb",
    "#ff4081",
    "#18ffff",
    "#76ff03",
)

STATUS_PIE_COLORS: dict[str, str] = {
    "Open": "#448aff",
    "In Progress": "#2979ff",
    "Blocked": "#ff1744",
    "Ready To Close": "#ffea00",
    "Closed": "#00e676",
}

SIDE_DONUT_COLORS: dict[str, str] = {
    "FC": "#00e5ff",
    "WM": "#e040fb",
    "Both": "#ff4081",
}

PATCH_TYPE_BAR_COLORS: dict[str, str] = {
    "Weekly Hotfix": COLOR_BLUE,
    "Urgent Hotfix": COLOR_RED,
    "Demo UAT Patch": COLOR_PURPLE,
    "Release Patch": COLOR_TEAL,
}

CARD_ACCENTS: dict[str, str] = {
    "default": COLOR_BLUE,
    "open": COLOR_BLUE,
    "uat": COLOR_ORANGE,
    "stage": COLOR_YELLOW,
    "queries": COLOR_PURPLE,
    "blocked": COLOR_RED,
    "ready": COLOR_GREEN,
    "closed": COLOR_TEAL,
    "urgent": COLOR_PINK,
}

INSIGHT_TONES: dict[str, str] = {
    "info": COLOR_BLUE,
    "warning": COLOR_YELLOW,
    "risk": COLOR_ORANGE,
    "critical": COLOR_RED,
    "healthy": COLOR_GREEN,
}

PAGE_TITLE = "Release & Patch Command Center"
PAGE_SUBTITLE = (
    "Operational snapshot from Patch Lifecycle — open the tracker for edits and detail."
)

CHART_HEIGHT = 380
CHART_FONT = "Inter, Segoe UI, Roboto, Helvetica, Arial, sans-serif"

PLOTLY_LAYOUT_DEFAULTS: dict = {
    "font": {"family": CHART_FONT, "size": 13, "color": "#37474f"},
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "margin": {"l": 24, "r": 24, "t": 48, "b": 24},
    "title": {"text": "", "font": {"size": 16, "color": "#263238"}},
    "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
    "xaxis": {"title": {"text": ""}},
    "yaxis": {"title": {"text": ""}},
}

TYPE_FILTER_OPTIONS: tuple[tuple[str, str], ...] = (
    ("All types", "All"),
    ("Weekly Hotfix", "Weekly Hotfix"),
    ("Urgent Hotfix", "Urgent Hotfix"),
    ("Demo UAT", "Demo UAT Patch"),
    ("Release Patch", "Release Patch"),
)
