"""Orbit Autopilot phase-1 synthetic charter and decision authority tests.

Test data are isolated SQLite in-memory records and disposable project roots.
These tests neither authenticate a founder nor spawn host agents, spend model
credits, run background workers, modify Git, or touch production installations.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source" / "runtime"))

import orbit_autopilot
import orbit_mcp
import orbit_tasks


class AutopilotCharterTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = (Path(temp.name) / "roadmap-project").resolve()
        self.root.mkdir()
        self.other = (Path(temp.name) / "unrelated").resolve()
        self.other.mkdir()
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.addCleanup(self.conn.close)
        orbit_tasks.setup(self.conn)
        orbit_autopilot.setup(self.conn)
        self.project = "example"
        self.mission = "roadmap-iteration-one"
        self.expiry = (datetime.now(timezone.utc) +
                       timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.base = {"project_root": str(self.root), "project": self.project}
        self.make_task("api", ["src/api/"])
        self.make_task("ui", ["src/ui/"], deps=["api"], role="frontend")
        self.fields = {
            **self.base, "mission_id": self.mission,
            "objective": "Implement and test the approved UI and API milestone",
            "roadmap_ref": "docs/ROADMAP.md",
            "roadmap_revision": "roadmap-approved-20261107",
            "branch": "feat/test-autopilot",
            "expires_at": self.expiry,
            "task_keys": ["api", "ui"],
            "allowed_paths": ["src/api/", "src/ui/"],
            "allowed_decisions": ["task_order", "implementation_detail", "ui_polish",
                                  "bounded_retry"],
            "max_parallel": 1,
            "max_attempts_per_task": 2,
        }

    def make_task(self, key, paths, *, deps=None, role="backend", project=None, root=None):
        root = root or self.root
        project = project or self.project
        return orbit_tasks.plan(self.conn, {
            "project": project, "task_key": key,
            "step": "IMPLEMENT", "role": role,
            "goal": "Implement approved milestone with real tested deliverables",
            "reason": "Deliver bounded engineering work against the existing plan",
            "write_paths": paths, "depends_on": deps or [], "confirm_write": True,
        }, root)

    def call(self, name="orbit_autopilot_charter", **kwargs):
        payload = {**self.base, **kwargs}
        return orbit_mcp.execute(self.conn, name, payload)

    def preview(self, **kwargs):
        return self.call(action="preview", **{**self.fields, **kwargs})

    def activate(self, **kwargs):
        fields = {**self.fields, **kwargs}
        digest = self.call(action="preview", **fields)["charter_digest"]
        return self.call(action="activate", **fields,
                         "expected_digest": digest,
                         "approval_reference": "actual-owner-review-claimed-123",
                         "confirm_write": True})

    def next(self, **kwargs):
        return self.call("orbit_autopilot_next",
                         mission_id=self.mission, expected_revision=1,
                         reported_branch="feat/test-autopilot",
                         host="codex", available_host_tools=["spawn_agent"],
                         host_workspace_mode="workspace-write", **kwargs)

    def decision(self, kind, task="api", **kwargs):
        return self.call("orbit_autopilot_decision", mission_id=self.mission,
                         expected_revision=1,
                         reported_branch="feat/test-autopilot",
                         category=kind, task_key=task, **kwargs)

    def control(self, action, rev, **kwargs):
        return self.call(action=action, mission_id=self.mission,
                         expected_revision=rev, **kwargs)

    def test_preview_is_nonmutating_and_binds_existing_task_specs(self):
        before = self.conn.total_changes
        result = self.preview()
        self.assertEqual(result["status"], "PREVIEW_ONLY")
        self.assertEqual(len(result["charter_digest"]), 64)
        self.assertEqual(result["charter"]["task_keys"], ["api", "ui"])
        self.assertEqual(result["charter"]["branch"], "feat/test-autopilot")
        self.assertFalse(result["charter"]["autonomous_runner_enabled"])
        self.assertFalse(result["charter"]["host_permissions_granted"])
        self.assertFalse(result["execution_allowed"])
        self.assertEqual(self.conn.total_changes, before)

    def test_explicit_activating_write_is_not_owner_authentication(self):
        before = self.conn.total_changes
        result = self.activate()
        self.assertEqual(result["status"], "CHARTER_RECORDED")
        self.assertEqual(result["recorded_state"], "ACTIVE")
        self.assertEqual(result["revision"], 1)
        self.assertGreater(self.conn.total_changes, before)
        for field in ("approval_authenticated", "host_permissions_verified",
                      "execution_allowed", "agent_invoked"):
            self.assertFalse(result[field])
        self.assertEqual(self.conn.execute(
            "SELECT action FROM orbit_autopilot_events").fetchone()[0], "ACTIVATE")
        self.assertEqual(self.call(action="status", mission_id=self.mission)["status"],
                         "ACTIVE")
        self.assertEqual(len(orbit_mcp.TOOLS), 55)

    def test_activate_needs_exact_review_digest_and_confirm_write(self):
        p = self.preview()
        dry = self.call(action="activate", **self.fields,
                        expected_digest=p["charter_digest"], confirm_write=False)
        self.assertEqual(dry["status"], "PREVIEW_ONLY")
        self.assertIsNone(self.conn.execute(
            "SELECT 1 FROM orbit_autopilot_missions").fetchone())
        with self.assertRaisesRegex(ValueError, "digest"):
            self.call(action="activate", **self.fields, expected_digest="f"*64,
                      approval_reference="claimed-review-1234", confirm_write=True)
        with self.assertRaises(ValueError):
            self.call(action="activate", **self.fields, expected_digest=p["charter_digest"],
                      confirm_write=True)
        self.assertIsNone(self.conn.execute(
            "SELECT 1 FROM orbit_autopilot_missions").fetchone())

    def test_charter_never_allows_unregistered_or_cross_project_tasks(self):
        with self.assertRaisesRegex(ValueError, "not registered"):
            self.preview(task_keys=["api", "missing"])
        self.make_task("foreign", ["src/foreign/"], project="other")
        with self.assertRaisesRegex(ValueError, "not registered"):
            self.preview(task_keys=["foreign"])

    def test_task_dependencies_must_stay_inside_mission(self):
        with self.assertRaisesRegex(ValueError, "dependency"):
            self.preview(task_keys=["ui"])

    def test_protected_or_out_of_scope_paths_are_denied(self):
        with self.assertRaises(ValueError):
            self.preview(allowed_paths=[".git/"])
        with self.assertRaisesRegex(ValueError, "scope"):
            self.preview(allowed_paths=["src/api/"])
        with self.assertRaises(ValueError):
            self.preview(allowed_paths=["../outside/"])
        with self.assertRaises(ValueError):
            self.preview(allowed_paths=["src\\api\\"])
        with self.assertRaises(ValueError):
            self.preview(allowed_paths=["src/api."])

    def test_protected_branches_and_bad_expiry_are_denied(self):
        for branch in ("main", "release/0.32.0", "feat/../../main",
                       "autopilot/test.lock", "feat//nested", "fix/"):
            with self.subTest(branch=branch), self.assertRaises(ValueError):
                self.preview(branch=branch)
        with self.assertRaises(ValueError):
            self.preview(expires_at="2020-01-01T00:00:00Z")
        with self.assertRaises(ValueError):
            self.preview(expires_at=(datetime.now(timezone.utc)+timedelta(days=45)).
                         strftime("%Y-%m-%dT%H:%M:%SZ"))

    def test_budget_and_decision_category_limits(self):
        for opts in (
            {"max_parallel": 3},
            {"max_parallel": True},
            {"max_attempts_per_task": 0},
            {"allowed_decisions": ["release"]},
            {"allowed_decisions": ["task_order", "task_order"]},
            {"task_keys": ["api", "api"]},
            {"task_keys": []},
        ):
            with self.subTest(opts=opts), self.assertRaises(ValueError):
                self.preview(**opts)

    def test_next_read_only_and_never_reserves_or_spawns(self):
        self.activate()
        before = self.conn.total_changes
        result = self.next()
        self.assertEqual(result["status"], "NEXT_TASK_REVIEW_REQUIRED")
        self.assertEqual([row["task_key"] for row in result["ready_now"]], ["api"])
        for field in ("execution_allowed", "native_agent_invoked",
                      "host_permission_verified", "owner_approval_authenticated",
                      "git_branch_verified", "run_loop_started", "state_written"):
            self.assertFalse(result[field])
        self.assertEqual(self.conn.total_changes, before)
        status = self.conn.execute(
            "SELECT status FROM orbit_agent_tasks WHERE task_key='api'").fetchone()[0]
        self.assertEqual(status, "PLANNED")

    def test_missing_or_denied_host_tool_cannot_progress(self):
        self.activate()
        unavailable = self.next(available_host_tools=[])
        self.assertEqual(unavailable["status"], "HOLD_NATIVE_TOOL_UNAVAILABLE")
        self.assertFalse(unavailable["native_agent_invoked"])
        readonly = self.next(host_workspace_mode="read-only")
        self.assertEqual(readonly["status"], "HOLD_HOST_WORKSPACE_READ_ONLY")
        self.assertFalse(readonly["execution_allowed"])

    def test_branch_mismatch_and_stale_revision_fail_closed(self):
        self.activate()
        self.assertEqual(self.next(reported_branch="feat/other")["status"],
                         "HOLD_BRANCH_MISMATCH")
        self.assertEqual(self.next(expected_revision=8)["status"],
                         "HOLD_STALE_REVISION")
        self.assertEqual(self.decision("task_order", reported_branch="feat/other")["status"],
                         "HOLD_BRANCH_MISMATCH")

    def test_pause_resume_stop_are_revisioned_and_audited(self):
        self.activate()
        p = self.control("pause", 1)
        self.assertEqual(p["status"], "PREVIEW_ONLY")
        self.assertEqual(self.next()["status"], "NEXT_TASK_REVIEW_REQUIRED")
        paused = self.control("pause", 1, confirm_write=True)
        self.assertEqual(paused["status"], "PAUSED")
        self.assertEqual(paused["revision"], 2)
        self.assertEqual(self.next()["status"], "HOLD_MISSION_INACTIVE")
        self.assertEqual(self.control("pause", 1, confirm_write=True)["status"],
                         "HOLD_STALE_REVISION")
        with self.assertRaises(ValueError):
            self.control("resume", 2, confirm_write=True,
                         approval_reference="actual-owner-review-claimed-123")
        resumed = self.control("resume", 2, confirm_write=True,
                               approval_reference="owner-reapproved-9876")
        self.assertEqual(resumed["status"], "ACTIVE")
        self.assertEqual(resumed["revision"], 3)
        stopped = self.control("stop", 3, confirm_write=True)
        self.assertEqual(stopped["status"], "STOPPED")
        self.assertEqual(stopped["revision"], 4)
        self.assertEqual(self.control("resume", 4, confirm_write=True,
                                      approval_reference="new-claimed-789")["status"],
                         "HOLD_INVALID_TRANSITION")
        self.assertEqual([row[0] for row in self.conn.execute(
            "SELECT action FROM orbit_autopilot_events ORDER BY revision")],
            ["ACTIVATE", "PAUSE", "RESUME", "STOP"])

    def test_expiry_prevents_new_selection_and_resume(self):
        self.activate()
        future = datetime.now(timezone.utc) + timedelta(days=40)
        with patch.object(orbit_autopilot, "utc_now", return_value=future):
            self.assertEqual(self.next()["status"], "HOLD_MISSION_INACTIVE")
            self.assertEqual(self.call(action="status", mission_id=self.mission)["status"],
                             "EXPIRED")
        paused = self.control("pause", 1, confirm_write=True)
        self.assertEqual(paused["status"], "PAUSED")
        with patch.object(orbit_autopilot, "utc_now", return_value=future):
            self.assertEqual(self.control("resume", 2, confirm_write=True,
                                          approval_reference="new-review-6789")["status"],
                             "HOLD_EXPIRED")

    def test_new_mission_in_same_root_requires_stop(self):
        self.activate()
        fields = {**self.fields, "mission_id": "second-mission"}
        digest = self.preview(**fields)["charter_digest"]
        duplicate = self.call(action="activate", **fields,
                              expected_digest=digest,
                              approval_reference="reviewed-second-mission",
                              confirm_write=True)
        self.assertEqual(duplicate["status"], "HOLD_EXISTING_MISSION_IN_WORKSPACE")
        self.control("stop", 1, confirm_write=True)
        accepted = self.call(action="activate", **fields,
                             expected_digest=digest,
                             approval_reference="reviewed-second-mission",
                             confirm_write=True)
        self.assertEqual(accepted["status"], "CHARTER_RECORDED")
        self.assertEqual(self.preview()["status"], "HOLD_MISSION_ID_ALREADY_USED")

    def test_source_spec_mutation_causes_hold(self):
        self.activate()
        self.conn.execute(
            "UPDATE orbit_agent_tasks SET goal=? WHERE task_key='api'",
            ("Unapproved replacement source goal",))
        self.conn.commit()
        self.assertEqual(self.next()["status"], "HOLD_CHARTER_SOURCE_DRIFT")
        self.assertEqual(self.decision("implementation_detail")["status"],
                         "HOLD_CHARTER_SOURCE_DRIFT")

    def test_registered_task_state_can_progress_to_next_approved_dependency(self):
        self.activate()
        self.conn.execute(
            "UPDATE orbit_agent_tasks SET status='REVIEW_ACCEPTED' WHERE task_key='api'")
        self.conn.commit()
        next_one = self.next()
        self.assertEqual(next_one["status"], "NEXT_TASK_REVIEW_REQUIRED")
        self.assertEqual([x["task_key"] for x in next_one["ready_now"]], ["ui"])

    def test_attempt_budget_prevents_repeated_autopilot_candidate(self):
        self.activate()
        for i in (1, 2):
            self.conn.execute(
                """INSERT INTO orbit_task_attempts
                   (project,project_root,task_key,attempt_number,step,
                    reserved_at,disposition,host_session,updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (self.project, str(self.root), "api", i, "IMPLEMENT",
                 "2026-11-07", "FAILED", "", "2026-11-07"))
        self.conn.commit()
        self.assertEqual(self.next()["status"], "HOLD_NO_CHARTER_READY_TASKS")

    def test_routine_decision_is_reviewable_not_executed(self):
        self.activate()
        before = self.conn.total_changes
        result = self.decision("implementation_detail")
        self.assertEqual(result["status"], "DELEGATED_DECISION_REVIEW_REQUIRED")
        self.assertTrue(result["decision_category_allowed"])
        self.assertFalse(result["execution_allowed"])
        self.assertFalse(result["decision_implemented"])
        self.assertEqual(self.conn.total_changes, before)

    def test_irreversible_and_extra_scope_decisions_hold_founder(self):
        self.activate()
        for kind in sorted(orbit_autopilot.FOUNDER_ONLY):
            with self.subTest(kind=kind):
                self.assertEqual(self.decision(kind)["status"], "HOLD_FOUNDER_REVIEW")
        self.assertEqual(self.decision("ui_polish", task="outside")["status"],
                         "HOLD_FOUNDER_REVIEW")
        with self.assertRaises(ValueError):
            self.decision("silently_publish_release")

    def test_cross_root_mission_isolation(self):
        self.activate()
        foreign = self.call(action="status", project_root=str(self.other),
                            mission_id=self.mission)
        self.assertEqual(foreign["status"], "NO_MISSION")
        foreign_next = self.next(project_root=str(self.other))
        self.assertEqual(foreign_next["status"], "HOLD_MISSION_INACTIVE")

    def test_stored_approval_cannot_be_inferred_as_host_permission(self):
        self.activate()
        current = self.call(action="status", mission_id=self.mission)
        self.assertTrue(current["owner_approval_reference_caller_reported"])
        self.assertFalse(current["approval_authenticated"])
        self.assertFalse(current["host_permissions_verified"])
        self.assertFalse(current["execution_allowed"])
        self.assertFalse(current["agent_invoked"])

    def test_tool_schema_rejects_extra_keys_and_invalid_actions(self):
        self.assertIn("orbit_autopilot_charter", orbit_mcp.TOOL_MAP)
        self.assertIn("orbit_autopilot_next", orbit_mcp.TOOL_MAP)
        self.assertIn("orbit_autopilot_decision", orbit_mcp.TOOL_MAP)
        with self.assertRaises(ValueError):
            self.call(action="override_permissions", mission_id=self.mission)
        with self.assertRaises(ValueError):
            self.call(action="status", mission_id=self.mission, bypass_security=True)
        for tool in ("orbit_autopilot_next", "orbit_autopilot_decision"):
            item = next(t for t in orbit_mcp.TOOLS if t["name"] == tool)
            self.assertTrue(item["annotations"]["readOnlyHint"])

    def test_multiple_missions_cannot_share_different_project_keys_same_root(self):
        self.make_task("foreign", ["else/"], project="other")
        self.activate()
        fields = {**self.fields, "project": "other", "mission_id": "foreign-mission",
                  "task_keys": ["foreign"], "allowed_paths": ["else/"]}
        second = self.call(action="preview", **fields)
        self.assertEqual(second["status"], "PREVIEW_ONLY")
        rejected = self.call(action="activate", **fields,
                             expected_digest=second["charter_digest"],
                             approval_reference="reviewed-foreign-mission",
                             confirm_write=True)
        self.assertEqual(rejected["status"], "HOLD_EXISTING_MISSION_IN_WORKSPACE")


if __name__ == "__main__":
    unittest.main()
