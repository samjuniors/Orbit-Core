"""Regression for a native worker ending normally without completing its objective.

One real Codex host fixture returned a terminal COMPLETED session but could
not create alpha.txt. Prevent a permanent RUNNING lock without claiming a PASS.
All tests use disposable in-memory SQLite and no host agent execution.
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source" / "runtime"))
import orbit_mcp
import orbit_tasks


class NativeCompletedObjectiveBlockedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "project"
        self.root.mkdir()
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.addCleanup(self.db.close)
        orbit_tasks.setup(self.db)
        a = self.call("orbit_task_plan", task_key="alpha", step="IMPLEMENT",
                      role="backend", goal="Create alpha.txt with the approved literal",
                      reason="Confirm objective failure after real native session termination",
                      depends_on=[], write_paths=["alpha.txt"], confirm_write=True)
        self.assertEqual(a["status"], "PLANNED")
        b = self.call("orbit_task_reserve", task_key="alpha", expected_revision=1,
                      approval_reference="fixture-host-owner-approved", confirm_write=True)
        self.assertEqual(b["status"], "RESERVED")
        c = self.call("orbit_task_started", task_key="alpha", expected_revision=2,
                      host_session="/root/alpha", confirm_write=True)
        self.assertEqual(c["status"], "RUNNING_REPORTED")

    def call(self, tool, **args):
        return orbit_mcp.execute(self.db, tool, {
            "project_root": str(self.root), "project": "codex-acceptance", **args
        })

    def report(self, **overrides):
        fields = {
            "task_key": "alpha", "expected_revision": 3,
            "outcome": "BLOCKED",
            "evidence": "Native child /root/alpha finished, but alpha.txt was absent",
            "observed_host_session": "/root/alpha",
            "host_state": "COMPLETED",
            "changed_paths": [],
            "confirm_write": True,
        }
        fields.update(overrides)
        return self.call("orbit_task_report", **fields)

    def current(self):
        return self.call("orbit_task_list")["tasks"][0]

    def test_without_explicit_incomplete_objective_holds_and_preserves_revision(self):
        for arg in ({}, {"objective_completed": True}):
            with self.subTest(arg=arg):
                out = self.report(**arg)
                self.assertEqual(out["status"], "HOLD_HOST_RECONCILIATION")
                self.assertFalse(out["host_status_verified"])
                self.assertEqual(self.current()["revision"], 3)
                self.assertEqual(self.current()["status"], "RUNNING")
        with self.assertRaises(ValueError):
            self.report(objective_completed=None)
        self.assertEqual(self.current()["revision"], 3)

    def test_completed_but_blocked_does_not_accept_changed_files(self):
        out = self.report(objective_completed=False, changed_paths=["alpha.txt"])
        self.assertEqual(out["status"], "HOLD_HOST_RECONCILIATION")
        self.assertEqual(self.current()["revision"], 3)

    def test_wrong_session_or_unknown_host_state_never_releases_scope(self):
        for args in (
            {"observed_host_session": "/root/not-alpha", "objective_completed": False},
            {"host_state": "UNKNOWN", "objective_completed": False},
            {"host_state": "RUNNING", "objective_completed": False},
        ):
            with self.subTest(args=args):
                out=self.report(**args)
                self.assertEqual(out["status"], "HOLD_HOST_RECONCILIATION")
        self.assertEqual(self.current()["status"], "RUNNING")

    def test_preview_cannot_change_ledger_even_with_all_guards_met(self):
        out = self.report(objective_completed=False, confirm_write=False)
        self.assertEqual(out["status"], "PREVIEW_ONLY")
        self.assertEqual(self.current()["revision"], 3)
        self.assertEqual(self.current()["status"], "RUNNING")

    def test_real_completed_host_can_report_blocked_objective_without_pass(self):
        result = self.report(objective_completed=False)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["task"]["revision"], 4)
        self.assertEqual(result["task"]["changed_paths"], [])
        self.assertEqual(result["task"]["host_session"], "/root/alpha")
        self.assertIn("TASK_OBJECTIVE_REPORTED_INCOMPLETE", result["task"]["note"])
        self.assertFalse(result["host_status_verified"])
        self.assertEqual(result["verification"], "HOST_REPORTED_NOT_ATTESTED")
        attempt = self.db.execute("SELECT disposition FROM orbit_task_attempts").fetchone()[0]
        self.assertEqual(attempt, "HOST_REPORTED_BLOCKED")
        with self.assertRaisesRegex(ValueError,"Only reported completed work"):
            self.call("orbit_task_review", task_key="alpha", expected_revision=4,
                      verdict="ACCEPT", review_evidence="Independently verified alpha.txt is absent",
                      confirm_write=True)

    def test_stale_replay_does_not_rewrite_history(self):
        first=self.report(objective_completed=False)
        stale=self.report(objective_completed=False)
        self.assertEqual(first["status"], "BLOCKED")
        self.assertEqual(stale["status"], "STALE_REVISION")
        self.assertEqual(self.current()["revision"], 4)

    def test_retry_preserves_historical_session_and_budget(self):
        self.report(objective_completed=False)
        with self.assertRaisesRegex(ValueError, "fresh host/user approval"):
            self.call("orbit_task_reserve", task_key="alpha", expected_revision=4,
                      approval_reference="fixture-host-owner-approved", confirm_write=True)
        fresh=self.call("orbit_task_reserve", task_key="alpha", expected_revision=4,
                        approval_reference="new-explicit-approval", confirm_write=True)
        self.assertEqual(fresh["status"], "RESERVED")
        self.assertEqual(fresh["task"]["host_session"], "")
        attempts=self.db.execute("SELECT disposition,host_session FROM orbit_task_attempts ORDER BY attempt_number").fetchall()
        self.assertEqual(len(attempts), 2)
        self.assertEqual(attempts[0]["host_session"], "/root/alpha")
        self.assertEqual(attempts[0]["disposition"], "HOST_REPORTED_BLOCKED")

    def test_host_completed_not_sufficient_for_failure_or_cancellation(self):
        for outcome in ("FAILED","CANCELLED"):
            with self.subTest(outcome=outcome):
                out=self.report(outcome=outcome, objective_completed=False)
                self.assertEqual(out["status"], "HOLD_HOST_RECONCILIATION")
        self.assertEqual(self.current()["status"], "RUNNING")

    def test_schema_rejects_nonboolean_objective_completed(self):
        with self.assertRaises(ValueError):
            self.report(objective_completed="false")
        self.assertEqual(self.current()["revision"],3)


if __name__ == "__main__":
    unittest.main()
