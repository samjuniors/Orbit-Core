"""Writable-scope symlink guards: filesystem aliases never authorize host writes.

All roots are disposable. Symlink creation can require elevated permission on
Windows; those platform cases are skipped explicitly, not counted as verified.
The host still owns real filesystem sandbox enforcement and permission.
"""
from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source" / "runtime"))
import orbit_tasks
import orbit_delegation


class SymlinkWriteScopeTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = (Path(temp.name) / "project").resolve()
        self.root.mkdir()
        self.outside = (Path(temp.name) / "outside").resolve()
        self.outside.mkdir()
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.addCleanup(self.conn.close)
        orbit_tasks.setup(self.conn)

    def link(self, target, name):
        name.parent.mkdir(parents=True, exist_ok=True)
        try:
            os.symlink(str(target), str(name), target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest("OS symlink creation unavailable: " + type(exc).__name__)

    def plan(self, key, path, project="scope-lab", confirm=True):
        return orbit_tasks.plan(self.conn, {
            "project": project,
            "task_key": key,
            "step": "Implement",
            "role": "backend",
            "goal": "Implement approved code with independent source review",
            "reason": "Exercise safely scoped task execution and isolation",
            "write_paths": [path],
            "depends_on": [],
            "confirm_write": confirm,
        }, self.root)

    def reserve(self, key, project="scope-lab"):
        row = self.conn.execute(
            "SELECT revision FROM orbit_agent_tasks "
            "WHERE project=? AND task_key=?", (project, key)).fetchone()
        return orbit_tasks.reserve(self.conn, {
            "project": project, "task_key": key,
            "expected_revision": row["revision"],
            "approval_reference": "disposable-explicit-host-approval",
            "confirm_write": True,
        }, self.root)

    def counts(self):
        return (self.conn.execute(
            "SELECT COUNT(*) FROM orbit_agent_tasks WHERE status='RESERVED'"
        ).fetchone()[0], self.conn.execute(
            "SELECT COUNT(*) FROM orbit_task_attempts"
        ).fetchone()[0])

    def test_plan_rejects_symlink_outside_workspace(self):
        self.link(self.outside, self.root / "src" / "external")
        with self.assertRaisesRegex(ValueError, "Unsafe resolved writable scope"):
            self.plan("external", "src/external/output.py")
        self.assertEqual(self.counts(), (0, 0))
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM orbit_agent_tasks").fetchone()[0], 0)

    def test_symlink_inserted_after_plan_is_rejected_at_reserve_without_attempt(self):
        result = self.plan("late-link", "src/external/output.py")
        self.assertEqual(result["status"], "PLANNED")
        self.link(self.outside, self.root / "src" / "external")
        with self.assertRaisesRegex(ValueError, "Unsafe resolved writable scope"):
            self.reserve("late-link")
        self.assertEqual(self.counts(), (0, 0))
        self.assertEqual(self.conn.execute(
            "SELECT status FROM orbit_agent_tasks").fetchone()[0], "PLANNED")

    def test_within_root_alias_collides_with_existing_reserved_scope(self):
        real = self.root / "src" / "real"
        real.mkdir(parents=True)
        self.link(real, self.root / "src" / "alias")
        self.assertEqual(self.plan("real", "src/real/")["status"], "PLANNED")
        self.assertEqual(self.plan("alias", "src/alias/")["status"], "PLANNED")
        self.assertEqual(self.reserve("real")["status"], "RESERVED")
        with self.assertRaisesRegex(ValueError, "Overlapping writable scopes"):
            self.reserve("alias")
        self.assertEqual(self.counts(), (1, 1))

    def test_alias_to_protected_control_directory_is_refused(self):
        protected = self.root / ".git"
        protected.mkdir()
        self.link(protected, self.root / "workspace")
        with self.assertRaisesRegex(ValueError, "Unsafe resolved writable scope"):
            self.plan("control", "workspace/config")
        self.assertEqual(self.counts(), (0, 0))

    def test_normal_disjoint_paths_still_reserve_independently(self):
        self.plan("api", "src/api/")
        self.plan("ui", "src/ui/")
        self.assertEqual(self.reserve("api")["status"], "RESERVED")
        self.assertEqual(self.reserve("ui")["status"], "RESERVED")
        self.assertEqual(self.counts(), (2, 2))

    def test_handoff_refuses_symlink_changed_after_reservation(self):
        self.assertEqual(self.plan("late-handoff", "src/external/")["status"], "PLANNED")
        self.assertEqual(self.reserve("late-handoff")["status"], "RESERVED")
        self.link(self.outside, self.root / "src" / "external")
        packet = orbit_delegation.handoff(self.conn, {
            "project": "scope-lab", "task_key": "late-handoff",
            "host": "antigravity", "available_host_tools": ["invoke_subagent"],
        }, self.root)
        self.assertEqual(packet["status"], "HOLD_UNSAFE_WRITE_SCOPE")
        self.assertIsNone(packet["handoff"])
        self.assertFalse(packet["native_invoked"])
        self.assertEqual(self.counts(), (1, 1))
        self.assertEqual(self.conn.execute(
            "SELECT status FROM orbit_agent_tasks").fetchone()[0], "RESERVED")

    def test_preview_is_read_only_and_unsafe_alias_is_not_silently_approved(self):
        self.link(self.outside, self.root / "external")
        with self.assertRaisesRegex(ValueError, "Unsafe resolved writable scope"):
            self.plan("preview", "external/file.py", confirm=False)
        self.assertEqual(self.counts(), (0, 0))


if __name__ == "__main__":
    unittest.main()
