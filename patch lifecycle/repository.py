"""Database access for Patch Lifecycle patches."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import config
import db
from logic import (
    CreatePatchOptions,
    branch_sort_key,
    compute_initial_lifecycle,
    compute_patch_side,
    compute_system_status,
    initial_priority,
    lifecycle_track_for_filter,
    normalize_operator,
    patch_side_matches_filter,
    resolve_patch_status_display,
    validate_ticket_id,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def default_jira_url(patch_id: str) -> str:
    key = patch_id.strip().upper()
    if config.JIRA_BROWSE_BASE and key:
        return f"{config.JIRA_BROWSE_BASE}/{key}"
    return ""


def lifecycle_row_to_dict(row: Any) -> dict[str, str]:
    return {name: row[name] for name in config.ALL_LIFECYCLE_FIELDS}


def _status_track(patch_side: str) -> str:
    if patch_side == config.PATCH_SIDE_WM:
        return config.PATCH_SIDE_WM
    return config.PATCH_SIDE_FC


def _create_patch_options(conn: Any, internal_id: int, patch_row: Any) -> CreatePatchOptions:
    query_count = conn.execute(
        "SELECT COUNT(*) AS c FROM patch_queries WHERE patch_id = ?",
        (internal_id,),
    ).fetchone()["c"]
    return CreatePatchOptions(
        patch_type=patch_row["patch_type"],
        patch_side=row["patch_side"] if "patch_side" in row.keys() else config.PATCH_SIDE_FC,
        has_queries=query_count > 0,
        db_linked_to_hotfix_prod=bool(patch_row["db_linked_to_hotfix_prod"]),
        db_has_repo_change=bool(patch_row["db_has_repo_change"]),
        db_query_part_of_deployable=bool(patch_row["db_query_part_of_deployable"]),
        config_applied_in_production=bool(patch_row["config_applied_in_production"]),
        config_stored_in_repo=bool(patch_row["config_stored_in_repo"]),
        config_stored_in_prod_branch=bool(patch_row["config_stored_in_prod_branch"]),
        config_must_apply_in_uat=bool(patch_row["config_must_apply_in_uat"]),
    )


def _insert_lifecycle_row(
    conn: Any,
    internal_id: int,
    lifecycle: dict[str, str],
) -> None:
    conn.execute(
        """
        INSERT INTO patch_lifecycle_status (
            patch_id, production_status, release_branch_status, prod_branch_status,
            stage_query_status, uat_query_status, uat_deployment_status,
            qa_verification_status, closure_status,
            wm_hotfix_branch_status, wm_master_production_status, wm_release_branch_status,
            wm_integration_stage_status, wm_uat_branch_status,
            wm_stage_query_status, wm_uat_query_status, wm_qa_verification_status,
            wm_closure_status, blocker_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            internal_id,
            lifecycle[config.LIFECYCLE_FIELD_PRODUCTION],
            lifecycle[config.LIFECYCLE_FIELD_RELEASE_BRANCH],
            lifecycle[config.LIFECYCLE_FIELD_PROD_BRANCH],
            lifecycle[config.LIFECYCLE_FIELD_STAGE_QUERY],
            lifecycle[config.LIFECYCLE_FIELD_UAT_QUERY],
            lifecycle[config.LIFECYCLE_FIELD_UAT_DEPLOYMENT],
            lifecycle[config.LIFECYCLE_FIELD_QA],
            lifecycle[config.LIFECYCLE_FIELD_CLOSURE],
            lifecycle[config.WM_LIFECYCLE_FIELD_HOTFIX_BRANCH],
            lifecycle[config.WM_LIFECYCLE_FIELD_MASTER_PRODUCTION],
            lifecycle[config.WM_LIFECYCLE_FIELD_RELEASE_BRANCH],
            lifecycle[config.WM_LIFECYCLE_FIELD_INTEGRATION_STAGE],
            lifecycle[config.WM_LIFECYCLE_FIELD_UAT_BRANCH],
            lifecycle[config.WM_LIFECYCLE_FIELD_STAGE_QUERY],
            lifecycle[config.WM_LIFECYCLE_FIELD_UAT_QUERY],
            lifecycle[config.WM_LIFECYCLE_FIELD_QA],
            lifecycle[config.WM_LIFECYCLE_FIELD_CLOSURE],
            "",
        ),
    )


def ensure_lifecycle_row(conn: Any, internal_id: int, patch_row: Any) -> Any:
    """Return lifecycle row, creating defaults from patch type if missing."""
    lc_row = conn.execute(
        "SELECT * FROM patch_lifecycle_status WHERE patch_id = ?",
        (internal_id,),
    ).fetchone()
    if lc_row is not None:
        return lc_row

    opts = _create_patch_options(conn, internal_id, patch_row)
    lifecycle = compute_initial_lifecycle(opts)
    _insert_lifecycle_row(conn, internal_id, lifecycle)
    return conn.execute(
        "SELECT * FROM patch_lifecycle_status WHERE patch_id = ?",
        (internal_id,),
    ).fetchone()


@dataclass
class PatchCreateInput:
    patch_id: str
    patch_type: str
    title: str = ""
    description: str = ""
    bug_id: str = ""
    jira_url: str = ""
    branch_name: str = ""
    release_name: str = ""
    patch_date: str = ""
    qa_date: str = ""
    qa_status: str = ""
    developer_name: str = ""
    product_module: str = ""
    repo_names: list[str] = field(default_factory=list)
    mysql_queries: list[str] = field(default_factory=list)
    postgresql_queries: list[str] = field(default_factory=list)
    configuration_changes: str = ""
    steps: str = ""
    db_linked_to_hotfix_prod: bool = False
    db_has_repo_change: bool = False
    db_query_part_of_deployable: bool = False
    config_applied_in_production: bool = False
    config_stored_in_repo: bool = False
    config_stored_in_prod_branch: bool = False
    config_must_apply_in_uat: bool = False


@dataclass(frozen=True)
class PatchSummary:
    id: int
    patch_id: str
    patch_type: str
    priority: str
    title: str
    branch_name: str
    developer_name: str
    qa_status: str
    qa_date: str
    patch_date: str
    repos_summary: str
    system_status: str
    manual_status_override: str | None
    final_status: str
    is_urgent: bool
    patch_side: str
    lifecycle: dict[str, str]


@dataclass
class PatchDetail:
    id: int
    patch_id: str
    bug_id: str
    jira_url: str
    title: str
    description: str
    patch_type: str
    priority: str
    branch_name: str
    release_name: str
    patch_date: str
    qa_date: str
    qa_status: str
    developer_name: str
    product_module: str
    system_status: str
    manual_status_override: str | None
    patch_side: str
    lifecycle: dict[str, str]
    blocker_reason: str
    repos: list[str]
    mysql_queries: list[str]
    postgresql_queries: list[str]
    activity: list[dict[str, str]]
    created_by: str
    created_at: str
    updated_by: str
    updated_at: str


def _log_activity(
    conn: Any,
    patch_internal_id: int,
    *,
    action: str,
    operator: str,
    field_name: str = "",
    old_value: str = "",
    new_value: str = "",
) -> None:
    conn.execute(
        """
        INSERT INTO patch_activity_log
            (patch_id, action, field_name, old_value, new_value, updated_by, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            patch_internal_id,
            action,
            field_name,
            old_value,
            new_value,
            operator,
            _utc_now_iso(),
        ),
    )


def create_patch(data: PatchCreateInput, operator: str) -> int:
    operator = normalize_operator(operator)
    patch_key = data.patch_id.strip().upper()
    if not validate_ticket_id(patch_key):
        raise ValueError(f"Invalid patch ID format: {data.patch_id!r}")
    if data.bug_id.strip() and not validate_ticket_id(data.bug_id.strip()):
        raise ValueError(f"Invalid bug ID format: {data.bug_id!r}")

    has_queries = bool(data.mysql_queries or data.postgresql_queries)
    patch_side = compute_patch_side(data.repo_names)
    opts = CreatePatchOptions(
        patch_type=data.patch_type,
        patch_side=patch_side,
        has_queries=has_queries,
        db_linked_to_hotfix_prod=data.db_linked_to_hotfix_prod,
        db_has_repo_change=data.db_has_repo_change,
        db_query_part_of_deployable=data.db_query_part_of_deployable,
        config_applied_in_production=data.config_applied_in_production,
        config_stored_in_repo=data.config_stored_in_repo,
        config_stored_in_prod_branch=data.config_stored_in_prod_branch,
        config_must_apply_in_uat=data.config_must_apply_in_uat,
    )
    lifecycle = compute_initial_lifecycle(opts)
    system_status = compute_system_status(lifecycle, track=_status_track(patch_side))
    now = _utc_now_iso()
    jira_url = data.jira_url.strip() or default_jira_url(patch_key)

    description = data.description.strip()
    if data.configuration_changes.strip():
        description = (
            f"{description}\n\nConfiguration changes:\n{data.configuration_changes.strip()}"
        ).strip()
    if data.steps.strip():
        description = f"{description}\n\nSteps:\n{data.steps.strip()}".strip()

    with db.get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM patches WHERE patch_id = ?",
            (patch_key,),
        ).fetchone()
        if existing:
            raise ValueError(f"Patch ID already exists: {patch_key}")

        cur = conn.execute(
            """
            INSERT INTO patches (
                patch_id, bug_id, jira_url, title, description, patch_type, priority,
                branch_name, release_name, patch_date, qa_date, qa_status, developer_name,
                product_module, patch_side, system_status, manual_status_override,
                db_linked_to_hotfix_prod, db_has_repo_change, db_query_part_of_deployable,
                config_applied_in_production, config_stored_in_repo,
                config_stored_in_prod_branch, config_must_apply_in_uat,
                created_by, created_at, updated_by, updated_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?, ?
            )
            """,
            (
                patch_key,
                data.bug_id.strip().upper() or None,
                jira_url or None,
                data.title.strip(),
                description,
                data.patch_type,
                initial_priority(data.patch_type),
                data.branch_name.strip(),
                data.release_name.strip(),
                data.patch_date.strip() or None,
                data.qa_date.strip() or None,
                data.qa_status.strip(),
                data.developer_name.strip(),
                data.product_module.strip(),
                patch_side,
                system_status,
                None,
                int(data.db_linked_to_hotfix_prod),
                int(data.db_has_repo_change),
                int(data.db_query_part_of_deployable),
                int(data.config_applied_in_production),
                int(data.config_stored_in_repo),
                int(data.config_stored_in_prod_branch),
                int(data.config_must_apply_in_uat),
                operator,
                now,
                operator,
                now,
            ),
        )
        internal_id = int(cur.lastrowid)

        conn.execute(
            """
            INSERT INTO patch_lifecycle_status (
                patch_id, production_status, release_branch_status, prod_branch_status,
                stage_query_status, uat_query_status, uat_deployment_status,
                qa_verification_status, closure_status,
                wm_hotfix_branch_status, wm_master_production_status, wm_release_branch_status,
                wm_integration_stage_status, wm_uat_branch_status,
                wm_stage_query_status, wm_uat_query_status, wm_qa_verification_status,
                wm_closure_status, blocker_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                internal_id,
                lifecycle[config.LIFECYCLE_FIELD_PRODUCTION],
                lifecycle[config.LIFECYCLE_FIELD_RELEASE_BRANCH],
                lifecycle[config.LIFECYCLE_FIELD_PROD_BRANCH],
                lifecycle[config.LIFECYCLE_FIELD_STAGE_QUERY],
                lifecycle[config.LIFECYCLE_FIELD_UAT_QUERY],
                lifecycle[config.LIFECYCLE_FIELD_UAT_DEPLOYMENT],
                lifecycle[config.LIFECYCLE_FIELD_QA],
                lifecycle[config.LIFECYCLE_FIELD_CLOSURE],
                lifecycle[config.WM_LIFECYCLE_FIELD_HOTFIX_BRANCH],
                lifecycle[config.WM_LIFECYCLE_FIELD_MASTER_PRODUCTION],
                lifecycle[config.WM_LIFECYCLE_FIELD_RELEASE_BRANCH],
                lifecycle[config.WM_LIFECYCLE_FIELD_INTEGRATION_STAGE],
                lifecycle[config.WM_LIFECYCLE_FIELD_UAT_BRANCH],
                lifecycle[config.WM_LIFECYCLE_FIELD_STAGE_QUERY],
                lifecycle[config.WM_LIFECYCLE_FIELD_UAT_QUERY],
                lifecycle[config.WM_LIFECYCLE_FIELD_QA],
                lifecycle[config.WM_LIFECYCLE_FIELD_CLOSURE],
                "",
            ),
        )

        for repo in data.repo_names:
            name = repo.strip()
            if name:
                conn.execute(
                    "INSERT INTO patch_repositories (patch_id, repo_name) VALUES (?, ?)",
                    (internal_id, name),
                )

        for text in data.mysql_queries:
            q = text.strip()
            if q:
                conn.execute(
                    """
                    INSERT INTO patch_queries (
                        patch_id, query_type, query_text, stage_status, uat_status
                    ) VALUES (?, 'mysql', ?, ?, ?)
                    """,
                    (
                        internal_id,
                        q,
                        lifecycle[config.LIFECYCLE_FIELD_STAGE_QUERY],
                        lifecycle[config.LIFECYCLE_FIELD_UAT_QUERY],
                    ),
                )

        for text in data.postgresql_queries:
            q = text.strip()
            if q:
                conn.execute(
                    """
                    INSERT INTO patch_queries (
                        patch_id, query_type, query_text, stage_status, uat_status
                    ) VALUES (?, 'postgresql', ?, ?, ?)
                    """,
                    (
                        internal_id,
                        q,
                        lifecycle[config.LIFECYCLE_FIELD_STAGE_QUERY],
                        lifecycle[config.LIFECYCLE_FIELD_UAT_QUERY],
                    ),
                )

        _log_activity(
            conn,
            internal_id,
            action="created",
            operator=operator,
            new_value=patch_key,
        )
        return internal_id


def _is_pending_summary(display: Any) -> bool:
    if display.system_status == config.SYSTEM_STATUS_CLOSED:
        return False
    if display.manual_status_override in config.NEGATIVE_MANUAL_OVERRIDES | {"Duplicate"}:
        return False
    return True


def _side_sql_clause(side_filter: str) -> tuple[str, list[Any]]:
    if side_filter == config.SIDE_FILTER_FC:
        return "patch_side IN (?, ?)", [config.PATCH_SIDE_FC, config.PATCH_SIDE_BOTH]
    if side_filter == config.SIDE_FILTER_WM:
        return "patch_side IN (?, ?)", [config.PATCH_SIDE_WM, config.PATCH_SIDE_BOTH]
    return "1 = 1", []


def list_distinct_branches_for_type(
    *,
    patch_type: str,
    side_filter: str = config.SIDE_FILTER_FC,
) -> list[str]:
    """Branch/release labels for the type sub-filter dropdown (latest first)."""
    side_clause, side_params = _side_sql_clause(side_filter)
    with db.get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT DISTINCT COALESCE(
                NULLIF(TRIM(branch_name), ''),
                NULLIF(TRIM(release_name), '')
            ) AS branch_label
            FROM patches
            WHERE is_archived = 0
              AND patch_type = ?
              AND {side_clause}
              AND branch_label IS NOT NULL
              AND branch_label != ''
            """,
            [patch_type, *side_params],
        ).fetchall()
    labels = [row["branch_label"] for row in rows if row["branch_label"]]
    return sorted(labels, key=branch_sort_key, reverse=True)


def list_patches(
    *,
    patch_type: str | None = None,
    developer: str | None = None,
    branch_name: str | None = None,
    pending_only: bool = False,
    require_pending: bool = False,
    side_filter: str = config.SIDE_FILTER_FC,
) -> list[PatchSummary]:
    clauses = ["is_archived = 0"]
    params: list[Any] = []
    if patch_type:
        clauses.append("patch_type = ?")
        params.append(patch_type)
    if developer:
        clauses.append("LOWER(developer_name) LIKE ?")
        params.append(f"%{developer.strip().lower()}%")
    if branch_name:
        clauses.append(
            "COALESCE(NULLIF(TRIM(branch_name), ''), NULLIF(TRIM(release_name), '')) = ?"
        )
        params.append(branch_name)
    side_clause, side_params = _side_sql_clause(side_filter)
    if side_params:
        clauses.append(side_clause)
        params.extend(side_params)
    where = " AND ".join(clauses)
    track = lifecycle_track_for_filter(side_filter)
    apply_pending = pending_only or require_pending

    summaries: list[PatchSummary] = []
    with db.get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT id, patch_id, patch_type, priority, title, branch_name,
                   developer_name, qa_status, qa_date, patch_date, patch_side,
                   system_status, manual_status_override
            FROM patches
            WHERE {where}
            ORDER BY id DESC
            """,
            params,
        ).fetchall()

        for row in rows:
            if not patch_side_matches_filter(row["patch_side"], side_filter):
                continue
            lc_row = ensure_lifecycle_row(conn, row["id"], row)
            repo_rows = conn.execute(
                """
                SELECT repo_name FROM patch_repositories
                WHERE patch_id = ? ORDER BY id
                """,
                (row["id"],),
            ).fetchall()
            repos_summary = ", ".join(r["repo_name"] for r in repo_rows if r["repo_name"])
            lifecycle = lifecycle_row_to_dict(lc_row)
            display = resolve_patch_status_display(
                lifecycle,
                row["manual_status_override"],
                track=track,
            )
            if apply_pending and not _is_pending_summary(display):
                continue
            summaries.append(
                PatchSummary(
                    id=row["id"],
                    patch_id=row["patch_id"],
                    patch_type=row["patch_type"],
                    priority=row["priority"],
                    title=row["title"],
                    branch_name=row["branch_name"],
                    developer_name=row["developer_name"],
                    qa_status=row["qa_status"],
                    qa_date=row["qa_date"] or "",
                    patch_date=row["patch_date"] or "",
                    repos_summary=repos_summary,
                    patch_side=row["patch_side"],
                    system_status=display.system_status,
                    manual_status_override=display.manual_status_override,
                    final_status=display.final_status,
                    is_urgent=row["priority"] == config.PRIORITY_URGENT
                    and display.system_status != config.SYSTEM_STATUS_CLOSED,
                    lifecycle=lifecycle,
                )
            )
    return summaries


def get_patch(internal_id: int) -> PatchDetail | None:
    with db.get_connection() as conn:
        row = conn.execute("SELECT * FROM patches WHERE id = ?", (internal_id,)).fetchone()
        if not row:
            return None
        lc = ensure_lifecycle_row(conn, internal_id, row)
        repos = [
            r["repo_name"]
            for r in conn.execute(
                "SELECT repo_name FROM patch_repositories WHERE patch_id = ? ORDER BY id",
                (internal_id,),
            ).fetchall()
        ]
        mysql = [
            q["query_text"]
            for q in conn.execute(
                "SELECT query_text FROM patch_queries WHERE patch_id = ? AND query_type = 'mysql'",
                (internal_id,),
            ).fetchall()
        ]
        psql = [
            q["query_text"]
            for q in conn.execute(
                """
                SELECT query_text FROM patch_queries
                WHERE patch_id = ? AND query_type = 'postgresql'
                """,
                (internal_id,),
            ).fetchall()
        ]
        activity_rows = conn.execute(
            """
            SELECT action, field_name, old_value, new_value, updated_by, updated_at
            FROM patch_activity_log WHERE patch_id = ?
            ORDER BY id DESC
            LIMIT 50
            """,
            (internal_id,),
        ).fetchall()

    lifecycle = lifecycle_row_to_dict(lc)
    patch_side = row["patch_side"] or config.PATCH_SIDE_FC
    display = resolve_patch_status_display(
        lifecycle,
        row["manual_status_override"],
        track=_status_track(patch_side),
    )

    return PatchDetail(
        id=row["id"],
        patch_id=row["patch_id"],
        bug_id=row["bug_id"] or "",
        jira_url=row["jira_url"] or "",
        title=row["title"] or "",
        description=row["description"] or "",
        patch_type=row["patch_type"],
        priority=row["priority"],
        branch_name=row["branch_name"] or "",
        release_name=row["release_name"] or "",
        patch_date=row["patch_date"] or "",
        qa_date=row["qa_date"] or "",
        qa_status=row["qa_status"] or "",
        developer_name=row["developer_name"] or "",
        product_module=row["product_module"] or "",
        patch_side=patch_side,
        system_status=display.system_status,
        manual_status_override=display.manual_status_override,
        lifecycle=lifecycle,
        blocker_reason=lc["blocker_reason"] if lc else "",
        repos=repos,
        mysql_queries=mysql,
        postgresql_queries=psql,
        activity=[dict(r) for r in activity_rows],
        created_by=row["created_by"],
        created_at=row["created_at"],
        updated_by=row["updated_by"],
        updated_at=row["updated_at"],
    )


def update_lifecycle(
    internal_id: int,
    lifecycle: dict[str, str],
    operator: str,
    *,
    manual_status_override: str | None = None,
    blocker_reason: str = "",
) -> None:
    from logic import validate_status_transition

    operator = normalize_operator(operator)
    with db.get_connection() as conn:
        old_lc_row = conn.execute(
            "SELECT * FROM patch_lifecycle_status WHERE patch_id = ?",
            (internal_id,),
        ).fetchone()
        if not old_lc_row:
            raise ValueError("Patch lifecycle not found")
        old_lc = lifecycle_row_to_dict(old_lc_row)
        merged = {**old_lc, **{k: lifecycle[k] for k in lifecycle if k in config.ALL_LIFECYCLE_FIELDS}}

        for field_name in config.ALL_LIFECYCLE_FIELDS:
            if field_name not in lifecycle:
                continue
            new_val = lifecycle[field_name]
            old_val = old_lc.get(field_name, "")
            if new_val == old_val:
                continue
            err = validate_status_transition(field_name, old_val, new_val, merged)
            if err:
                raise ValueError(err)
            _log_activity(
                conn,
                internal_id,
                action="status_change",
                operator=operator,
                field_name=field_name,
                old_value=old_val,
                new_value=new_val,
            )

        patch_row = conn.execute(
            "SELECT patch_side FROM patches WHERE id = ?",
            (internal_id,),
        ).fetchone()
        patch_side = patch_row["patch_side"] if patch_row else config.PATCH_SIDE_FC

        conn.execute(
            """
            UPDATE patch_lifecycle_status SET
                production_status = ?,
                release_branch_status = ?,
                prod_branch_status = ?,
                stage_query_status = ?,
                uat_query_status = ?,
                uat_deployment_status = ?,
                qa_verification_status = ?,
                closure_status = ?,
                wm_hotfix_branch_status = ?,
                wm_master_production_status = ?,
                wm_release_branch_status = ?,
                wm_integration_stage_status = ?,
                wm_uat_branch_status = ?,
                wm_stage_query_status = ?,
                wm_uat_query_status = ?,
                wm_qa_verification_status = ?,
                wm_closure_status = ?,
                blocker_reason = ?
            WHERE patch_id = ?
            """,
            (
                merged[config.LIFECYCLE_FIELD_PRODUCTION],
                merged[config.LIFECYCLE_FIELD_RELEASE_BRANCH],
                merged[config.LIFECYCLE_FIELD_PROD_BRANCH],
                merged[config.LIFECYCLE_FIELD_STAGE_QUERY],
                merged[config.LIFECYCLE_FIELD_UAT_QUERY],
                merged[config.LIFECYCLE_FIELD_UAT_DEPLOYMENT],
                merged[config.LIFECYCLE_FIELD_QA],
                merged[config.LIFECYCLE_FIELD_CLOSURE],
                merged[config.WM_LIFECYCLE_FIELD_HOTFIX_BRANCH],
                merged[config.WM_LIFECYCLE_FIELD_MASTER_PRODUCTION],
                merged[config.WM_LIFECYCLE_FIELD_RELEASE_BRANCH],
                merged[config.WM_LIFECYCLE_FIELD_INTEGRATION_STAGE],
                merged[config.WM_LIFECYCLE_FIELD_UAT_BRANCH],
                merged[config.WM_LIFECYCLE_FIELD_STAGE_QUERY],
                merged[config.WM_LIFECYCLE_FIELD_UAT_QUERY],
                merged[config.WM_LIFECYCLE_FIELD_QA],
                merged[config.WM_LIFECYCLE_FIELD_CLOSURE],
                blocker_reason,
                internal_id,
            ),
        )

        new_system = compute_system_status(merged, track=_status_track(patch_side))
        override = manual_status_override if manual_status_override else None
        now = _utc_now_iso()
        conn.execute(
            """
            UPDATE patches SET
                system_status = ?,
                manual_status_override = ?,
                updated_by = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (new_system, override, operator, now, internal_id),
        )
