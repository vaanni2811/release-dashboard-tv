"""Unit tests for decide_hotfix (pure logic)."""

from __future__ import annotations

import unittest
from datetime import date

from logic import decide_hotfix


class TestFreeze(unittest.TestCase):
    def test_blocks_inside_window(self) -> None:
        d = decide_hotfix(
            hotfix_date=date(2026, 4, 10),
            release_live_date=date(2026, 4, 1),
            release_tag="",
            release_branch_override=None,
            freeze_start=date(2026, 4, 8),
            freeze_end=date(2026, 4, 15),
            branch_names=[],
            release_branch_exists=False,
            skip_leading_wednesdays=1,
        )
        self.assertTrue(d.blocked)
        self.assertIsNone(d.proposed_branch_name)


class TestPastDateValidation(unittest.TestCase):
    def test_blocks_past_hotfix_date(self) -> None:
        d = decide_hotfix(
            hotfix_date=date(2026, 4, 1),
            release_live_date=date(2026, 4, 1),
            release_tag="prod_tag_14apr26",
            release_branch_override=None,
            freeze_start=None,
            freeze_end=None,
            branch_names=[],
            release_branch_exists=False,
            skip_leading_wednesdays=1,
            current_date=date(2026, 4, 10),
        )
        self.assertTrue(d.blocked)
        self.assertIn("Past hotfix dates are not allowed", d.block_reason or "")

    def test_blocks_stale_release_live_date(self) -> None:
        d = decide_hotfix(
            hotfix_date=date(2026, 5, 6),
            release_live_date=date(2025, 5, 6),
            release_tag="prod_tag_14apr26",
            release_branch_override="release_6may26",
            freeze_start=None,
            freeze_end=None,
            branch_names=["hotfix_r26q2.2"],
            release_branch_exists=False,
            skip_leading_wednesdays=1,
            current_date=date(2026, 4, 28),
        )
        self.assertTrue(d.blocked)
        self.assertIn("looks too old", d.block_reason or "")


class TestAlreadyCut(unittest.TestCase):
    def test_expected_branch_exists(self) -> None:
        d = decide_hotfix(
            hotfix_date=date(2026, 4, 15),
            release_live_date=date(2026, 4, 8),
            release_tag="prod_tag_x",
            release_branch_override=None,
            freeze_start=None,
            freeze_end=None,
            branch_names=["hotfix_r26q2.2", "prod"],
            release_branch_exists=True,
            skip_leading_wednesdays=1,
        )
        self.assertFalse(d.blocked)
        self.assertTrue(d.already_cut_for_week)
        self.assertEqual(d.proposed_branch_name, "hotfix_r26q2.2")
        self.assertEqual(d.source_ref, "hotfix_r26q2.2")
        self.assertEqual(d.decision_kind, "already_cut_for_week")

    def test_already_cut_release_day_source_is_release_branch(self) -> None:
        """When go-live date equals hotfix Wednesday, source ref is the release branch (not the hotfix)."""
        same = date(2026, 4, 15)
        d = decide_hotfix(
            hotfix_date=same,
            release_live_date=same,
            release_tag="",
            release_branch_override=None,
            freeze_start=None,
            freeze_end=None,
            branch_names=["hotfix_r26q2.2", "release_15apr26"],
            release_branch_exists=False,
            skip_leading_wednesdays=1,
        )
        self.assertTrue(d.already_cut_for_week)
        self.assertEqual(d.proposed_branch_name, "hotfix_r26q2.2")
        self.assertEqual(d.source_ref, "release_15apr26")


class TestExistingChain(unittest.TestCase):
    def test_next_after_max(self) -> None:
        d = decide_hotfix(
            hotfix_date=date(2026, 4, 22),
            release_live_date=date(2026, 4, 8),
            release_tag="t",
            release_branch_override=None,
            freeze_start=None,
            freeze_end=None,
            branch_names=["hotfix_r26q2.2"],
            release_branch_exists=True,
            skip_leading_wednesdays=1,
        )
        self.assertFalse(d.blocked)
        self.assertFalse(d.already_cut_for_week)
        self.assertEqual(d.proposed_branch_name, "hotfix_r26q2.3")
        self.assertEqual(d.source_ref, "hotfix_r26q2.2")
        self.assertEqual(d.source_kind, "branch")
        self.assertEqual(d.decision_kind, "existing_hotfix_chain")

    def test_chain_uses_release_branch_when_hotfix_date_equals_release_live(self) -> None:
        same = date(2026, 5, 6)
        d = decide_hotfix(
            hotfix_date=same,
            release_live_date=same,
            release_tag="prod_tag_x",
            release_branch_override=None,
            freeze_start=None,
            freeze_end=None,
            branch_names=["hotfix_r26q2.1"],
            release_branch_exists=True,
            skip_leading_wednesdays=1,
        )
        self.assertEqual(d.proposed_branch_name, "hotfix_r26q2.2")
        self.assertEqual(d.source_ref, "release_6may26")
        self.assertEqual(d.source_kind, "branch")
        self.assertEqual(d.decision_kind, "existing_hotfix_chain")

    def test_chain_release_day_uses_list_when_exists_flag_false(self) -> None:
        same = date(2026, 5, 6)
        d = decide_hotfix(
            hotfix_date=same,
            release_live_date=same,
            release_tag="t",
            release_branch_override=None,
            freeze_start=None,
            freeze_end=None,
            branch_names=["hotfix_r26q2.1", "release_6may26"],
            release_branch_exists=False,
            skip_leading_wednesdays=1,
        )
        self.assertEqual(d.source_ref, "release_6may26")


class TestReleaseGoLive(unittest.TestCase):
    """Create release branch from tag when go-live Wednesday matches and branch is missing."""

    def test_release_branch_from_tag_when_missing(self) -> None:
        same = date(2026, 5, 6)
        d = decide_hotfix(
            hotfix_date=same,
            release_live_date=same,
            release_tag="prod_tag_14apr26",
            release_branch_override=None,
            freeze_start=None,
            freeze_end=None,
            branch_names=["hotfix_r26q2.1", "prod"],
            release_branch_exists=False,
            skip_leading_wednesdays=1,
        )
        self.assertFalse(d.blocked)
        self.assertEqual(d.decision_kind, "release_branch_from_tag")
        self.assertEqual(d.proposed_branch_name, "release_6may26")
        self.assertEqual(d.source_ref, "prod_tag_14apr26")
        self.assertEqual(d.source_kind, "tag")

    def test_go_live_same_date_no_tag_blocks(self) -> None:
        same = date(2026, 5, 6)
        d = decide_hotfix(
            hotfix_date=same,
            release_live_date=same,
            release_tag="",
            release_branch_override=None,
            freeze_start=None,
            freeze_end=None,
            branch_names=[],
            release_branch_exists=False,
            skip_leading_wednesdays=1,
        )
        self.assertTrue(d.blocked)
        self.assertIn("Release tag is required", d.block_reason or "")


class TestFirstHotfix(unittest.TestCase):
    def test_from_prod_when_no_release_branch(self) -> None:
        d = decide_hotfix(
            hotfix_date=date(2026, 4, 15),
            release_live_date=date(2026, 4, 8),
            release_tag="",
            release_branch_override=None,
            freeze_start=None,
            freeze_end=None,
            branch_names=[],
            release_branch_exists=False,
            prod_branch="prod",
            skip_leading_wednesdays=1,
        )
        self.assertFalse(d.blocked)
        self.assertEqual(d.proposed_branch_name, "hotfix_r26q2.1")
        self.assertEqual(d.source_ref, "prod")
        self.assertEqual(d.source_kind, "branch")
        self.assertEqual(d.decision_kind, "first_prod")

    def test_from_release_tag_when_release_branch_exists(self) -> None:
        d = decide_hotfix(
            hotfix_date=date(2026, 4, 15),
            release_live_date=date(2026, 4, 8),
            release_tag="prod_tag_17mar26",
            release_branch_override=None,
            freeze_start=None,
            freeze_end=None,
            branch_names=[],
            release_branch_exists=True,
            skip_leading_wednesdays=1,
        )
        self.assertFalse(d.blocked)
        self.assertEqual(d.source_ref, "prod_tag_17mar26")
        self.assertEqual(d.source_kind, "tag")
        self.assertEqual(d.decision_kind, "first_after_release_tag")

    def test_blocked_when_release_branch_but_no_tag(self) -> None:
        d = decide_hotfix(
            hotfix_date=date(2026, 4, 15),
            release_live_date=date(2026, 4, 8),
            release_tag="  ",
            release_branch_override=None,
            freeze_start=None,
            freeze_end=None,
            branch_names=[],
            release_branch_exists=True,
            skip_leading_wednesdays=1,
        )
        self.assertTrue(d.blocked)

    def test_from_release_branch_when_hotfix_equals_release_live(self) -> None:
        same = date(2026, 4, 8)
        d = decide_hotfix(
            hotfix_date=same,
            release_live_date=same,
            release_tag="",
            release_branch_override=None,
            freeze_start=None,
            freeze_end=None,
            branch_names=[],
            release_branch_exists=True,
            skip_leading_wednesdays=1,
        )
        self.assertFalse(d.blocked)
        self.assertEqual(d.source_ref, "release_8apr26")
        self.assertEqual(d.source_kind, "branch")
        self.assertEqual(d.decision_kind, "first_from_release_branch")


if __name__ == "__main__":
    unittest.main()
