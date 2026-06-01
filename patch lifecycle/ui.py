"""Streamlit UI for Patch Lifecycle."""

from __future__ import annotations

import re

import pandas as pd
import streamlit as st

import config
import db
import display
import repository
from logic import can_close, group_by_branch_name
from repository import PatchCreateInput

_VIEW_KEY = "pl_view"
_PATCH_ID_KEY = "pl_selected_patch_id"


def _operator() -> str:
    if config.OPERATOR_SESSION_KEY not in st.session_state:
        st.session_state[config.OPERATOR_SESSION_KEY] = config.DEFAULT_OPERATOR
    return st.session_state[config.OPERATOR_SESSION_KEY]


def _set_view(view: str, patch_id: int | None = None) -> None:
    st.session_state[_VIEW_KEY] = view
    if patch_id is not None:
        st.session_state[_PATCH_ID_KEY] = patch_id
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
        repos = st.text_area("Repositories (one per line)", height=80)
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
    include_branch: bool = False,
) -> pd.DataFrame:
    rows: list[dict[str, str]] = []
    lifecycle_columns = display.lifecycle_table_columns()
    for p in patches:
        lifecycle = p.lifecycle
        row: dict[str, str] = {
            "Patch ID": f"{'🔴 ' if p.is_urgent else ''}{p.patch_id}",
            "Details": _truncate(p.title),
            "Repos": _truncate(p.repos_summary or "", 36),
            "Developer": p.developer_name or "—",
            "Patch Date": p.patch_date or "—",
            "QA Date": p.qa_date or "—",
            "QA Stat": p.qa_status or "—",
        }
        if include_branch:
            row["Branch"] = p.branch_name or "—"
        for col_label, field in lifecycle_columns:
            status = lifecycle.get(field, config.STATUS_NOT_REQUIRED)
            row[col_label] = display.status_table_cell(status)
        row["Final Status"] = p.final_status
        rows.append(row)
    df = pd.DataFrame(rows)
    if any(p.manual_status_override for p in patches):
        df["System Status"] = [p.system_status if p.manual_status_override else "—" for p in patches]
    return df


def _inject_table_styles() -> None:
    st.markdown(
        """
        <style>
            [data-testid="stDataFrame"] { font-size: 0.92rem; }
            [data-testid="stDataFrame"] div[data-testid="glideDataEditor"] {
                font-family: inherit;
            }
            .pl-branch-heading {
                background: #f0f2f6;
                border-left: 4px solid #ff4b4b;
                padding: 0.4rem 0.85rem;
                border-radius: 0.35rem;
                margin: 1.1rem 0 0.35rem 0;
                font-weight: 650;
                font-size: 1.05rem;
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
) -> None:
    st.markdown(
        f'<div class="pl-branch-heading">{branch_name}</div>',
        unsafe_allow_html=True,
    )
    df = _patches_to_dataframe(branch_patches)
    table_key = f"pl_table_{view_key}_{_branch_table_key(branch_name)}"

    selection = st.dataframe(
        df,
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
            st.caption(
                f"Selected: **{p.patch_id}** — {p.final_status} · "
                f"Release {display.status_cell(p.lifecycle.get(config.LIFECYCLE_FIELD_RELEASE_BRANCH, ''))} · "
                f"Prod {display.status_cell(p.lifecycle.get(config.LIFECYCLE_FIELD_PROD_BRANCH, ''))} · "
                f"Production {display.status_cell(p.lifecycle.get(config.LIFECYCLE_FIELD_PRODUCTION, ''))} · "
                f"Stage Q {display.status_cell(p.lifecycle.get(config.LIFECYCLE_FIELD_STAGE_QUERY, ''))} · "
                f"UAT Q {display.status_cell(p.lifecycle.get(config.LIFECYCLE_FIELD_UAT_QUERY, ''))}"
            )


def _render_patch_table(patches: list[repository.PatchSummary], *, empty: str) -> None:
    if not patches:
        st.info(empty)
        return

    st.caption(display.STATUS_LEGEND)
    _inject_table_styles()

    view_key = st.session_state.get(_VIEW_KEY, "list")
    branch_groups = group_by_branch_name(patches, branch_getter=lambda p: p.branch_name)
    for branch_name, branch_patches in branch_groups:
        _render_branch_section(branch_name, branch_patches, view_key=view_key)


def _render_list(*, pending_only: bool) -> None:
    st.subheader("Pending follow-ups" if pending_only else "All patches")
    f1, f2 = st.columns(2)
    with f1:
        type_filter = st.selectbox(
            "Filter by type",
            options=["All"] + list(config.PATCH_TYPES),
            key=f"pl_filter_type_{pending_only}",
        )
    with f2:
        dev_filter = st.text_input("Filter by developer", key=f"pl_filter_dev_{pending_only}")

    patches = repository.list_patches(
        patch_type=None if type_filter == "All" else type_filter,
        developer=dev_filter.strip() or None,
        pending_only=pending_only,
    )
    _render_patch_table(
        patches,
        empty="No patches yet." if not pending_only else "No pending follow-ups.",
    )


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
    st.markdown(f"**Final status:** {final}")
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
    new_lifecycle: dict[str, str] = {}
    field_labels = {f: label for label, f in display.lifecycle_table_columns()}
    field_labels[config.LIFECYCLE_FIELD_CLOSURE] = "Closure"
    ordered_fields = [f for _, f in display.lifecycle_table_columns()] + [
        config.LIFECYCLE_FIELD_CLOSURE
    ]
    for field in ordered_fields:
        label = field_labels.get(field, field.replace("_", " ").title())
        current = patch.lifecycle.get(field, config.STATUS_PENDING)
        new_lifecycle[field] = st.selectbox(
            f"{display.status_icon(current)} {label}",
            options=list(config.LIFECYCLE_STATUSES),
            index=list(config.LIFECYCLE_STATUSES).index(current),
            key=f"lc_{patch.id}_{field}",
        )

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
            if new_lifecycle.get(config.LIFECYCLE_FIELD_CLOSURE) == config.STATUS_COMPLETED:
                ok, blocking = can_close(new_lifecycle)
                if not ok:
                    st.error(f"Cannot close — incomplete: {', '.join(blocking)}")
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
