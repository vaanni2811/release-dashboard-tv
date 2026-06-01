"""Configuration for Patch Lifecycle."""

from __future__ import annotations

import os
import re
from pathlib import Path

TOOL_ROOT = Path(__file__).resolve().parent
DATA_DIR = TOOL_ROOT / "data"
DATABASE_PATH = DATA_DIR / "patches.db"

# Primary patch id and optional bug id (e.g. FCSKY-122193, FCSKY-120767).
TICKET_ID_PATTERN = re.compile(r"^[A-Z][A-Z0-9]+-\d+$", re.IGNORECASE)

# Optional: set in .env as JIRA_BROWSE_BASE=https://your-org.atlassian.net/browse/
JIRA_BROWSE_BASE: str = os.environ.get("JIRA_BROWSE_BASE", "").rstrip("/")
if JIRA_BROWSE_BASE and not JIRA_BROWSE_BASE.endswith("/browse"):
    JIRA_BROWSE_BASE = f"{JIRA_BROWSE_BASE}/browse"

# --- Patch types ---
PATCH_TYPE_WEEKLY = "Weekly Hotfix"
PATCH_TYPE_URGENT = "Urgent Hotfix"
PATCH_TYPE_RELEASE = "Release Patch"
PATCH_TYPE_DB_QUERY = "DB Query Patch"
PATCH_TYPE_CONFIG = "Configuration Patch"

PATCH_TYPES: tuple[str, ...] = (
    PATCH_TYPE_WEEKLY,
    PATCH_TYPE_URGENT,
    PATCH_TYPE_RELEASE,
    PATCH_TYPE_DB_QUERY,
    PATCH_TYPE_CONFIG,
)

PRIORITY_NORMAL = "normal"
PRIORITY_URGENT = "urgent"

# --- Lifecycle status values ---
STATUS_NOT_REQUIRED = "Not Required"
STATUS_PENDING = "Pending"
STATUS_IN_PROGRESS = "In Progress"
STATUS_COMPLETED = "Completed"
STATUS_BLOCKED = "Blocked"
STATUS_FAILED = "Failed"
STATUS_SKIPPED = "Skipped"

LIFECYCLE_STATUSES: tuple[str, ...] = (
    STATUS_NOT_REQUIRED,
    STATUS_PENDING,
    STATUS_IN_PROGRESS,
    STATUS_COMPLETED,
    STATUS_BLOCKED,
    STATUS_FAILED,
    STATUS_SKIPPED,
)

# Keys in patch_lifecycle_status row (and logic dicts).
LIFECYCLE_FIELD_PRODUCTION = "production_status"
LIFECYCLE_FIELD_RELEASE_BRANCH = "release_branch_status"
LIFECYCLE_FIELD_PROD_BRANCH = "prod_branch_status"
LIFECYCLE_FIELD_STAGE_QUERY = "stage_query_status"
LIFECYCLE_FIELD_UAT_QUERY = "uat_query_status"
LIFECYCLE_FIELD_UAT_DEPLOYMENT = "uat_deployment_status"
LIFECYCLE_FIELD_QA = "qa_verification_status"
LIFECYCLE_FIELD_CLOSURE = "closure_status"

LIFECYCLE_FIELDS: tuple[str, ...] = (
    LIFECYCLE_FIELD_PRODUCTION,
    LIFECYCLE_FIELD_RELEASE_BRANCH,
    LIFECYCLE_FIELD_PROD_BRANCH,
    LIFECYCLE_FIELD_STAGE_QUERY,
    LIFECYCLE_FIELD_UAT_QUERY,
    LIFECYCLE_FIELD_UAT_DEPLOYMENT,
    LIFECYCLE_FIELD_QA,
    LIFECYCLE_FIELD_CLOSURE,
)

# Order used when deriving system status (first actionable item wins).
LIFECYCLE_STATUS_ORDER: tuple[str, ...] = (
    LIFECYCLE_FIELD_PRODUCTION,
    LIFECYCLE_FIELD_RELEASE_BRANCH,
    LIFECYCLE_FIELD_PROD_BRANCH,
    LIFECYCLE_FIELD_STAGE_QUERY,
    LIFECYCLE_FIELD_UAT_QUERY,
    LIFECYCLE_FIELD_UAT_DEPLOYMENT,
    LIFECYCLE_FIELD_QA,
)

# Computed system status labels (prefix "Pending " added in logic when step is open).
LIFECYCLE_COMPUTED_LABELS: dict[str, str] = {
    LIFECYCLE_FIELD_PRODUCTION: "Pending Production",
    LIFECYCLE_FIELD_RELEASE_BRANCH: "Pending Release Branch",
    LIFECYCLE_FIELD_PROD_BRANCH: "Pending Prod Branch",
    LIFECYCLE_FIELD_STAGE_QUERY: "Pending Stage Query",
    LIFECYCLE_FIELD_UAT_QUERY: "Pending UAT Query",
    LIFECYCLE_FIELD_UAT_DEPLOYMENT: "Pending UAT Deployment",
    LIFECYCLE_FIELD_QA: "Pending QA Verification",
}

SYSTEM_STATUS_BLOCKED = "Blocked"
SYSTEM_STATUS_READY_TO_CLOSE = "Ready to Close"
SYSTEM_STATUS_CLOSED = "Closed"

# Manual final-status overrides (optional; when set, UI shows override + system status).
MANUAL_STATUS_OVERRIDES: tuple[str, ...] = (
    "On Hold",
    "Blocked by Dev",
    "Blocked by QA",
    "Waiting for Approval",
    "Duplicate",
    "Cancelled",
    "Not Going in Release",
)

# --- Operators (pilot team; extend in config as team grows) ---
OPERATORS: tuple[str, ...] = (
    "Vanni Chaudhary",
    "Tanisha Rawat",
)

DEFAULT_OPERATOR: str = OPERATORS[0]

# Streamlit session_state key for the sidebar operator dropdown.
OPERATOR_SESSION_KEY = "patch_lifecycle_operator"
