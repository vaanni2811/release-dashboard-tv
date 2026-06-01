"""Table display helpers — status icons and column layout."""

from __future__ import annotations

import config

def lifecycle_table_columns() -> tuple[tuple[str, str], ...]:
    """Read column field keys from config at call time (safe after tool module reloads)."""
    return (
        ("Release Branch", config.LIFECYCLE_FIELD_RELEASE_BRANCH),
        ("Prod Branch", config.LIFECYCLE_FIELD_PROD_BRANCH),
        ("Production", config.LIFECYCLE_FIELD_PRODUCTION),
        ("Stage Query", config.LIFECYCLE_FIELD_STAGE_QUERY),
        ("UAT Query", config.LIFECYCLE_FIELD_UAT_QUERY),
        ("UAT Deploy", config.LIFECYCLE_FIELD_UAT_DEPLOYMENT),
        ("QA Verify", config.LIFECYCLE_FIELD_QA),
    )


# Backwards-compatible alias for imports/tests.
LIFECYCLE_TABLE_COLUMNS = lifecycle_table_columns()

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
    "🚫 Blocked · ❌ Failed · ⏭️ Skipped"
)


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
