"""Tests for priority-first, read-only remediation planning from accepted findings."""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source" / "runtime"))
import orbit_findings
import orbit_tasks


class FindingsPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project"
        self.root.mkdir()
        self.project = "sample"
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.addCleanup(self.conn.close)
        orbit_findings.setup(self.conn)
        orbit_tasks.setup(self.conn)

    def _finding(self, fid, severity, confidence, scope="STRUCTURAL"):
        return {
            "id": fid, "category": "security" if scope == "SOURCE" else "testing",
            "severity": severity, "confidence": confidence,
            "summary": f"Review evidence for {fid}.",
            "evidence": ["src/main.py"],
            "recommendation": "Inspect the actual condition and propose a minimal correction.",
            "is_confirmed_defect": False,
        }

    def _audit(self, findings, snapshot):
        return {
            "status": "SCANNED",
            "inventory_snapshot_sha256": snapshot * 64,
            "findings": findings,
            "findings_count": len(findings),
        }

    def _accept_all(self):
        rows = orbit_findings.list_findings(self.conn, self.project, self.root)["findings"]
        for row in rows:
            orbit_findings.set_disposition(
                self.conn, self.project, self.root, row["finding_id"],
                "ACCEPTED", row["revision"]
            )

    def test_priority_first_plan_is_read_only_and_has_no_inferred_write_scope(self):
        structural = [
            self._finding("TEST_LOW", "LOW", "HIGH"),
            self._finding("TEST_HIGH", "HIGH", "HIGH"),
            self._finding("TEST_MED", "MEDIUM", "MEDIUM"),
        ]
        orbit_findings.reconcile(
            self.conn, self.project, self.root, self._audit(structural, "a")
        )
        source = [self._finding("SOURCE_MED", "MEDIUM", "HIGH", "SOURCE")]
        orbit_findings.reconcile(
            self.conn, self.project, self.root, self._audit(source, "b"),
            audit_scope="SOURCE"
        )
        self._accept_all()
        before = self.conn.total_changes
        result = orbit_findings.remediation_plan(self.conn, self.project, self.root)
        self.assertEqual(result["status"], "DRAFT_VALIDATED")
        self.assertEqual(result["accepted_finding_count"], 4)
        self.assertEqual(result["priority_order"][0], "finding-test-high")
        self.assertEqual(result["priority_order"][1], "finding-source-med")
        self.assertEqual(result["proposed_tasks"][0]["priority"], "P1")
        self.assertTrue(all(task["write_paths"] == [] for task in result["proposed_tasks"]))
        self.assertTrue(all(task["depends_on"] == [] for task in result["proposed_tasks"]))
        self.assertTrue(all(task["verification_gates"] for task in result["proposed_tasks"]))
        self.assertTrue(result["review_waves"][0]["task_keys"][0] == "finding-test-high")
        self.assertFalse(result["tasks_created"])
        self.assertFalse(result["task_registration_performed"])
        self.assertEqual(self.conn.total_changes, before)
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM orbit_agent_tasks").fetchone()[0], 0)

    def test_unaccepted_and_stale_findings_are_not_planned(self):
        items = [self._finding("TEST_ACCEPT", "HIGH", "HIGH"),
                 self._finding("TEST_REVIEW", "CRITICAL", "HIGH")]
        orbit_findings.reconcile(
            self.conn, self.project, self.root, self._audit(items, "c")
        )
        row = next(x for x in orbit_findings.list_findings(
            self.conn, self.project, self.root)["findings"] if x["finding_id"] == "TEST_ACCEPT")
        orbit_findings.set_disposition(
            self.conn, self.project, self.root, "TEST_ACCEPT", "ACCEPTED", row["revision"]
        )
        result = orbit_findings.remediation_plan(self.conn, self.project, self.root)
        self.assertEqual(result["accepted_finding_count"], 1)
        self.assertEqual([x["finding_id"] for x in result["proposed_tasks"]], ["TEST_ACCEPT"])
        self.assertEqual(result["unreviewed_or_stale_count"], 1)

    def test_oversized_accepted_plan_holds_without_partial_truncation(self):
        items = [self._finding(f"TEST_{i:02d}", "MEDIUM", "HIGH") for i in range(13)]
        orbit_findings.reconcile(
            self.conn, self.project, self.root, self._audit(items, "d")
        )
        self._accept_all()
        result = orbit_findings.remediation_plan(self.conn, self.project, self.root)
        self.assertEqual(result["status"], "HOLD_PLAN_TOO_LARGE")
        self.assertEqual(result["accepted_finding_count"], 13)
        self.assertFalse(result["tasks_created"])
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM orbit_agent_tasks").fetchone()[0], 0)

    def test_existing_task_key_collision_holds(self):
        item = self._finding("TEST_COLLISION", "HIGH", "HIGH")
        orbit_findings.reconcile(
            self.conn, self.project, self.root, self._audit([item], "e")
        )
        self._accept_all()
        orbit_tasks.plan(self.conn, {
            "project": self.project, "task_key": "finding-test-collision",
            "step": "existing", "role": "software-engineer",
            "goal": "Existing task already owns this stable key.",
            "reason": "Collision test task is already registered.",
            "write_paths": [], "depends_on": [], "confirm_write": True,
        }, self.root)
        result = orbit_findings.remediation_plan(self.conn, self.project, self.root)
        self.assertEqual(result["status"], "HOLD_EXISTING_TASK_KEYS")
        self.assertFalse(result["tasks_created"])


if __name__ == "__main__":
    unittest.main()
