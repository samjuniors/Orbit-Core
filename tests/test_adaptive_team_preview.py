"""Regression tests for Orbit's review-only adaptive Team Builder."""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source" / "runtime"))

import orbit_mcp
import orbit_tasks
import orbit_team_builder


class AdaptiveTeamPreviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "sandbox-project"
        self.root.mkdir()
        # Match production MCP project_root canonicalization on Windows.
        self.root = self.root.resolve(strict=True)
        self.conn = sqlite3.connect(":memory:")
        self.addCleanup(self.conn.close)
        self.conn.row_factory = sqlite3.Row
        orbit_tasks.setup(self.conn)
        self.project = "team-sandbox"
        self.add_task("api", "backend", "Create secure API route", "REVIEW_ACCEPTED")
        self.add_task("tests", "qa", "Run repeatable API regression checks",
                      "PLANNED", ["api"])

    def add_task(self, key, role, goal, status, deps=None, project=None):
        self.conn.execute(
            """INSERT INTO orbit_agent_tasks
               (project, project_root, task_key, step, role, goal, reason,
                write_paths, depends_on, status, revision, created_at, updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (project or self.project, str(self.root), key, "build", role,
             goal, "Reviewed task", "[]", json.dumps(deps or []),
             status, 1, "2026-01-01T00:00:00+00:00",
             "2026-01-01T00:00:00+00:00"))
        self.conn.commit()

    def args(self, **overrides):
        a = {
            "project_root": str(self.root),
            "project": self.project,
            "host": "codex",
            "available_host_tools": ["collaboration.spawn_agent"],
            "tasks": [
                {"task_key": "api", "expected_revision": 1, "kind": "agent"},
                {"task_key": "tests", "expected_revision": 1, "kind": "bot"},
            ],
        }
        a.update(overrides)
        return a

    def test_registry_and_read_only_contract(self):
        names = [item["name"] for item in orbit_mcp.TOOLS]
        self.assertIn("orbit_team_preview", names)
        self.assertIn("orbit_team_preview", orbit_mcp.READ_ONLY_TOOLS)
        before = self.conn.total_changes
        result = orbit_mcp.execute(self.conn, "orbit_team_preview", self.args())
        self.assertEqual(result["status"], "TEAM_REVIEW_READY")
        self.assertEqual(self.conn.total_changes, before)
        self.assertEqual(result["chief"], "ORBIT")
        self.assertEqual(result["max_active_native_workers"], 2)
        self.assertFalse(result["worker_spawned"])
        self.assertFalse(result["team_activation_allowed"])
        self.assertFalse(result["host_permission_verified"])
        by_key = {w["task_key"]: w for w in result["workers"]}
        self.assertEqual(by_key["api"]["lead"], "engineering")
        self.assertEqual(by_key["tests"]["lead"], "quality")
        self.assertEqual(by_key["tests"]["proposed_kind"], "bot")
        self.assertFalse(by_key["tests"]["tool_permission_verified"])
        self.assertEqual(result["orbit_native_invocation_hints"],
                         ["collaboration.spawn_agent"])
        self.assertEqual(by_key["api"]["worker_tool_grants"], [])
        self.assertEqual(by_key["tests"]["worker_tool_grants"], [])
        self.assertEqual(result["handoffs"][0]["channel"], "AGENT_TO_BOT")
        self.assertEqual(result["handoffs"][0]["gate"], "REVIEWABLE_HANDOFF")
        self.assertFalse(result["handoffs"][0]["message_sent"])

    def test_dynamic_kind_and_bot_to_bot_handoff(self):
        self.add_task("format", "writer", "Format generated notes",
                      "REVIEW_ACCEPTED")
        self.add_task("publish-notes", "writer", "Batch note formatting",
                      "PLANNED", ["format"])
        args = self.args(tasks=[
            {"task_key": "format", "expected_revision": 1, "kind": "bot"},
            {"task_key": "publish-notes", "expected_revision": 1, "kind": "bot"},
        ])
        result = orbit_team_builder.preview(self.conn, self.root, self.project, args)
        self.assertEqual(result["handoffs"][0]["channel"], "BOT_TO_BOT")
        self.assertFalse(result["handoffs"][0]["host_delivery_allowed"])

    def test_unreviewed_dependency_never_crosses_gate(self):
        self.conn.execute(
            "UPDATE orbit_agent_tasks SET status='REPORTED_DONE' WHERE task_key='api'")
        result = orbit_team_builder.preview(
            self.conn, self.root, self.project, self.args())
        self.assertEqual(result["handoffs"][0]["gate"], "HOLD_UPSTREAM_REVIEW")
        self.assertFalse(result["handoffs"][0]["message_sent"])

    def test_stale_revision_cross_project_and_denied_permission(self):
        stale = self.args(tasks=[{"task_key": "api", "expected_revision": 2}])
        self.assertEqual(
            orbit_team_builder.preview(self.conn, self.root, self.project, stale)["status"],
            "HOLD_STALE_TASK")
        other = self.args(project="unrelated-project")
        self.assertEqual(
            orbit_mcp.execute(self.conn, "orbit_team_preview", other)["status"],
            "HOLD_TASK_MISSING")
        denied = self.args(permission_state="DENIED")
        result = orbit_team_builder.preview(self.conn, self.root, self.project, denied)
        self.assertEqual(result["status"], "HOLD_PERMISSION_DENIED")
        self.assertTrue(all(not w["spawn_allowed"] for w in result["workers"]))

    def test_duplicate_unknown_worker_and_schema_rejected(self):
        with self.assertRaises(ValueError):
            orbit_team_builder.preview(self.conn, self.root, self.project,
                self.args(tasks=[
                    {"task_key": "api", "expected_revision": 1},
                    {"task_key": "api", "expected_revision": 1},
                ]))
        with self.assertRaises(ValueError):
            orbit_mcp.execute(self.conn, "orbit_team_preview",
                self.args(tasks=[{"task_key": "api",
                                  "expected_revision": 1, "kind": "superuser"}]))
        with self.assertRaises(ValueError):
            orbit_mcp.execute(self.conn, "orbit_team_preview",
                self.args(bypass_permissions=True))


if __name__ == "__main__":
    unittest.main()
