"""Patch Lifecycle analytics for the Home command center (no Streamlit)."""

from __future__ import annotations

import os
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any

import config
import db
import repository
from logic import (
    closure_field_for_track,
    is_track_closed,
    lifecycle_tracks_for_view,
    patch_side_matches_filter,
    resolve_patch_status_display,
)

_OPEN_STATUSES = frozenset({config.STATUS_PENDING, config.STATUS_IN_PROGRESS})
_BLOCKED_STATUSES = frozenset({config.STATUS_BLOCKED, config.STATUS_FAILED})
_INACTIVE_OVERRIDES = config.NEGATIVE_MANUAL_OVERRIDES | frozenset({"Duplicate"})
_BLOCKED_OVERRIDES = frozenset(
    {"Blocked by Dev", "Blocked by QA", "On Hold"}
)

DATE_THIS_WEEK = "This Week"
DATE_THIS_MONTH = "This Month"
DATE_CURRENT_RELEASE = "Current Release"
DATE_CUSTOM = "Custom Range"
DATE_ALL = "All Time"

DATE_PRESETS: tuple[str, ...] = (
    DATE_THIS_WEEK,
    DATE_THIS_MONTH,
    DATE_CURRENT_RELEASE,
    DATE_CUSTOM,
    DATE_ALL,
)

TYPE_FILTER_ALL = "All"


@dataclass(frozen=True)
class DashboardFilters:
    side_filter: str = config.SIDE_FILTER_FC
    date_preset: str = DATE_ALL
    patch_type: str = TYPE_FILTER_ALL
    custom_start: date | None = None
    custom_end: date | None = None
    current_release: str = ""


@dataclass
class AnalyticsPatch:
    id: int
    patch_id: str
    patch_type: str
    priority: str
    patch_side: str
    developer_name: str
    branch_name: str
    release_name: str
    created_at: datetime
    updated_at: datetime
    manual_status_override: str | None
    lifecycle: dict[str, str]
    fc_status: str
    wm_status: str
    query_count: int


@dataclass
class DashboardMetrics:
    total_open: int = 0
    weekly_hotfix: int = 0
    urgent: int = 0
    release: int = 0
    demo_uat: int = 0
    pending_stage: int = 0
    pending_uat: int = 0
    pending_release_branch: int = 0
    pending_production_master: int = 0
    pending_queries: int = 0
    ready_to_close: int = 0
    blocked: int = 0
    closed_this_month: int = 0
    status_pie: dict[str, int] = field(default_factory=dict)
    patch_type_counts: dict[str, int] = field(default_factory=dict)
    side_distribution: dict[str, int] = field(default_factory=dict)
    pending_actions: dict[str, int] = field(default_factory=dict)
    aging_buckets: dict[str, int] = field(default_factory=dict)
    weekly_created: dict[str, int] = field(default_factory=dict)
    weekly_closed: dict[str, int] = field(default_factory=dict)
    developer_total: dict[str, int] = field(default_factory=dict)
    developer_open: dict[str, int] = field(default_factory=dict)
    developer_blocked: dict[str, int] = field(default_factory=dict)
    release_readiness_pct: float = 0.0
    uat_readiness_pct: float = 0.0
    stage_readiness_pct: float = 0.0
    patches_in_scope: int = 0


def _parse_dt(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _week_label(d: date) -> str:
    start = _week_start(d)
    return start.strftime("%d %b")


def _inactive(override: str | None) -> bool:
    return (override or "").strip() in _INACTIVE_OVERRIDES


def _primary_status(patch: AnalyticsPatch, side_filter: str) -> str:
    if side_filter == config.SIDE_FILTER_WM:
        return patch.wm_status
    return patch.fc_status


def _tracks_closed(patch: AnalyticsPatch, side_filter: str) -> bool:
    tracks = lifecycle_tracks_for_view(patch.patch_side, side_filter)
    if not tracks:
        return True
    return all(is_track_closed(patch.lifecycle, track) for track in tracks)


def _field_pending(lifecycle: dict[str, str], field: str) -> bool:
    return lifecycle.get(field, "") in _OPEN_STATUSES


def _pending_stage(patch: AnalyticsPatch, side_filter: str) -> bool:
    if side_filter == config.SIDE_FILTER_WM:
        return _field_pending(patch.lifecycle, config.WM_LIFECYCLE_FIELD_INTEGRATION_STAGE)
    if side_filter == config.SIDE_FILTER_ALL:
        if patch.patch_side == config.PATCH_SIDE_WM:
            return _field_pending(patch.lifecycle, config.WM_LIFECYCLE_FIELD_INTEGRATION_STAGE)
        return _field_pending(patch.lifecycle, config.LIFECYCLE_FIELD_UAT_DEPLOYMENT)
    return _field_pending(patch.lifecycle, config.LIFECYCLE_FIELD_UAT_DEPLOYMENT)


def _pending_uat(patch: AnalyticsPatch, side_filter: str) -> bool:
    if side_filter == config.SIDE_FILTER_WM:
        return (
            _field_pending(patch.lifecycle, config.WM_LIFECYCLE_FIELD_UAT_BRANCH)
            or _field_pending(patch.lifecycle, config.WM_LIFECYCLE_FIELD_UAT_QUERY)
        )
    if side_filter == config.SIDE_FILTER_ALL:
        fc = _field_pending(patch.lifecycle, config.LIFECYCLE_FIELD_UAT_DEPLOYMENT) or _field_pending(
            patch.lifecycle, config.LIFECYCLE_FIELD_UAT_QUERY
        )
        wm = _field_pending(patch.lifecycle, config.WM_LIFECYCLE_FIELD_UAT_BRANCH) or _field_pending(
            patch.lifecycle, config.WM_LIFECYCLE_FIELD_UAT_QUERY
        )
        if patch.patch_side == config.PATCH_SIDE_BOTH:
            return fc or wm
        if patch.patch_side == config.PATCH_SIDE_WM:
            return wm
        return fc
    return _field_pending(patch.lifecycle, config.LIFECYCLE_FIELD_UAT_DEPLOYMENT) or _field_pending(
        patch.lifecycle, config.LIFECYCLE_FIELD_UAT_QUERY
    )


def _pending_release_branch(patch: AnalyticsPatch, side_filter: str) -> bool:
    if side_filter == config.SIDE_FILTER_WM:
        return _field_pending(patch.lifecycle, config.WM_LIFECYCLE_FIELD_RELEASE_BRANCH)
    if side_filter == config.SIDE_FILTER_ALL and patch.patch_side == config.PATCH_SIDE_WM:
        return _field_pending(patch.lifecycle, config.WM_LIFECYCLE_FIELD_RELEASE_BRANCH)
    return _field_pending(patch.lifecycle, config.LIFECYCLE_FIELD_RELEASE_BRANCH)


def _pending_production_master(patch: AnalyticsPatch, side_filter: str) -> bool:
    if side_filter == config.SIDE_FILTER_WM:
        return _field_pending(patch.lifecycle, config.WM_LIFECYCLE_FIELD_MASTER_PRODUCTION)
    if side_filter == config.SIDE_FILTER_ALL and patch.patch_side == config.PATCH_SIDE_WM:
        return _field_pending(patch.lifecycle, config.WM_LIFECYCLE_FIELD_MASTER_PRODUCTION)
    return _field_pending(patch.lifecycle, config.LIFECYCLE_FIELD_PRODUCTION)


def _pending_queries(patch: AnalyticsPatch, side_filter: str) -> bool:
    fc_q = _field_pending(patch.lifecycle, config.LIFECYCLE_FIELD_STAGE_QUERY) or _field_pending(
        patch.lifecycle, config.LIFECYCLE_FIELD_UAT_QUERY
    )
    wm_q = _field_pending(patch.lifecycle, config.WM_LIFECYCLE_FIELD_STAGE_QUERY) or _field_pending(
        patch.lifecycle, config.WM_LIFECYCLE_FIELD_UAT_QUERY
    )
    if side_filter == config.SIDE_FILTER_WM:
        return wm_q or patch.query_count > 0 and wm_q
    if side_filter == config.SIDE_FILTER_FC:
        return fc_q or (patch.query_count > 0 and fc_q)
    if patch.patch_side == config.PATCH_SIDE_WM:
        return wm_q
    if patch.patch_side == config.PATCH_SIDE_BOTH:
        return fc_q or wm_q
    return fc_q or patch.query_count > 0


def _status_bucket(patch: AnalyticsPatch, side_filter: str) -> str:
    if _tracks_closed(patch, side_filter):
        return "Closed"
    override = (patch.manual_status_override or "").strip()
    if override in _BLOCKED_OVERRIDES:
        return "Blocked"
    lifecycle = patch.lifecycle
    tracks = lifecycle_tracks_for_view(patch.patch_side, side_filter)
    fields: list[str] = []
    for track in tracks:
        if track == config.PATCH_SIDE_WM:
            fields.extend(config.WM_LIFECYCLE_STATUS_ORDER)
        else:
            fields.extend(config.LIFECYCLE_STATUS_ORDER)
    if any(lifecycle.get(f, "") in _BLOCKED_STATUSES for f in fields):
        return "Blocked"
    status = _primary_status(patch, side_filter)
    if status == config.SYSTEM_STATUS_READY_TO_CLOSE:
        return "Ready To Close"
    if status == config.SYSTEM_STATUS_BLOCKED:
        return "Blocked"
    if any(lifecycle.get(f, "") == config.STATUS_IN_PROGRESS for f in fields):
        return "In Progress"
    return "Open"


def _is_open(patch: AnalyticsPatch, side_filter: str) -> bool:
    return not _inactive(patch.manual_status_override) and not _tracks_closed(patch, side_filter)


def _pending_action_fields(side_filter: str) -> tuple[tuple[str, str], ...]:
    if side_filter == config.SIDE_FILTER_WM:
        return (
            ("Pending Master / Production", config.WM_LIFECYCLE_FIELD_MASTER_PRODUCTION),
            ("Pending Release Branch", config.WM_LIFECYCLE_FIELD_RELEASE_BRANCH),
            ("Pending Hotfix Branch", config.WM_LIFECYCLE_FIELD_HOTFIX_BRANCH),
            ("Pending Stage", config.WM_LIFECYCLE_FIELD_INTEGRATION_STAGE),
            ("Pending UAT", config.WM_LIFECYCLE_FIELD_UAT_BRANCH),
            ("Pending Stage Query", config.WM_LIFECYCLE_FIELD_STAGE_QUERY),
            ("Pending UAT Query", config.WM_LIFECYCLE_FIELD_UAT_QUERY),
            ("Pending QA", config.WM_LIFECYCLE_FIELD_QA),
        )
    return (
        ("Pending Production", config.LIFECYCLE_FIELD_PRODUCTION),
        ("Pending Release Branch", config.LIFECYCLE_FIELD_RELEASE_BRANCH),
        ("Pending Prod Branch", config.LIFECYCLE_FIELD_PROD_BRANCH),
        ("Pending Stage", config.LIFECYCLE_FIELD_UAT_DEPLOYMENT),
        ("Pending UAT Query", config.LIFECYCLE_FIELD_UAT_QUERY),
        ("Pending Stage Query", config.LIFECYCLE_FIELD_STAGE_QUERY),
        ("Pending QA", config.LIFECYCLE_FIELD_QA),
    )


def _resolve_current_release(patches: list[AnalyticsPatch]) -> str:
    env_release = os.environ.get("CURRENT_RELEASE", "").strip()
    if env_release:
        return env_release
    from logic import branch_sort_key

    labels: list[str] = []
    for p in patches:
        label = (p.branch_name or p.release_name or "").strip()
        if label:
            labels.append(label)
    if not labels:
        return ""
    return sorted(labels, key=branch_sort_key, reverse=True)[0]


def _in_date_range(
    patch: AnalyticsPatch,
    *,
    preset: str,
    custom_start: date | None,
    custom_end: date | None,
    current_release: str,
) -> bool:
    if preset == DATE_ALL:
        return True
    created = patch.created_at.date()
    today = date.today()
    if preset == DATE_THIS_WEEK:
        start = _week_start(today)
        return start <= created <= today
    if preset == DATE_THIS_MONTH:
        start = today.replace(day=1)
        return start <= created <= today
    if preset == DATE_CURRENT_RELEASE:
        if not current_release:
            return True
        branch = (patch.branch_name or patch.release_name or "").strip().lower()
        return current_release.lower() in branch or branch in current_release.lower()
    if preset == DATE_CUSTOM and custom_start and custom_end:
        return custom_start <= created <= custom_end
    return True


def load_analytics_patches() -> list[AnalyticsPatch]:
    db.init_db()
    rows: list[AnalyticsPatch] = []
    with db.get_connection() as conn:
        patch_rows = conn.execute(
            """
            SELECT p.*,
                   (SELECT COUNT(*) FROM patch_queries q WHERE q.patch_id = p.id) AS query_count
            FROM patches p
            WHERE p.is_archived = 0
            ORDER BY p.id DESC
            """
        ).fetchall()
        for row in patch_rows:
            lc_row = repository.ensure_lifecycle_row(conn, row["id"], row)
            lifecycle = repository.lifecycle_row_to_dict(lc_row)
            fc_display = resolve_patch_status_display(
                lifecycle,
                row["manual_status_override"],
                track=config.PATCH_SIDE_FC,
            )
            wm_display = resolve_patch_status_display(
                lifecycle,
                row["manual_status_override"],
                track=config.PATCH_SIDE_WM,
            )
            rows.append(
                AnalyticsPatch(
                    id=row["id"],
                    patch_id=row["patch_id"],
                    patch_type=row["patch_type"],
                    priority=row["priority"] or config.PRIORITY_NORMAL,
                    patch_side=row["patch_side"] or config.PATCH_SIDE_FC,
                    developer_name=(row["developer_name"] or "").strip() or "Unassigned",
                    branch_name=row["branch_name"] or "",
                    release_name=row["release_name"] or "",
                    created_at=_parse_dt(row["created_at"]),
                    updated_at=_parse_dt(row["updated_at"]),
                    manual_status_override=(row["manual_status_override"] or "").strip() or None,
                    lifecycle=lifecycle,
                    fc_status=fc_display.system_status,
                    wm_status=wm_display.system_status,
                    query_count=int(row["query_count"] or 0),
                )
            )
    return rows


def compute_dashboard_metrics(filters: DashboardFilters) -> DashboardMetrics:
    all_patches = load_analytics_patches()
    current_release = filters.current_release or _resolve_current_release(all_patches)

    scoped: list[AnalyticsPatch] = []
    for patch in all_patches:
        if not patch_side_matches_filter(patch.patch_side, filters.side_filter):
            continue
        if filters.patch_type != TYPE_FILTER_ALL and patch.patch_type != filters.patch_type:
            continue
        if not _in_date_range(
            patch,
            preset=filters.date_preset,
            custom_start=filters.custom_start,
            custom_end=filters.custom_end,
            current_release=current_release,
        ):
            continue
        if _inactive(patch.manual_status_override):
            continue
        scoped.append(patch)

    metrics = DashboardMetrics(patches_in_scope=len(scoped))
    today = date.today()
    month_start = today.replace(day=1)

    pending_action_counter: Counter[str] = Counter()
    aging_counter: Counter[str] = Counter()
    weekly_created: Counter[str] = Counter()
    weekly_closed: Counter[str] = Counter()

    for patch in scoped:
        metrics.patch_type_counts[patch.patch_type] = (
            metrics.patch_type_counts.get(patch.patch_type, 0) + 1
        )
        side_label = config.PATCH_SIDE_LABELS.get(patch.patch_side, patch.patch_side)
        metrics.side_distribution[side_label] = metrics.side_distribution.get(side_label, 0) + 1

        bucket = _status_bucket(patch, filters.side_filter)
        metrics.status_pie[bucket] = metrics.status_pie.get(bucket, 0) + 1

        dev = patch.developer_name
        metrics.developer_total[dev] = metrics.developer_total.get(dev, 0) + 1

        open_patch = _is_open(patch, filters.side_filter)
        if open_patch:
            metrics.total_open += 1
            metrics.developer_open[dev] = metrics.developer_open.get(dev, 0) + 1

        if patch.patch_type == config.PATCH_TYPE_WEEKLY and open_patch:
            metrics.weekly_hotfix += 1
        if (
            patch.patch_type == config.PATCH_TYPE_URGENT or patch.priority == config.PRIORITY_URGENT
        ) and open_patch:
            metrics.urgent += 1
        if patch.patch_type == config.PATCH_TYPE_RELEASE and open_patch:
            metrics.release += 1
        if patch.patch_type == config.PATCH_TYPE_DEMO_UAT and open_patch:
            metrics.demo_uat += 1

        if open_patch and _pending_stage(patch, filters.side_filter):
            metrics.pending_stage += 1
        if open_patch and _pending_uat(patch, filters.side_filter):
            metrics.pending_uat += 1
        if open_patch and _pending_release_branch(patch, filters.side_filter):
            metrics.pending_release_branch += 1
        if open_patch and _pending_production_master(patch, filters.side_filter):
            metrics.pending_production_master += 1
        if open_patch and _pending_queries(patch, filters.side_filter):
            metrics.pending_queries += 1

        status = _primary_status(patch, filters.side_filter)
        if open_patch and status == config.SYSTEM_STATUS_READY_TO_CLOSE:
            metrics.ready_to_close += 1
        if bucket == "Blocked":
            metrics.blocked += 1
            metrics.developer_blocked[dev] = metrics.developer_blocked.get(dev, 0) + 1

        if _tracks_closed(patch, filters.side_filter) and patch.updated_at.date() >= month_start:
            metrics.closed_this_month += 1

        if open_patch:
            days = (datetime.now(timezone.utc) - patch.created_at).days
            if days <= 2:
                aging_counter["0–2 days"] += 1
            elif days <= 5:
                aging_counter["3–5 days"] += 1
            elif days <= 10:
                aging_counter["6–10 days"] += 1
            else:
                aging_counter["10+ days"] += 1

        for label, field_name in _pending_action_fields(filters.side_filter):
            if _field_pending(patch.lifecycle, field_name):
                pending_action_counter[label] += 1

        week_lbl = _week_label(patch.created_at.date())
        weekly_created[week_lbl] += 1
        if _tracks_closed(patch, filters.side_filter):
            weekly_closed[_week_label(patch.updated_at.date())] += 1

    metrics.pending_actions = dict(pending_action_counter)
    metrics.aging_buckets = dict(aging_counter)

    # Last 8 weeks for trend
    weeks: list[str] = []
    cursor = _week_start(today)
    for _ in range(8):
        weeks.insert(0, cursor.strftime("%d %b"))
        cursor -= timedelta(days=7)
    metrics.weekly_created = {w: weekly_created.get(w, 0) for w in weeks}
    metrics.weekly_closed = {w: weekly_closed.get(w, 0) for w in weeks}

    if scoped:
        closed_or_ready = metrics.status_pie.get("Closed", 0) + metrics.status_pie.get(
            "Ready To Close", 0
        )
        metrics.release_readiness_pct = round(100.0 * closed_or_ready / len(scoped), 1)

        uat_ready = sum(
            1
            for p in scoped
            if not _pending_uat(p, filters.side_filter) or _tracks_closed(p, filters.side_filter)
        )
        stage_ready = sum(
            1
            for p in scoped
            if not _pending_stage(p, filters.side_filter) or _tracks_closed(p, filters.side_filter)
        )
        metrics.uat_readiness_pct = round(100.0 * uat_ready / len(scoped), 1)
        metrics.stage_readiness_pct = round(100.0 * stage_ready / len(scoped), 1)

    for ptype in config.PATCH_TYPES:
        metrics.patch_type_counts.setdefault(ptype, 0)
    for label in ("FC", "WM", "Both"):
        metrics.side_distribution.setdefault(label, 0)
    for label in ("Open", "In Progress", "Blocked", "Ready To Close", "Closed"):
        metrics.status_pie.setdefault(label, 0)
    for label in ("0–2 days", "3–5 days", "6–10 days", "10+ days"):
        metrics.aging_buckets.setdefault(label, 0)

    return metrics
