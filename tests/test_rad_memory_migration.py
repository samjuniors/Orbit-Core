"""Safe, disposable SQLite checks for explicit scoped memory migration."""
from __future__ import annotations

import os
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source" / "runtime"))
sys.path.insert(0, str(ROOT / "scripts"))
import orbit_mcp
import migrate_scoped_memory as migrator


class RootMemoryMigrationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.temp = Path(tmp.name)
        self.one = self.temp / "one"
        self.two = self.temp / "two"
        self.one.mkdir()
        self.two.mkdir()
        self.db = self.temp / "memories.sqlite3"
        with patch.dict(os.environ, {"ORBIT_LOCAL_DB": str(self.db)}):
            conn = orbit_mcp.db_connect()
        self.addCleanup(conn.close)
        self.conn = conn
        for key, content in (("a", "LEGACY_ONE"), ("b", "LEGACY_TWO")):
            orbit_mcp.memory_save(conn, {
                "project": "demo", "key": key, "kind": sorted(orbit_mcp.KINDS)[0],
                "summary": content, "source": "synthetic",
                "confirm_write": True,
            })

    def test_dry_run_apply_backup_and_idempotent_copy(self):
        with patch.dict(os.environ, {
            "ORBIT_TRUSTED_ROOTS": os.pathsep.join([str(self.one), str(self.two)]),
        }):
            before = self.db.read_bytes()
            preview = migrator.preview_or_apply(self.db, "demo", self.one)
            self.assertEqual(preview["status"], "PREVIEW_ONLY")
            self.assertEqual(preview["legacy_count"], 2)
            self.assertEqual(preview["scoped_count_before"], 0)
            self.assertEqual(self.db.read_bytes(), before)
            self.assertEqual(list(self.temp.glob("*.before-scope-*")), [])

            with self.assertRaisesRegex(ValueError, "confirmation"):
                migrator.preview_or_apply(self.db, "demo", self.one, apply=True)
            first = migrator.preview_or_apply(
                self.db, "demo", self.one, apply=True,
                confirmation="MIGRATE SCOPED MEMORY")
            self.assertEqual(first["copied"], 2)
            self.assertEqual(first["scoped_count_after"], 2)
            self.assertTrue(first["backup_created"])
            backups = list(self.temp.glob("memories.sqlite3.before-scope-*.sqlite3"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(first["backup_name"], backups[0].name)
            with closing(sqlite3.connect(backups[0])) as backup_db:
                self.assertEqual(backup_db.execute(
                    "SELECT COUNT(*) FROM memories WHERE project='demo'"
                ).fetchone()[0], 2)
            self.assertEqual(orbit_mcp.memory_recall(
                self.conn, {"project": "demo", "project_root": str(self.one)})[0]["project"],
                "demo")
            self.assertEqual(len(orbit_mcp.memory_recall(
                self.conn, {"project": "demo", "project_root": str(self.two)})), 0)
            self.assertEqual(len(orbit_mcp.memory_recall(
                self.conn, {"project": "demo"})), 2)
            second = migrator.preview_or_apply(self.db, "demo", self.one,
                apply=True, confirmation="MIGRATE SCOPED MEMORY")
            self.assertEqual(second["copied"], 0)
            self.assertEqual(len(orbit_mcp.memory_recall(
                self.conn, {"project": "demo", "project_root": str(self.one)})), 2)

    def test_missing_allowlist_and_outside_root_refused(self):
        with patch.dict(os.environ, {"ORBIT_TRUSTED_ROOTS": ""}):
            with self.assertRaisesRegex(ValueError, "ORBIT_TRUSTED_ROOTS"):
                migrator.preview_or_apply(self.db, "demo", self.one)
        with patch.dict(os.environ, {"ORBIT_TRUSTED_ROOTS": str(self.one)}):
            with self.assertRaisesRegex(ValueError, "ORBIT_TRUSTED_ROOTS"):
                migrator.preview_or_apply(self.db, "demo", self.two)
            with self.assertRaisesRegex(ValueError, "existing absolute regular file"):
                migrator.preview_or_apply(self.temp / "absent.sqlite3", "demo", self.one)
        self.assertEqual(list(self.temp.glob("*.before-scope-*")), [])


if __name__ == "__main__":
    unittest.main()
