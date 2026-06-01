"""Decision engine: freeze, sequencing, and source ref selection."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from utils import (
    date_in_freeze,
    hotfix_prefix_for_date,
    hotfix_week_number_in_quarter,
    max_hotfix_sequence,
    release_branch_display_name,
)

DecisionKind = Literal[
    "already_cut_for_week",
    "existing_hotfix_chain",
    "first_after_release_tag",
    "first_from_release_branch",
    "first_prod",
    "release_branch_from_tag",
]


def _release_branch_resolvable(
    rb_name: str, branch_names: list[str], release_branch_exists: bool
) -> bool:
    """True if the release branch is present (API flag) or appears in the fetched branch list."""
    if release_branch_exists:
        return True
    if not rb_name:
        return False
    for n in branch_names:
        if n == rb_name or n.casefold() == rb_name.casefold():
            return True
    return False


def _release_live_hotfix_day(
    hotfix_date: date,
    release_live_date: date,
    rb_name: str,
    branch_names: list[str],
    release_branch_exists: bool,
) -> bool:
    """Hotfix Wednesday is the release go-live date and the release branch can be resolved."""
    return hotfix_date == release_live_date and _release_branch_resolvable(
        rb_name, branch_names, release_branch_exists
    )


@dataclass(frozen=True)
class HotfixDecision:
    """Outcome of evaluating hotfix rules for one repo and date."""

    blocked: bool
    block_reason: str | None
    proposed_branch_name: str | None
    source_ref: str | None
    source_kind: str | None
    reason: str
    decision_kind: DecisionKind | None
    hotfix_prefix: str
    next_sequence: int | None
    already_cut_for_week: bool = False
    hotfix_week_number: int | None = None


def decide_hotfix(
    hotfix_date: date,
    release_live_date: date,
    release_tag: str,
    release_branch_override: str | None,
    freeze_start: date | None,
    freeze_end: date | None,
    branch_names: list[str],
    release_branch_exists: bool,
    prod_branch: str = "prod",
    skip_leading_wednesdays: int = 0,
    release_branch_naming: str = "day_short_month",
    current_date: date | None = None,
) -> HotfixDecision:
    """
    Pure decision logic (no API). Caller supplies branch list and whether
    the release branch exists on the remote.
    """
    prefix = hotfix_prefix_for_date(hotfix_date)
    week_n = hotfix_week_number_in_quarter(hotfix_date, skip_leading_wednesdays)
    expected_for_week = f"{prefix}.{week_n}" if week_n is not None else None

    if current_date is not None and hotfix_date < current_date:
        return HotfixDecision(
            blocked=True,
            block_reason="Past hotfix dates are not allowed. Choose an upcoming Wednesday.",
            proposed_branch_name=None,
            source_ref=None,
            source_kind=None,
            reason=(
                f"Selected hotfix date `{hotfix_date.isoformat()}` is before today "
                f"`{current_date.isoformat()}`. Previous branches are historical and cannot be cut again."
            ),
            decision_kind=None,
            hotfix_prefix=prefix,
            next_sequence=None,
            hotfix_week_number=week_n,
        )

    if release_live_date < hotfix_date - timedelta(days=180):
        return HotfixDecision(
            blocked=True,
            block_reason="Release live date looks too old for the selected hotfix date.",
            proposed_branch_name=None,
            source_ref=None,
            source_kind=None,
            reason=(
                f"Release live date `{release_live_date.isoformat()}` is far earlier than selected hotfix "
                f"date `{hotfix_date.isoformat()}`. This usually means a wrong year was entered "
                "(for example 2025 instead of 2026)."
            ),
            decision_kind=None,
            hotfix_prefix=prefix,
            next_sequence=None,
            hotfix_week_number=week_n,
        )

    if date_in_freeze(hotfix_date, freeze_start, freeze_end):
        return HotfixDecision(
            blocked=True,
            block_reason="Hotfix date falls inside the configured freeze window.",
            proposed_branch_name=None,
            source_ref=None,
            source_kind=None,
            reason="Branch creation is blocked during the freeze window.",
            decision_kind=None,
            hotfix_prefix=prefix,
            next_sequence=None,
            hotfix_week_number=week_n,
        )

    rb_name = release_branch_display_name(release_live_date, release_branch_override, release_branch_naming)
    tag_clean = release_tag.strip()

    if expected_for_week and expected_for_week in branch_names:
        release_day = _release_live_hotfix_day(
            hotfix_date, release_live_date, rb_name, branch_names, release_branch_exists
        )
        src = rb_name if release_day else expected_for_week
        reason = (
            f"The hotfix week you selected maps to **`{expected_for_week}`** (calendar hotfix week "
            f"{week_n} for `{prefix}`). That branch already exists on the remote — nothing new to create."
        )
        if release_day:
            reason += (
                f" Release go-live matches this Wednesday — **source ref** is the release branch "
                f"`{rb_name}` (parent context for this week)."
            )
        return HotfixDecision(
            blocked=False,
            block_reason=None,
            proposed_branch_name=expected_for_week,
            source_ref=src,
            source_kind="branch",
            reason=reason,
            decision_kind="already_cut_for_week",
            hotfix_prefix=prefix,
            next_sequence=None,
            already_cut_for_week=True,
            hotfix_week_number=week_n,
        )

    # Go-live Wednesday: create the release branch from the monthly tag when it does not exist yet
    if (
        hotfix_date == release_live_date
        and not _release_branch_resolvable(rb_name, branch_names, release_branch_exists)
    ):
        if not tag_clean:
            return HotfixDecision(
                blocked=True,
                block_reason="Release tag is required to create the release branch on go-live.",
                proposed_branch_name=None,
                source_ref=None,
                source_kind=None,
                reason=(
                    f"The hotfix Wednesday matches the **release live date** ({release_live_date.isoformat()}), "
                    f"but **`{rb_name}`** is not on Bitbucket yet. Enter the **release tag** (e.g. `prod_tag_14apr26`) "
                    "so that branch can be created from the tag — weekly hotfix naming is skipped for this cut."
                ),
                decision_kind=None,
                hotfix_prefix=prefix,
                next_sequence=None,
                hotfix_week_number=week_n,
            )
        return HotfixDecision(
            blocked=False,
            block_reason=None,
            proposed_branch_name=rb_name,
            source_ref=tag_clean,
            source_kind="tag",
            reason=(
                f"**Release go-live:** branch `{rb_name}` is not on the remote yet. "
                f"Create it from tag **`{tag_clean}`** (tip of that tag becomes `{rb_name}`)."
            ),
            decision_kind="release_branch_from_tag",
            hotfix_prefix=prefix,
            next_sequence=None,
            hotfix_week_number=week_n,
        )

    max_seq = max_hotfix_sequence(branch_names, prefix)
    if max_seq is not None:
        next_n = max_seq + 1
        prev_branch = f"{prefix}.{max_seq}"
        release_day = _release_live_hotfix_day(
            hotfix_date, release_live_date, rb_name, branch_names, release_branch_exists
        )
        source_ref = rb_name if release_day else prev_branch
        extra = ""
        if expected_for_week and expected_for_week not in branch_names:
            extra = (
                f" Note: for this Wednesday the calendar week slot is **`{expected_for_week}`**, "
                f"which is not present yet; the next chained branch is still `.{next_n}` from "
                f"`{prev_branch}`."
            )
        if release_day:
            chain_reason = (
                f"Existing hotfix branch(es) for {prefix}: latest sequence {max_seq}. "
                f"Proposed next hotfix is **`{prefix}.{next_n}`**, cut from the **release branch** "
                f"`{rb_name}` because the hotfix Wednesday matches the **release live date**."
            )
        else:
            chain_reason = (
                f"Existing hotfix branch(es) for {prefix}: latest sequence {max_seq}. "
                f"Next branch chains from {prev_branch} (Bitbucket = source of truth for refs)."
                f"{extra}"
            )
        return HotfixDecision(
            blocked=False,
            block_reason=None,
            proposed_branch_name=f"{prefix}.{next_n}",
            source_ref=source_ref,
            source_kind="branch",
            reason=chain_reason,
            decision_kind="existing_hotfix_chain",
            hotfix_prefix=prefix,
            next_sequence=next_n,
            hotfix_week_number=week_n,
        )

    # First hotfix in this quarter for this prefix
    next_n = 1
    proposed = f"{prefix}.{next_n}"
    if _release_branch_resolvable(rb_name, branch_names, release_branch_exists):
        if hotfix_date == release_live_date:
            return HotfixDecision(
                blocked=False,
                block_reason=None,
                proposed_branch_name=proposed,
                source_ref=rb_name,
                source_kind="branch",
                reason=(
                    f"No existing {prefix}.* branches. Release branch **`{rb_name}`** exists and the "
                    "hotfix Wednesday matches the **release live date**, so the first hotfix is cut "
                    "from the **release branch**."
                ),
                decision_kind="first_from_release_branch",
                hotfix_prefix=prefix,
                next_sequence=next_n,
                hotfix_week_number=week_n,
            )
        if not tag_clean:
            return HotfixDecision(
                blocked=True,
                block_reason="Release tag is required when the release branch exists on the repo.",
                proposed_branch_name=None,
                source_ref=None,
                source_kind=None,
                reason=(
                    f"Release branch `{rb_name}` exists but no release tag was provided. "
                    "Enter the monthly release tag (admin input), or pick a hotfix date equal to the "
                    "release live date to cut from the release branch instead."
                ),
                decision_kind=None,
                hotfix_prefix=prefix,
                next_sequence=None,
                hotfix_week_number=week_n,
            )
        return HotfixDecision(
            blocked=False,
            block_reason=None,
            proposed_branch_name=proposed,
            source_ref=tag_clean,
            source_kind="tag",
            reason=(
                f"No existing {prefix}.* branches. Release branch `{rb_name}` exists on the repo, "
                f"so the first hotfix uses the configured release tag `{tag_clean}`."
            ),
            decision_kind="first_after_release_tag",
            hotfix_prefix=prefix,
            next_sequence=next_n,
            hotfix_week_number=week_n,
        )

    return HotfixDecision(
        blocked=False,
        block_reason=None,
        proposed_branch_name=proposed,
        source_ref=prod_branch,
        source_kind="branch",
        reason=(
            f"No existing {prefix}.* branches and release branch `{rb_name}` was not found; "
            f"first hotfix is cut from `{prod_branch}`."
        ),
        decision_kind="first_prod",
        hotfix_prefix=prefix,
        next_sequence=next_n,
        hotfix_week_number=week_n,
    )
