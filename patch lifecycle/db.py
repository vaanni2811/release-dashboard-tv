"""SQLite schema and connection for Patch Lifecycle."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import config

SCHEMA_VERSION = 1

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


def ensure_data_dir() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)


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
