"""Real independent-process SQLite Swarm reservation and path-alias regressions.

Child Python interpreters share only a disposable SQLite file and workspace
root. This validates OS-process contention on the CI runner; it does NOT
attest genuine IDE subagent execution, host consent or multi-PC recovery.
"""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

RUNTIME = Path(__file__).resolve().parents[1] / "source" / "runtime"
sys.path.insert(0, str(RUNTIME))
import orbit_tasks


# A new interpreter imports the actual Orbit reservation implementation.
# The explicit stdin barrier prevents one worker from reserving before the
# other processes are ready to contend for the same SQLite transaction.
WORKER = r'''
import json
from pathlib import Path
import sqlite3
import sys
sys.path.insert(0, sys.argv[1])
import orbit_tasks

db_file, root, project, task_key = sys.argv[2:]
print("READY", flush=True)
if sys.stdin.readline().strip() != "GO":
    raise SystemExit("Missing parent start signal")
conn = sqlite3.connect(db_file, timeout=20)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA busy_timeout=20000")
try:
    try:
        result = orbit_tasks.reserve(conn, {
            "project": project,
            "task_key": task_key,
            "expected_revision": 1,
            "approval_reference": "disposable-test-host-approval",
            "confirm_write": True,
        }, Path(root))
        print(json.dumps({"status": result["status"]}), flush=True)
    except ValueError as exc:
        print(json.dumps({"status": "DENIED", "error": str(exc)}), flush=True)
finally:
    conn.close()
'''


class SwarmProcessIsolationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = (Path(temp.name) / "workspace").resolve()
        self.root.mkdir()
        self.db_file = Path(temp.name) / "swarm.sqlite3"
        self.db = sqlite3.connect(str(self.db_file), timeout=20)
        self.db.row_factory = sqlite3.Row
        self.addCleanup(self.db.close)
        orbit_tasks.setup(self.db)

    def task(self, task_key, path, project="swarm-process"):
        result = orbit_tasks.plan(self.db, {
            "project": project,
            "task_key": task_key,
            "step": "Implement",
            "role": "backend",
            "goal": "Implement the approved source change with regression evidence",
            "reason": "Run disposable cross-process Swarm contention regressions",
            "write_paths": [path],
            "depends_on": [],
            "confirm_write": True,
        }, self.root)
        self.assertEqual(result["status"], "PLANNED")

    def run_workers(self, *jobs):
        processes = []
        try:
            for project, task_key in jobs:
                p = subprocess.Popen(
                    [sys.executable, "-c", WORKER, str(RUNTIME),
                     str(self.db_file), str(self.root), project, task_key],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE, text=True,
                )
                processes.append(p)
            for p in processes:
                self.assertEqual(p.stdout.readline().strip(), "READY",
                                 "Worker failed to initialize")
            for p in processes:
                p.stdin.write("GO\n")
                p.stdin.flush()
                p.stdin.close()
                p.stdin = None
            results = []
            for p in processes:
                stdout, stderr = p.communicate(timeout=40)
                self.assertEqual(p.returncode, 0, stderr)
                lines = stdout.splitlines()
                self.assertEqual(len(lines), 1, stdout + stderr)
                results.append(json.loads(lines[0]))
            return results
        finally:
            for p in processes:
                if p.poll() is None:
                    p.kill()
                p.wait(timeout=5)
                for stream in (p.stdin, p.stdout, p.stderr):
                    if stream is not None:
                        stream.close()

    def counts(self):
        active = self.db.execute(
            "SELECT COUNT(*) FROM orbit_agent_tasks "
            "WHERE status='RESERVED' AND project_root=?", (str(self.root),)
        ).fetchone()[0]
        attempts = self.db.execute(
            "SELECT COUNT(*) FROM orbit_task_attempts"
        ).fetchone()[0]
        return active, attempts

    def test_independent_processes_reject_unicode_and_case_alias(self):
        self.task("alpha", "src/Caf\u00e9.py")
        self.task("beta", "SRC/Cafe\u0301.py")
        results = self.run_workers(
            ("swarm-process", "alpha"), ("swarm-process", "beta"))
        self.assertEqual([r["status"] for r in results].count("RESERVED"), 1)
        self.assertEqual([r["status"] for r in results].count("DENIED"), 1)
        self.assertEqual(self.counts(), (1, 1))

    def test_independent_processes_allow_two_disjoint_but_not_three(self):
        for name in ("alpha", "beta", "gamma"):
            self.task(name, "src/" + name + "/")
        results = self.run_workers(*[
            ("swarm-process", key) for key in ("alpha", "beta", "gamma")
        ])
        self.assertEqual([r["status"] for r in results].count("RESERVED"), 2)
        self.assertEqual([r["status"] for r in results].count("DENIED"), 1)
        self.assertTrue(any("cap of 2" in r.get("error", "") for r in results))
        self.assertEqual(self.counts(), (2, 2))

    def test_independent_processes_guard_stale_same_task_revision(self):
        self.task("shared", "src/shared.py")
        results = self.run_workers(
            ("swarm-process", "shared"), ("swarm-process", "shared"))
        self.assertCountEqual(
            [r["status"] for r in results], ["RESERVED", "STALE_REVISION"])
        self.assertEqual(self.counts(), (1, 1))

    def test_other_project_error_never_discloses_identity_or_private_scope(self):
        self.task("secret-payroll-task", "private/payroll-file.py",
                  project="secret-workspace")
        first = self.run_workers(("secret-workspace", "secret-payroll-task"))
        self.assertEqual(first[0]["status"], "RESERVED")
        self.task("public", "private/payroll-file.py", project="public-workspace")
        second = self.run_workers(("public-workspace", "public"))
        self.assertEqual(second[0]["status"], "DENIED")
        message = second[0]["error"]
        for secret in ("secret-payroll-task", "secret-workspace",
                       "private/payroll-file.py"):
            self.assertNotIn(secret, message)
        self.assertEqual(self.counts(), (1, 1))

    def test_windows_ambiguous_trailing_components_are_rejected_at_plan(self):
        for path in ("src/module.py.", "src/ui /component.py",
                     "src/ui./component.py", "src/module.py "):
            with self.subTest(path=path), self.assertRaisesRegex(
                ValueError, "Trailing dots or spaces"
            ):
                self.task("bad-alias", path)
        self.assertEqual(self.counts(), (0, 0))


if __name__ == "__main__":
    unittest.main()
