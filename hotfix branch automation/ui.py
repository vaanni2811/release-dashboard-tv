"""Streamlit UI for HP Branch Cut (hotfix branch automation)."""

from __future__ import annotations

import os
from datetime import date, datetime

import streamlit as st

import bitbucket
import bitbucket_auth
import config
from logic import decide_hotfix
from utils import format_date_display, release_branch_display_name, upcoming_wednesdays


@st.cache_data(ttl=120, show_spinner="Loading branches from Bitbucket…")
def _load_bitbucket_state(workspace: str, slug: str, release_branch_key: str) -> tuple[list[str], bool]:
    names = bitbucket.list_all_branch_names(workspace, slug)
    exists = False
    if release_branch_key.strip():
        exists = bitbucket.branch_exists(workspace, slug, release_branch_key.strip())
    return names, exists


def _parse_date_input(label: str, key: str) -> date | None:
    raw = st.text_input(label, key=key, placeholder="YYYY-MM-DD")
    if not (raw or "").strip():
        return None
    try:
        return datetime.strptime(raw.strip(), "%Y-%m-%d").date()
    except ValueError:
        st.error(f"Invalid date for {label}: use YYYY-MM-DD.")
        return None


def render() -> None:
    st.title("Hotfix branch automation")
    st.caption("Rule-driven Bitbucket hotfix branches — replaces manual cuts and Excel lineage.")

    credentials_set = bitbucket_auth.credentials_available()
    workspace = (config.BITBUCKET_WORKSPACE or os.environ.get("BITBUCKET_WORKSPACE") or "").strip()

    if not credentials_set:
        st.warning(
            "**Bitbucket credentials** are not set. Preview still works; **Create Branch** needs "
            "one of: **BITBUCKET_TOKEN**, **BITBUCKET_EMAIL** + **BITBUCKET_API_TOKEN**, or "
            "**BITBUCKET_USERNAME** + **BITBUCKET_APP_PASSWORD** (export before `streamlit run app.py`)."
        )
    if not workspace:
        st.warning(
            "Set **workspace** in `hotfix branch automation/config.py` or export **BITBUCKET_WORKSPACE** "
            "so API calls target the correct Bitbucket Cloud workspace."
        )

    repo_labels = [r["label"] for r in config.REPOS]
    repo_slugs = {r["label"]: r["slug"] for r in config.REPOS}

    col1, col2 = st.columns(2)
    with col1:
        selected_label = st.selectbox("Repository", options=repo_labels or ["(add repos in config.py)"])
    slug = repo_slugs.get(selected_label, "")

    today = date.today()
    weds = [w for w in upcoming_wednesdays(today=today, months_ahead=1) if w >= today]
    if not weds:
        st.error("No upcoming Wednesdays in the current planning window (this month + next).")
        st.stop()
    wed_options = {format_date_display(w): w for w in weds}
    with col2:
        hotfix_key = st.selectbox("Hotfix date (Wednesday)", options=list(wed_options.keys()))
    hotfix_date = wed_options[hotfix_key]
    st.caption(
        f"Upcoming Wednesdays only (this month + next). "
        f"Suffix `N` uses `HOTFIX_SKIP_LEADING_WEDNESDAYS={config.HOTFIX_SKIP_LEADING_WEDNESDAYS}` in "
        "`hotfix branch automation/config.py`."
    )

    st.subheader("Admin inputs (monthly)")
    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        release_live = _parse_date_input("Release live date", "release_live")
    with ac2:
        release_tag = st.text_input(
            "Release tag",
            key="release_tag",
            placeholder="e.g. prod_tag_17mar26",
        )
    with ac3:
        release_branch_override = st.text_input(
            "Release branch (optional override)",
            key="release_branch_override",
            placeholder="leave empty to derive from release live date",
        )

    st.subheader("Optional freeze window")
    fc1, fc2 = st.columns(2)
    with fc1:
        freeze_start = _parse_date_input("Freeze start (optional)", "freeze_start")
    with fc2:
        freeze_end = _parse_date_input("Freeze end (optional)", "freeze_end")

    if (freeze_start is None) ^ (freeze_end is None):
        st.error("Provide both freeze start and end, or leave both empty.")

    derived_rb = (
        release_branch_display_name(release_live, "", config.RELEASE_BRANCH_NAMING)
        if release_live
        else None
    )
    rb_display = (
        release_branch_display_name(release_live, release_branch_override, config.RELEASE_BRANCH_NAMING)
        if release_live
        else None
    )
    if release_live:
        st.info(f"Derived release branch name: **{derived_rb}** (override in field above if needed).")

    preview = st.button("Refresh preview from Bitbucket", type="secondary")

    branch_names: list[str] = []
    release_branch_exists = False
    fetch_error: str | None = None

    if preview:
        _load_bitbucket_state.clear()

    if credentials_set and workspace and slug:
        try:
            rb_key = (rb_display or "").strip()
            branch_names, release_branch_exists = _load_bitbucket_state(workspace, slug, rb_key)
        except bitbucket.BitbucketError as e:
            fetch_error = str(e)
    elif preview:
        st.info("Set Bitbucket credentials and workspace to load branches from Bitbucket.")

    if fetch_error:
        st.error(fetch_error)

    if credentials_set and workspace and slug and rb_display and not fetch_error:
        exists_note = "found on Bitbucket" if release_branch_exists else "**not** found on Bitbucket (name must match exactly)"
        st.caption(
            f"Active **release branch ref** for rules: `{rb_display}` — {exists_note}. "
            "After changing the override, click **Refresh preview from Bitbucket**."
        )

    if not release_live:
        st.stop()

    decision = decide_hotfix(
        hotfix_date=hotfix_date,
        release_live_date=release_live,
        release_tag=release_tag,
        release_branch_override=(release_branch_override or "").strip() or None,
        freeze_start=freeze_start,
        freeze_end=freeze_end,
        branch_names=branch_names,
        release_branch_exists=release_branch_exists,
        prod_branch=config.PROD_BRANCH,
        skip_leading_wednesdays=config.HOTFIX_SKIP_LEADING_WEDNESDAYS,
        release_branch_naming=config.RELEASE_BRANCH_NAMING,
        current_date=today,
    )

    st.subheader("Decision")
    if decision.blocked:
        st.error(decision.block_reason or "Blocked")
    elif decision.already_cut_for_week:
        st.info(decision.reason)
    else:
        st.success("Ready (not blocked by freeze).")
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Proposed branch", decision.proposed_branch_name or "—")
    with m2:
        st.metric("Source ref", decision.source_ref or "—")
    with m3:
        st.metric("Source type", decision.source_kind or "—")
    st.write("**Reason:** ", decision.reason)
    if not credentials_set:
        st.caption(
            "Without Bitbucket credentials, branch list is empty — preview shows naming and source "
            "rules as if there were no remote hotfix branches yet."
        )

    can_create = (
        credentials_set
        and bool(workspace)
        and bool(slug)
        and not decision.blocked
        and not decision.already_cut_for_week
        and bool(decision.proposed_branch_name)
        and bool(decision.source_ref)
    )
    create_clicked = st.button(
        "Create branch in Bitbucket",
        type="primary",
        disabled=not can_create,
        help="Creates the proposed branch from the source ref shown above. Nothing is created until you click this.",
    )
    if not can_create and credentials_set and workspace and slug:
        if decision.blocked:
            st.caption("Create is disabled while the decision is blocked (e.g. freeze window).")
        elif decision.already_cut_for_week:
            st.caption("Create is disabled — this calendar hotfix week already has a branch on Bitbucket.")
        elif not (decision.proposed_branch_name and decision.source_ref):
            st.caption("Create is disabled until the preview shows a valid branch name and source ref.")

    if create_clicked and not decision.blocked and decision.proposed_branch_name and decision.source_ref:
        try:
            assert decision.source_kind
            h = bitbucket.resolve_source_hash(
                workspace, slug, decision.source_ref, decision.source_kind
            )
            bitbucket.create_branch(workspace, slug, decision.proposed_branch_name, h)
            st.success(f"Created branch **{decision.proposed_branch_name}** from {decision.source_ref}.")
        except bitbucket.BitbucketError as e:
            st.error(str(e))
