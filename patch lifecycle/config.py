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

# --- Patch sides (FC / WM / Both) ---
PATCH_SIDE_FC = "fc"
PATCH_SIDE_WM = "wm"
PATCH_SIDE_BOTH = "both"

PATCH_SIDES: tuple[str, ...] = (PATCH_SIDE_FC, PATCH_SIDE_WM, PATCH_SIDE_BOTH)

PATCH_SIDE_LABELS: dict[str, str] = {
    PATCH_SIDE_FC: "FC",
    PATCH_SIDE_WM: "WM",
    PATCH_SIDE_BOTH: "Both",
}

SIDE_FILTER_FC = "FC Patches"
SIDE_FILTER_WM = "WM Patches"
SIDE_FILTER_ALL = "All Patches"

SIDE_FILTERS: tuple[str, ...] = (SIDE_FILTER_FC, SIDE_FILTER_WM, SIDE_FILTER_ALL)

SIDE_FILTER_SESSION_KEY = "patch_lifecycle_side_filter"

# Sub-filter sentinels (type → branch / pending scope).
SUBFILTER_ALL = "__all__"
SUBFILTER_PENDING = "__pending__"

# --- Patch types ---
PATCH_TYPE_WEEKLY = "Weekly Hotfix"
PATCH_TYPE_URGENT = "Urgent Hotfix"
PATCH_TYPE_DEMO_UAT = "Demo UAT Patch"
PATCH_TYPE_RELEASE = "Release Patch"
PATCH_TYPE_DB_QUERY = "DB Query Patch"
PATCH_TYPE_CONFIG = "Configuration Patch"

PATCH_TYPES: tuple[str, ...] = (
    PATCH_TYPE_WEEKLY,
    PATCH_TYPE_URGENT,
    PATCH_TYPE_DEMO_UAT,
    PATCH_TYPE_RELEASE,
    PATCH_TYPE_DB_QUERY,
    PATCH_TYPE_CONFIG,
)

WM_HOTFIX_PATCH_TYPES: frozenset[str] = frozenset(
    {PATCH_TYPE_WEEKLY, PATCH_TYPE_URGENT, PATCH_TYPE_DEMO_UAT}
)

PRIORITY_NORMAL = "normal"
PRIORITY_URGENT = "urgent"

# --- WM repositories ---
WM_REPOS_CANONICAL: frozenset[str] = frozenset(
    {
        "platform",
        "platform-ng",
        "platform-og",
        "bifrost",
        "deckard",
        "deepthought",
        "megamind",
        "mater",
        "platform-icons",
        "hedwig",
        "devops",
    }
)

WM_REPO_SHORTHANDS: dict[str, str] = {
    "platform": "platform",
    "platform-ng": "platform-ng",
    "ng": "platform-ng",
    "platform-og": "platform-og",
    "og": "platform-og",
    "bifrost": "bifrost",
    "deckard": "deckard",
    "deepthought": "deepthought",
    "megamind": "megamind",
    "mater": "mater",
    "platform-icons": "platform-icons",
    "icons": "platform-icons",
    "hedwig": "hedwig",
    "devops": "devops",
}

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

# FC lifecycle field keys (patch_lifecycle_status columns).
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

LIFECYCLE_STATUS_ORDER: tuple[str, ...] = (
    LIFECYCLE_FIELD_PRODUCTION,
    LIFECYCLE_FIELD_RELEASE_BRANCH,
    LIFECYCLE_FIELD_PROD_BRANCH,
    LIFECYCLE_FIELD_STAGE_QUERY,
    LIFECYCLE_FIELD_UAT_QUERY,
    LIFECYCLE_FIELD_UAT_DEPLOYMENT,
    LIFECYCLE_FIELD_QA,
)

LIFECYCLE_COMPUTED_LABELS: dict[str, str] = {
    LIFECYCLE_FIELD_PRODUCTION: "Pending Production",
    LIFECYCLE_FIELD_RELEASE_BRANCH: "Pending Release Branch",
    LIFECYCLE_FIELD_PROD_BRANCH: "Pending Prod Branch",
    LIFECYCLE_FIELD_STAGE_QUERY: "Pending Stage Query",
    LIFECYCLE_FIELD_UAT_QUERY: "Pending UAT Query",
    LIFECYCLE_FIELD_UAT_DEPLOYMENT: "Pending UAT Deployment",
    LIFECYCLE_FIELD_QA: "Pending QA Verification",
}

# WM lifecycle field keys.
WM_LIFECYCLE_FIELD_HOTFIX_BRANCH = "wm_hotfix_branch_status"
WM_LIFECYCLE_FIELD_MASTER_PRODUCTION = "wm_master_production_status"
WM_LIFECYCLE_FIELD_RELEASE_BRANCH = "wm_release_branch_status"
WM_LIFECYCLE_FIELD_INTEGRATION_STAGE = "wm_integration_stage_status"
WM_LIFECYCLE_FIELD_UAT_BRANCH = "wm_uat_branch_status"
WM_LIFECYCLE_FIELD_STAGE_QUERY = "wm_stage_query_status"
WM_LIFECYCLE_FIELD_UAT_QUERY = "wm_uat_query_status"
WM_LIFECYCLE_FIELD_QA = "wm_qa_verification_status"
WM_LIFECYCLE_FIELD_CLOSURE = "wm_closure_status"

WM_LIFECYCLE_FIELDS: tuple[str, ...] = (
    WM_LIFECYCLE_FIELD_HOTFIX_BRANCH,
    WM_LIFECYCLE_FIELD_MASTER_PRODUCTION,
    WM_LIFECYCLE_FIELD_RELEASE_BRANCH,
    WM_LIFECYCLE_FIELD_INTEGRATION_STAGE,
    WM_LIFECYCLE_FIELD_UAT_BRANCH,
    WM_LIFECYCLE_FIELD_STAGE_QUERY,
    WM_LIFECYCLE_FIELD_UAT_QUERY,
    WM_LIFECYCLE_FIELD_QA,
    WM_LIFECYCLE_FIELD_CLOSURE,
)

WM_LIFECYCLE_STATUS_ORDER: tuple[str, ...] = (
    WM_LIFECYCLE_FIELD_HOTFIX_BRANCH,
    WM_LIFECYCLE_FIELD_MASTER_PRODUCTION,
    WM_LIFECYCLE_FIELD_RELEASE_BRANCH,
    WM_LIFECYCLE_FIELD_INTEGRATION_STAGE,
    WM_LIFECYCLE_FIELD_UAT_BRANCH,
    WM_LIFECYCLE_FIELD_STAGE_QUERY,
    WM_LIFECYCLE_FIELD_UAT_QUERY,
    WM_LIFECYCLE_FIELD_QA,
)

WM_LIFECYCLE_COMPUTED_LABELS: dict[str, str] = {
    WM_LIFECYCLE_FIELD_HOTFIX_BRANCH: "Pending Hotfix Branch",
    WM_LIFECYCLE_FIELD_MASTER_PRODUCTION: "Pending Master / Production",
    WM_LIFECYCLE_FIELD_RELEASE_BRANCH: "Pending Release Branch",
    WM_LIFECYCLE_FIELD_INTEGRATION_STAGE: "Pending WM-FC Integration / Stage",
    WM_LIFECYCLE_FIELD_UAT_BRANCH: "Pending UAT Branch",
    WM_LIFECYCLE_FIELD_STAGE_QUERY: "Pending Stage Query",
    WM_LIFECYCLE_FIELD_UAT_QUERY: "Pending UAT Query",
    WM_LIFECYCLE_FIELD_QA: "Pending QA Verification",
}

ALL_LIFECYCLE_FIELDS: tuple[str, ...] = LIFECYCLE_FIELDS + WM_LIFECYCLE_FIELDS

SYSTEM_STATUS_BLOCKED = "Blocked"
SYSTEM_STATUS_READY_TO_CLOSE = "Ready to Close"
SYSTEM_STATUS_CLOSED = "Closed"

MANUAL_STATUS_OVERRIDES: tuple[str, ...] = (
    "On Hold",
    "Blocked by Dev",
    "Blocked by QA",
    "Waiting for Approval",
    "Duplicate",
    "Cancelled",
    "Reverted",
    "Not Going in Release",
)

# Manual overrides that mark a patch inactive (excluded from pending; red row).
NEGATIVE_MANUAL_OVERRIDES: frozenset[str] = frozenset({"Cancelled", "Reverted"})

OPERATORS: tuple[str, ...] = (
    "Vanni Chaudhary",
    "Tanisha Rawat",
)

DEFAULT_OPERATOR: str = OPERATORS[0]
OPERATOR_SESSION_KEY = "patch_lifecycle_operator"
