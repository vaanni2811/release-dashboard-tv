"""Unit tests for utils (dates, prefixes, sequences)."""

from __future__ import annotations

import unittest
from datetime import date

from utils import (
    date_in_freeze,
    hotfix_prefix_for_date,
    hotfix_week_number_in_quarter,
    max_hotfix_sequence,
    release_branch_display_name,
    release_branch_name,
    release_branch_name_day_short,
    upcoming_wednesdays,
)


class TestHotfixPrefix(unittest.TestCase):
    def test_prefix_q2_2026(self) -> None:
        self.assertEqual(hotfix_prefix_for_date(date(2026, 4, 15)), "hotfix_r26q2")

    def test_prefix_q1(self) -> None:
        self.assertEqual(hotfix_prefix_for_date(date(2026, 1, 7)), "hotfix_r26q1")


class TestHotfixWeekNumber(unittest.TestCase):
    def test_april_15_2026_calendar_ordinal(self) -> None:
        # Q2 2026: Apr 1, 8, 15 are 1st–3rd Wednesdays
        self.assertEqual(hotfix_week_number_in_quarter(date(2026, 4, 15), skip_leading=0), 3)
        self.assertEqual(hotfix_week_number_in_quarter(date(2026, 4, 15), skip_leading=1), 2)

    def test_first_wed_skip_one_returns_none(self) -> None:
        self.assertIsNone(hotfix_week_number_in_quarter(date(2026, 4, 1), skip_leading=1))


class TestMaxHotfixSequence(unittest.TestCase):
    def test_max_from_branches(self) -> None:
        names = ["hotfix_r26q2.1", "other", "hotfix_r26q2.7", "hotfix_r26q2.2"]
        self.assertEqual(max_hotfix_sequence(names, "hotfix_r26q2"), 7)

    def test_none_when_no_match(self) -> None:
        self.assertIsNone(max_hotfix_sequence(["main", "prod"], "hotfix_r26q2"))


class TestReleaseBranchName(unittest.TestCase):
    def test_april(self) -> None:
        self.assertEqual(release_branch_name(date(2026, 4, 8)), "release_april26")

    def test_day_short_may(self) -> None:
        self.assertEqual(release_branch_name_day_short(date(2026, 5, 6)), "release_6may26")

    def test_display_override_wins(self) -> None:
        d = date(2026, 5, 6)
        self.assertEqual(
            release_branch_display_name(d, "release_custom", "full_month"),
            "release_custom",
        )


class TestFreeze(unittest.TestCase):
    def test_inside(self) -> None:
        self.assertTrue(date_in_freeze(date(2026, 4, 10), date(2026, 4, 1), date(2026, 4, 15)))

    def test_outside_when_partial_none(self) -> None:
        self.assertFalse(date_in_freeze(date(2026, 4, 10), None, date(2026, 4, 15)))


class TestUpcomingWednesdays(unittest.TestCase):
    def test_includes_current_and_next_month(self) -> None:
        w = upcoming_wednesdays(today=date(2026, 4, 10), months_ahead=1)
        self.assertIn(date(2026, 4, 1), w)
        self.assertTrue(any(x.month == 5 for x in w))


if __name__ == "__main__":
    unittest.main()
