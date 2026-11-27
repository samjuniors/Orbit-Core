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
    def test_oversized_source_marks_scan_incomplete(self):
        path = self.root / "large.py"
        path.write_bytes(b"x" * (orbit_source_audit.MAX_FILE_BYTES + 1))
        result = orbit_source_audit.scan_source(self.root)
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertTrue(result["truncated"])
        self.assertIn("large.py", result["unreadable_paths"])

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


if __name__ == "__main__":
    unittest.main()
