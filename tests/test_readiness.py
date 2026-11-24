"""Tests for persistent project scan/readiness lifecycle."""
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source" / "runtime"))
import orbit_readiness


def audit(status="SCANNED", snapshot="a" * 64):
    return {
        "status": status,
        "inventory_snapshot_sha256": snapshot,
        "summary": {"files": 12, "directories": 3},
        "findings_count": 2,
    }


class ProjectReadinessTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        orbit_readiness.setup(self.conn)
        self.project = "sample"
        self.root = "/tmp/orbit-project"

    def tearDown(self):
        self.conn.close()

    def test_new_project_requires_scan(self):
        result = orbit_readiness.get_status(self.conn, self.project, self.root)
        self.assertEqual(result["status"], "SCAN_REQUIRED")
        self.assertTrue(result["scan_required_to_revalidate"])

    def test_complete_scan_persists_snapshot_and_counts(self):
        token = orbit_readiness.begin_scan(self.conn, self.project, self.root)
        self.assertEqual(orbit_readiness.get_status(self.conn, self.project, self.root)["status"], "SCANNING")
        result = orbit_readiness.complete_scan(self.conn, self.project, self.root, token, audit())
        self.assertEqual(result["status"], "SCANNED")
        self.assertTrue(result["last_scan_complete"])
        self.assertEqual(result["file_count"], 12)
        self.assertIsNone(result["changed_since_previous_scan"])
        self.assertIn("not a content hash", result["snapshot_semantics"])

    def test_changed_inventory_is_reported_on_next_complete_scan(self):
        first = orbit_readiness.begin_scan(self.conn, self.project, self.root)
        orbit_readiness.complete_scan(self.conn, self.project, self.root, first, audit(snapshot="a" * 64))
        second = orbit_readiness.begin_scan(self.conn, self.project, self.root)
        changed = orbit_readiness.complete_scan(
            self.conn, self.project, self.root, second, audit(snapshot="b" * 64)
        )
        self.assertEqual(changed["status"], "SCANNED")
        self.assertTrue(changed["changed_since_previous_scan"])
        self.assertEqual(changed["scan_count"], 2)

    def test_incomplete_scan_is_not_reported_as_current_complete(self):
        token = orbit_readiness.begin_scan(self.conn, self.project, self.root)
        result = orbit_readiness.complete_scan(
            self.conn, self.project, self.root, token, audit(status="INCOMPLETE")
        )
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertFalse(result["last_scan_complete"])

    def test_failure_preserves_last_good_snapshot(self):
        good = orbit_readiness.begin_scan(self.conn, self.project, self.root)
        orbit_readiness.complete_scan(self.conn, self.project, self.root, good, audit())
        prior = orbit_readiness.get_status(self.conn, self.project, self.root)["last_snapshot_sha256"]
        failed = orbit_readiness.begin_scan(self.conn, self.project, self.root)
        result = orbit_readiness.fail_scan(
            self.conn, self.project, self.root, failed, "PermissionError"
        )
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["last_snapshot_sha256"], prior)
        self.assertEqual(result["last_error"], "PermissionError")

    def test_interrupted_scan_is_detected_on_next_start(self):
        orbit_readiness.begin_scan(self.conn, self.project, self.root)
        next_scan = orbit_readiness.begin_scan(self.conn, self.project, self.root)
        self.assertTrue(next_scan["recovered_interrupted_scan"])
        self.assertEqual(orbit_readiness.get_status(self.conn, self.project, self.root)["status"], "SCANNING")

    def test_stale_scan_token_cannot_overwrite_newer_scan(self):
        old = orbit_readiness.begin_scan(self.conn, self.project, self.root)
        newer = orbit_readiness.begin_scan(self.conn, self.project, self.root)
        result = orbit_readiness.complete_scan(self.conn, self.project, self.root, old, audit())
        self.assertEqual(result["status"], "STALE_SCAN_RESULT")
        accepted = orbit_readiness.complete_scan(self.conn, self.project, self.root, newer, audit())
        self.assertEqual(accepted["status"], "SCANNED")

    def test_project_and_root_are_isolated(self):
        token = orbit_readiness.begin_scan(self.conn, self.project, self.root)
        orbit_readiness.complete_scan(self.conn, self.project, self.root, token, audit())
        self.assertEqual(
            orbit_readiness.get_status(self.conn, self.project, "/tmp/other")["status"],
            "SCAN_REQUIRED",
        )
        self.assertEqual(
            orbit_readiness.get_status(self.conn, "other", self.root)["status"],
            "SCAN_REQUIRED",
        )

    def test_invalid_snapshot_and_counts_are_rejected(self):
        token = orbit_readiness.begin_scan(self.conn, self.project, self.root)
        with self.assertRaises(ValueError):
            orbit_readiness.complete_scan(
                self.conn, self.project, self.root, token, audit(snapshot="not-a-digest")
            )




class ProjectReadinessIntegrationTests(unittest.TestCase):
    def test_explicit_scan_persists_readiness_even_with_prebuilt_connection(self):
        import tempfile
        import orbit_intake
        import orbit_mcp
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            (root / "README.md").write_text("Project", encoding="utf-8")
            conn = sqlite3.connect(":memory:")
            conn.row_factory = sqlite3.Row
            orbit_intake.setup(conn)
            try:
                result = orbit_mcp.scan(
                    {"project_root": str(root), "project": "sample"}, conn
                )
                self.assertEqual(result["readiness"]["status"], "SCANNED")
                self.assertTrue(result["readiness"]["last_scan_complete"])
            finally:
                conn.close()

    def test_resume_scan_can_remain_read_only(self):
        import tempfile
        import orbit_intake
        import orbit_mcp
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            conn = sqlite3.connect(":memory:")
            conn.row_factory = sqlite3.Row
            orbit_intake.setup(conn)
            before = conn.total_changes
            try:
                result = orbit_mcp.scan(
                    {"project_root": str(root), "project": "sample"},
                    conn, persist_readiness=False
                )
                self.assertIsNone(result["readiness"])
                self.assertEqual(conn.total_changes, before)
            finally:
                conn.close()


if __name__ == "__main__":
    unittest.main()


    def test_source_scan_state_persists_content_snapshot_and_detects_change(self):
        orbit_readiness.setup(self.conn)
        first = orbit_readiness.begin_source_scan(self.conn, self.project, self.root)
        source_audit = {
            "status": "SCANNED", "inventory_snapshot_sha256": "a" * 64,
            "summary": {"source_files": 2, "source_bytes_read": 100},
            "findings_count": 1,
        }
        result = orbit_readiness.complete_source_scan(
            self.conn, self.project, self.root, first, source_audit
        )
        self.assertEqual(result["source_status"], "SCANNED")
        self.assertTrue(result["source_scan_complete"])
        second = orbit_readiness.begin_source_scan(self.conn, self.project, self.root)
        source_audit["inventory_snapshot_sha256"] = "b" * 64
        changed = orbit_readiness.complete_source_scan(
            self.conn, self.project, self.root, second, source_audit
        )
        self.assertTrue(changed["changed_since_previous_source_scan"])
        self.assertEqual(changed["source_scan_count"], 2)

    def test_failed_source_scan_preserves_previous_snapshot(self):
        orbit_readiness.setup(self.conn)
        token = orbit_readiness.begin_source_scan(self.conn, self.project, self.root)
        source_audit = {
            "status": "SCANNED", "inventory_snapshot_sha256": "a" * 64,
            "summary": {"source_files": 1, "source_bytes_read": 20},
            "findings_count": 0,
        }
        orbit_readiness.complete_source_scan(
            self.conn, self.project, self.root, token, source_audit
        )
        token2 = orbit_readiness.begin_source_scan(self.conn, self.project, self.root)
        failed = orbit_readiness.fail_source_scan(
            self.conn, self.project, self.root, token2, "PermissionError"
        )
        self.assertEqual(failed["source_status"], "FAILED")
        self.assertEqual(failed["source_snapshot_sha256"], "a" * 64)


if __name__ == "__main__":
    unittest.main()
