"""Unit tests for Patch Lifecycle logic."""

from __future__ import annotations

import unittest

import config
from logic import (
    CreatePatchOptions,
    branch_sort_key,
    can_close,
    compute_initial_lifecycle,
    compute_patch_side,
    compute_system_status,
    group_by_branch_name,
    is_track_closed,
    is_wm_repo,
    merge_lifecycle_on_type_change,
    normalize_repo_name,
    patch_row_tone,
    resolve_patch_status_display,
    validate_status_transition,
)


class TestLifecycleDefaults(unittest.TestCase):
    def test_weekly_hotfix_with_queries(self) -> None:
        lc = compute_initial_lifecycle(
            CreatePatchOptions(config.PATCH_TYPE_WEEKLY, has_queries=True)
        )
        self.assertEqual(lc[config.LIFECYCLE_FIELD_PRODUCTION], config.STATUS_PENDING)
        self.assertEqual(lc[config.LIFECYCLE_FIELD_STAGE_QUERY], config.STATUS_PENDING)

    def test_weekly_hotfix_without_queries(self) -> None:
        lc = compute_initial_lifecycle(
            CreatePatchOptions(config.PATCH_TYPE_WEEKLY, has_queries=False)
        )
        self.assertEqual(lc[config.LIFECYCLE_FIELD_STAGE_QUERY], config.STATUS_NOT_REQUIRED)

    def test_release_patch_prod_nr(self) -> None:
        lc = compute_initial_lifecycle(
            CreatePatchOptions(config.PATCH_TYPE_RELEASE, has_queries=False)
        )
        self.assertEqual(lc[config.LIFECYCLE_FIELD_PRODUCTION], config.STATUS_NOT_REQUIRED)
        self.assertEqual(lc[config.LIFECYCLE_FIELD_UAT_DEPLOYMENT], config.STATUS_PENDING)

    def test_db_query_patch_flags(self) -> None:
        lc = compute_initial_lifecycle(
            CreatePatchOptions(
                config.PATCH_TYPE_DB_QUERY,
                db_linked_to_hotfix_prod=True,
                db_has_repo_change=False,
            )
        )
        self.assertEqual(lc[config.LIFECYCLE_FIELD_PRODUCTION], config.STATUS_PENDING)
        self.assertEqual(lc[config.LIFECYCLE_FIELD_RELEASE_BRANCH], config.STATUS_NOT_REQUIRED)

    def test_type_change_keep_current(self) -> None:
        current = {config.LIFECYCLE_FIELD_PRODUCTION: config.STATUS_COMPLETED}
        new = compute_initial_lifecycle(CreatePatchOptions(config.PATCH_TYPE_RELEASE))
        merged = merge_lifecycle_on_type_change(current, new, reset_to_defaults=False)
        self.assertEqual(merged[config.LIFECYCLE_FIELD_PRODUCTION], config.STATUS_COMPLETED)


class TestSystemStatus(unittest.TestCase):
    def test_pending_production(self) -> None:
        lc = compute_initial_lifecycle(CreatePatchOptions(config.PATCH_TYPE_WEEKLY))
        self.assertEqual(compute_system_status(lc), "Pending Production")

    def test_ready_to_close(self) -> None:
        lc = {f: config.STATUS_NOT_REQUIRED for f in config.LIFECYCLE_FIELDS}
        lc[config.LIFECYCLE_FIELD_CLOSURE] = config.STATUS_PENDING
        for f in config.LIFECYCLE_STATUS_ORDER:
            lc[f] = config.STATUS_COMPLETED
        self.assertEqual(compute_system_status(lc), config.SYSTEM_STATUS_READY_TO_CLOSE)

    def test_manual_override_display(self) -> None:
        lc = compute_initial_lifecycle(CreatePatchOptions(config.PATCH_TYPE_WEEKLY))
        display = resolve_patch_status_display(lc, "On Hold")
        self.assertEqual(display.final_status, "On Hold")
        self.assertEqual(display.system_status, "Pending Production")
        self.assertTrue(display.shows_both)

    def test_validate_operator(self) -> None:
        from logic import normalize_operator, validate_operator

        self.assertTrue(validate_operator("Tanisha Rawat"))
        self.assertFalse(validate_operator("Unknown"))
        self.assertEqual(normalize_operator("Vanni Chaudhary"), "Vanni Chaudhary")


class TestValidation(unittest.TestCase):
    def test_uat_query_before_stage_blocked(self) -> None:
        lc = {
            config.LIFECYCLE_FIELD_STAGE_QUERY: config.STATUS_PENDING,
            config.LIFECYCLE_FIELD_UAT_QUERY: config.STATUS_PENDING,
        }
        err = validate_status_transition(
            config.LIFECYCLE_FIELD_UAT_QUERY,
            config.STATUS_PENDING,
            config.STATUS_COMPLETED,
            lc,
        )
        self.assertIsNotNone(err)

    def test_can_close_blocks_pending(self) -> None:
        ok, blocking = can_close(
            {config.LIFECYCLE_FIELD_UAT_DEPLOYMENT: config.STATUS_PENDING}
        )
        self.assertFalse(ok)
        self.assertIn(config.LIFECYCLE_FIELD_UAT_DEPLOYMENT, blocking)


class TestBranchGrouping(unittest.TestCase):
    def test_hotfix_branch_latest_first(self) -> None:
        branches = ["hotfix_r26q2.8", "hotfix_r26q2.15", "hotfix_r26q2.9"]
        ordered = sorted(branches, key=branch_sort_key, reverse=True)
        self.assertEqual(ordered[0], "hotfix_r26q2.15")

    def test_newer_quarter_before_older(self) -> None:
        branches = ["hotfix_r26q2.9", "hotfix_r26q3.1"]
        ordered = sorted(branches, key=branch_sort_key, reverse=True)
        self.assertEqual(ordered[0], "hotfix_r26q3.1")

    def test_no_branch_last(self) -> None:
        branches = ["", "hotfix_r26q2.9", "release_april26"]
        ordered = sorted(branches, key=branch_sort_key, reverse=True)
        self.assertEqual(ordered[-1], "")

    def test_group_by_branch_name(self) -> None:
        items = [
            {"branch": "hotfix_r26q2.8", "id": 1},
            {"branch": "hotfix_r26q2.15", "id": 2},
            {"branch": "hotfix_r26q2.15", "id": 3},
        ]
        groups = group_by_branch_name(items, branch_getter=lambda x: x["branch"])
        self.assertEqual([name for name, _ in groups], ["hotfix_r26q2.15", "hotfix_r26q2.8"])
        self.assertEqual([i["id"] for i in groups[0][1]], [2, 3])


class TestPatchSide(unittest.TestCase):
    def test_wm_repo_shorthand(self) -> None:
        self.assertEqual(normalize_repo_name("ng"), "platform-ng")
        self.assertTrue(is_wm_repo("bifrost"))

    def test_fc_only_repos(self) -> None:
        self.assertEqual(compute_patch_side(["fcsky", "fcsky-ui"]), config.PATCH_SIDE_FC)

    def test_wm_only_repos(self) -> None:
        self.assertEqual(compute_patch_side(["bifrost", "deckard"]), config.PATCH_SIDE_WM)

    def test_both_sides(self) -> None:
        self.assertEqual(
            compute_patch_side(["fcsky", "bifrost"]),
            config.PATCH_SIDE_BOTH,
        )

    def test_wm_hotfix_defaults(self) -> None:
        lc = compute_initial_lifecycle(
            CreatePatchOptions(
                config.PATCH_TYPE_WEEKLY,
                patch_side=config.PATCH_SIDE_WM,
                has_queries=True,
            )
        )
        self.assertEqual(
            lc[config.WM_LIFECYCLE_FIELD_HOTFIX_BRANCH],
            config.STATUS_PENDING,
        )
        self.assertEqual(
            lc[config.LIFECYCLE_FIELD_PRODUCTION],
            config.STATUS_NOT_REQUIRED,
        )

    def test_both_side_gets_fc_and_wm_defaults(self) -> None:
        lc = compute_initial_lifecycle(
            CreatePatchOptions(
                config.PATCH_TYPE_WEEKLY,
                patch_side=config.PATCH_SIDE_BOTH,
                has_queries=False,
            )
        )
        self.assertEqual(lc[config.LIFECYCLE_FIELD_PRODUCTION], config.STATUS_PENDING)
        self.assertEqual(
            lc[config.WM_LIFECYCLE_FIELD_MASTER_PRODUCTION],
            config.STATUS_PENDING,
        )


class TestPatchRowTone(unittest.TestCase):
    def test_cancelled_override_is_negative(self) -> None:
        tone = patch_row_tone(
            lifecycle={config.LIFECYCLE_FIELD_CLOSURE: config.STATUS_PENDING},
            manual_status_override="Cancelled",
            patch_side=config.PATCH_SIDE_FC,
            side_filter=config.SIDE_FILTER_FC,
        )
        self.assertEqual(tone, "negative")

    def test_reverted_override_is_negative(self) -> None:
        tone = patch_row_tone(
            lifecycle={config.LIFECYCLE_FIELD_CLOSURE: config.STATUS_COMPLETED},
            manual_status_override="Reverted",
            patch_side=config.PATCH_SIDE_FC,
            side_filter=config.SIDE_FILTER_FC,
        )
        self.assertEqual(tone, "negative")

    def test_fc_track_closed_is_complete(self) -> None:
        lifecycle = {config.LIFECYCLE_FIELD_CLOSURE: config.STATUS_COMPLETED}
        self.assertTrue(is_track_closed(lifecycle, config.PATCH_SIDE_FC))
        tone = patch_row_tone(
            lifecycle=lifecycle,
            manual_status_override=None,
            patch_side=config.PATCH_SIDE_FC,
            side_filter=config.SIDE_FILTER_FC,
        )
        self.assertEqual(tone, "complete")

    def test_both_side_needs_both_tracks_on_all_tab(self) -> None:
        fc_only_closed = {
            config.LIFECYCLE_FIELD_CLOSURE: config.STATUS_COMPLETED,
            config.WM_LIFECYCLE_FIELD_CLOSURE: config.STATUS_PENDING,
        }
        tone = patch_row_tone(
            lifecycle=fc_only_closed,
            manual_status_override=None,
            patch_side=config.PATCH_SIDE_BOTH,
            side_filter=config.SIDE_FILTER_ALL,
        )
        self.assertIsNone(tone)

        both_closed = {
            config.LIFECYCLE_FIELD_CLOSURE: config.STATUS_COMPLETED,
            config.WM_LIFECYCLE_FIELD_CLOSURE: config.STATUS_COMPLETED,
        }
        tone = patch_row_tone(
            lifecycle=both_closed,
            manual_status_override=None,
            patch_side=config.PATCH_SIDE_BOTH,
            side_filter=config.SIDE_FILTER_ALL,
        )
        self.assertEqual(tone, "complete")


if __name__ == "__main__":
    unittest.main()
