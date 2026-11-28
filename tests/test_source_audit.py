"""Tests for bounded, consented, non-executing source audits."""
import json
import sqlite3
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source" / "runtime"))
import orbit_source_audit
import orbit_mcp
import orbit_findings


class SourceAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project"
        self.root.mkdir()

    @unittest.skipUnless(orbit_source_audit._WINDOWS_SAFE_RELATIVE_SCAN, "Safe traversal adapter unavailable")
    def test_source_review_signals_are_not_confirmed_defects_and_raw_code_is_not_returned(self):
        source = self.root / "main.py"
        source.write_text(
            "value = eval(user_input)\nsubprocess.run(command, shell=True)\n",
            encoding="utf-8",
        )
        (self.root / ".env").write_text("SECRET_DO_NOT_READ", encoding="utf-8")
        (self.root / "node_modules").mkdir()
        (self.root / "node_modules" / "vendor.py").write_text("eval('x')", encoding="utf-8")
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*"))
        result = orbit_source_audit.scan_source(self.root)
        after = sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*"))
        self.assertEqual(result["status"], "SCANNED")
        self.assertEqual(result["summary"]["source_files"], 1)
        ids = {item["id"] for item in result["findings"]}
        self.assertTrue(any(item.startswith("SOURCE_DYNAMIC_CODE_") for item in ids))
        self.assertTrue(any(item.startswith("SOURCE_SUBPROCESS_SHELL_TRUE_") for item in ids))
        self.assertTrue(all(item["is_confirmed_defect"] is False for item in result["findings"]))
        self.assertFalse(result["source_contents_returned"])
        self.assertFalse(result["source_contents_persisted"])
        self.assertFalse(result["project_scripts_executed"])
        self.assertNotIn("SECRET_DO_NOT_READ", json.dumps(result))
        self.assertNotIn("user_input", json.dumps(result))
        self.assertEqual(before, after)

    @unittest.skipUnless(orbit_source_audit._WINDOWS_SAFE_RELATIVE_SCAN, "Safe traversal adapter unavailable")
    def test_content_change_changes_source_snapshot_even_when_size_is_unchanged(self):
        path = self.root / "main.py"
        path.write_text("x = 1\n", encoding="utf-8")
        first = orbit_source_audit.scan_source(self.root)
        path.write_text("x = 2\n", encoding="utf-8")
        second = orbit_source_audit.scan_source(self.root)
        self.assertNotEqual(first["inventory_snapshot_sha256"], second["inventory_snapshot_sha256"])

    @unittest.skipUnless(orbit_source_audit._WINDOWS_SAFE_RELATIVE_SCAN, "Safe traversal adapter unavailable")
    @unittest.skipIf(sys.platform == "win32", "POSIX allows non-UTF-8 filename bytes")
    def test_non_utf8_filename_does_not_abort_scan(self):
        name = b"bad\xff.py"
        try:
            with open(bytes(self.root) + b"/" + name, "w", encoding="utf-8") as handle:
                handle.write("value = eval(user_input)\nimport ast\nast.parse(\n")
        except OSError:
            self.skipTest("Filesystem rejects non-UTF-8 names")
        result = orbit_source_audit.scan_source(self.root)
        json.dumps(result)

    @unittest.skipUnless(orbit_source_audit._WINDOWS_SAFE_RELATIVE_SCAN, "Safe traversal adapter unavailable")
    def test_source_snapshot_is_keyed_not_a_plain_content_hash(self):
        import hashlib
        (self.root / "main.py").write_text('KEY = "guessable"\n', encoding="utf-8")
        key = b"k" * 32
        first = orbit_source_audit.scan_source(self.root, key)
        self.assertEqual(first["inventory_snapshot_sha256"],
                         orbit_source_audit.scan_source(self.root, key)["inventory_snapshot_sha256"])
        self.assertNotEqual(first["inventory_snapshot_sha256"],
                            orbit_source_audit.scan_source(self.root, b"x" * 32)["inventory_snapshot_sha256"])
        raw = (self.root / "main.py").read_bytes()
        plain = hashlib.sha256()
        path = b"main.py"
        plain.update(len(path).to_bytes(4, "big")); plain.update(path)
        plain.update(len(raw).to_bytes(8, "big")); plain.update(hashlib.sha256(raw).digest())
        self.assertNotEqual(first["inventory_snapshot_sha256"], plain.hexdigest())

    def test_source_snapshot_key_persists_privately(self):
        import os
        with mock.patch.dict(os.environ, {"ORBIT_LOCAL_DB": str(Path(self.temp.name) / "db" / "m.sqlite3")}):
            first = orbit_mcp.source_snapshot_key()
            self.assertEqual(len(first), 32)
            self.assertEqual(orbit_mcp.source_snapshot_key(), first)
            key_file = Path(self.temp.name) / "db" / "source-snapshot.key"
            if os.name != "nt":
                self.assertEqual(key_file.stat().st_mode & 0o777, 0o600)

    def test_oversized_source_marks_scan_incomplete(self):
        path = self.root / "large.py"
        path.write_bytes(b"x" * (orbit_source_audit.MAX_FILE_BYTES + 1))
        result = orbit_source_audit.scan_source(self.root)
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertTrue(result["truncated"])
        self.assertIn("large.py", result["unreadable_paths"])

    @unittest.skipUnless(__import__("os").name == "nt", "Windows-only fail-closed adapter test")
    def test_windows_source_audit_fails_closed_without_opening_files(self):
        (self.root / "main.py").write_text("value = eval(input())\n", encoding="utf-8")
        with mock.patch.object(orbit_source_audit, "_WINDOWS_SAFE_RELATIVE_SCAN", False):
            result = orbit_source_audit.scan_source(self.root)
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertEqual(result["scan_mode"], "BLOCKED_UNSAFE_WINDOWS_PATH_TRAVERSAL")
        self.assertEqual(result["scan_block_reason"], "WINDOWS_REPARSE_POINT_SAFE_RELATIVE_OPEN_UNAVAILABLE")
        self.assertFalse(result["source_contents_read"])
        self.assertIsNone(result["inventory_snapshot_sha256"])
        self.assertEqual(result["findings"], [])

    def test_stale_structural_scan_does_not_reconcile_findings(self):
        import os
        import orbit_readiness
        db = Path(self.temp.name) / "db" / "memory.sqlite3"
        with mock.patch.dict(os.environ, {"ORBIT_LOCAL_DB": str(db)}):
            conn = orbit_mcp.db_connect()
        try:
            args = {"project_root": str(self.root), "project": "sample", "action": "reconcile"}
            stale = {"status": "STALE_SCAN_RESULT", "data_written": False}
            with mock.patch.object(orbit_readiness, "complete_scan", return_value=stale), \
                    mock.patch.object(orbit_findings, "reconcile",
                                      side_effect=AssertionError("stale scan reconciled")):
                result = orbit_mcp.execute(conn, "orbit_project_findings", args)
            self.assertEqual(result["status"], "STALE_SCAN_RESULT")
            self.assertFalse(result["findings_written"])
        finally:
            conn.close()

    def test_mcp_requires_read_consent_and_preview_does_not_write(self):
        (self.root / "main.py").write_text("value = eval(input())\n", encoding="utf-8")
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        try:
            args = {"project_root": str(self.root), "project": "sample",
                    "action": "source_reconcile"}
            denied = orbit_mcp.execute(conn, "orbit_project_findings", args)
            self.assertEqual(denied["status"], "READ_CONSENT_REQUIRED")
            before = conn.total_changes
            preview = orbit_mcp.execute(conn, "orbit_project_findings",
                {**args, "confirm_read": True, "confirm_write": False})
            self.assertEqual(preview["status"], "PREVIEW_ONLY")
            self.assertEqual(conn.total_changes, before)
            self.assertFalse(conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='orbit_project_readiness'"
            ).fetchone())
        finally:
            conn.close()

    @unittest.skipUnless(orbit_source_audit._WINDOWS_SAFE_RELATIVE_SCAN, "Safe traversal adapter unavailable")
    def test_confirmed_source_reconcile_persists_scope_not_raw_contents(self):
        (self.root / "main.py").write_text("value = eval(input())\n", encoding="utf-8")
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        orbit_findings.setup(conn)
        try:
            args = {"project_root": str(self.root), "project": "sample",
                    "action": "source_reconcile", "confirm_read": True,
                    "confirm_write": True}
            result = orbit_mcp.execute(conn, "orbit_project_findings", args)
            self.assertEqual(result["status"], "RECONCILED")
            self.assertEqual(result["audit_scope"], "SOURCE")
            self.assertEqual(result["source_readiness"]["source_status"], "SCANNED")
            self.assertTrue(result["findings"])
            self.assertEqual(result["findings"][0]["audit_scope"], "SOURCE")
            stored = conn.execute(
                "SELECT summary,evidence FROM orbit_project_findings"
            ).fetchone()
            self.assertNotIn("eval(input())", stored["summary"] + stored["evidence"])
        finally:
            conn.close()

    @unittest.skipIf(__import__("os").name == "nt", "POSIX descriptor-relative audit test")
    def test_posix_source_audit_skips_symlinks_and_rejects_hardlinks(self):
        import os
        (self.root / "main.py").write_text("value = eval(input())\n", encoding="utf-8")
        outside = Path(self.temp.name) / "outside.py"
        outside.write_text("SECRET_OUTSIDE_ROOT", encoding="utf-8")
        (self.root / "linked.py").symlink_to(outside)
        os.link(self.root / "main.py", self.root / "hardlinked.py")
        result = orbit_source_audit.scan_source(self.root)
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertEqual(result["summary"]["source_files"], 0)
        self.assertEqual(result["symlinks_skipped"], 1)
        self.assertIn("hardlinked.py", result["unreadable_paths"])
        self.assertNotIn("SECRET_OUTSIDE_ROOT", json.dumps(result))

    @unittest.skipIf(__import__("os").name == "nt", "POSIX descriptor-relative audit test")
    def test_posix_source_audit_leaf_swap_to_symlink_fails_closed(self):
        import os
        source = self.root / "race.py"
        source.write_text("value = 1\n", encoding="utf-8")
        outside = Path(self.temp.name) / "outside.py"
        outside.write_text("SECRET_OUTSIDE_ROOT", encoding="utf-8")
        real_open = os.open
        swapped = False

        def racing_open(path, flags, *args, **kwargs):
            nonlocal swapped
            if path == "race.py" and kwargs.get("dir_fd") is not None and not swapped:
                swapped = True
                source.unlink()
                source.symlink_to(outside)
            return real_open(path, flags, *args, **kwargs)

        with mock.patch.object(orbit_source_audit.os, "open", side_effect=racing_open):
            result = orbit_source_audit.scan_source(self.root)
        self.assertTrue(swapped)
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertIn("race.py", result["unreadable_paths"])
        self.assertNotIn("SECRET_OUTSIDE_ROOT", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
