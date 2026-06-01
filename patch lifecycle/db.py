"""SQLite schema and connection for Patch Lifecycle."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import config

SCHEMA_VERSION = 2

_SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS patches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patch_id TEXT NOT NULL UNIQUE,
    bug_id TEXT,
    jira_url TEXT,
    title TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    patch_type TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'normal',
    branch_name TEXT NOT NULL DEFAULT '',
    release_name TEXT NOT NULL DEFAULT '',
    patch_date TEXT,
    qa_date TEXT,
    qa_status TEXT NOT NULL DEFAULT '',
    developer_name TEXT NOT NULL DEFAULT '',
    product_module TEXT NOT NULL DEFAULT '',
    patch_side TEXT NOT NULL DEFAULT 'fc',
    system_status TEXT NOT NULL DEFAULT '',
    manual_status_override TEXT,
    db_linked_to_hotfix_prod INTEGER NOT NULL DEFAULT 0,
    db_has_repo_change INTEGER NOT NULL DEFAULT 0,
    db_query_part_of_deployable INTEGER NOT NULL DEFAULT 0,
    config_applied_in_production INTEGER NOT NULL DEFAULT 0,
    config_stored_in_repo INTEGER NOT NULL DEFAULT 0,
    config_stored_in_prod_branch INTEGER NOT NULL DEFAULT 0,
    config_must_apply_in_uat INTEGER NOT NULL DEFAULT 0,
    is_archived INTEGER NOT NULL DEFAULT 0,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_by TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS patch_repositories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patch_id INTEGER NOT NULL REFERENCES patches(id) ON DELETE CASCADE,
    repo_name TEXT NOT NULL DEFAULT '',
    service_name TEXT NOT NULL DEFAULT '',
    rpm_name TEXT NOT NULL DEFAULT '',
    extra_repo TEXT NOT NULL DEFAULT '',
    build_notes TEXT NOT NULL DEFAULT '',
    deployment_notes TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS patch_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patch_id INTEGER NOT NULL REFERENCES patches(id) ON DELETE CASCADE,
    query_type TEXT NOT NULL,
    query_text TEXT NOT NULL DEFAULT '',
    stage_status TEXT NOT NULL DEFAULT 'Not Required',
    stage_executed_by TEXT,
    stage_executed_at TEXT,
    uat_status TEXT NOT NULL DEFAULT 'Not Required',
    uat_executed_by TEXT,
    uat_executed_at TEXT,
    rollback_query TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS patch_lifecycle_status (
    patch_id INTEGER PRIMARY KEY REFERENCES patches(id) ON DELETE CASCADE,
    production_status TEXT NOT NULL,
    release_branch_status TEXT NOT NULL,
    prod_branch_status TEXT NOT NULL,
    stage_query_status TEXT NOT NULL,
    uat_query_status TEXT NOT NULL,
    uat_deployment_status TEXT NOT NULL,
    qa_verification_status TEXT NOT NULL,
    closure_status TEXT NOT NULL,
    wm_hotfix_branch_status TEXT NOT NULL DEFAULT 'Not Required',
    wm_master_production_status TEXT NOT NULL DEFAULT 'Not Required',
    wm_release_branch_status TEXT NOT NULL DEFAULT 'Not Required',
    wm_integration_stage_status TEXT NOT NULL DEFAULT 'Not Required',
    wm_uat_branch_status TEXT NOT NULL DEFAULT 'Not Required',
    wm_stage_query_status TEXT NOT NULL DEFAULT 'Not Required',
    wm_uat_query_status TEXT NOT NULL DEFAULT 'Not Required',
    wm_qa_verification_status TEXT NOT NULL DEFAULT 'Not Required',
    wm_closure_status TEXT NOT NULL DEFAULT 'Not Required',
    blocker_reason TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS patch_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patch_id INTEGER NOT NULL REFERENCES patches(id) ON DELETE CASCADE,
    link_type TEXT NOT NULL,
    url TEXT NOT NULL,
    label TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS patch_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patch_id INTEGER NOT NULL REFERENCES patches(id) ON DELETE CASCADE,
    author TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS patch_activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patch_id INTEGER NOT NULL REFERENCES patches(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    field_name TEXT NOT NULL DEFAULT '',
    old_value TEXT NOT NULL DEFAULT '',
    new_value TEXT NOT NULL DEFAULT '',
    updated_by TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_patches_patch_id ON patches(patch_id);
CREATE INDEX IF NOT EXISTS idx_patches_system_status ON patches(system_status);
CREATE INDEX IF NOT EXISTS idx_patches_developer ON patches(developer_name);
CREATE INDEX IF NOT EXISTS idx_patches_type ON patches(patch_type);
"""

_MIGRATION_V2_SQL = (
    "ALTER TABLE patches ADD COLUMN patch_side TEXT NOT NULL DEFAULT 'fc'",
    "ALTER TABLE patch_lifecycle_status ADD COLUMN wm_hotfix_branch_status TEXT NOT NULL DEFAULT 'Not Required'",
    "ALTER TABLE patch_lifecycle_status ADD COLUMN wm_master_production_status TEXT NOT NULL DEFAULT 'Not Required'",
    "ALTER TABLE patch_lifecycle_status ADD COLUMN wm_release_branch_status TEXT NOT NULL DEFAULT 'Not Required'",
    "ALTER TABLE patch_lifecycle_status ADD COLUMN wm_integration_stage_status TEXT NOT NULL DEFAULT 'Not Required'",
    "ALTER TABLE patch_lifecycle_status ADD COLUMN wm_uat_branch_status TEXT NOT NULL DEFAULT 'Not Required'",
    "ALTER TABLE patch_lifecycle_status ADD COLUMN wm_stage_query_status TEXT NOT NULL DEFAULT 'Not Required'",
    "ALTER TABLE patch_lifecycle_status ADD COLUMN wm_uat_query_status TEXT NOT NULL DEFAULT 'Not Required'",
    "ALTER TABLE patch_lifecycle_status ADD COLUMN wm_qa_verification_status TEXT NOT NULL DEFAULT 'Not Required'",
    "ALTER TABLE patch_lifecycle_status ADD COLUMN wm_closure_status TEXT NOT NULL DEFAULT 'Not Required'",
)


def ensure_data_dir() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def _apply_migrations(conn: sqlite3.Connection, current_version: int) -> None:
    if current_version >= SCHEMA_VERSION:
        return

    if current_version < 2:
        patch_cols = _table_columns(conn, "patches")
        if "patch_side" not in patch_cols:
            conn.execute(_MIGRATION_V2_SQL[0])

        lc_cols = _table_columns(conn, "patch_lifecycle_status")
        for statement in _MIGRATION_V2_SQL[1:]:
            col_name = statement.split("ADD COLUMN ")[1].split(" ")[0]
            if col_name not in lc_cols:
                conn.execute(statement)

        conn.execute("UPDATE schema_version SET version = ?", (2,))


def _ensure_side_index(conn: sqlite3.Connection) -> None:
    if "patch_side" in _table_columns(conn, "patches"):
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_patches_side ON patches(patch_side)"
        )


def _backfill_patch_sides(conn: sqlite3.Connection) -> None:
    from logic import compute_patch_side

    if "patch_side" not in _table_columns(conn, "patches"):
        return

    rows = conn.execute("SELECT id FROM patches").fetchall()
    for row in rows:
        internal_id = row["id"]
        repos = [
            r["repo_name"]
            for r in conn.execute(
                "SELECT repo_name FROM patch_repositories WHERE patch_id = ?",
                (internal_id,),
            ).fetchall()
        ]
        side = compute_patch_side(repos)
        conn.execute(
            "UPDATE patches SET patch_side = ? WHERE id = ?",
            (side, internal_id),
        )


def init_db(db_path: Path | None = None) -> None:
    """Create database file and tables if missing."""
    ensure_data_dir()
    path = db_path or config.DATABASE_PATH
    with get_connection(path) as conn:
        conn.executescript(_SCHEMA_SQL)
        row = conn.execute("SELECT version FROM schema_version LIMIT 1").fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO schema_version (version) VALUES (?)",
                (SCHEMA_VERSION,),
            )
            current_version = SCHEMA_VERSION
        else:
            current_version = int(row["version"])

        _apply_migrations(conn, current_version)
        _ensure_side_index(conn)
        _backfill_patch_sides(conn)


@contextmanager
def get_connection(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    path = db_path or config.DATABASE_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
