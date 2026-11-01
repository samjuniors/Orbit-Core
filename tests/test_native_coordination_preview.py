"""v0.30 synthetic contract tests for the native coordination bridge.

Only disposable in-memory task state is used. This suite does not invoke a
coding host, authenticate approval, inspect actual Git changes or run a model.
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source" / "runtime"))

import orbit_mcp
import orbit_tasks


class NativeCoordinationPreviewTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name, "project").resolve()
        self.root.mkdir()
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.addCleanup(self.conn.close)
        orbit_tasks.setup(self.conn)
        self.project = "coordination-lab"
        self.host = {
            "project_root": str(self.root),
            "project": self.project,
            "host": "codex",
            "available_host_tools": ["spawn_agent"],
            "host_workspace_mode": "workspace-write",
        }

    def task(self, key, *, paths=(), deps=(), role="backend", project=None):
        project = project or self.project
        result = orbit_tasks.plan(self.conn, {
            "project": project, "task_key": key, "step": "Implementation",
            "role": role,
            "goal": "Implement reviewed and scoped functionality in source",
            "reason": "A bounded worker responsibility in the approved plan",
            "write_paths": list(paths), "depends_on": list(deps),
            "confirm_write": True,
        }, self.root)
        self.assertEqual(result["status"], "PLANNED")
        return result["task"]["revision"]

    def reserve(self, key, *, project=None):
        project = project or self.project
        rev = self.conn.execute(
            "SELECT revision FROM orbit_agent_tasks WHERE project=? AND project_root=? AND task_key=?",
            (project, str(self.root), key)).fetchone()["revision"]
        result = orbit_tasks.reserve(self.conn, {
            "project": project, "task_key": key, "expected_revision": rev,
            "approval_reference": "synthetic-host-approval-ref",
            "confirm_write": True,
        }, self.root)
        self.assertEqual(result["status"], "RESERVED")
        return result["task"]["revision"]

    def state(self, key, status, *, project=None):
        self.conn.execute(
            "UPDATE orbit_agent_tasks SET status=?,revision=revision+1 WHERE project=? AND project_root=? AND task_key=?",
            (status, project or self.project, str(self.root), key))
        self.conn.commit()

    def preview(self, **kwargs):
        return orbit_mcp.execute(
            self.conn, "orbit_native_coordination_preview",
            {**self.host, **kwargs},
        )

    def test_empty_project_needs_plan_and_never_writes(self):
        before = self.conn.total_changes
        out = self.preview()
        self.assertEqual(out["status"], "NO_REGISTERED_TASKS")
        self.assertEqual(out["stage"], "PLAN_FIRST")
        self.assertEqual(out["reservation_candidates"], [])
        self.assertFalse(out["agent_invoked"])
        self.assertFalse(out["state_written"])
        self.assertFalse(out["host_permissions_verified"])
        self.assertFalse(out["release_authorized"])
        self.assertEqual(self.conn.total_changes, before)

    def test_valid_draft_returns_only_registration_previews(self):
        draft = [{
            "task_key": "api", "step": "Implementation",
            "role": "backend", "goal": "Build a tested Python service endpoint",
            "reason": "Implement API separately from the UI and review",
            "write_paths": ["src/api/"], "depends_on": [],
        }, {
            "task_key": "ui", "step": "Implementation",
            "role": "frontend", "goal": "Build a tested accessible frontend interface",
            "reason": "Separate frontend worker with disjoint ownership",
            "write_paths": ["src/ui/"], "depends_on": [],
        }]
        before = self.conn.total_changes
        out = self.preview(draft_tasks=draft)
        self.assertEqual(out["status"], "DRAFT_REVIEW_REQUIRED")
        self.assertEqual(out["draft_status"], "DRAFT_VALIDATED")
        self.assertEqual(len(out["registration_preview"]), 2)
        self.assertEqual(out["review_waves"][0]["task_keys"], ["api", "ui"])
        self.assertTrue(all(not x["arguments_preview_only"]["confirm_write"]
                            for x in out["registration_preview"]))
        self.assertEqual(out["handoffs"], [])
        self.assertFalse(out["task_registered"])
        self.assertEqual(self.conn.total_changes, before)

    def test_draft_with_missing_dependency_or_existing_key_holds(self):
        proposed = [{
            "task_key": "qa", "step": "Review", "role": "qa",
            "goal": "Review actual source and test artifacts independently",
            "reason": "Quality gate must inspect a real completed worker",
            "write_paths": [], "depends_on": ["unregistered"],
        }]
        out = self.preview(draft_tasks=proposed)
        self.assertEqual(out["status"], "HOLD_DRAFT_REVIEW")
        self.assertEqual(out["draft_status"], "HOLD_MISSING_DEPENDENCIES")
        self.assertEqual(out["registration_preview"], [])
        self.task("qa")
        out2 = self.preview(draft_tasks=[{**proposed[0], "depends_on": []}])
        self.assertEqual(out2["status"], "HOLD_DRAFT_REVIEW")
        self.assertEqual(out2["draft_status"], "HOLD_EXISTING_TASK_KEYS")

    def test_registered_tasks_propose_disjoint_reservations_and_optional_skills(self):
        self.task("api", paths=["src/api/"])
        self.task("ui", paths=["src/ui/"], role="frontend")
        before = self.conn.total_changes
        out = self.preview(include_skill_review=True)
        self.assertEqual(out["status"], "RESERVATION_REVIEW_REQUIRED")
        self.assertEqual([x["task_key"] for x in out["reservation_candidates"]], ["api", "ui"])
        self.assertTrue(all(not x["confirm_write"] and x["real_host_permission_required"]
                            for x in out["reservation_candidates"]))
        self.assertEqual([x["tool"] for x in out["optional_skill_reviews"]],
                         ["orbit_capability_select"] * 2)
        self.assertTrue(all(x["status"] == "OPTIONAL_READ_ONLY_REVIEW_NOT_EXECUTED"
                            for x in out["optional_skill_reviews"]))
        self.assertFalse(out["skill_installed"])
        self.assertEqual(self.conn.total_changes, before)

    def test_reserved_tasks_reuse_existing_all_or_nothing_native_preflight(self):
        self.task("api", paths=["src/api/"])
        self.task("ui", paths=["src/ui/"], role="frontend")
        a = self.reserve("api")
        b = self.reserve("ui")
        before = self.conn.total_changes
        out = self.preview(reserved_tasks=[
            {"task_key": "api", "expected_revision": a},
            {"task_key": "ui", "expected_revision": b},
        ])
        self.assertEqual(out["status"], "HOST_INVOCATIONS_REQUIRED")
        self.assertEqual(out["stage"], "REAL_HOST_INVOCATION_REQUIRED")
        self.assertEqual([x["native_tool"] for x in out["handoffs"]],
                         ["spawn_agent", "spawn_agent"])
        self.assertEqual(out["after_real_invocation"]["tool"], "orbit_task_started")
        self.assertFalse(out["agent_invoked"])
        self.assertFalse(out["host_permissions_verified"])
        self.assertEqual(self.conn.total_changes, before)

    def test_preflight_with_one_of_two_reserved_tasks_returns_no_partial_packets(self):
        self.task("api", paths=["src/api/"])
        self.task("ui", paths=["src/ui/"], role="frontend")
        rev = self.reserve("api")
        self.reserve("ui")
        out = self.preview(reserved_tasks=[{"task_key": "api", "expected_revision": rev}])
        self.assertEqual(out["status"], "HOLD_HOST_PREFLIGHT")
        self.assertEqual(out["handoffs"], [])
        self.assertEqual(out["preflight"]["status"], "HOLD_HOST_PREFLIGHT")

    def test_stale_revision_or_read_only_workspace_holds_host_handoff(self):
        self.task("api", paths=["src/api/"])
        rev = self.reserve("api")
        stale = self.preview(reserved_tasks=[
            {"task_key": "api", "expected_revision": rev - 1}
        ])
        self.assertEqual(stale["status"], "HOLD_HOST_PREFLIGHT")
        self.assertEqual(stale["handoffs"], [])
        denied = self.preview(
            host_workspace_mode="read-only",
            reserved_tasks=[{"task_key": "api", "expected_revision": rev}],
        )
        self.assertEqual(denied["status"], "HOLD_HOST_PREFLIGHT")
        self.assertEqual(denied["handoffs"], [])
        self.assertIn("HOLD_HOST_WORKSPACE_READ_ONLY",
                      [x["status"] for x in denied["preflight"]["issues"]])

    def test_running_reservation_requires_real_host_reconciliation(self):
        self.task("api")
        rev = self.reserve("api")
        self.conn.execute(
            "UPDATE orbit_agent_tasks SET status='RUNNING',host_session='synthetic-session',revision=? "
            "WHERE project=? AND project_root=? AND task_key=?",
            (rev + 1, self.project, str(self.root), "api"))
        self.conn.commit()
        result = self.preview()
        self.assertEqual(result["status"], "HOLD_HOST_RECONCILIATION")
        self.assertTrue(result["host_reconciliation"]["needs_host_reconciliation"])
        self.assertEqual(result["reservation_candidates"] if "reservation_candidates" in result else [], [])
        self.assertFalse(result["host_session_liveness_verified"])

    def test_other_project_active_record_holds_without_leaking_identity(self):
        self.task("our-api", paths=["src/ours/"])
        self.task("other-secret", paths=["src/else/"], project="private-project")
        self.reserve("other-secret", project="private-project")
        out = self.preview()
        self.assertEqual(out["status"], "HOLD_HOST_RECONCILIATION")
        self.assertNotIn("other-secret", str(out))
        self.assertNotIn("private-project", str(out))
        self.assertEqual(out["handoffs"], [])
        self.assertFalse(out["host_reconciliation"]["needs_host_reconciliation"])

    def test_reported_work_requires_independent_review_before_next_wave(self):
        self.task("api", paths=["src/api/"])
        self.task("qa", paths=[], deps=("api",), role="qa")
        self.state("api", "REPORTED_DONE")
        before = self.conn.total_changes
        out = self.preview()
        self.assertEqual(out["status"], "INDEPENDENT_TASK_REVIEW_REQUIRED")
        self.assertEqual(out["pending_independent_reviews"][0]["tool"],
                         "orbit_task_review")
        self.assertEqual(out["reservation_candidates"], [])
        self.assertEqual(self.conn.total_changes, before)

    def test_all_review_accepted_needs_independent_integration_not_release(self):
        self.task("api", paths=["src/api/"])
        self.state("api", "REVIEW_ACCEPTED")
        out = self.preview()
        self.assertEqual(out["status"], "INTEGRATION_REVIEW_REQUIRED")
        self.assertFalse(out["source_tests_verified"])
        self.assertFalse(out["release_authorized"])
        self.assertIn("orbit_swarm_integration_review", out["next"])

    def test_native_tool_missing_suggests_serial_host_work_without_fake_agent(self):
        self.task("api", paths=["src/api/"])
        out = self.preview(available_host_tools=[])
        self.assertEqual(out["status"], "HOLD_NATIVE_TOOL_UNAVAILABLE")
        self.assertEqual(out["reservation_candidates"], [])
        self.assertFalse(out["serial_fallback"]["native_agent_invoked"])
        self.assertFalse(out["agent_invoked"])
        self.assertFalse(out["host_permissions_verified"])

    def test_bad_mode_conflicting_inputs_and_width_are_rejected(self):
        draft = [{
            "task_key": "api", "step": "Implementation", "role": "backend",
            "goal": "Build a separately reviewed endpoint implementation",
            "reason": "Clearly bounded development responsibility",
            "write_paths": [], "depends_on": [],
        }]
        with self.assertRaises(ValueError):
            self.preview(draft_tasks=draft, reserved_tasks=[{
                "task_key": "api", "expected_revision": 1
            }])
        with self.assertRaises(ValueError):
            self.preview(host_workspace_mode="bypass")
        with self.assertRaises(ValueError):
            self.preview(available_host_tools=["spawn_agent", "spawn_agent"])
        with self.assertRaises(ValueError):
            self.preview(max_parallel=1, reserved_tasks=[
                {"task_key": "api", "expected_revision": 1},
                {"task_key": "ui", "expected_revision": 1},
            ])
        with self.assertRaises(ValueError):
            self.preview(draft_tasks=[{**draft[0], "unexpected": "unsafe"}])

    def test_tool_exposure_is_read_only_without_duplicate_executor(self):
        metadata = next(t for t in orbit_mcp.TOOLS
                        if t["name"] == "orbit_native_coordination_preview")
        self.assertTrue(metadata["annotations"]["readOnlyHint"])
        self.assertTrue(metadata["annotations"]["idempotentHint"])
        self.assertFalse(metadata["annotations"]["destructiveHint"])
        self.assertFalse(metadata["annotations"]["openWorldHint"])
        self.assertEqual(len(orbit_mcp.TOOLS), 48)
        self.assertIn("orbit_task_started",
                      [x["name"] for x in orbit_mcp.TOOLS])
        self.assertFalse(self.preview()["state_written"])


if __name__ == "__main__":
    unittest.main()
