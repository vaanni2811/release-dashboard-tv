"""Home dashboard theme, colors, and layout constants."""

from __future__ import annotations

# Semantic palette
COLOR_GREEN = "#2e7d32"
COLOR_YELLOW = "#f9a825"
COLOR_ORANGE = "#ef6c00"
COLOR_RED = "#c62828"
COLOR_BLUE = "#1565c0"
COLOR_TEAL = "#00897b"
COLOR_PURPLE = "#6a1b9a"
COLOR_SLATE = "#546e7a"

CHART_PALETTE: tuple[str, ...] = (
    "#4e79a7",
    "#59a14f",
    "#f28e2b",
    "#e15759",
    "#76b7b2",
    "#edc948",
    "#b07aa1",
    "#ff9da7",
    "#9c755f",
    "#bab0ac",
)

STATUS_PIE_COLORS: dict[str, str] = {
    "Open": "#42a5f5",
    "In Progress": "#1565c0",
    "Blocked": "#e53935",
    "Ready To Close": "#ffb300",
    "Closed": "#43a047",
}

SIDE_DONUT_COLORS: dict[str, str] = {
    "FC": COLOR_TEAL,
    "WM": COLOR_PURPLE,
    "Both": "#7e57c2",
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
    "urgent": COLOR_RED,
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
    "title": {"font": {"size": 16, "color": "#263238"}},
    "legend": {"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
}

TYPE_FILTER_OPTIONS: tuple[tuple[str, str], ...] = (
    ("All types", "All"),
    ("Weekly Hotfix", "Weekly Hotfix"),
    ("Urgent Hotfix", "Urgent Hotfix"),
    ("Demo UAT", "Demo UAT Patch"),
    ("Release Patch", "Release Patch"),
)
