"""Synthetic chartered team staffing/handoff regression tests.

These tests never launch any agent or assume saved approval is host consent.
"""
from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source" / "runtime"))

import orbit_autopilot
import orbit_mcp
import orbit_tasks
import orbit_team_events


class CharteredTeamEventTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name, "synthetic-project")
        self.root.mkdir()
        self.root = self.root.resolve(strict=True)
        self.other = Path(temp.name, "other-project")
        self.other.mkdir()
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.addCleanup(self.conn.close)
        orbit_tasks.setup(self.conn)
        orbit_autopilot.setup(self.conn)
        self.project = "test-team"
        self.mission = "team-phase"
        self.new_task("api", "backend", "Build a safe API for the local fixture", [])
        self.new_task("qa", "qa", "Run repeatable API regression checks", ["api"])
        base = {
            "project_root": str(self.root), "project": self.project,
            "mission_id": self.mission,
            "objective": "Implement bounded team collaboration on the fixture",
            "roadmap_ref": "docs/ROADMAP.md",
            "roadmap_revision": "reviewed-synthetic-tasks",
            "branch": "feat/synthetic-team",
            "expires_at": (datetime.now(timezone.utc) +
                           timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "task_keys": ["api", "qa"],
            "allowed_paths": ["src/api/", "tests/"],
            "allowed_decisions": ["implementation_detail"],
            "max_parallel": 1, "max_attempts_per_task": 2,
        }
        preview = orbit_mcp.execute(self.conn, "orbit_autopilot_charter",
                                    {**base, "action": "preview"})
        result = orbit_mcp.execute(self.conn, "orbit_autopilot_charter", {
            **base, "action": "activate",
            "expected_digest": preview["charter_digest"],
            "approval_reference": "caller-reported-owner-review",
            "confirm_write": True,
        })
        self.assertEqual(result["status"], "CHARTER_RECORDED")
        self.args = {
            "project_root": str(self.root), "project": self.project,
            "mission_id": self.mission, "expected_revision": 1,
            "reported_branch": "feat/synthetic-team",
        }

    def new_task(self, key, role, goal, deps):
        paths = ["src/api/"] if key == "api" else ["tests/"]
        result = orbit_tasks.plan(self.conn, {
            "project": self.project, "task_key": key, "step": "BUILD",
            "role": role, "goal": goal,
            "reason": "Synthetic scoped task for an approved development mission",
            "write_paths": paths, "depends_on": deps, "confirm_write": True,
        }, self.root)
        self.assertEqual(result["status"], "PLANNED")

    def event(self, **kwargs):
        return orbit_mcp.execute(self.conn, "orbit_team_event",
                                 {**self.args, **kwargs})

    def staffing(self, **kwargs):
        fields = {
            "action": "staff", "event_key": "staff-api", "task_key": "api",
            "task_revision": 1, "worker_kind": "agent", "host": "codex",
            "available_host_tools": ["collaboration.spawn_agent", "read_file", "test_runner"],
            "requested_tool_names": ["read_file", "test_runner"],
            "requested_skill_names": [], "permission_state": "UNKNOWN",
        }
        return self.event(**{**fields, **kwargs})

    def approve_staff(self, **kwargs):
        proposal = self.staffing(**kwargs)
        self.assertEqual(proposal["status"], "STAFFING_REQUEST_REVIEW")
        return self.staffing(**{
            **kwargs, "expected_digest": proposal["review_digest"],
            "review_manifest": proposal["payload"]["skill_manifest"],
            "confirm_write": True})

    def test_staffing_preview_is_read_only_and_host_untrusted(self):
        before = self.conn.total_changes
        result = self.staffing()
        self.assertEqual(result["status"], "STAFFING_REQUEST_REVIEW")
        self.assertEqual(self.conn.total_changes, before)
        self.assertNotIn("orbit_team_events", [
            row[0] for row in self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")])
        self.assertEqual(result["payload"]["requested_tool_names"],
                         ["read_file", "test_runner"])
        self.assertEqual(result["payload"]["host_tool_grants"], [])
        self.assertFalse(result["worker_spawned"])
        self.assertFalse(result["tool_permission_granted"])

    def test_exact_manifest_and_digest_required_for_local_staff_event(self):
        preview = self.staffing()
        bad = self.staffing(confirm_write=True, expected_digest="a"*64)
        self.assertEqual(bad["status"], "HOLD_SKILL_PINS_NOT_REVALIDATED")
        unpinned = self.staffing(
            confirm_write=True, expected_digest=preview["review_digest"])
        self.assertEqual(unpinned["status"], "HOLD_SKILL_PINS_NOT_REVALIDATED")
        good = self.approve_staff()
        self.assertEqual(good["status"], "STAFF_REQUEST_RECORDED")
        self.assertTrue(good["state_written"])
        self.assertFalse(good["worker_spawned"])
        self.assertFalse(good["skill_installed"])
        self.assertFalse(good["tool_permission_granted"])
        replay = self.staffing(
            review_manifest=preview["payload"]["skill_manifest"],
            expected_digest=preview["review_digest"], confirm_write=True)
        self.assertEqual(replay["status"], "ALREADY_RECORDED")
        inbox = self.event(action="inbox", task_key="api")
        self.assertEqual(inbox["event_count"], 1)
        self.assertNotIn("payload_json", inbox["events"][0])

    def test_concurrent_duplicate_request_blocked_even_new_key(self):
        self.approve_staff()
        p = self.staffing(event_key="second-key")
        self.assertEqual(p["status"], "STAFFING_REQUEST_REVIEW")
        result = self.staffing(
            event_key="second-key", review_manifest=p["payload"]["skill_manifest"],
            expected_digest=p["review_digest"], confirm_write=True)
        self.assertEqual(result["status"], "HOLD_EXISTING_STAFF_REQUEST")

    def test_no_recursive_tools_or_stale_task_or_cross_project(self):
        result = self.staffing(requested_tool_names=["collaboration.spawn_agent"])
        self.assertEqual(result["status"], "HOLD_RECURSIVE_OR_PRIVILEGED_TOOL")
        self.assertEqual(self.staffing(task_revision=2)["status"],
                         "HOLD_STALE_TASK_REVISION")
        self.assertEqual(self.staffing(project="unrelated")["status"],
                         "HOLD_MISSION_INACTIVE")
        self.assertEqual(self.staffing(permission_state="DENIED")["status"],
                         "HOLD_PERMISSION_DENIED")
        with self.assertRaises(ValueError):
            self.staffing(requested_tool_names=["read_file"],
                          permission_state="INVALID")
        result = self.staffing(requested_tool_names=["not-advertised"])
        self.assertEqual(result["status"], "HOLD_UNADVERTISED_TOOL")

    def test_handoff_requires_reviewed_dependency_and_exact_revisions(self):
        request = {
            "action": "handoff", "event_key": "handoff-api-qa",
            "task_key": "api", "task_revision": 1,
            "peer_task_key": "qa", "peer_revision": 1,
            "summary": "Verified acceptance evidence for the reviewed API implementation",
            "evidence_ref": "git:synthetic-api-verified-commit",
        }
        held = self.event(**request)
        self.assertEqual(held["status"], "HOLD_UPSTREAM_INDEPENDENT_REVIEW")
        self.conn.execute(
            """UPDATE orbit_agent_tasks
               SET status='REVIEW_ACCEPTED', review_evidence='reviewed synthetic diff'
               WHERE project=? AND project_root=? AND task_key='api'""",
            (self.project, str(self.root)))
        self.conn.commit()
        proposal = self.event(**request)
        self.assertEqual(proposal["status"], "HANDOFF_REVIEW")
        recorded = self.event(**{**request, "expected_digest": proposal["review_digest"],
                                 "confirm_write": True})
        self.assertEqual(recorded["status"], "HANDOFF_EVENT_RECORDED")
        self.assertFalse(recorded["peer_message_sent"])
        self.assertFalse(recorded["payload"]["delivered_to_host"])
        self.assertEqual(self.event(action="inbox", task_key="qa")["event_count"], 1)
        blocked = self.event(**{**request, "peer_revision": 3})
        self.assertEqual(blocked["status"], "HOLD_STALE_TASK_REVISION")

    def test_retire_never_claims_host_stop_or_removes_profiles(self):
        self.approve_staff()
        held = self.event(
            action="retire", event_key="retire-api",
            task_key="api", task_revision=1, host_terminal_state="COMPLETED")
        self.assertEqual(held["status"], "HOLD_TASK_NOT_TERMINAL")
        self.conn.execute(
            """UPDATE orbit_agent_tasks
               SET status='REVIEW_ACCEPTED',review_evidence='synthetic source review',
                   host_session='host-claimed-session'
               WHERE project=? AND project_root=? AND task_key='api'""",
            (self.project, str(self.root)))
        self.conn.commit()
        args = dict(action="retire", event_key="retire-api",
                    task_key="api", task_revision=1,
                    observed_host_session="host-claimed-session",
                    host_terminal_state="COMPLETED")
        p = self.event(**args)
        self.assertEqual(p["status"], "RETIRE_NOTE_REVIEW")
        saved = self.event(**{**args, "expected_digest": p["review_digest"],
                              "confirm_write": True})
        self.assertEqual(saved["status"], "RETIRE_NOTE_RECORDED")
        self.assertFalse(saved["worker_stopped"])
        self.assertFalse(saved["payload"]["profile_deleted"])
        self.assertFalse(saved["payload"]["native_host_termination_verified"])

    def test_paused_charter_holds_write_and_history_is_still_visible(self):
        self.approve_staff()
        control = orbit_mcp.execute(self.conn, "orbit_autopilot_charter", {
            "project_root": str(self.root), "project": self.project,
            "mission_id": self.mission, "expected_revision": 1,
            "action": "pause", "confirm_write": True})
        self.assertEqual(control["status"], "PAUSED")
        self.assertEqual(self.staffing(event_key="another")["status"],
                         "HOLD_MISSION_INACTIVE")
        self.assertEqual(self.event(action="inbox")["event_count"], 1)

    def test_unexpected_schema_fields_cannot_override_permission(self):
        with self.assertRaises(ValueError):
            self.event(action="staff", task_key="api", event_key="evil",
                       bypass_host_permission=True)
        self.assertNotIn("orbit_team_event", orbit_mcp.READ_ONLY_TOOLS)
        self.assertEqual(len(orbit_mcp.TOOLS), 57)


if __name__ == "__main__":
    unittest.main()
