"""Shared-SQLite reservation concurrency and cross-project privacy regression.

These are separate SQLite connections in one process, not independent real
coding-agent sessions and not cross-process/host acceptance.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source" / "runtime"))
import orbit_tasks


class SwarmReservationIsolationTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = (Path(tmp.name) / "workspace").resolve()
        self.root.mkdir()
        self.db_path = Path(tmp.name) / "isolated.sqlite3"
        self.conn = self.connect()
        self.addCleanup(self.conn.close)
        orbit_tasks.setup(self.conn)

    def connect(self):
        conn = sqlite3.connect(str(self.db_path), timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=15000")
        return conn

    def task(self, key, path, project="swarm-fixture"):
        result = orbit_tasks.plan(self.conn, {
            "project": project,
            "task_key": key,
            "step": "Implement",
            "role": "backend",
            "goal": "Implement a scoped feature and prepare independently reviewed output",
            "reason": "Required for the approved project milestone and QA workflow",
            "write_paths": [path],
            "depends_on": [],
            "confirm_write": True,
        }, self.root)
        self.assertEqual(result["status"], "PLANNED")
        return result["task"]["revision"]

    def reserve(self, conn, key, revision, project="swarm-fixture"):
        return orbit_tasks.reserve(conn, {
            "project": project,
            "task_key": key,
            "expected_revision": revision,
            "approval_reference": "approved-by-real-host-fixture",
            "confirm_write": True,
        }, self.root)

    def race(self, keys):
        barrier = Barrier(len(keys))
        def attempt(key):
            conn = self.connect()
            try:
                barrier.wait(timeout=15)
                try:
                    return (key, self.reserve(conn, key, 1)["status"])
                except ValueError as exc:
                    return (key, "DENIED: " + str(exc))
            finally:
                conn.close()
        with ThreadPoolExecutor(max_workers=len(keys)) as pool:
            return dict(pool.map(attempt, keys))

    def counts(self):
        active = self.conn.execute(
            "SELECT COUNT(*) FROM orbit_agent_tasks "
            "WHERE project_root=? AND status IN ('RESERVED','RUNNING')",
            (str(self.root),)).fetchone()[0]
        attempts = self.conn.execute(
            "SELECT COUNT(*) FROM orbit_task_attempts").fetchone()[0]
        return active, attempts

    def test_collision_race_allows_only_one_reservation(self):
        self.task("alpha", "src/shared.py")
        self.task("beta", "src/shared.py")
        results = list(self.race(["alpha", "beta"]).values())
        self.assertEqual(results.count("RESERVED"), 1)
        self.assertEqual(sum(value.startswith("DENIED: ") for value in results), 1)
        self.assertEqual(self.counts(), (1, 1))

    def test_disjoint_race_allows_two_then_enforces_cap(self):
        self.task("alpha", "src/alpha/")
        self.task("beta", "src/beta/")
        self.task("gamma", "src/gamma/")
        results = self.race(["alpha", "beta"])
        self.assertEqual(list(results.values()).count("RESERVED"), 2)
        self.assertEqual(self.counts(), (2, 2))
        with self.assertRaisesRegex(ValueError, "cap of 2"):
            self.reserve(self.conn, "gamma", 1)
        self.assertEqual(self.counts(), (2, 2))

    def test_same_key_concurrent_reservation_has_one_stale_revision(self):
        self.task("single", "src/single.py")
        barrier = Barrier(2)
        def attempt(_):
            conn = self.connect()
            try:
                barrier.wait(timeout=15)
                return self.reserve(conn, "single", 1)["status"]
            finally:
                conn.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, range(2)))
        self.assertCountEqual(results, ["RESERVED", "STALE_REVISION"])
        self.assertEqual(self.counts(), (1, 1))

    def test_other_project_conflict_redacts_task_and_path(self):
        private_key = "secret-client-identity"
        private_path = "private/customer-secret.py"
        self.task(private_key, private_path, project="private-project")
        self.reserve(self.conn, private_key, 1, project="private-project")
        self.task("public-task", private_path, project="public-project")
        before = self.counts()
        with self.assertRaises(ValueError) as failure:
            self.reserve(self.conn, "public-task", 1, project="public-project")
        message = str(failure.exception)
        self.assertIn("active reservation", message)
        self.assertNotIn(private_key, message)
        self.assertNotIn(private_path, message)
        self.assertNotIn("private-project", message)
        self.assertEqual(self.counts(), before)
        status = self.conn.execute(
            "SELECT status FROM orbit_agent_tasks WHERE project='public-project'"
        ).fetchone()[0]
        self.assertEqual(status, "PLANNED")


if __name__ == "__main__":
    unittest.main()
