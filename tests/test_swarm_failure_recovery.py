"""Failure propagation and truthful serial fallback for the v0.27 Swarm preview.

Tests only read disposable project-scoped records; no agents are launched.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source" / "runtime"))
import orbit_swarm
import orbit_tasks


class SwarmRecoveryReadinessTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = (Path(tmp.name) / "project").resolve()
        self.root.mkdir()
        self.outside = (Path(tmp.name) / "other").resolve()
        self.outside.mkdir()
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.addCleanup(self.db.close)
        orbit_tasks.setup(self.db)

    def task(self, key, *, deps=(), status="PLANNED", paths=(), project="fixture"):
        self.db.execute(
            """INSERT INTO orbit_agent_tasks
               (project,project_root,task_key,step,role,goal,reason,
                write_paths,depends_on,status,revision,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (project, str(self.root), key, "Implement", "backend",
             "Implement an approved task with independently inspected QA",
             "Exercise safe dependency recovery across native hosts",
             json.dumps(list(paths)), json.dumps(list(deps)), status, 1,
             "2026-10-30", "2026-10-30"))
        self.db.commit()

    def preview(self, **overrides):
        return orbit_swarm.preview(self.db, self.root, "fixture", {
            "host": "antigravity",
            "available_host_tools": ["invoke_subagent"],
            **overrides,
        })

    def link(self, target, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(target, path, target_is_directory=True)
        except (NotImplementedError, OSError) as err:
            self.skipTest("OS symlink unavailable: " + type(err).__name__)

    def test_failed_ancestor_blocks_dependent_chain_but_not_independent_work(self):
        self.task("base", status="FAILED")
        self.task("middle", deps=["base"])
        self.task("final", deps=["middle"])
        self.task("independent", paths=["frontend/"])
        before = self.db.total_changes
        outcome = self.preview()
        self.assertEqual([task["task_key"] for task in outcome["ready_now"]], ["independent"])
        deferred = {entry["task_key"]: entry for entry in outcome["deferred"]}
        self.assertEqual(deferred["middle"]["reason"], "UPSTREAM_REWORK_REQUIRED")
        self.assertEqual(deferred["middle"]["blocking_task_keys"], ["base"])
        self.assertEqual(deferred["final"]["blocking_task_keys"], ["base"])
        self.assertEqual(deferred["base"]["reason"], "REVIEW_TASK_STATE")
        self.assertEqual(self.db.total_changes, before)

    def test_rework_cancel_and_denial_propagate_and_then_recover_by_review(self):
        for state in ("REWORK", "CANCELLED", "BLOCKED"):
            with self.subTest(state=state):
                self.db.execute("DELETE FROM orbit_agent_tasks")
                self.db.commit()
                self.task("upstream", status=state)
                self.task("child", deps=["upstream"], paths=["child/"])
                result = self.preview()
                entry = next(x for x in result["deferred"] if x["task_key"] == "child")
                self.assertEqual(entry["reason"], "UPSTREAM_REWORK_REQUIRED")
                self.assertEqual(entry["blocking_task_keys"], ["upstream"])
                self.db.execute(
                    "UPDATE orbit_agent_tasks SET status='REVIEW_ACCEPTED' WHERE task_key='upstream'")
                self.db.commit()
                self.assertEqual([x["task_key"] for x in self.preview()["ready_now"]], ["child"])

    def test_unreviewed_report_is_not_promoted_to_failure_or_accepted(self):
        self.task("upstream", status="REPORTED_DONE")
        self.task("child", deps=["upstream"])
        result = self.preview()
        entry = next(x for x in result["deferred"] if x["task_key"] == "child")
        self.assertEqual(entry["reason"], "DEPENDENCY_REVIEW_REQUIRED")
        self.assertEqual(entry["unaccepted_dependencies"], ["upstream"])

    def test_no_native_host_tool_only_proposes_single_manual_fallback(self):
        self.task("a", paths=["src/a/"])
        self.task("b", paths=["src/b/"])
        before = self.db.total_changes
        result = self.preview(host="codex", available_host_tools=[])
        self.assertEqual(result["status"], "HOLD_NATIVE_TOOL_UNAVAILABLE")
        self.assertEqual(len(result["ready_now"]), 2)
        serial = result["serial_fallback"]
        self.assertEqual(serial["mode"], "MANUAL_SERIAL_REVIEW_ONLY")
        self.assertEqual(serial["task_key"], "a")
        self.assertFalse(serial["native_agent_invoked"])
        self.assertFalse(serial["host_permission_verified"])
        self.assertEqual(self.db.total_changes, before)
        actual = self.preview(host="codex", available_host_tools=["spawn_agent"])
        self.assertIsNone(actual["serial_fallback"])

    def test_resolved_symlink_aliases_are_serialized(self):
        real = self.root / "src" / "real"
        real.mkdir(parents=True)
        self.link(real, self.root / "src" / "link")
        self.task("a", paths=["src/real/"])
        self.task("b", paths=["src/link/"])
        result = self.preview()
        self.assertEqual([x["task_key"] for x in result["ready_now"]], ["a"])
        self.assertEqual(result["deferred"][0]["reason"], "OVERLAPPING_WRITE_SCOPE")

    def test_symlink_escape_holds_read_only_and_does_not_disclose_target(self):
        self.link(self.outside, self.root / "src" / "external")
        self.task("danger", paths=["src/external/private.py"])
        before = self.db.total_changes
        result = self.preview()
        self.assertEqual(result["status"], "HOLD_INVALID_TASK_RECORD")
        self.assertEqual(result["ready_now"], [])
        self.assertNotIn(str(self.outside), json.dumps(result))
        self.assertEqual(before, self.db.total_changes)


if __name__ == "__main__":
    unittest.main()
