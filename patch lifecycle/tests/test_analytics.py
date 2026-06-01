"""Unit tests for Patch Lifecycle analytics."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import config
import db
import repository
from analytics import DashboardFilters, compute_dashboard_metrics
from repository import PatchCreateInput


class TestAnalytics(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._saved_db_path = config.DATABASE_PATH
        config.DATABASE_PATH = Path(self._tmpdir.name) / "test.db"
        db.init_db()

    def tearDown(self) -> None:
        config.DATABASE_PATH = self._saved_db_path
        self._tmpdir.cleanup()

    def test_empty_metrics(self) -> None:
        metrics = compute_dashboard_metrics(DashboardFilters())
        self.assertEqual(metrics.patches_in_scope, 0)
        self.assertEqual(metrics.total_open, 0)

    def test_open_weekly_patch_counted(self) -> None:
        repository.create_patch(
            PatchCreateInput(
                patch_id="FCSKY-880001",
                patch_type=config.PATCH_TYPE_WEEKLY,
                branch_name="hotfix_r26q2.9",
                developer_name="Test Dev",
            ),
            "Vanni Chaudhary",
        )
        metrics = compute_dashboard_metrics(
            DashboardFilters(
                date_preset="All Time",
                patch_type="All",
            )
        )
        self.assertEqual(metrics.patches_in_scope, 1)
        self.assertEqual(metrics.total_open, 1)
        self.assertEqual(metrics.weekly_hotfix, 1)
        self.assertEqual(metrics.patch_type_counts[config.PATCH_TYPE_WEEKLY], 1)

    def test_cancelled_excluded(self) -> None:
        patch_id = repository.create_patch(
            PatchCreateInput(
                patch_id="FCSKY-880002",
                patch_type=config.PATCH_TYPE_WEEKLY,
            ),
            "Vanni Chaudhary",
        )
        patch = repository.get_patch(patch_id)
        assert patch is not None
        repository.update_lifecycle(
            patch.id,
            patch.lifecycle,
            "Vanni Chaudhary",
            manual_status_override="Cancelled",
        )
        metrics = compute_dashboard_metrics(
            DashboardFilters(date_preset="All Time"),
        )
        self.assertEqual(metrics.patches_in_scope, 0)


if __name__ == "__main__":
    unittest.main()
