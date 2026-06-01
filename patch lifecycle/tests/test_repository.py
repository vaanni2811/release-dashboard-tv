"""Integration tests for Patch Lifecycle repository."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import config
import db
import repository
from repository import PatchCreateInput


class TestRepository(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._saved_db_path = config.DATABASE_PATH
        config.DATABASE_PATH = Path(self._tmpdir.name) / "test.db"
        db.init_db()

    def tearDown(self) -> None:
        config.DATABASE_PATH = self._saved_db_path
        self._tmpdir.cleanup()

    def test_create_and_list(self) -> None:
        pid = repository.create_patch(
            PatchCreateInput(
                patch_id="FCSKY-999002",
                patch_type=config.PATCH_TYPE_WEEKLY,
                title="List test",
            ),
            "Tanisha Rawat",
        )
        self.assertGreater(pid, 0)
        rows = repository.list_patches()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].patch_id, "FCSKY-999002")
        self.assertEqual(rows[0].final_status, "Pending Production")
        self.assertEqual(
            rows[0].lifecycle[config.LIFECYCLE_FIELD_PRODUCTION],
            config.STATUS_PENDING,
        )
        self.assertEqual(
            rows[0].lifecycle[config.LIFECYCLE_FIELD_RELEASE_BRANCH],
            config.STATUS_PENDING,
        )

    def test_duplicate_patch_id_rejected(self) -> None:
        repository.create_patch(
            PatchCreateInput(patch_id="FCSKY-999003", patch_type=config.PATCH_TYPE_WEEKLY),
            "Vanni Chaudhary",
        )
        with self.assertRaises(ValueError):
            repository.create_patch(
                PatchCreateInput(patch_id="FCSKY-999003", patch_type=config.PATCH_TYPE_WEEKLY),
                "Vanni Chaudhary",
            )

    def test_update_lifecycle(self) -> None:
        pid = repository.create_patch(
            PatchCreateInput(
                patch_id="FCSKY-999004",
                patch_type=config.PATCH_TYPE_WEEKLY,
            ),
            "Vanni Chaudhary",
        )
        detail = repository.get_patch(pid)
        assert detail is not None
        lc = dict(detail.lifecycle)
        lc[config.LIFECYCLE_FIELD_PRODUCTION] = config.STATUS_COMPLETED
        repository.update_lifecycle(pid, lc, "Vanni Chaudhary")
        updated = repository.get_patch(pid)
        assert updated is not None
        self.assertEqual(
            updated.lifecycle[config.LIFECYCLE_FIELD_PRODUCTION],
            config.STATUS_COMPLETED,
        )
        self.assertEqual(updated.system_status, "Pending Release Branch")


    def test_developer_filter_case_insensitive(self) -> None:
        repository.create_patch(
            PatchCreateInput(
                patch_id="FCSKY-999010",
                patch_type=config.PATCH_TYPE_WEEKLY,
                developer_name="Chandan Yadav",
            ),
            "Vanni Chaudhary",
        )
        rows = repository.list_patches(developer="chandan")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].patch_id, "FCSKY-999010")

    def test_branch_subfilter(self) -> None:
        repository.create_patch(
            PatchCreateInput(
                patch_id="FCSKY-999011",
                patch_type=config.PATCH_TYPE_WEEKLY,
                branch_name="hotfix_r26q2.9",
            ),
            "Vanni Chaudhary",
        )
        repository.create_patch(
            PatchCreateInput(
                patch_id="FCSKY-999012",
                patch_type=config.PATCH_TYPE_WEEKLY,
                branch_name="hotfix_r26q2.8",
            ),
            "Vanni Chaudhary",
        )
        rows = repository.list_patches(
            patch_type=config.PATCH_TYPE_WEEKLY,
            branch_name="hotfix_r26q2.9",
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].patch_id, "FCSKY-999011")
        branches = repository.list_distinct_branches_for_type(
            patch_type=config.PATCH_TYPE_WEEKLY,
        )
        self.assertIn("hotfix_r26q2.9", branches)


if __name__ == "__main__":
    unittest.main()
