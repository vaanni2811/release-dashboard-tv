"""Table display helpers — status icons and column layout."""

from __future__ import annotations

import pandas as pd

import config


def fc_lifecycle_table_columns() -> tuple[tuple[str, str], ...]:
    return (
        ("Production", config.LIFECYCLE_FIELD_PRODUCTION),
        ("Release Branch", config.LIFECYCLE_FIELD_RELEASE_BRANCH),
        ("Prod Branch", config.LIFECYCLE_FIELD_PROD_BRANCH),
        ("Stage Query", config.LIFECYCLE_FIELD_STAGE_QUERY),
        ("UAT Query", config.LIFECYCLE_FIELD_UAT_QUERY),
        ("UAT Deploy", config.LIFECYCLE_FIELD_UAT_DEPLOYMENT),
        ("QA Verify", config.LIFECYCLE_FIELD_QA),
    )


def wm_lifecycle_table_columns() -> tuple[tuple[str, str], ...]:
    return (
        ("Hotfix Branch", config.WM_LIFECYCLE_FIELD_HOTFIX_BRANCH),
        ("Master / Production", config.WM_LIFECYCLE_FIELD_MASTER_PRODUCTION),
        ("Release Branch", config.WM_LIFECYCLE_FIELD_RELEASE_BRANCH),
        ("Integration / Stage", config.WM_LIFECYCLE_FIELD_INTEGRATION_STAGE),
        ("UAT Branch", config.WM_LIFECYCLE_FIELD_UAT_BRANCH),
        ("Stage Query", config.WM_LIFECYCLE_FIELD_STAGE_QUERY),
        ("UAT Query", config.WM_LIFECYCLE_FIELD_UAT_QUERY),
        ("QA Verify", config.WM_LIFECYCLE_FIELD_QA),
    )


def lifecycle_table_columns(side_filter: str = config.SIDE_FILTER_FC) -> tuple[tuple[str, str], ...]:
    """Lifecycle columns for the active side tab."""
    if side_filter == config.SIDE_FILTER_WM:
        return wm_lifecycle_table_columns()
    return fc_lifecycle_table_columns()


# Backwards-compatible alias for imports/tests.
LIFECYCLE_TABLE_COLUMNS = fc_lifecycle_table_columns()


def patch_side_label(patch_side: str) -> str:
    return config.PATCH_SIDE_LABELS.get(patch_side, patch_side.upper())


STATUS_ICONS: dict[str, str] = {
    config.STATUS_NOT_REQUIRED: "➖",
    config.STATUS_PENDING: "🟡",
    config.STATUS_IN_PROGRESS: "🔵",
    config.STATUS_COMPLETED: "✅",
    config.STATUS_BLOCKED: "🚫",
    config.STATUS_FAILED: "❌",
    config.STATUS_SKIPPED: "⏭️",
}

STATUS_LEGEND = (
    "➖ Not Required · 🟡 Pending · 🔵 In Progress · ✅ Completed · "
    "🚫 Blocked · ❌ Failed · ⏭️ Skipped · "
    "Rows: green = all done · red = cancelled / reverted"
)

PATCH_ROW_STYLES: dict[str, str] = {
    "negative": (
        "background-color: #efb0b0; "
        "color: #4a1212; "
        "border-top: 1px solid #d98585; "
        "border-bottom: 1px solid #d98585;"
    ),
    "complete": (
        "background-color: #8fd19e; "
        "color: #0f3318; "
        "border-top: 1px solid #5fb872; "
        "border-bottom: 1px solid #5fb872;"
    ),
}


def style_patch_dataframe(
    df: pd.DataFrame,
    row_tones: list[str | None],
) -> pd.io.formats.style.Styler:
    """Apply soft row backgrounds for cancelled/reverted and fully closed patches."""

    def _row_style(row: pd.Series) -> list[str]:
        tone = row_tones[row.name] if row.name < len(row_tones) else None
        css = PATCH_ROW_STYLES.get(tone or "", "")
        if css:
            return [css] * len(row)
        return [""] * len(row)

    return df.style.apply(_row_style, axis=1)


def status_icon(status: str) -> str:
    """Single-cell icon for lifecycle status."""
    return STATUS_ICONS.get(status, "❓")


def status_cell(status: str) -> str:
    """Icon + short label for tooltips / wide mode."""
    icon = status_icon(status)
    if status == config.STATUS_NOT_REQUIRED:
        return icon
    short = status.replace("Not Required", "N/R").replace("In Progress", "WIP")
    return f"{icon} {short}" if len(short) <= 12 else icon


def status_table_cell(status: str) -> str:
    """Readable label for table cells (icon + status text)."""
    if not status:
        status = config.STATUS_NOT_REQUIRED
    icon = status_icon(status)
    return f"{icon} {status}"


def detail_lifecycle_sections(patch_side: str) -> tuple[tuple[str, tuple[tuple[str, str], ...]], ...]:
    """Sections shown on patch detail (FC and/or WM)."""
    sections: list[tuple[str, tuple[tuple[str, str], ...]]] = []
    if patch_side in (config.PATCH_SIDE_FC, config.PATCH_SIDE_BOTH):
        sections.append(("FC lifecycle", fc_lifecycle_table_columns()))
    if patch_side in (config.PATCH_SIDE_WM, config.PATCH_SIDE_BOTH):
        sections.append(("WM lifecycle", wm_lifecycle_table_columns()))
    return tuple(sections)
