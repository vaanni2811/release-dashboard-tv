#!/usr/bin/env python3
"""Seed sample patches for dashboard demo (hotfix_r26q2.14). Run once:

    cd "patch lifecycle"
    python seed_sample_data.py
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import config
import db
import repository
from repository import PatchCreateInput

BRANCH = "hotfix_r26q2.14"
OPERATOR = config.DEFAULT_OPERATOR
C = config.STATUS_COMPLETED
P = config.STATUS_PENDING
IP = config.STATUS_IN_PROGRESS
B = config.STATUS_BLOCKED
NR = config.STATUS_NOT_REQUIRED

FC_FIELDS = config.LIFECYCLE_FIELDS
WM_FIELDS = config.WM_LIFECYCLE_FIELDS

FC_REPOS = ("fcsky", "fcsky-ui", "fcsky-rest", "fconnect-config", "fcsky-mobile")
WM_REPOS = ("bifrost", "platform-ng", "deckard", "megamind", "hedwig", "deepthought", "mater", "platform-icons", "devops", "platform-og")
DEVELOPERS = (
    "Vanni Chaudhary",
    "Tanisha Rawat",
    "Chandan Yadav",
    "Rajesh Kumar",
    "Priya Sharma",
    "Amit Singh",
    "Neha Gupta",
    "Rohit Mehta",
    "Sneha Patel",
    "Karan Joshi",
)
MODULES = ("Sales", "Finance", "Operations", "Marketing", "Support", "HR", "Inventory", "CRM", "Reporting", "Admin")


def _fc_all(**overrides: str) -> dict[str, str]:
    base = {f: NR for f in FC_FIELDS}
    base[config.LIFECYCLE_FIELD_CLOSURE] = P
    base.update(overrides)
    return base


def _wm_all(**overrides: str) -> dict[str, str]:
    base = {f: NR for f in WM_FIELDS}
    base[config.WM_LIFECYCLE_FIELD_CLOSURE] = P
    base.update(overrides)
    return base


def _fc_ready(**overrides: str) -> dict[str, str]:
    return _fc_all(
        **{
            config.LIFECYCLE_FIELD_PRODUCTION: C,
            config.LIFECYCLE_FIELD_RELEASE_BRANCH: C,
            config.LIFECYCLE_FIELD_PROD_BRANCH: C,
            config.LIFECYCLE_FIELD_STAGE_QUERY: C,
            config.LIFECYCLE_FIELD_UAT_QUERY: C,
            config.LIFECYCLE_FIELD_UAT_DEPLOYMENT: C,
            config.LIFECYCLE_FIELD_QA: C,
            config.LIFECYCLE_FIELD_CLOSURE: P,
        },
        **overrides,
    )


def _wm_ready(**overrides: str) -> dict[str, str]:
    return _wm_all(
        **{
            config.WM_LIFECYCLE_FIELD_HOTFIX_BRANCH: C,
            config.WM_LIFECYCLE_FIELD_MASTER_PRODUCTION: C,
            config.WM_LIFECYCLE_FIELD_RELEASE_BRANCH: C,
            config.WM_LIFECYCLE_FIELD_INTEGRATION_STAGE: C,
            config.WM_LIFECYCLE_FIELD_UAT_BRANCH: C,
            config.WM_LIFECYCLE_FIELD_STAGE_QUERY: C,
            config.WM_LIFECYCLE_FIELD_UAT_QUERY: C,
            config.WM_LIFECYCLE_FIELD_QA: C,
            config.WM_LIFECYCLE_FIELD_CLOSURE: P,
        },
        **overrides,
    )


def _fc_closed() -> dict[str, str]:
    return _fc_all(
        **{
            config.LIFECYCLE_FIELD_PRODUCTION: C,
            config.LIFECYCLE_FIELD_RELEASE_BRANCH: C,
            config.LIFECYCLE_FIELD_PROD_BRANCH: C,
            config.LIFECYCLE_FIELD_STAGE_QUERY: C,
            config.LIFECYCLE_FIELD_UAT_QUERY: C,
            config.LIFECYCLE_FIELD_UAT_DEPLOYMENT: C,
            config.LIFECYCLE_FIELD_QA: C,
            config.LIFECYCLE_FIELD_CLOSURE: C,
        }
    )


def _wm_closed() -> dict[str, str]:
    return _wm_all(
        **{
            config.WM_LIFECYCLE_FIELD_HOTFIX_BRANCH: C,
            config.WM_LIFECYCLE_FIELD_MASTER_PRODUCTION: C,
            config.WM_LIFECYCLE_FIELD_RELEASE_BRANCH: C,
            config.WM_LIFECYCLE_FIELD_INTEGRATION_STAGE: C,
            config.WM_LIFECYCLE_FIELD_UAT_BRANCH: C,
            config.WM_LIFECYCLE_FIELD_STAGE_QUERY: C,
            config.WM_LIFECYCLE_FIELD_UAT_QUERY: C,
            config.WM_LIFECYCLE_FIELD_QA: C,
            config.WM_LIFECYCLE_FIELD_CLOSURE: C,
        }
    )


def _patch_created_days_ago(internal_id: int, days: int) -> None:
    ts = (datetime.now(timezone.utc) - timedelta(days=days)).replace(microsecond=0).isoformat()
    with db.get_connection() as conn:
        conn.execute(
            "UPDATE patches SET created_at = ?, updated_at = ? WHERE id = ?",
            (ts, ts, internal_id),
        )


def _seed_fc_weekly() -> list[int]:
    scenarios: list[tuple[str, dict, str | None, list[str], bool]] = [
        ("Login timeout on franchise dashboard", {}, None, [], False),
        ("Fix NPE in royalty calculation export", {"production_status": C, "release_branch_status": IP}, None, [], False),
        (
            "Patch payment gateway callback URL",
            _fc_ready(),
            None,
            [],
            False,
        ),
        ("Closed: invoice PDF footer alignment", _fc_closed(), None, [], False),
        (
            "UAT blocked — franchisee list filter",
            _fc_all(
                production_status=C,
                release_branch_status=C,
                prod_branch_status=C,
                stage_query_status=C,
                uat_query_status=B,
                uat_deployment_status=P,
            ),
            None,
            [],
            False,
        ),
        (
            "Pending UAT deploy — training module",
            _fc_all(
                production_status=C,
                release_branch_status=C,
                prod_branch_status=C,
                stage_query_status=C,
                uat_query_status=C,
                uat_deployment_status=P,
            ),
            None,
            [],
            False,
        ),
        (
            "DB index for lead search",
            _fc_all(
                production_status=C,
                release_branch_status=C,
                prod_branch_status=IP,
                stage_query_status=P,
                uat_query_status=NR,
            ),
            None,
            ["CREATE INDEX idx_leads ON leads(status);"],
            True,
        ),
        ("Cancelled duplicate entry fix", {}, "Cancelled", [], False),
        ("Reverted — experimental cache toggle", _fc_all(production_status=C), "Reverted", [], False),
        (
            "Ready to close — audit log export",
            _fc_ready(),
            None,
            [],
            False,
        ),
    ]
    ids: list[int] = []
    for i, (title, lc, override, queries, _) in enumerate(scenarios):
        pid = repository.create_patch(
            PatchCreateInput(
                patch_id=f"FCSKY-991{i + 1:03d}",
                patch_type=config.PATCH_TYPE_WEEKLY,
                title=title,
                branch_name=BRANCH,
                developer_name=DEVELOPERS[i],
                product_module=MODULES[i],
                qa_status=("Pass" if lc.get(config.LIFECYCLE_FIELD_QA) == C else "Pending"),
                patch_date=(datetime.now(timezone.utc) - timedelta(days=i)).strftime("%Y-%m-%d"),
                repo_names=[FC_REPOS[i % len(FC_REPOS)]],
                mysql_queries=queries,
            ),
            OPERATOR,
        )
        patch = repository.get_patch(pid)
        assert patch is not None
        if lc:
            repository.update_lifecycle(
                pid,
                {**patch.lifecycle, **lc},
                OPERATOR,
                manual_status_override=override,
            )
        _patch_created_days_ago(pid, [1, 2, 4, 6, 3, 5, 8, 11, 14, 2][i])
        ids.append(pid)
    return ids


def _seed_wm_weekly() -> list[int]:
    scenarios: list[tuple[str, dict, str | None, list[str]]] = [
        ("Platform NG menu permissions", {}, None, []),
        (
            "Bifrost API rate limit config",
            {"wm_hotfix_branch_status": C, "wm_master_production_status": IP},
            None,
            [],
        ),
        ("Ready — deckard widget cache bust", _wm_ready(), None, []),
        ("Closed — megamind notification batch", _wm_closed(), None, []),
        (
            "Blocked WM stage integration",
            _wm_all(
                wm_hotfix_branch_status=C,
                wm_master_production_status=C,
                wm_release_branch_status=C,
                wm_integration_stage_status=B,
            ),
            None,
            [],
        ),
        (
            "Pending UAT branch — hedwig templates",
            _wm_all(
                wm_hotfix_branch_status=C,
                wm_master_production_status=C,
                wm_release_branch_status=C,
                wm_integration_stage_status=C,
                wm_uat_branch_status=P,
            ),
            None,
            [],
        ),
        (
            "WM query pending stage execution",
            _wm_all(
                wm_hotfix_branch_status=C,
                wm_master_production_status=C,
                wm_stage_query_status=P,
                wm_uat_query_status=NR,
            ),
            None,
            ["UPDATE wm_settings SET flag=1 WHERE env='stage';"],
        ),
        ("Cancelled WM rollout", {}, "Cancelled", []),
        (
            "In progress — deepthought analytics",
            _wm_all(
                wm_hotfix_branch_status=C,
                wm_master_production_status=IP,
                wm_release_branch_status=P,
            ),
            None,
            [],
        ),
        ("Ready to close — mater SSO fix", _wm_ready(), None, []),
    ]
    ids: list[int] = []
    for i, (title, lc, override, queries) in enumerate(scenarios):
        pid = repository.create_patch(
            PatchCreateInput(
                patch_id=f"FCSKY-992{i + 1:03d}",
                patch_type=config.PATCH_TYPE_WEEKLY,
                title=title,
                branch_name=BRANCH,
                developer_name=DEVELOPERS[i],
                product_module=MODULES[i],
                qa_status="Pending",
                patch_date=(datetime.now(timezone.utc) - timedelta(days=i + 1)).strftime("%Y-%m-%d"),
                repo_names=[WM_REPOS[i]],
                mysql_queries=queries,
            ),
            OPERATOR,
        )
        patch = repository.get_patch(pid)
        assert patch is not None
        if lc:
            repository.update_lifecycle(
                pid,
                {**patch.lifecycle, **lc},
                OPERATOR,
                manual_status_override=override,
            )
        _patch_created_days_ago(pid, [2, 3, 5, 7, 4, 6, 9, 12, 1, 3][i])
        ids.append(pid)
    return ids


def _seed_demo_uat() -> list[int]:
    """Demo UAT patches — mix FC and WM repos on same branch."""
    fc_uat_titles = [
        "Demo UAT — new franchise onboarding wizard",
        "Demo UAT — sales KPI dashboard widgets",
        "Demo UAT — mobile push notification prefs",
    ]
    wm_uat_titles = [
        "Demo UAT — platform-ng theme selector",
        "Demo UAT — bifrost report export CSV",
        "Demo UAT — deckard calendar sync",
    ]
    both_titles = [
        "Demo UAT — FC+WM unified search",
        "Demo UAT — cross-platform user prefs",
        "Demo UAT — shared audit trail view",
        "Demo UAT — integration smoke test fixes",
    ]
    ids: list[int] = []
    idx = 0

    for i, title in enumerate(fc_uat_titles):
        lc = _fc_all(
            production_status=C,
            release_branch_status=C,
            stage_query_status=C if i >= 1 else NR,
            uat_deployment_status=P if i == 0 else C,
            uat_query_status=P if i == 1 else (C if i >= 1 else NR),
        )
        pid = repository.create_patch(
            PatchCreateInput(
                patch_id=f"FCSKY-993{idx + 1:03d}",
                patch_type=config.PATCH_TYPE_DEMO_UAT,
                title=title,
                branch_name=BRANCH,
                developer_name=DEVELOPERS[idx],
                product_module=MODULES[idx],
                repo_names=[FC_REPOS[i % len(FC_REPOS)]],
            ),
            OPERATOR,
        )
        patch = repository.get_patch(pid)
        assert patch is not None
        repository.update_lifecycle(pid, {**patch.lifecycle, **lc}, OPERATOR)
        _patch_created_days_ago(pid, [1, 4, 7][i])
        ids.append(pid)
        idx += 1

    for i, title in enumerate(wm_uat_titles):
        lc = _wm_all(
            wm_hotfix_branch_status=C,
            wm_uat_branch_status=P if i == 0 else C,
            wm_integration_stage_status=P if i == 2 else C,
        )
        pid = repository.create_patch(
            PatchCreateInput(
                patch_id=f"FCSKY-993{idx + 1:03d}",
                patch_type=config.PATCH_TYPE_DEMO_UAT,
                title=title,
                branch_name=BRANCH,
                developer_name=DEVELOPERS[idx],
                product_module=MODULES[idx],
                repo_names=[WM_REPOS[i]],
            ),
            OPERATOR,
        )
        patch = repository.get_patch(pid)
        assert patch is not None
        repository.update_lifecycle(pid, {**patch.lifecycle, **lc}, OPERATOR)
        _patch_created_days_ago(pid, [2, 5, 8][i])
        ids.append(pid)
        idx += 1

    for i, title in enumerate(both_titles):
        lc_fc = _fc_all(
            production_status=C,
            uat_deployment_status=P if i < 2 else C,
            qa_verification_status=P if i == 0 else IP,
        )
        lc_wm = _wm_all(
            wm_hotfix_branch_status=C,
            wm_uat_branch_status=P if i < 2 else C,
        )
        pid = repository.create_patch(
            PatchCreateInput(
                patch_id=f"FCSKY-993{idx + 1:03d}",
                patch_type=config.PATCH_TYPE_DEMO_UAT,
                title=title,
                branch_name=BRANCH,
                developer_name=DEVELOPERS[idx],
                product_module=MODULES[idx],
                repo_names=[FC_REPOS[i % len(FC_REPOS)], WM_REPOS[i % len(WM_REPOS)]],
            ),
            OPERATOR,
        )
        patch = repository.get_patch(pid)
        assert patch is not None
        repository.update_lifecycle(pid, {**patch.lifecycle, **lc_fc, **lc_wm}, OPERATOR)
        _patch_created_days_ago(pid, [3, 6, 10, 15][i])
        ids.append(pid)
        idx += 1

    return ids


def main() -> None:
    db.init_db()
    with db.get_connection() as conn:
        exists = conn.execute(
            "SELECT id FROM patches WHERE patch_id = ?",
            ("FCSKY-991001",),
        ).fetchone()
    if exists:
        print("Sample data already seeded (FCSKY-991001 exists). Skip or delete those patches first.")
        return

    fc_ids = _seed_fc_weekly()
    wm_ids = _seed_wm_weekly()
    uat_ids = _seed_demo_uat()
    total = len(fc_ids) + len(wm_ids) + len(uat_ids)
    print(f"Seeded {total} sample patches on {BRANCH}:")
    print(f"  FC weekly hotfix:  {len(fc_ids)}  (FCSKY-991001 … FCSKY-991010)")
    print(f"  WM weekly hotfix:  {len(wm_ids)}  (FCSKY-992001 … FCSKY-992010)")
    print(f"  Demo UAT patches:  {len(uat_ids)}  (FCSKY-993001 … FCSKY-993010)")


if __name__ == "__main__":
    main()
