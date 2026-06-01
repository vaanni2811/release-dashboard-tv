"""Business insight sentences for the Home dashboard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import dashboard_config as dash_config


@dataclass(frozen=True)
class Insight:
    message: str
    tone: str
    prefilter_key: str = ""


def build_insights(metrics: Any, *, side_filter: str) -> list[Insight]:
    """Generate rule-based insight cards from dashboard metrics."""
    m = metrics
    insights: list[Insight] = []

    if m.pending_uat > 0:
        insights.append(
            Insight(
                f"UAT carry-forward is pending for <strong>{m.pending_uat}</strong> patch{'es' if m.pending_uat != 1 else ''}.",
                "warning",
                "pending_uat",
            )
        )
    if m.urgent > 0:
        insights.append(
            Insight(
                f"<strong>{m.urgent}</strong> urgent patch{'es' if m.urgent != 1 else ''} still open.",
                "critical",
                "urgent",
            )
        )
    if side_filter in ("WM Patches", "All Patches") and m.pending_stage > 0:
        insights.append(
            Insight(
                f"WM has <strong>{m.pending_stage}</strong> patch{'es' if m.pending_stage != 1 else ''} pending stage / integration.",
                "warning",
                "pending_stage",
            )
        )
    if side_filter in ("FC Patches", "All Patches") and m.pending_release_branch > 0:
        insights.append(
            Insight(
                f"<strong>{m.pending_release_branch}</strong> patch{'es' if m.pending_release_branch != 1 else ''} pending release branch update.",
                "risk",
                "pending_release_branch",
            )
        )
    if m.pending_queries > 0:
        insights.append(
            Insight(
                f"<strong>{m.pending_queries}</strong> patch{'es' if m.pending_queries != 1 else ''} have pending DB queries.",
                "warning",
                "pending_queries",
            )
        )
    if m.pending_production_master > 0:
        insights.append(
            Insight(
                f"<strong>{m.pending_production_master}</strong> patch{'es' if m.pending_production_master != 1 else ''} pending production / master merge.",
                "risk",
                "pending_production",
            )
        )
    if m.blocked > 0:
        insights.append(
            Insight(
                f"<strong>{m.blocked}</strong> patch{'es' if m.blocked != 1 else ''} blocked or at risk.",
                "critical",
                "blocked",
            )
        )

    readiness = m.release_readiness_pct
    if m.patches_in_scope == 0:
        insights.append(
            Insight(
                "No patches in the current filter scope — create patches in Patch Lifecycle to populate this dashboard.",
                "info",
            )
        )
    elif readiness >= 90:
        insights.append(
            Insight(
                f"Current release readiness is <strong>{readiness:.0f}%</strong> — on track.",
                "healthy",
            )
        )
    else:
        drift = "High" if readiness < 60 else "Medium" if readiness < 85 else "Low"
        insights.append(
            Insight(
                f"Current release readiness is <strong>{readiness:.0f}%</strong>. Branch drift risk: <strong>{drift}</strong>.",
                "risk" if readiness < 85 else "info",
            )
        )
        insights.append(
            Insight(
                f"UAT readiness <strong>{m.uat_readiness_pct:.0f}%</strong> · Stage readiness <strong>{m.stage_readiness_pct:.0f}%</strong>.",
                "info",
            )
        )

    if m.ready_to_close > 0:
        insights.append(
            Insight(
                f"<strong>{m.ready_to_close}</strong> patch{'es' if m.ready_to_close != 1 else ''} ready to close.",
                "healthy",
                "ready_to_close",
            )
        )

    return insights[:8]


def insight_border_color(tone: str) -> str:
    return dash_config.INSIGHT_TONES.get(tone, dash_config.COLOR_BLUE)
