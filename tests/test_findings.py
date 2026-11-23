"""Tests for persistent project finding reconciliation."""
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source" / "runtime"))
import orbit_findings


def audit(snapshot, findings, status="SCANNED"):
    return {"status": status, "inventory_snapshot_sha256": snapshot,
            "findings": findings}


def finding(fid="TEST_STRUCTURE_NOT_DISCOVERED", evidence=None):
    return {
        "id": fid, "category": "testing", "severity": "MEDIUM",
        "confidence": "MEDIUM", "summary": "No conventional test structure discovered.",
        "evidence": evidence or ["src/main.py"],
        "recommendation": "Review the actual test strategy.",
        "is_confirmed_defect": False,
    }


class ProjectFindingTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        orbit_findings.setup(self.conn)
        self.root = "/tmp/orbit-project"
        self.project = "sample"

    def tearDown(self):
        self.conn.close()

    def test_new_persistent_resolved_and_recurring_lifecycle(self):
        first = orbit_findings.reconcile(
            self.conn, self.project, self.root, audit("a" * 64, [finding()])
        )
        self.assertEqual(first["status"], "RECONCILED")
        row = first["findings"][0]
        self.assertEqual(row["lifecycle"], "NEW")
        self.assertEqual(row["disposition"], "UNREVIEWED")
        self.assertFalse(row["is_confirmed_defect"])

        second = orbit_findings.reconcile(
            self.conn, self.project, self.root, audit("b" * 64, [finding()])
        )
        self.assertEqual(second["findings"][0]["lifecycle"], "OPEN")
        self.assertEqual(second["findings"][0]["occurrence_count"], 1)

        resolved = orbit_findings.reconcile(
            self.conn, self.project, self.root, audit("c" * 64, [])
        )
        self.assertEqual(resolved["resolved_count"], 1)
        self.assertEqual(resolved["findings"][0]["lifecycle"], "RESOLVED")

        recurring = orbit_findings.reconcile(
            self.conn, self.project, self.root, audit("d" * 64, [finding()])
        )
        self.assertEqual(recurring["findings"][0]["lifecycle"], "RECURRING")
        self.assertEqual(recurring["findings"][0]["occurrence_count"], 2)
        self.assertEqual(recurring["findings"][0]["disposition"], "UNREVIEWED")

    def test_incomplete_scan_marks_stale_and_never_resolves(self):
        orbit_findings.reconcile(
            self.conn, self.project, self.root, audit("a" * 64, [finding()])
        )
        result = orbit_findings.reconcile(
            self.conn, self.project, self.root, audit("b" * 64, [], "INCOMPLETE")
        )
        self.assertEqual(result["resolved_count"], 0)
        self.assertEqual(result["findings"][0]["lifecycle"], "STALE")

    def test_disposition_requires_revision_and_does_not_confirm_defect(self):
        result = orbit_findings.reconcile(
            self.conn, self.project, self.root, audit("a" * 64, [finding()])
        )
        row = result["findings"][0]
        updated = orbit_findings.set_disposition(
            self.conn, self.project, self.root, row["finding_id"], "ACCEPTED", row["revision"]
        )
        self.assertEqual(updated["status"], "UPDATED")
        self.assertFalse(updated["defect_confirmed"])
        stale = orbit_findings.set_disposition(
            self.conn, self.project, self.root, row["finding_id"], "FALSE_POSITIVE", row["revision"]
        )
        self.assertEqual(stale["status"], "STALE_REVISION")

    def test_evidence_change_resets_disposition_for_review(self):
        result = orbit_findings.reconcile(
            self.conn, self.project, self.root, audit("a" * 64, [finding()])
        )
        row = result["findings"][0]
        orbit_findings.set_disposition(
            self.conn, self.project, self.root, row["finding_id"], "ACCEPTED", row["revision"]
        )
        changed = orbit_findings.reconcile(
            self.conn, self.project, self.root,
            audit("b" * 64, [finding(evidence=["src/main.py", "src/api.py"])])
        )
        self.assertEqual(changed["findings"][0]["disposition"], "UNREVIEWED")

    def test_project_and_root_are_isolated(self):
        orbit_findings.reconcile(
            self.conn, self.project, self.root, audit("a" * 64, [finding()])
        )
        other = orbit_findings.list_findings(self.conn, self.project, "/tmp/other")
        self.assertEqual(other["status"], "EMPTY")


if __name__ == "__main__":
    unittest.main()
