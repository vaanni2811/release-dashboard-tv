"""Business rules: lifecycle defaults, validation, patch type changes."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, TypeVar

import config

T = TypeVar("T")

HOTFIX_BRANCH_RE = re.compile(r"^hotfix_r(\d{2})q(\d+)\.(\d+)$", re.IGNORECASE)
NO_BRANCH_LABEL = "— No branch —"


@dataclass
class CreatePatchOptions:
    """Inputs used when applying initial lifecycle defaults on create."""

    patch_type: str
    has_queries: bool = False
    # DB Query Patch
    db_linked_to_hotfix_prod: bool = False
    db_has_repo_change: bool = False
    db_query_part_of_deployable: bool = False
    # Configuration Patch
    config_applied_in_production: bool = False
    config_stored_in_repo: bool = False
    config_stored_in_prod_branch: bool = False
    config_must_apply_in_uat: bool = False


def _nr() -> str:
    return config.STATUS_NOT_REQUIRED


def _p() -> str:
    return config.STATUS_PENDING


def _query_status(has_queries: bool) -> str:
    return _p() if has_queries else _nr()


def _hotfix_defaults(has_queries: bool) -> dict[str, str]:
    return {
        config.LIFECYCLE_FIELD_PRODUCTION: _p(),
        config.LIFECYCLE_FIELD_RELEASE_BRANCH: _p(),
        config.LIFECYCLE_FIELD_PROD_BRANCH: _p(),
        config.LIFECYCLE_FIELD_STAGE_QUERY: _query_status(has_queries),
        config.LIFECYCLE_FIELD_UAT_QUERY: _query_status(has_queries),
        config.LIFECYCLE_FIELD_UAT_DEPLOYMENT: _p(),
        config.LIFECYCLE_FIELD_QA: _p(),
        config.LIFECYCLE_FIELD_CLOSURE: config.STATUS_PENDING,
    }


def initial_priority(patch_type: str) -> str:
    if patch_type == config.PATCH_TYPE_URGENT:
        return config.PRIORITY_URGENT
    return config.PRIORITY_NORMAL


def is_urgent_highlight(patch_type: str, closure_status: str) -> bool:
    """Urgent patches stay highlighted until closed."""
    if patch_type != config.PATCH_TYPE_URGENT:
        return False
    return closure_status != config.STATUS_COMPLETED and closure_status.lower() != "closed"


def compute_initial_lifecycle(opts: CreatePatchOptions) -> dict[str, str]:
    """Return default lifecycle statuses for a new patch (editable after create)."""
    t = opts.patch_type
    q = opts.has_queries

    if t in (config.PATCH_TYPE_WEEKLY, config.PATCH_TYPE_URGENT):
        return _hotfix_defaults(q)

    if t == config.PATCH_TYPE_RELEASE:
        return {
            config.LIFECYCLE_FIELD_PRODUCTION: _nr(),
            config.LIFECYCLE_FIELD_RELEASE_BRANCH: _nr(),
            config.LIFECYCLE_FIELD_PROD_BRANCH: _nr(),
            config.LIFECYCLE_FIELD_STAGE_QUERY: _query_status(q),
            config.LIFECYCLE_FIELD_UAT_QUERY: _query_status(q),
            config.LIFECYCLE_FIELD_UAT_DEPLOYMENT: _p(),
            config.LIFECYCLE_FIELD_QA: _p(),
            config.LIFECYCLE_FIELD_CLOSURE: config.STATUS_PENDING,
        }

    if t == config.PATCH_TYPE_DB_QUERY:
        return {
            config.LIFECYCLE_FIELD_PRODUCTION: _p() if opts.db_linked_to_hotfix_prod else _nr(),
            config.LIFECYCLE_FIELD_RELEASE_BRANCH: _p() if opts.db_has_repo_change else _nr(),
            config.LIFECYCLE_FIELD_PROD_BRANCH: _p() if opts.db_has_repo_change else _nr(),
            config.LIFECYCLE_FIELD_STAGE_QUERY: _p(),
            config.LIFECYCLE_FIELD_UAT_QUERY: _p(),
            config.LIFECYCLE_FIELD_UAT_DEPLOYMENT: _p() if opts.db_query_part_of_deployable else _nr(),
            config.LIFECYCLE_FIELD_QA: _p(),
            config.LIFECYCLE_FIELD_CLOSURE: config.STATUS_PENDING,
        }

    if t == config.PATCH_TYPE_CONFIG:
        return {
            config.LIFECYCLE_FIELD_PRODUCTION: _p() if opts.config_applied_in_production else _nr(),
            config.LIFECYCLE_FIELD_RELEASE_BRANCH: _p() if opts.config_stored_in_repo else _nr(),
            config.LIFECYCLE_FIELD_PROD_BRANCH: _p() if opts.config_stored_in_prod_branch else _nr(),
            config.LIFECYCLE_FIELD_STAGE_QUERY: _nr(),
            config.LIFECYCLE_FIELD_UAT_QUERY: _nr(),
            config.LIFECYCLE_FIELD_UAT_DEPLOYMENT: _p() if opts.config_must_apply_in_uat else _nr(),
            config.LIFECYCLE_FIELD_QA: _p(),
            config.LIFECYCLE_FIELD_CLOSURE: config.STATUS_PENDING,
        }

    raise ValueError(f"Unknown patch type: {t!r}")


def merge_lifecycle_on_type_change(
    current: dict[str, str],
    new_defaults: dict[str, str],
    *,
    reset_to_defaults: bool,
) -> dict[str, str]:
    """
    When patch type changes, never silently overwrite statuses.

    If reset_to_defaults is False, keep current values.
    If True, replace with new_defaults (UI must confirm before calling with True).
    """
    if reset_to_defaults:
        return dict(new_defaults)
    return dict(current)


@dataclass
class TypeChangePreview:
    """Shown in UI before applying a patch type change."""

    old_type: str
    new_type: str
    current_lifecycle: dict[str, str] = field(default_factory=dict)
    proposed_defaults: dict[str, str] = field(default_factory=dict)


def preview_patch_type_change(
    old_type: str,
    new_type: str,
    current_lifecycle: dict[str, str],
    opts: CreatePatchOptions,
) -> TypeChangePreview:
    opts.patch_type = new_type
    return TypeChangePreview(
        old_type=old_type,
        new_type=new_type,
        current_lifecycle=dict(current_lifecycle),
        proposed_defaults=compute_initial_lifecycle(opts),
    )


def validate_ticket_id(value: str) -> bool:
    return bool(config.TICKET_ID_PATTERN.match(value.strip()))


def validate_operator(name: str) -> bool:
    return name.strip() in config.OPERATORS


def normalize_operator(name: str) -> str:
    """Return canonical operator name or raise ValueError."""
    trimmed = name.strip()
    for op in config.OPERATORS:
        if op == trimmed:
            return op
    raise ValueError(f"Unknown operator: {name!r}. Must be one of: {', '.join(config.OPERATORS)}")


def validate_status_transition(
    field: str,
    old_status: str,
    new_status: str,
    lifecycle: dict[str, str],
) -> str | None:
    """Return error message or None if OK."""
    if (
        field == config.LIFECYCLE_FIELD_UAT_QUERY
        and new_status == config.STATUS_COMPLETED
        and lifecycle.get(config.LIFECYCLE_FIELD_STAGE_QUERY) != config.STATUS_COMPLETED
    ):
        return "UAT query cannot be Completed before Stage query is Completed."
    return None


_OPEN_LIFECYCLE_STATUSES = frozenset(
    {
        config.STATUS_PENDING,
        config.STATUS_IN_PROGRESS,
        config.STATUS_FAILED,
    }
)


def compute_system_status(lifecycle: dict[str, str]) -> str:
    """
    Derive display status from lifecycle fields (stored as system_status).

    Priority: Closed → Blocked (any step) → Ready to Close → first open step label.
    """
    closure = lifecycle.get(config.LIFECYCLE_FIELD_CLOSURE, "")
    if closure in (config.STATUS_COMPLETED, "Closed"):
        return config.SYSTEM_STATUS_CLOSED

    for field_name in config.LIFECYCLE_STATUS_ORDER:
        status = lifecycle.get(field_name, "")
        if status == config.STATUS_BLOCKED:
            return config.SYSTEM_STATUS_BLOCKED

    for field_name in config.LIFECYCLE_STATUS_ORDER:
        status = lifecycle.get(field_name, "")
        if status == config.STATUS_FAILED:
            return config.SYSTEM_STATUS_BLOCKED

    ok, _ = can_close(lifecycle)
    if ok and closure not in (config.STATUS_COMPLETED, "Closed"):
        return config.SYSTEM_STATUS_READY_TO_CLOSE

    for field_name in config.LIFECYCLE_STATUS_ORDER:
        status = lifecycle.get(field_name, "")
        if status in _OPEN_LIFECYCLE_STATUSES:
            return config.LIFECYCLE_COMPUTED_LABELS[field_name]

    if ok:
        return config.SYSTEM_STATUS_READY_TO_CLOSE
    return config.SYSTEM_STATUS_READY_TO_CLOSE


@dataclass(frozen=True)
class PatchStatusDisplay:
    """Final + system status for listing and detail header."""

    system_status: str
    manual_status_override: str | None
    final_status: str

    @property
    def shows_both(self) -> bool:
        return bool(self.manual_status_override)


def resolve_patch_status_display(
    lifecycle: dict[str, str],
    manual_status_override: str | None,
) -> PatchStatusDisplay:
    system = compute_system_status(lifecycle)
    override = (manual_status_override or "").strip() or None
    final = override if override else system
    return PatchStatusDisplay(
        system_status=system,
        manual_status_override=override,
        final_status=final,
    )


def can_close(lifecycle: dict[str, str]) -> tuple[bool, list[str]]:
    """Block close if any required step is not done."""
    blocking: list[str] = []
    for field_name in config.LIFECYCLE_FIELDS:
        if field_name == config.LIFECYCLE_FIELD_CLOSURE:
            continue
        status = lifecycle.get(field_name, "")
        if status in (
            config.STATUS_PENDING,
            config.STATUS_IN_PROGRESS,
            config.STATUS_BLOCKED,
            config.STATUS_FAILED,
        ):
            blocking.append(field_name)
    return len(blocking) == 0, blocking


def branch_display_name(branch_name: str | None) -> str:
    return (branch_name or "").strip() or NO_BRANCH_LABEL


def branch_sort_key(branch_name: str | None) -> tuple[int, int, int, int, str]:
    """
    Sort key for branch headings (latest hotfix first).

    hotfix_r26q2.15 sorts above hotfix_r26q2.9; unassigned branches sort last.
    """
    name = branch_display_name(branch_name)
    if name == NO_BRANCH_LABEL:
        return (0, 0, 0, 0, "")

    match = HOTFIX_BRANCH_RE.match(name)
    if match:
        return (
            3,
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
            name.lower(),
        )

    return (2, 0, 0, 0, name.lower())


def group_by_branch_name(
    items: list[T],
    *,
    branch_getter: Callable[[T], str],
) -> list[tuple[str, list[T]]]:
    """Group items under branch headings, latest branch first."""
    groups: dict[str, list[T]] = defaultdict(list)
    for item in items:
        label = branch_display_name(branch_getter(item))
        groups[label].append(item)

    ordered = sorted(groups.keys(), key=branch_sort_key, reverse=True)
    return [(label, groups[label]) for label in ordered]
