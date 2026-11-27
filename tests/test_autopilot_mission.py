"""Synthetic acceptance tests for the bounded multi-task mission supervisor."""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source" / "runtime"))
sys.path.insert(0, str(ROOT / "scripts"))

import orbit_autopilot
import orbit_autopilot_mission as mission
import orbit_autopilot_runner as runner
import orbit_tasks


class Exited:
    pid = 987650
    returncode = 0
    def poll(self):
        return 0


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args],
                            stdin=subprocess.DEVNULL, capture_output=True)
    if result.returncode:
        raise AssertionError(result.stderr.decode(errors="replace")[-300:])
    return result.stdout


class MissionSupervisorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name, "repo").resolve()
        self.root.mkdir()
        git(self.root, "init", "-b", "feat/mission-test")
        git(self.root, "config", "user.email", "orbit-test@example.invalid")
        git(self.root, "config", "user.name", "Orbit Test")
        (self.root / "README.md").write_text("# Fixture\n")
        git(self.root, "add", "README.md")
        git(self.root, "commit", "-m", "fixture baseline")

        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.addCleanup(self.db.close)
        orbit_tasks.setup(self.db)
        orbit_autopilot.setup(self.db)
        runner.setup(self.db)
        mission.setup(self.db)
        self.project = "mission-fixture"
        self.mission = "three-task-delivery"
        self.codex = Path(self.tmp.name, "codex.exe")
        self.codex.write_text("fixture")

        tasks = [
            ("api", "Add the API implementation", ["src/api/"], []),
            ("docs", "Document the approved API", ["docs/"], ["api"]),
            ("smoke", "Add the API smoke test", ["tests/"], ["docs"]),
        ]
        for key, goal, paths, deps in tasks:
            result = orbit_tasks.plan(self.db, {
                "project": self.project, "task_key": key, "step": "IMPLEMENT",
                "role": "backend" if key == "api" else "writer",
                "goal": goal, "reason": "Bounded mission integration fixture",
                "write_paths": paths, "depends_on": deps, "confirm_write": True,
            }, self.root)
            self.assertEqual(result["status"], "PLANNED")

        self.charter_fields = {
            "mission_id": self.mission,
            "objective": "Complete a three-task synthetic delivery",
            "roadmap_ref": "docs/ROADMAP.md",
            "roadmap_revision": "fixture-r1",
            "branch": "feat/mission-test",
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=2)).strftime(
                "%Y-%m-%dT%H:%M:%SZ"),
            "task_keys": ["api", "docs", "smoke"],
            "allowed_paths": ["src/api/", "docs/", "tests/"],
            "allowed_decisions": ["implementation_detail"],
            "max_attempts_per_task": 1,
        }
        preview = orbit_autopilot.charter(
            self.db, self.root, self.project,
            {**self.charter_fields, "action": "preview"})
        approved = orbit_autopilot.charter(
            self.db, self.root, self.project,
            {**self.charter_fields, "action": "activate",
             "expected_digest": preview["charter_digest"],
             "approval_reference": "fixture-approval-reference",
             "confirm_write": True})
        self.assertEqual(approved["status"], "CHARTER_RECORDED")

    def launch(self, work, prompt, logs, executable):
        if "Task: api" in prompt:
            target = work / "src" / "api" / "api.py"
            target.parent.mkdir(parents=True)
            target.write_text("def health():\n    return True\n")
        elif "Task: docs" in prompt:
            target = work / "docs" / "api.md"
            target.parent.mkdir(parents=True)
            target.write_text("# API\n\nThe health endpoint is available.\n")
        elif "Task: smoke" in prompt:
            target = work / "tests" / "test_api.py"
            target.parent.mkdir(parents=True)
            target.write_text("def test_health():\n    assert True\n")
        else:
            raise AssertionError("unexpected task prompt")
        (logs / "codex-events.jsonl").write_text(
            json.dumps({"type": "turn.completed"}) + "\n")
        return Exited()

    def reviewer_and_commit(self):
        """Simulate a separate reviewer after inspecting the isolated diff."""
        job = runner._job(self.db, self.root, self.project, self.mission)
        self.assertEqual(job["state"], "REVIEW_REQUIRED")
        task = mission._task(self.db, self.root, self.project, job["task_key"])
        self.assertEqual(task["status"], "REPORTED_DONE")
        reviewed = orbit_tasks.review(self.db, {
            "project": self.project, "task_key": job["task_key"],
            "expected_revision": task["revision"], "verdict": "ACCEPT",
            "review_evidence": "Independent fixture review inspected the isolated diff and verified the expected files.",
            "confirm_write": True,
        }, self.root)
        self.assertEqual(reviewed["status"], "REVIEW_ACCEPTED")

        work = Path(job["workspace"])
        changed = json.loads(job["changed_paths"])
        for name in changed:
            source = work / name
            destination = self.root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
        git(self.root, "add", "--", *changed)
        git(self.root, "commit", "-m", "reviewed " + job["task_key"])

    def test_one_charter_approval_runs_three_tasks_with_review_gates(self):
        accepted = []

        def review_wait(_seconds):
            self.reviewer_and_commit()
            accepted.append(True)

        result = mission.run_mission(
            self.db, self.root, self.project, self.mission, 1,
            operator_confirmed=True, codex_path=str(self.codex),
            max_seconds=60, review_wait_seconds=5, poll_seconds=0.05,
            launch=self.launch, sleep=review_wait)
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(len(accepted), 3)
        self.assertEqual(result["completed_tasks"], 3)
        self.assertIsNone(runner._job(self.db, self.root, self.project, self.mission))
        self.assertEqual(git(self.root, "status", "--porcelain"), b"")
        self.assertTrue((self.root / "src/api/api.py").is_file())
        self.assertTrue((self.root / "docs/api.md").is_file())
        self.assertTrue((self.root / "tests/test_api.py").is_file())
        state = mission.status(self.db, self.root, self.project, self.mission)
        self.assertEqual(state["status"], "COMPLETED")
        self.assertFalse(state["worker_running_verified"])
        self.assertEqual(state["event_integrity_warnings"], 0)

    def test_cold_resume_after_review_wait_timeout_continues_mission(self):
        first = mission.run_mission(
            self.db, self.root, self.project, self.mission, 1,
            operator_confirmed=True, codex_path=str(self.codex),
            max_seconds=2, review_wait_seconds=1, poll_seconds=0.05,
            launch=self.launch, sleep=lambda _seconds: None)
        self.assertEqual(first["status"], "WAITING_REVIEW")
        self.reviewer_and_commit()

        second = mission.run_mission(
            self.db, self.root, self.project, self.mission, 1,
            operator_confirmed=True, codex_path=str(self.codex),
            max_seconds=30, review_wait_seconds=5, poll_seconds=0.05,
            launch=self.launch, sleep=lambda _seconds: self.reviewer_and_commit())
        self.assertEqual(second["status"], "COMPLETED")
        self.assertEqual(second["completed_tasks"], 3)

    def test_cold_pause_resume_revision_is_adopted_only_from_charter_events(self):
        first = mission.run_mission(
            self.db, self.root, self.project, self.mission, 1,
            operator_confirmed=True, codex_path=str(self.codex),
            max_seconds=2, review_wait_seconds=1, poll_seconds=0.05,
            launch=self.launch, sleep=lambda _seconds: None)
        self.assertEqual(first["status"], "WAITING_REVIEW")

        paused = orbit_autopilot.charter(self.db, self.root, self.project, {
            "mission_id": self.mission, "action": "pause",
            "expected_revision": 1, "confirm_write": True})
        self.assertEqual(paused["status"], "PAUSED")
        resume_args = {
            "mission_id": self.mission, "action": "resume",
            "expected_revision": 2, "reported_branch": "feat/mission-test",
            "approval_reference": "fresh-cold-resume-reference",
        }
        preview = orbit_autopilot.charter(
            self.db, self.root, self.project, resume_args)
        self.assertEqual(preview["status"], "PREVIEW_ONLY")
        resumed = orbit_autopilot.charter(self.db, self.root, self.project, {
            **resume_args, "expected_resume_digest": preview["resume_review_digest"],
            "confirm_write": True})
        self.assertEqual(resumed["status"], "ACTIVE")
        self.assertEqual(resumed["revision"], 3)

        self.reviewer_and_commit()
        second = mission.run_mission(
            self.db, self.root, self.project, self.mission, 3,
            operator_confirmed=True, codex_path=str(self.codex),
            max_seconds=30, review_wait_seconds=5, poll_seconds=0.05,
            launch=self.launch, sleep=lambda _seconds: self.reviewer_and_commit())
        self.assertEqual(second["status"], "COMPLETED")

    def test_tampered_runner_path_record_is_not_reported(self):
        result = runner.run_once(
            self.db, self.root, self.project, self.mission, 1,
            operator_confirmed=True, codex_path=str(self.codex),
            launch=self.launch)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.db.execute("""UPDATE orbit_autopilot_runner_jobs
            SET changed_paths=? WHERE project=? AND project_root=? AND mission_id=?""",
            (json.dumps(["docs/forged.py"]), self.project,
             str(self.root), self.mission))
        self.db.commit()
        job = runner._job(self.db, self.root, self.project, self.mission)
        report = mission._record_local_report(
            self.db, self.root, self.project, job)
        self.assertEqual(report["status"], "HOLD_LOCAL_RUN_WORKSPACE_REVIEW")
        self.assertEqual(mission._task(
            self.db, self.root, self.project, "api")["status"], "PLANNED")

    def test_cli_mission_refuses_headless_approval(self):
        with tempfile.TemporaryDirectory() as folder:
            db_path = Path(folder, "orbit.sqlite3")
            disk = sqlite3.connect(db_path)
            self.db.backup(disk)
            disk.close()
            env = os.environ.copy()
            env["ORBIT_LOCAL_DB"] = str(db_path)
            script = ROOT / "scripts" / "orbit_autopilot_local.py"
            result = subprocess.run([
                sys.executable, str(script), "mission",
                "--project-root", str(self.root), "--project", self.project,
                "--mission-id", self.mission, "--revision", "1",
            ], input=b"", capture_output=True, env=env, timeout=15)
            self.assertEqual(result.returncode, 2)
            self.assertIn(b"interactive local terminal", result.stderr)
            check = sqlite3.connect(db_path)
            self.assertEqual(check.execute(
                "SELECT COUNT(*) FROM orbit_autopilot_mission_runs").fetchone()[0], 0)
            self.assertEqual(check.execute(
                "SELECT COUNT(*) FROM orbit_autopilot_runner_jobs").fetchone()[0], 0)
            check.close()

    def test_rework_stops_mission_without_automatic_retry(self):
        first = mission.run_mission(
            self.db, self.root, self.project, self.mission, 1,
            operator_confirmed=True, codex_path=str(self.codex),
            max_seconds=2, review_wait_seconds=1, poll_seconds=0.05,
            launch=self.launch, sleep=lambda _seconds: None)
        self.assertEqual(first["status"], "WAITING_REVIEW")
        job = runner._job(self.db, self.root, self.project, self.mission)
        task = mission._task(self.db, self.root, self.project, job["task_key"])
        reviewed = orbit_tasks.review(self.db, {
            "project": self.project, "task_key": job["task_key"],
            "expected_revision": task["revision"], "verdict": "REWORK",
            "review_evidence": "Independent reviewer found a specific issue requiring a new task plan.",
            "confirm_write": True,
        }, self.root)
        self.assertEqual(reviewed["status"], "REWORK")
        second = mission.run_mission(
            self.db, self.root, self.project, self.mission, 1,
            operator_confirmed=True, codex_path=str(self.codex),
            max_seconds=5, review_wait_seconds=2, poll_seconds=0.05,
            launch=lambda *args: self.fail("rework must not auto-retry"))
        self.assertEqual(second["status"], "BLOCKED")
        self.assertEqual(second["task_status"], "REWORK")
        self.assertEqual(runner._job(self.db, self.root, self.project, self.mission)["state"],
                         "REVIEW_REQUIRED")

    def test_second_supervisor_is_held_by_exclusive_process_lock(self):
        with mission._mission_lock(self.root, self.project, self.mission) as acquired:
            self.assertTrue(acquired)
            result = mission.run_mission(
                self.db, self.root, self.project, self.mission, 1,
                operator_confirmed=True,
                launch=lambda *args: self.fail("concurrent worker must not launch"))
        self.assertEqual(result["status"], "HOLD_SUPERVISOR_ALREADY_RUNNING")
        self.assertIsNone(mission._run(self.db, self.root, self.project, self.mission))

    def test_event_metadata_tampering_is_detected(self):
        result = mission.run_mission(
            self.db, self.root, self.project, self.mission, 1,
            operator_confirmed=True, codex_path=str(self.codex),
            max_seconds=2, review_wait_seconds=1, poll_seconds=0.05,
            launch=self.launch, sleep=lambda _seconds: None)
        self.assertEqual(result["status"], "WAITING_REVIEW")
        event = dict(self.db.execute("""SELECT * FROM orbit_autopilot_mission_events
            ORDER BY event_id LIMIT 1""").fetchone())
        self.db.execute("""INSERT INTO orbit_autopilot_mission_events
            (run_id,project,project_root,mission_id,event_type,task_key,state,
             recorded_at,payload_json,payload_sha256,event_sha256)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (event["run_id"], event["project"], event["project_root"],
             event["mission_id"], "FORGED_EVENT", event["task_key"],
             event["state"], event["recorded_at"], event["payload_json"],
             event["payload_sha256"], event["event_sha256"]))
        self.db.commit()
        report = mission.status(self.db, self.root, self.project, self.mission)
        self.assertEqual(report["event_integrity_warnings"], 1)
        self.assertEqual(report["timeline"][-1]["event"], "UNTRUSTED_EVENT")

    def test_no_mission_approval_never_launches(self):
        result = mission.run_mission(
            self.db, self.root, self.project, self.mission, 1,
            launch=lambda *args: self.fail("worker must not launch"))
        self.assertEqual(result["status"], "HOLD_LOCAL_OPERATOR_CONFIRMATION_REQUIRED")
        self.assertIsNone(mission._run(self.db, self.root, self.project, self.mission))

    def test_worker_output_is_not_auto_accepted(self):
        result = mission.run_mission(
            self.db, self.root, self.project, self.mission, 1,
            operator_confirmed=True, codex_path=str(self.codex),
            max_seconds=2, review_wait_seconds=1, poll_seconds=0.05,
            launch=self.launch, sleep=lambda _seconds: None)
        self.assertEqual(result["status"], "WAITING_REVIEW")
        task = mission._task(self.db, self.root, self.project, "api")
        self.assertEqual(task["status"], "REPORTED_DONE")
        self.assertEqual(mission._task(self.db, self.root, self.project, "docs")["status"],
                         "PLANNED")
        self.assertEqual(runner._job(self.db, self.root, self.project, self.mission)["state"],
                         "REVIEW_REQUIRED")

    def test_event_ledger_is_append_only(self):
        mission.run_mission(
            self.db, self.root, self.project, self.mission, 1,
            operator_confirmed=True, codex_path=str(self.codex),
            max_seconds=2, review_wait_seconds=1, poll_seconds=0.05,
            launch=self.launch, sleep=lambda _seconds: None)
        with self.assertRaises(sqlite3.DatabaseError):
            self.db.execute("UPDATE orbit_autopilot_mission_events SET state='FORGED'")
        with self.assertRaises(sqlite3.DatabaseError):
            self.db.execute("DELETE FROM orbit_autopilot_mission_events")
        self.db.rollback()


if __name__ == "__main__":
    unittest.main()
