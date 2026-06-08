"""Tests for monthly release date/label helpers."""

from __future__ import annotations

import unittest
from datetime import date

from monthly_dates import (
    default_processing_days,
    form_generator_query,
    quarter_label,
    release_document_title,
    title_date_range,
)


class TestMonthlyDates(unittest.TestCase):
    def test_quarter_label(self) -> None:
        self.assertEqual(quarter_label("R26", "Q2"), "R26Q2")

    def test_title_date_range(self) -> None:
        wed = date(2026, 6, 10)
        thu = date(2026, 6, 11)
        sat = date(2026, 6, 13)
        self.assertEqual(title_date_range(wed, thu, sat), "June/10 - June/13, 2026")

    def test_release_document_title(self) -> None:
        self.assertEqual(
            release_document_title("R26", "June", "June/10 - June/13, 2026"),
            "R26 June Release document (June/10 - June/13, 2026)",
        )

    def test_default_processing_days_june(self) -> None:
        wed, thu, sat = default_processing_days(2026, "June")
        self.assertEqual(wed.month, 6)
        self.assertEqual(thu.month, 6)
        self.assertEqual(sat.month, 6)
        self.assertEqual(wed.weekday(), 2)
        self.assertEqual(thu.weekday(), 3)
        self.assertEqual(sat.weekday(), 5)

    def test_form_generator_query(self) -> None:
        self.assertEqual(
            form_generator_query("JUN26"),
            "CREATE TABLE CLIENT_XMLS_BKP_JUN26 SELECT * FROM CLIENT_XMLS;",
        )


if __name__ == "__main__":
    unittest.main()
