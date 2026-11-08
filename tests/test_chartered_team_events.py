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


    def _synthetic_lease(self, **kwargs):
        fields = {
            "action": "lease", "event_key": "lease-api",
            "task_key": "api", "task_revision": 1,
            "staff_event_key": "staff-api",
            "available_host_tools": ["read_file", "test_runner"],
            "lease_tool_names": ["read_file"],
            "lease_skill_names": [],
            "lease_expires_at": (datetime.now(timezone.utc) +
                                 timedelta(hours=4)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "host_workspace_mode": "read-only",
            "permission_state": "UNKNOWN",
        }
        return self.event(**{**fields, **kwargs})

    def _save_lease(self):
        self.approve_staff()
        preview = self._synthetic_lease()
        self.assertEqual(preview["status"], "CAPABILITY_INTENT_REVIEW")
        result = self._synthetic_lease(
            lease_expires_at=preview["payload"]["lease_expires_at"],
            expected_digest=preview["review_digest"], confirm_write=True)
        self.assertEqual(result["status"], "CAPABILITY_INTENT_RECORDED")
        return preview

    def test_capability_intent_is_no_host_grant_and_pinned_to_staff_request(self):
        self.approve_staff()
        before = self.conn.total_changes
        preview = self._synthetic_lease()
        self.assertEqual(preview["status"], "CAPABILITY_INTENT_REVIEW")
        self.assertEqual(before, self.conn.total_changes)
        self.assertEqual(preview["payload"]["requested_tool_names"], ["read_file"])
        self.assertFalse(preview["payload"]["host_skill_activation"])
        self.assertEqual(preview["payload"]["host_tool_grants"], [])
        self.assertFalse(preview["payload"]["host_lease_token_issued"])
        expiry = preview["payload"]["lease_expires_at"]
        mismatch = self._synthetic_lease(
            lease_expires_at=expiry, expected_digest="0"*64, confirm_write=True)
        self.assertEqual(mismatch["status"], "HOLD_DIGEST_MISMATCH")
        saved = self._synthetic_lease(
            lease_expires_at=expiry, expected_digest=preview["review_digest"],
            confirm_write=True)
        self.assertEqual(saved["status"], "CAPABILITY_INTENT_RECORDED")
        self.assertFalse(saved["tool_permission_granted"])
        replay = self._synthetic_lease(
            lease_expires_at=expiry, expected_digest=preview["review_digest"],
            confirm_write=True)
        self.assertEqual(replay["status"], "ALREADY_RECORDED")
        inbox = self.event(action="inbox", task_key="api")
        self.assertEqual(len(inbox["capability_intents"]), 1)
        self.assertFalse(inbox["capability_intents"][0]["actual_lease_granted"])

    def test_capability_expansion_privilege_drift_and_expiry_hold(self):
        self.approve_staff()
        self.assertEqual(
            self._synthetic_lease(lease_tool_names=["spawn_agent"])["status"],
            "HOLD_PRIVILEGED_WORKER_CAPABILITY")
        self.assertEqual(
            self._synthetic_lease(lease_tool_names=["write_file"])["status"],
            "HOLD_CAPABILITY_SCOPE_EXPANSION")
        self.assertEqual(
            self._synthetic_lease(available_host_tools=[])["status"],
            "HOLD_HOST_TOOL_NOT_CURRENTLY_REPORTED")
        self.assertEqual(
            self._synthetic_lease(lease_skill_names=["unapproved-skill"])["status"],
            "HOLD_SKILL_SCOPE_EXPANSION")
        self.assertEqual(
            self._synthetic_lease(lease_expires_at="2099-01-01T00:00:00Z")["status"],
            "HOLD_LEASE_EXPIRY_OUTSIDE_CHARTER")
        self.assertEqual(
            self._synthetic_lease(task_revision=42)["status"],
            "HOLD_STALE_TASK_REVISION")
        self.assertEqual(
            self._synthetic_lease(permission_state="DENIED")["status"],
            "HOLD_PERMISSION_DENIED")
        self.assertEqual(
            self._synthetic_lease(staff_event_key="missing-event")["status"],
            "HOLD_EVENT_NOT_FOUND")

    def test_duplicate_active_capability_intent_must_first_be_revoked(self):
        previous = self._save_lease()
        p = self._synthetic_lease(
            event_key="lease-again",
            lease_expires_at=previous["payload"]["lease_expires_at"])
        self.assertEqual(p["status"], "CAPABILITY_INTENT_REVIEW")
        denied = self._synthetic_lease(
            event_key="lease-again",
            lease_expires_at=previous["payload"]["lease_expires_at"],
            expected_digest=p["review_digest"], confirm_write=True)
        self.assertEqual(denied["status"], "HOLD_EXISTING_CAPABILITY_INTENT")

    def test_revoke_request_allowed_on_paused_charter_without_claiming_host_stop(self):
        self._save_lease()
        change = orbit_mcp.execute(self.conn, "orbit_autopilot_charter", {
            "project_root": str(self.root), "project": self.project,
            "mission_id": self.mission, "action": "pause",
            "expected_revision": 1, "confirm_write": True})
        self.assertEqual(change["status"], "PAUSED")
        args = {
            "action": "revoke", "event_key": "revoke-api",
            "lease_event_key": "lease-api", "task_key": "api",
            "expected_revision": 2, "summary": "Revoke proposed access after paused mission",
        }
        preview = self.event(**args)
        self.assertEqual(preview["status"], "CAPABILITY_REVOKE_REVIEW")
        out = self.event(**{**args, "expected_digest": preview["review_digest"],
                            "confirm_write": True})
        self.assertEqual(out["status"], "CAPABILITY_REVOKE_REQUEST_RECORDED")
        self.assertFalse(out["payload"]["host_revocation_verified"])
        self.assertFalse(out["worker_stopped"])
        self.assertEqual(self.event(**args)["status"],
                         "HOLD_REVOKE_ALREADY_REQUESTED")
        inbox = self.event(action="inbox", task_key="api")
        self.assertTrue(
            inbox["capability_intents"][0]["host_revocation_requested"])
        self.assertFalse(inbox["capability_intents"][0]["actual_lease_granted"])

    def test_host_reported_handoff_receipt_not_a_native_message(self):
        request = {
            "action": "handoff", "event_key": "api-to-qa",
            "task_key": "api", "task_revision": 1,
            "peer_task_key": "qa", "peer_revision": 1,
            "summary": "Reviewed implementation evidence for downstream QA task",
            "evidence_ref": "git:synthetic-reviewed-api-commit",
        }
        self.conn.execute(
            """UPDATE orbit_agent_tasks
               SET status='REVIEW_ACCEPTED',review_evidence='local synthetic review'
               WHERE project=? AND project_root=? AND task_key='api'""",
            (self.project, str(self.root)))
        self.conn.commit()
        preview = self.event(**request)
        self.assertEqual(preview["status"], "HANDOFF_REVIEW")
        recorded = self.event(**{**request, "expected_digest": preview["review_digest"],
                                  "confirm_write": True})
        self.assertEqual(recorded["status"], "HANDOFF_EVENT_RECORDED")
        self.assertEqual(len(self.event(action="inbox", task_key="qa")[
            "handoffs_without_reported_receipts"]), 1)
        args = {
            "action": "receipt", "event_key": "qa-receipt",
            "task_key": "qa", "task_revision": 3,
            "handoff_event_key": "api-to-qa",
            "observed_host_session": "synthetic-host-session",
            "summary": "Host reported viewing reviewed upstream evidence",
        }
        self.assertEqual(self.event(**args)["status"],
                         "HOLD_STALE_TASK_REVISION")
        self.conn.execute(
            """UPDATE orbit_agent_tasks
               SET status='RUNNING',revision=3,host_session='synthetic-host-session'
               WHERE project=? AND project_root=? AND task_key='qa'""",
            (self.project, str(self.root)))
        self.conn.commit()
        self.assertEqual(self.event(**{**args,
            "observed_host_session": "unrelated-session"})["status"],
                         "HOLD_NATIVE_SESSION_MISMATCH")
        self.conn.execute(
            """UPDATE orbit_agent_tasks SET revision=2
               WHERE project=? AND project_root=? AND task_key='api'""",
            (self.project, str(self.root)))
        self.conn.commit()
        self.assertEqual(self.event(**args)["status"],
                         "HOLD_UPSTREAM_REVIEW_REVISION_DRIFT")
        self.conn.execute(
            """UPDATE orbit_agent_tasks SET revision=1
               WHERE project=? AND project_root=? AND task_key='api'""",
            (self.project, str(self.root)))
        self.conn.commit()
        self.assertEqual(self.event(**args)["status"],
                         "HOLD_NATIVE_SEND_REPORT_REQUIRED")
        send = {
            "action": "send_report", "event_key": "send-to-qa",
            "task_key": "qa", "task_revision": 3,
            "handoff_event_key": "api-to-qa",
            "observed_host_session": "synthetic-host-session",
            "delivery_outcome": "SENT",
            "summary": "Synthetic host claimed native message was delivered",
        }
        send_plan = self.event(**send)
        self.assertEqual(send_plan["status"], "HOST_DELIVERY_OBSERVATION_REVIEW")
        sender = self.event(**{**send, "expected_digest": send_plan["review_digest"],
                               "confirm_write": True})
        self.assertEqual(sender["status"], "HOST_DELIVERY_OBSERVATION_RECORDED")
        self.assertFalse(sender["payload"]["actual_message_delivery_verified"])
        args["send_event_key"] = "send-to-qa"
        proposed = self.event(**args)
        self.assertEqual(proposed["status"], "HANDOFF_RECEIPT_REVIEW")
        saved = self.event(**{**args, "expected_digest": proposed["review_digest"],
                              "confirm_write": True})
        self.assertEqual(saved["status"], "HANDOFF_RECEIPT_RECORDED")
        self.assertFalse(saved["payload"]["host_delivery_verified"])
        self.assertFalse(saved["peer_message_sent"])
        self.assertEqual(self.event(**args)["status"],
                         "HOLD_HANDOFF_ALREADY_ACKNOWLEDGED")
        inbox = self.event(action="inbox", task_key="qa")
        self.assertEqual(len(inbox["handoffs_without_reported_receipts"]), 0)
        self.assertFalse(inbox["host_receipts_authenticated"])

    def test_capability_receipt_actions_reject_unknown_fields(self):
        with self.assertRaises(ValueError):
            self.event(action="lease", event_key="unsafe",
                       host_override_unsafe=True)
        with self.assertRaises(ValueError):
            self.event(action="receipt", event_key="unsafe",
                       grant_permissions=True)
        self.assertEqual(len(orbit_mcp.TOOLS), 57)


    def _reserved_native_dispatch(self):
        """Create synthetic chartered staff+lease+reservation, no real host."""
        self.approve_staff()
        lease = self._synthetic_lease(host_workspace_mode="workspace-write")
        self.assertEqual(lease["status"], "CAPABILITY_INTENT_REVIEW")
        saved = self._synthetic_lease(
            host_workspace_mode="workspace-write",
            lease_expires_at=lease["payload"]["lease_expires_at"],
            expected_digest=lease["review_digest"], confirm_write=True)
        self.assertEqual(saved["status"], "CAPABILITY_INTENT_RECORDED")
        reservation = orbit_tasks.reserve(self.conn, {
            "project": self.project, "task_key": "api",
            "expected_revision": 1,
            "approval_reference": "synthetic-real-host-review-not-attested",
            "confirm_write": True,
        }, self.root)
        self.assertEqual(reservation["status"], "RESERVED")
        self.assertEqual(reservation["task"]["revision"], 2)
        return {
            "action": "dispatch", "task_key": "api", "task_revision": 2,
            "lease_event_key": "lease-api", "host": "codex",
            "available_host_tools": ["collaboration.spawn_agent", "read_file", "test_runner"],
            "host_workspace_mode": "workspace-write",
        }

    def test_dispatch_existing_native_preflight_without_invocation(self):
        args = self._reserved_native_dispatch()
        before = self.conn.total_changes
        result = self.event(**args)
        self.assertEqual(result["status"], "HOST_NATIVE_DISPATCH_REVIEW_REQUIRED")
        self.assertEqual(self.conn.total_changes, before)
        self.assertFalse(result["native_invoked"])
        self.assertFalse(result["host_permission_verified"])
        self.assertFalse(result["tool_grants_applied"])
        self.assertFalse(result["skill_activated"])
        self.assertFalse(result["message_sent"])
        p = result["dispatch_packet"]
        self.assertEqual(p["task_key"], "api")
        self.assertEqual(p["task_revision"], 2)
        self.assertEqual(p["native_tool_caller_reported"], "collaboration.spawn_agent")
        self.assertEqual(p["allowed_write_paths"], ["src/api/"])
        self.assertEqual(p["worker_requested_tools_not_granted"], ["read_file"])
        self.assertEqual(p["lease_event_key"], "lease-api")
        self.assertFalse(p["host_permission_authenticated"])
        self.assertFalse(p["profile_installed_in_host"])
        self.assertEqual(p["reviewed_handoff_references"], [])

    def test_dispatch_holds_on_host_denial_scope_expansion_and_stale_task(self):
        args = self._reserved_native_dispatch()
        self.assertEqual(self.event(**{**args, "host":"antigravity"})["status"],
                         "HOLD_STAFF_HOST_MISMATCH")
        self.assertEqual(self.event(**{**args, "host_workspace_mode":"read-only"})["status"],
                         "HOLD_WORKSPACE_MODE_DIFFERS_FROM_LEASE")
        self.assertEqual(self.event(**{**args, "permission_state":"DENIED"})["status"],
                         "HOLD_HOST_PERMISSION_DENIED")
        self.assertEqual(self.event(**{**args, "available_host_tools":["collaboration.spawn_agent"]})["status"],
                         "HOLD_WORKER_TOOL_NOT_ADVERTISED")
        self.assertEqual(self.event(**{**args, "task_revision":1})["status"],
                         "HOLD_STALE_TASK_REVISION")
        self.assertEqual(self.event(**{**args, "confirm_write":True})["status"],
                         "HOLD_DISPATCH_READ_ONLY")
        self.assertFalse(self.event(**{**args, "confirm_write":True})["state_written"])

    def test_dispatch_revocation_and_expired_intent_never_launch(self):
        from unittest.mock import patch
        args = self._reserved_native_dispatch()
        lease = self.event(action="inbox", task_key="api")["capability_intents"][0]
        # Expiry controls the dispatch even if the mission itself is still active.
        from datetime import datetime
        future = datetime.now(timezone.utc) + timedelta(hours=12)
        with patch.object(orbit_autopilot, "utc_now", return_value=future):
            self.assertEqual(self.event(**args)["status"],
                             "HOLD_CAPABILITY_INTENT_EXPIRED")
        rev = {
            "action": "revoke", "event_key": "revoke-api",
            "task_key": "api", "lease_event_key": "lease-api",
            "summary": "Worker task scope is revoked by local operator request",
        }
        preview = self.event(**rev)
        self.assertEqual(preview["status"], "CAPABILITY_REVOKE_REVIEW")
        saved = self.event(**{**rev, "expected_digest": preview["review_digest"],
                             "confirm_write": True})
        self.assertEqual(saved["status"], "CAPABILITY_REVOKE_REQUEST_RECORDED")
        self.assertEqual(self.event(**args)["status"],
                         "HOLD_CAPABILITY_REVOCATION_REQUESTED")

    def test_dispatch_requires_reviewed_dependency_handoff(self):
        # Staff QA bot and bind a write-scoped capability intent while PLANNED.
        proposal = self.staffing(
            task_key="qa", event_key="staff-qa", worker_kind="bot",
            requested_tool_names=["read_file"])
        self.assertEqual(proposal["status"], "STAFFING_REQUEST_REVIEW")
        approved = self.staffing(
            task_key="qa", event_key="staff-qa", worker_kind="bot",
            requested_tool_names=["read_file"],
            review_manifest=proposal["payload"]["skill_manifest"],
            expected_digest=proposal["review_digest"], confirm_write=True)
        self.assertEqual(approved["status"], "STAFF_REQUEST_RECORDED")
        lease = self._synthetic_lease(
            task_key="qa", event_key="lease-qa", staff_event_key="staff-qa",
            host_workspace_mode="workspace-write")
        self.assertEqual(lease["status"], "CAPABILITY_INTENT_REVIEW")
        saved = self._synthetic_lease(
            task_key="qa", event_key="lease-qa", staff_event_key="staff-qa",
            host_workspace_mode="workspace-write",
            lease_expires_at=lease["payload"]["lease_expires_at"],
            expected_digest=lease["review_digest"], confirm_write=True)
        self.assertEqual(saved["status"], "CAPABILITY_INTENT_RECORDED")
        # Synthetic task-review evidence (never independently verified by test).
        self.conn.execute(
            """UPDATE orbit_agent_tasks SET status='REVIEW_ACCEPTED',
               review_evidence='synthetic approved source diff'
               WHERE project=? AND project_root=? AND task_key='api'""",
            (self.project, str(self.root)))
        self.conn.commit()
        handoff = {
            "action": "handoff", "event_key": "api-to-qa",
            "task_key": "api", "task_revision": 1,
            "peer_task_key": "qa", "peer_revision": 1,
            "summary": "Synthetic reviewed API test evidence for QA",
            "evidence_ref": "git:synthetic-approved-commit",
        }
        plan = self.event(**handoff)
        self.assertEqual(plan["status"], "HANDOFF_REVIEW")
        saved = self.event(**{**handoff, "expected_digest": plan["review_digest"],
                             "confirm_write": True})
        self.assertEqual(saved["status"], "HANDOFF_EVENT_RECORDED")
        reserved = orbit_tasks.reserve(self.conn, {
            "project": self.project, "task_key": "qa", "expected_revision": 1,
            "approval_reference": "synthetic-qa-operator-reviewed",
            "confirm_write": True,
        }, self.root)
        self.assertEqual(reserved["status"], "RESERVED")
        request = {
            "action": "dispatch", "task_key": "qa", "task_revision": 2,
            "lease_event_key": "lease-qa", "host": "codex",
            "available_host_tools": ["collaboration.spawn_agent", "read_file"],
            "host_workspace_mode": "workspace-write",
        }
        result = self.event(**request)
        self.assertEqual(result["status"], "HOST_NATIVE_DISPATCH_REVIEW_REQUIRED")
        self.assertEqual(len(result["dispatch_packet"]["reviewed_handoff_references"]), 1)
        self.assertEqual(result["dispatch_packet"]["worker_kind"], "bot")
        self.conn.execute(
            """UPDATE orbit_agent_tasks SET revision=2
               WHERE project=? AND project_root=? AND task_key='api'""",
            (self.project, str(self.root)))
        self.conn.commit()
        self.assertEqual(self.event(**request)["status"],
                         "HOLD_MISSING_OR_AMBIGUOUS_REVIEWED_HANDOFF")


    def _native_recipient_with_handoff(self):
        """Synthetic native session and checked dependency, without model calls."""
        self.conn.execute(
            """UPDATE orbit_agent_tasks SET status='REVIEW_ACCEPTED',
               review_evidence='synthetic accepted source diff'
               WHERE project=? AND project_root=? AND task_key='api'""",
            (self.project, str(self.root)))
        self.conn.commit()
        staff = self.staffing(
            task_key="qa", event_key="staff-qa", worker_kind="bot",
            requested_tool_names=["read_file"])
        self.assertEqual(staff["status"], "STAFFING_REQUEST_REVIEW")
        self.assertEqual(self.staffing(
            task_key="qa", event_key="staff-qa", worker_kind="bot",
            requested_tool_names=["read_file"],
            review_manifest=staff["payload"]["skill_manifest"],
            expected_digest=staff["review_digest"], confirm_write=True)["status"],
            "STAFF_REQUEST_RECORDED")
        lease = self._synthetic_lease(
            task_key="qa", event_key="lease-qa",
            staff_event_key="staff-qa", host_workspace_mode="workspace-write")
        self.assertEqual(lease["status"], "CAPABILITY_INTENT_REVIEW")
        self.assertEqual(self._synthetic_lease(
            task_key="qa", event_key="lease-qa",
            staff_event_key="staff-qa", host_workspace_mode="workspace-write",
            lease_expires_at=lease["payload"]["lease_expires_at"],
            expected_digest=lease["review_digest"], confirm_write=True)["status"],
            "CAPABILITY_INTENT_RECORDED")
        handoff = {
            "action": "handoff", "event_key": "api-to-qa",
            "task_key": "api", "task_revision": 1,
            "peer_task_key": "qa", "peer_revision": 1,
            "summary": "Synthetic reviewed API test evidence for downstream QA",
            "evidence_ref": "git:reviewed-synthetic-upstream-source",
        }
        plan = self.event(**handoff)
        self.assertEqual(plan["status"], "HANDOFF_REVIEW")
        self.assertEqual(self.event(**{**handoff,
            "expected_digest": plan["review_digest"],
            "confirm_write": True})["status"], "HANDOFF_EVENT_RECORDED")
        reserved = orbit_tasks.reserve(self.conn, {
            "project": self.project, "task_key": "qa", "expected_revision": 1,
            "approval_reference": "synthetic-qa-permitted-native-worker",
            "confirm_write": True,
        }, self.root)
        self.assertEqual(reserved["status"], "RESERVED")
        running = orbit_tasks.started(self.conn, {
            "project": self.project, "task_key": "qa", "expected_revision": 2,
            "host_session": "claimed-codex-native-session",
            "confirm_write": True,
        }, self.root)
        self.assertEqual(running["status"], "RUNNING_REPORTED")
        return {
            "action": "route", "handoff_event_key": "api-to-qa",
            "task_key": "qa", "task_revision": 3,
            "observed_host_session": "claimed-codex-native-session",
            "host": "codex",
            "available_host_tools": ["collaboration.send_message"],
        }

    def test_relay_envelope_is_read_only_and_not_peer_chat(self):
        args = self._native_recipient_with_handoff()
        before = self.conn.total_changes
        result = self.event(**args)
        self.assertEqual(result["status"], "HOST_NATIVE_MESSAGE_REVIEW_REQUIRED")
        self.assertEqual(self.conn.total_changes, before)
        self.assertFalse(result["native_message_sent"])
        self.assertFalse(result["recipient_delivery_verified"])
        packet = result["relay_packet"]
        self.assertEqual(packet["format"], "orbit-native-relay-v1")
        self.assertEqual(packet["target_task"], "qa")
        self.assertEqual(packet["source_task"], "api")
        self.assertEqual(packet["native_send_tool_caller_reported"],
                         "collaboration.send_message")
        self.assertEqual(packet["target_session_caller_reported"],
                         "claimed-codex-native-session")
        self.assertFalse(packet["actual_native_delivery_verified"])
        self.assertNotIn("Synthetic reviewed API test evidence",
                         packet["message_body"])
        self.assertEqual(self.event(**{**args,"confirm_write":True})["status"],
                         "HOLD_ROUTE_READ_ONLY")
        self.assertEqual(self.event(**{**args,"host":"antigravity",
            "available_host_tools":["invoke_subagent"]})["status"],
                         "HOLD_NATIVE_MESSAGE_TOOL_UNAVAILABLE")
        self.assertEqual(self.event(**{**args,
            "available_host_tools":[]})["status"],
                         "HOLD_NATIVE_MESSAGE_TOOL_UNAVAILABLE")
        self.assertEqual(self.event(**{**args,
            "observed_host_session":"other-host-session"})["status"],
                         "HOLD_NATIVE_SESSION_MISMATCH")

    def test_audited_delivery_report_and_matching_recipient_receipt(self):
        args = self._native_recipient_with_handoff()
        report = {
            "action": "send_report", "event_key": "sent-api-qa",
            "task_key": "qa", "task_revision": 3,
            "observed_host_session": "claimed-codex-native-session",
            "handoff_event_key": "api-to-qa", "delivery_outcome": "SENT",
            "summary": "Host reported that native message tool sent the pointer",
        }
        p = self.event(**report)
        self.assertEqual(p["status"], "HOST_DELIVERY_OBSERVATION_REVIEW")
        saved = self.event(**{**report, "expected_digest":p["review_digest"],
                              "confirm_write":True})
        self.assertEqual(saved["status"], "HOST_DELIVERY_OBSERVATION_RECORDED")
        self.assertFalse(saved["payload"]["actual_message_delivery_verified"])
        self.assertEqual(self.event(**report)["status"],
                         "HOLD_DELIVERY_ALREADY_REPORTED")
        inbox = self.event(action="inbox", task_key="qa")
        self.assertEqual(len(inbox["handoffs_without_reported_receipts"]), 1)
        self.assertTrue(
            inbox["handoffs_without_reported_receipts"][0]["host_send_caller_reported"])
        receipt = {
            "action":"receipt", "event_key":"recv-api-qa", "task_key":"qa",
            "task_revision":3, "handoff_event_key":"api-to-qa",
            "send_event_key":"sent-api-qa",
            "observed_host_session":"claimed-codex-native-session",
            "summary":"Host reported QA agent received the reviewed evidence pointer",
        }
        a = self.event(**receipt)
        self.assertEqual(a["status"], "HANDOFF_RECEIPT_REVIEW")
        done = self.event(**{**receipt, "expected_digest":a["review_digest"],
                             "confirm_write":True})
        self.assertEqual(done["status"], "HANDOFF_RECEIPT_RECORDED")
        self.assertFalse(done["payload"]["host_delivery_verified"])
        self.assertEqual(len(self.event(action="inbox",task_key="qa")[
            "handoffs_without_reported_receipts"]), 0)
        self.assertFalse(self.event(**args)["native_message_sent"])
        self.assertEqual(self.event(**args)["status"],
                         "HOLD_HANDOFF_ALREADY_ACKNOWLEDGED")

    def test_failed_or_cross_session_send_report_cannot_authorize_ack(self):
        self._native_recipient_with_handoff()
        report = {
            "action":"send_report","event_key":"failed-send",
            "task_key":"qa","task_revision":3,
            "observed_host_session":"claimed-codex-native-session",
            "handoff_event_key":"api-to-qa", "delivery_outcome":"DENIED",
            "summary":"Host denied native message permission for this worker",
        }
        preview=self.event(**report)
        self.assertEqual(preview["status"],"HOST_DELIVERY_OBSERVATION_REVIEW")
        saved=self.event(**{**report,"expected_digest":preview["review_digest"],
                            "confirm_write":True})
        self.assertEqual(saved["status"],"HOST_DELIVERY_OBSERVATION_RECORDED")
        receipt={
            "action":"receipt","event_key":"invalid-receipt",
            "task_key":"qa","task_revision":3,
            "handoff_event_key":"api-to-qa","send_event_key":"failed-send",
            "observed_host_session":"claimed-codex-native-session",
            "summary":"Attempt to acknowledge the explicitly denied message",
        }
        self.assertEqual(self.event(**receipt)["status"],
                         "HOLD_NATIVE_SEND_NOT_REPORTED_SUCCESSFUL")
        self.assertEqual(self.event(**{**receipt,
            "send_event_key":"missing"})["status"], "HOLD_EVENT_NOT_FOUND")
        self.assertEqual(self.event(**{**report,
            "observed_host_session":"other-host-session"})["status"],
                         "HOLD_NATIVE_SESSION_MISMATCH")


    def test_native_stop_request_is_audit_only_and_not_pid_kill(self):
        recipient = self._native_recipient_with_handoff()
        request = {
            "action": "stop_request", "event_key": "stop-qa",
            "task_key": "qa", "task_revision": 3,
            "observed_host_session": "claimed-codex-native-session",
            "summary": "Owner requested stop of this bounded synthetic worker",
        }
        before = self.conn.total_changes
        p = self.event(**request)
        self.assertEqual(p["status"], "NATIVE_STOP_REQUEST_REVIEW")
        self.assertEqual(before, self.conn.total_changes)
        self.assertFalse(p["payload"]["process_terminated_by_orbit"])
        saved = self.event(**{**request,
            "expected_digest": p["review_digest"], "confirm_write": True})
        self.assertEqual(saved["status"], "NATIVE_STOP_REQUEST_RECORDED")
        self.assertTrue(saved["state_written"])
        self.assertFalse(saved["payload"]["task_scope_released"])
        self.assertEqual(self.event(**request)["status"],
                         "HOLD_STOP_ALREADY_REQUESTED")
        self.assertEqual(self.event(**recipient)["status"],
                         "HOLD_RECIPIENT_STOP_REQUESTED")
        self.assertEqual(self.event(
            action="receipt", event_key="post-stop-receipt",
            task_key="qa", task_revision=3,
            handoff_event_key="api-to-qa",
            observed_host_session="claimed-codex-native-session",
            summary="Attempted receipt after native worker stop request")["status"],
                         "HOLD_RECIPIENT_STOP_REQUESTED")
        current = orbit_tasks._row(self.conn,
            {"project":self.project,"task_key":"qa"}, self.root)
        self.assertEqual(current["status"], "RUNNING")

    def test_stop_plan_native_codex_hint_or_host_ui_fallback(self):
        self._native_recipient_with_handoff()
        plan = {
            "action": "stop_plan", "task_key": "qa", "task_revision": 3,
            "observed_host_session": "claimed-codex-native-session",
            "host": "codex",
            "available_host_tools": ["collaboration.interrupt_agent"],
        }
        self.assertEqual(self.event(**plan)["status"],
                         "HOLD_EXACT_STOP_REQUEST_REQUIRED")
        request = {
            "action": "stop_request", "event_key": "stop-qa",
            "task_key": "qa", "task_revision": 3,
            "observed_host_session": "claimed-codex-native-session",
            "summary": "Stop for host reconciliation of native task session",
        }
        p = self.event(**request)
        self.assertEqual(p["status"], "NATIVE_STOP_REQUEST_REVIEW")
        self.assertEqual(self.event(**{**request,
            "expected_digest": p["review_digest"], "confirm_write": True})["status"],
            "NATIVE_STOP_REQUEST_RECORDED")
        before = self.conn.total_changes
        ready = self.event(**plan)
        self.assertEqual(ready["status"], "HOST_NATIVE_STOP_REVIEW_REQUIRED")
        self.assertEqual(before, self.conn.total_changes)
        self.assertFalse(ready["native_stop_invoked"])
        self.assertFalse(ready["task_scope_released"])
        self.assertEqual(ready["host_action_hint"]["native_stop_tool_caller_reported"],
                         "collaboration.interrupt_agent")
        self.assertEqual(ready["host_action_hint"]["target_session_caller_reported"],
                         "claimed-codex-native-session")
        self.assertFalse(ready["host_action_hint"]["actual_stop_verified"])
        self.assertEqual(self.event(**{**plan,"host":"antigravity",
            "available_host_tools":["invoke_subagent"]})["status"],
                         "HOLD_STOP_HOST_MISMATCH")
        self.assertEqual(self.event(**{**plan,
            "available_host_tools":[]})["status"],
                         "HOLD_NATIVE_STOP_TOOL_UNAVAILABLE")
        self.assertEqual(self.event(**{**plan,
            "observed_host_session":"wrong-session"})["status"],
                         "HOLD_NATIVE_SESSION_MISMATCH")
        self.assertEqual(self.event(**{**plan, "confirm_write": True})["status"],
                         "HOLD_STOP_PLAN_READ_ONLY")

    def test_paused_mission_still_accepts_stop_request_and_safe_plan(self):
        self._native_recipient_with_handoff()
        paused = orbit_mcp.execute(self.conn, "orbit_autopilot_charter", {
            "project_root":str(self.root),"project":self.project,
            "mission_id":self.mission,"action":"pause",
            "expected_revision":1,"confirm_write":True})
        self.assertEqual(paused["status"],"PAUSED")
        req={
            "action":"stop_request","event_key":"paused-stop",
            "task_key":"qa","task_revision":3,
            "expected_revision":2,
            "observed_host_session":"claimed-codex-native-session",
            "summary":"Pause requires stopping exact synthetic host worker",
        }
        p=self.event(**req)
        self.assertEqual(p["status"],"NATIVE_STOP_REQUEST_REVIEW")
        saved=self.event(**{**req,"expected_digest":p["review_digest"],
                            "confirm_write":True})
        self.assertEqual(saved["status"],"NATIVE_STOP_REQUEST_RECORDED")
        hint=self.event(action="stop_plan", task_key="qa",task_revision=3,
                        expected_revision=2,host="codex",
                        observed_host_session="claimed-codex-native-session",
                        available_host_tools=["collaboration.interrupt_agent"])
        self.assertEqual(hint["status"],"HOST_NATIVE_STOP_REVIEW_REQUIRED")
        self.assertFalse(hint["native_stop_invoked"])

if __name__ == "__main__":
    unittest.main()
