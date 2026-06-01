"""Streamlit UI for Patch Lifecycle."""

from __future__ import annotations

import re

import pandas as pd
import streamlit as st

import config
import db
import display
import repository
from logic import (
    can_close,
    closure_field_for_track,
    group_by_branch_name,
    lifecycle_fields_for_track,
    patch_row_tone,
)
from repository import PatchCreateInput

_VIEW_KEY = "pl_view"
_PATCH_ID_KEY = "pl_selected_patch_id"


def _operator() -> str:
    if config.OPERATOR_SESSION_KEY not in st.session_state:
        st.session_state[config.OPERATOR_SESSION_KEY] = config.DEFAULT_OPERATOR
    return st.session_state[config.OPERATOR_SESSION_KEY]


def _side_filter() -> str:
    if config.SIDE_FILTER_SESSION_KEY not in st.session_state:
        st.session_state[config.SIDE_FILTER_SESSION_KEY] = config.SIDE_FILTER_FC
    return st.session_state[config.SIDE_FILTER_SESSION_KEY]


def _set_view(view: str, patch_id: int | None = None) -> None:
    st.session_state[_VIEW_KEY] = view
    if patch_id is not None:
        st.session_state[_PATCH_ID_KEY] = patch_id
    st.rerun()


def _render_side_toggle() -> None:
    current = _side_filter()
    cols = st.columns(len(config.SIDE_FILTERS))
    for col, label in zip(cols, config.SIDE_FILTERS):
        with col:
            if st.button(
                label,
                key=f"pl_side_{label}",
                use_container_width=True,
                type="primary" if current == label else "secondary",
            ):
                st.session_state[config.SIDE_FILTER_SESSION_KEY] = label
                st.rerun()


def _render_operator_bar() -> None:
    st.selectbox(
        "Operator",
        options=list(config.OPERATORS),
        key=config.OPERATOR_SESSION_KEY,
    )


def _render_nav() -> None:
    cols = st.columns(3)
    with cols[0]:
        if st.button("All patches", use_container_width=True):
            _set_view("All patches")
    with cols[1]:
        if st.button("Pending follow-ups", use_container_width=True):
            _set_view("Pending follow-ups")
    with cols[2]:
        if st.button("Create patch", use_container_width=True, type="primary"):
            _set_view("Create patch")


def _split_lines(text: str) -> list[str]:
    return [ln.strip() for ln in text.splitlines() if ln.strip()]


def _type_flags_in_form(patch_type: str) -> dict[str, bool]:
    flags: dict[str, bool] = {}
    if patch_type == config.PATCH_TYPE_DB_QUERY:
        st.markdown("**DB Query Patch options**")
        flags["db_linked_to_hotfix_prod"] = st.checkbox("Linked to hotfix production deployment")
        flags["db_has_repo_change"] = st.checkbox("Code/repo change exists")
        flags["db_query_part_of_deployable"] = st.checkbox("Query part of deployable patch")
    elif patch_type == config.PATCH_TYPE_CONFIG:
        st.markdown("**Configuration Patch options**")
        flags["config_applied_in_production"] = st.checkbox("Config applied in production")
        flags["config_stored_in_repo"] = st.checkbox("Config stored in repo")
        flags["config_stored_in_prod_branch"] = st.checkbox("Config stored in prod branch/repo")
        flags["config_must_apply_in_uat"] = st.checkbox("Must apply/test in UAT")
    return flags


def _render_create_form() -> None:
    st.subheader("Create patch")
    with st.form("pl_create_patch"):
        c1, c2 = st.columns(2)
        with c1:
            patch_id = st.text_input("Patch ID *", placeholder="FCSKY-122193")
            bug_id = st.text_input("Bug ID", placeholder="FCSKY-120767")
            patch_type = st.selectbox("Patch type", options=list(config.PATCH_TYPES))
            title = st.text_input("Title")
            branch_name = st.text_input("Branch name", placeholder="hotfix_r26q2.15")
            release_name = st.text_input("Release name", placeholder="Release April 26")
        with c2:
            developer_name = st.text_input("Developer", placeholder="vipin")
            qa_status = st.text_input("QA Status", placeholder="QA")
            qa_date = st.text_input("QA Date", placeholder="YYYY-MM-DD")
            patch_date = st.text_input("Patch Date", placeholder="YYYY-MM-DD")
            product_module = st.text_input("Product / Module")
            jira_url = st.text_input("Jira URL (optional override)")

        description = st.text_area("Description / Details", height=100)
        repos = st.text_area(
            "Repositories (one per line)",
            height=80,
            help="Patch side (FC / WM / Both) is derived automatically from repo names.",
        )
        mysql = st.text_area("MySQL queries", height=80)
        psql = st.text_area("PostgreSQL queries", height=80)
        configuration = st.text_area("Configuration changes", height=60)
        steps = st.text_area("Steps", height=60)

        flags = _type_flags_in_form(patch_type)
        submitted = st.form_submit_button("Create patch", type="primary")

    if submitted:
        if not patch_id.strip():
            st.error("Patch ID is required.")
            return
        try:
            payload = PatchCreateInput(
                patch_id=patch_id.strip(),
                patch_type=patch_type,
                title=title,
                description=description,
                bug_id=bug_id,
                jira_url=jira_url,
                branch_name=branch_name,
                release_name=release_name,
                patch_date=patch_date,
                qa_date=qa_date,
                qa_status=qa_status,
                developer_name=developer_name,
                product_module=product_module,
                repo_names=_split_lines(repos),
                mysql_queries=_split_lines(mysql),
                postgresql_queries=_split_lines(psql),
                configuration_changes=configuration,
                steps=steps,
                **flags,
            )
            new_id = repository.create_patch(payload, _operator())
            st.success(f"Created patch {patch_id.strip().upper()}")
            _set_view("Patch detail", new_id)
        except ValueError as exc:
            st.error(str(exc))


def _truncate(text: str, max_len: int = 48) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text or "—"
    return text[: max_len - 1] + "…"


def _patches_to_dataframe(
    patches: list[repository.PatchSummary],
    *,
    side_filter: str,
) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    lifecycle_columns = display.lifecycle_table_columns(side_filter)
    show_side = side_filter == config.SIDE_FILTER_ALL
    for p in patches:
        row: dict[str, str] = {
            "Patch ID": f"{'🔴 ' if p.is_urgent else ''}{p.patch_id}",
            "Details": _truncate(p.title),
        }
        if show_side:
            row["Side"] = display.patch_side_label(p.patch_side)
        row["Patch Type"] = p.patch_type
        row["Repos"] = _truncate(p.repos_summary or "", 36)
        row["Branch"] = p.branch_name or "—"
        row["Developer"] = p.developer_name or "—"
        row["Patch Date"] = p.patch_date or "—"
        row["QA Date"] = p.qa_date or "—"
        row["QA Stat"] = p.qa_status or "—"
        for col_label, field in lifecycle_columns:
            status = p.lifecycle.get(field, config.STATUS_NOT_REQUIRED)
            row[col_label] = display.status_table_cell(status)
        row["Final Status"] = p.final_status
        rows.append(row)
    return pd.DataFrame(rows)


def _inject_table_styles() -> None:
    st.markdown(
        """
        <style>
            [data-testid="stDataFrame"] { font-size: 0.92rem; }
            .pl-branch-heading {
                background: var(--secondary-background-color, #e8eaef);
                color: var(--text-color, #31333f);
                border-left: 4px solid #ff4b4b;
                padding: 0.4rem 0.85rem;
                border-radius: 0.35rem;
                margin: 1.1rem 0 0.35rem 0;
                font-weight: 650;
                font-size: 1.05rem;
            }
            [data-theme="dark"] .pl-branch-heading,
            .stApp[data-theme="dark"] .pl-branch-heading {
                background: #2d2f38;
                color: #fafafa;
                border-left-color: #ff6b6b;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _branch_table_key(branch_name: str) -> str:
    slug = re.sub(r"[^\w]+", "_", branch_name.strip().lower()).strip("_")
    return slug[:48] or "no_branch"


def _render_branch_section(
    branch_name: str,
    branch_patches: list[repository.PatchSummary],
    *,
    view_key: str,
    side_filter: str,
) -> None:
    st.markdown(
        f'<div class="pl-branch-heading">{branch_name}</div>',
        unsafe_allow_html=True,
    )
    df = _patches_to_dataframe(branch_patches, side_filter=side_filter)
    row_tones = [
        patch_row_tone(
            lifecycle=p.lifecycle,
            manual_status_override=p.manual_status_override,
            patch_side=p.patch_side,
            side_filter=side_filter,
        )
        for p in branch_patches
    ]
    styled_df = display.style_patch_dataframe(df, row_tones)
    table_key = f"pl_table_{view_key}_{side_filter}_{_branch_table_key(branch_name)}"

    selection = st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        key=table_key,
    )

    selected_rows: list[int] = []
    if selection is not None and hasattr(selection, "selection"):
        selected_rows = list(selection.selection.rows)

    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button(
            "Open selected patch",
            key=f"pl_open_{table_key}",
            disabled=not selected_rows,
            type="primary",
        ):
            _set_view("Patch detail", branch_patches[selected_rows[0]].id)
    with c2:
        if selected_rows:
            p = branch_patches[selected_rows[0]]
            lifecycle_columns = display.lifecycle_table_columns(side_filter)
            preview = " · ".join(
                f"{label} {display.status_cell(p.lifecycle.get(field, ''))}"
                for label, field in lifecycle_columns[:5]
            )
            st.caption(f"Selected: **{p.patch_id}** — {p.final_status} · {preview}")


def _render_patch_table(
    patches: list[repository.PatchSummary],
    *,
    empty: str,
    side_filter: str,
) -> None:
    if not patches:
        st.info(empty)
        return

    st.caption(display.STATUS_LEGEND)
    _inject_table_styles()

    view_key = st.session_state.get(_VIEW_KEY, "list")
    branch_groups = group_by_branch_name(patches, branch_getter=lambda p: p.branch_name)
    for branch_name, branch_patches in branch_groups:
        _render_branch_section(
            branch_name,
            branch_patches,
            view_key=view_key,
            side_filter=side_filter,
        )


def _subfilter_all_label(patch_type: str) -> str:
    if patch_type == config.PATCH_TYPE_DEMO_UAT:
        return "All UAT patches"
    if patch_type == config.PATCH_TYPE_RELEASE:
        return "All release branches"
    if patch_type in (config.PATCH_TYPE_WEEKLY, config.PATCH_TYPE_URGENT):
        return "All branches"
    return "All"


def _subfilter_pending_label(patch_type: str) -> str:
    if patch_type == config.PATCH_TYPE_DEMO_UAT:
        return "Pending UAT patches"
    return "Pending only"


def _subfilter_options(patch_type: str, side_filter: str) -> list[tuple[str, str]]:
    """Return (display label, value) pairs for the type sub-filter dropdown."""
    options: list[tuple[str, str]] = [
        (_subfilter_all_label(patch_type), config.SUBFILTER_ALL),
        (_subfilter_pending_label(patch_type), config.SUBFILTER_PENDING),
    ]
    for branch in repository.list_distinct_branches_for_type(
        patch_type=patch_type,
        side_filter=side_filter,
    ):
        options.append((branch, branch))
    return options


def _parse_subfilter(sub_value: str) -> tuple[str | None, bool]:
    """Map sub-filter value to branch name and whether pending-only applies."""
    if sub_value == config.SUBFILTER_ALL:
        return None, False
    if sub_value == config.SUBFILTER_PENDING:
        return None, True
    return sub_value, False


def _render_list(*, pending_only: bool) -> None:
    side_filter = _side_filter()
    st.subheader("Pending follow-ups" if pending_only else "All patches")
    f1, f2, f3 = st.columns([1.1, 1.1, 1.2])
    with f1:
        type_filter = st.selectbox(
            "Patch type",
            options=["All"] + list(config.PATCH_TYPES),
            key=f"pl_filter_type_{pending_only}_{side_filter}",
        )
    with f2:
        sub_value = config.SUBFILTER_ALL
        if type_filter != "All":
            sub_choices = _subfilter_options(type_filter, side_filter)
            sub_labels = [label for label, _ in sub_choices]
            sub_values = {label: value for label, value in sub_choices}
            sub_label = st.selectbox(
                "Scope",
                options=sub_labels,
                key=f"pl_filter_sub_{pending_only}_{side_filter}_{type_filter}",
            )
            sub_value = sub_values[sub_label]
        else:
            st.selectbox(
                "Scope",
                options=["All types"],
                disabled=True,
                key=f"pl_filter_sub_disabled_{pending_only}_{side_filter}",
            )
    with f3:
        dev_filter = st.text_input(
            "Developer",
            placeholder="Name (case insensitive)",
            key=f"pl_filter_dev_{pending_only}_{side_filter}",
        )

    branch_filter, require_pending = _parse_subfilter(sub_value)
    patches = repository.list_patches(
        patch_type=None if type_filter == "All" else type_filter,
        developer=dev_filter.strip() or None,
        branch_name=branch_filter,
        pending_only=pending_only,
        require_pending=require_pending and type_filter != "All",
        side_filter=side_filter,
    )
    _render_patch_table(
        patches,
        empty="No patches yet." if not pending_only else "No pending follow-ups.",
        side_filter=side_filter,
    )


def _render_lifecycle_section(
    patch: repository.PatchDetail,
    section_title: str,
    columns: tuple[tuple[str, str], ...],
    track: str,
) -> dict[str, str]:
    st.markdown(f"#### {section_title}")
    values: dict[str, str] = {}
    fields = lifecycle_fields_for_track(track)
    closure_field = closure_field_for_track(track)
    ordered = [f for _, f in columns] + [closure_field]

    for field in ordered:
        label = next((lbl for lbl, fld in columns if fld == field), "Closure")
        current = patch.lifecycle.get(field, config.STATUS_PENDING)
        values[field] = st.selectbox(
            f"{display.status_icon(current)} {label}",
            options=list(config.LIFECYCLE_STATUSES),
            index=list(config.LIFECYCLE_STATUSES).index(current),
            key=f"lc_{patch.id}_{track}_{field}",
        )
    return values


def _render_detail() -> None:
    internal_id = st.session_state.get(_PATCH_ID_KEY)
    if not internal_id:
        st.warning("No patch selected.")
        return
    patch = repository.get_patch(int(internal_id))
    if not patch:
        st.error("Patch not found.")
        return

    if st.button("← Back to list"):
        _set_view("All patches")

    st.subheader(patch.patch_id)
    if patch.priority == config.PRIORITY_URGENT and patch.system_status != config.SYSTEM_STATUS_CLOSED:
        st.markdown("🔴 **Urgent hotfix** — highlighted until closed")

    final = patch.manual_status_override or patch.system_status
    st.markdown(
        f"**Final status:** {final} · **Side:** {display.patch_side_label(patch.patch_side)}"
    )
    if patch.manual_status_override:
        st.markdown(f"**System status:** {patch.system_status}")
    if patch.jira_url:
        st.markdown(f"[Jira]({patch.jira_url})")
    st.markdown(f"**Type:** {patch.patch_type} | **Developer:** {patch.developer_name or '—'}")
    st.markdown(f"**Branch:** {patch.branch_name or '—'} | **Release:** {patch.release_name or '—'}")
    st.markdown(f"**Title:** {patch.title or '—'}")
    if patch.description:
        st.text_area("Description", value=patch.description, height=120, disabled=True)
    if patch.repos:
        st.markdown("**Repositories:** " + ", ".join(patch.repos))
    if patch.mysql_queries:
        st.markdown("**MySQL queries**")
        for q in patch.mysql_queries:
            st.code(q, language="sql")
    if patch.postgresql_queries:
        st.markdown("**PostgreSQL queries**")
        for q in patch.postgresql_queries:
            st.code(q, language="sql")

    st.divider()
    st.markdown("### Lifecycle")
    new_lifecycle: dict[str, str] = dict(patch.lifecycle)
    for section_title, columns in display.detail_lifecycle_sections(patch.patch_side):
        track = (
            config.PATCH_SIDE_WM
            if section_title.startswith("WM")
            else config.PATCH_SIDE_FC
        )
        new_lifecycle.update(_render_lifecycle_section(patch, section_title, columns, track))

    override_options = ["(none)"] + list(config.MANUAL_STATUS_OVERRIDES)
    current_override = patch.manual_status_override or "(none)"
    override_choice = st.selectbox(
        "Manual status override",
        options=override_options,
        index=override_options.index(current_override)
        if current_override in override_options
        else 0,
    )
    blocker = st.text_input("Blocker reason", value=patch.blocker_reason)

    if st.button("Save lifecycle", type="primary"):
        try:
            if patch.patch_side in (config.PATCH_SIDE_FC, config.PATCH_SIDE_BOTH):
                closure_field = closure_field_for_track(config.PATCH_SIDE_FC)
                if new_lifecycle.get(closure_field) == config.STATUS_COMPLETED:
                    ok, blocking = can_close(new_lifecycle, track=config.PATCH_SIDE_FC)
                    if not ok:
                        st.error(f"Cannot close FC track — incomplete: {', '.join(blocking)}")
                        st.stop()
            if patch.patch_side in (config.PATCH_SIDE_WM, config.PATCH_SIDE_BOTH):
                closure_field = closure_field_for_track(config.PATCH_SIDE_WM)
                if new_lifecycle.get(closure_field) == config.STATUS_COMPLETED:
                    ok, blocking = can_close(new_lifecycle, track=config.PATCH_SIDE_WM)
                    if not ok:
                        st.error(f"Cannot close WM track — incomplete: {', '.join(blocking)}")
                        st.stop()
            repository.update_lifecycle(
                patch.id,
                new_lifecycle,
                _operator(),
                manual_status_override=None
                if override_choice == "(none)"
                else override_choice,
                blocker_reason=blocker,
            )
            st.success("Saved.")
            st.rerun()
        except ValueError as exc:
            st.error(str(exc))

    st.divider()
    st.markdown("### Activity log")
    if not patch.activity:
        st.caption("No activity yet.")
    for entry in patch.activity:
        st.caption(
            f"{entry['updated_at']} — **{entry['updated_by']}** — "
            f"{entry['action']} {entry['field_name']} "
            f"{entry['old_value']} → {entry['new_value']}"
        )


def render() -> None:
    db.init_db()
    st.title("Patch Lifecycle")
    st.caption("Patch registry and lifecycle tracker (local SQLite).")
    _render_side_toggle()
    _render_operator_bar()
    _render_nav()

    view = st.session_state.get(_VIEW_KEY, "All patches")
    if view == "Create patch":
        _render_create_form()
    elif view == "Pending follow-ups":
        _render_list(pending_only=True)
    elif view == "Patch detail":
        _render_detail()
    else:
        _render_list(pending_only=False)
