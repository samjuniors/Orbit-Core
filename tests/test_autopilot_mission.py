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

    def reviewer_and_commit(self, mission_id=None, *, root=None, project=None):
        """Simulate a separate reviewer after inspecting the isolated diff."""
        mission_id = mission_id or self.mission
        root = root or self.root
        project = project or self.project
        job = runner._job(self.db, root, project, mission_id)
        self.assertEqual(job["state"], "REVIEW_REQUIRED")
        task = mission._task(self.db, root, project, job["task_key"])
        self.assertEqual(task["status"], "REPORTED_DONE")
        reviewed = orbit_tasks.review(self.db, {
            "project": project, "task_key": job["task_key"],
            "expected_revision": task["revision"], "verdict": "ACCEPT",
            "review_evidence": "Independent fixture review inspected the isolated diff and verified the expected files.",
            "confirm_write": True,
        }, root)
        self.assertEqual(reviewed["status"], "REVIEW_ACCEPTED")

        work = Path(job["workspace"])
        changed = json.loads(job["changed_paths"])
        for name in changed:
            source = work / name
            destination = root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
        git(root, "add", "--", *changed)
        git(root, "commit", "-m", "reviewed " + job["task_key"])

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
        finished = [item for item in state["timeline"]
                    if item["event"] == "TASK_RUN_FINISHED"]
        self.assertEqual(len(finished), 3)
        self.assertTrue(all(item["payload"]["execution_adapter"] ==
                            "codex-cli-isolated-clone" for item in finished))
        self.assertTrue(all(item["payload"]["provider_id"] == "codex"
                            and item["payload"]["host_native"] is False
                            and item["payload"]["model_selection_verified"] is False
                            and item["payload"]["provider_usage_verified"] is False
                            for item in finished))

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

    def test_rework_stops_when_charter_attempt_limit_is_one(self):
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
            "review_evidence": "Reviewer-recorded feedback requires a new task plan.",
            "confirm_write": True,
        }, self.root)
        self.assertEqual(reviewed["status"], "REWORK")
        second = mission.run_mission(
            self.db, self.root, self.project, self.mission, 1,
            operator_confirmed=True, codex_path=str(self.codex),
            max_seconds=5, review_wait_seconds=2, poll_seconds=0.05,
            launch=lambda *args: self.fail("attempt limit must prevent another launch"))
        self.assertEqual(second["status"], "BLOCKED")
        self.assertEqual(second["block_reason"], "REWORK")
        self.assertEqual(second["completed_tasks"], 0)
        self.assertEqual(second["tasks"], [
            {"task_key": "api", "status": "REWORK", "depends_on": []},
            {"task_key": "docs", "status": "PLANNED", "depends_on": ["api"]},
            {"task_key": "smoke", "status": "PLANNED", "depends_on": ["docs"]},
        ])
        self.assertIsNone(runner._job(self.db, self.root, self.project, self.mission))
        history = self.db.execute(
            "SELECT review_verdict FROM orbit_autopilot_runner_history "
            "WHERE project=? AND project_root=? AND mission_id=?",
            (self.project, str(self.root), self.mission)).fetchall()
        self.assertEqual([row[0] for row in history], ["REWORK"])
        self.assertEqual(mission._task(
            self.db, self.root, self.project, "api")["status"], "REWORK")

    def test_attempt_exhaustion_continues_independent_dag_tasks_only(self):
        replan_mission = "dag-replan"
        replan_project = "dag-replan-fixture"
        replan_root = Path(self.tmp.name, "dag-replan-repo").resolve()
        replan_root.mkdir()
        git(replan_root, "init", "-b", "feat/mission-test")
        git(replan_root, "config", "user.email", "orbit-test@example.invalid")
        git(replan_root, "config", "user.name", "Orbit Test")
        (replan_root / "README.md").write_text("# DAG replan fixture\\n")
        git(replan_root, "add", "README.md")
        git(replan_root, "commit", "-m", "DAG replan baseline")
        tasks = [
            ("api", "Add the API implementation", ["src/api/"], []),
            ("docs", "Document the approved API", ["docs/"], []),
            ("smoke", "Add the API smoke test", ["tests/"], ["api"]),
        ]
        for key, goal, paths, deps in tasks:
            planned = orbit_tasks.plan(self.db, {
                "project": replan_project, "task_key": key, "step": "IMPLEMENT",
                "role": "backend" if key == "api" else "writer",
                "goal": goal, "reason": "Bounded DAG replan fixture",
                "write_paths": paths, "depends_on": deps, "confirm_write": True,
            }, replan_root)
            self.assertEqual(planned["status"], "PLANNED")
        fields = dict(self.charter_fields)
        fields.update({
            "mission_id": replan_mission,
            "objective": "Finish independent work while preserving a blocked dependency",
            "task_keys": ["api", "docs", "smoke"],
            "allowed_paths": ["src/api/", "docs/", "tests/"],
            "max_attempts_per_task": 1,
        })
        preview = orbit_autopilot.charter(
            self.db, replan_root, replan_project, {**fields, "action": "preview"})
        activated = orbit_autopilot.charter(
            self.db, replan_root, replan_project,
            {**fields, "action": "activate",
             "expected_digest": preview["charter_digest"],
             "approval_reference": "dag-replan-approval-reference",
             "confirm_write": True})
        self.assertEqual(activated["status"], "CHARTER_RECORDED")
        review_count = 0

        def review_wait(_seconds):
            nonlocal review_count
            job = runner._job(self.db, replan_root, replan_project, replan_mission)
            self.assertIsNotNone(job)
            task = mission._task(
                self.db, replan_root, replan_project, job["task_key"])
            if job["task_key"] == "api":
                result = orbit_tasks.review(self.db, {
                    "project": replan_project, "task_key": "api",
                    "expected_revision": task["revision"], "verdict": "REWORK",
                    "review_evidence": "Correct the API contract before its dependent smoke test can proceed.",
                    "confirm_write": True,
                }, replan_root)
                self.assertEqual(result["status"], "REWORK")
            elif job["task_key"] == "docs":
                self.reviewer_and_commit(
                    replan_mission, root=replan_root, project=replan_project)
            else:
                self.fail("A task depending on the unresolved API must not launch")
            review_count += 1

        result = mission.run_mission(
            self.db, replan_root, replan_project, replan_mission, 1,
            operator_confirmed=True, codex_path=str(self.codex),
            max_seconds=30, review_wait_seconds=5, poll_seconds=0.05,
            launch=self.launch, sleep=review_wait)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["block_reason"], "REWORK")
        self.assertEqual(result["completed_tasks"], 1)
        self.assertEqual(review_count, 2)
        statuses = {item["task_key"]: item["status"] for item in result["tasks"]}
        self.assertEqual(statuses, {
            "api": "REWORK", "docs": "REVIEW_ACCEPTED", "smoke": "PLANNED"})
        smoke = next(item for item in result["tasks"] if item["task_key"] == "smoke")
        self.assertEqual(smoke["depends_on"], ["api"])
        state = mission.status(self.db, replan_root, replan_project, replan_mission)
        events = [item["event"] for item in state["timeline"]]
        self.assertIn("TASK_RETRY_LIMIT_REACHED", events)
        self.assertIn("TASK_REVIEW_ACCEPTED", events)
        self.assertIn("MISSION_BLOCKED_BY_REWORK", events)
        blocked = next(item for item in state["timeline"]
                       if item["event"] == "MISSION_BLOCKED_BY_REWORK")
        self.assertFalse(blocked["payload"]["task_graph_changed"])
        self.assertEqual(blocked["payload"]["rework_tasks"], ["api"])

    def test_rework_retries_once_within_charter_and_preserves_scope(self):
        retry_mission = "bounded-rework"
        retry_project = "retry-fixture"
        retry_root = Path(self.tmp.name, "retry-repo").resolve()
        retry_root.mkdir()
        git(retry_root, "init", "-b", "feat/mission-test")
        git(retry_root, "config", "user.email", "orbit-test@example.invalid")
        git(retry_root, "config", "user.name", "Orbit Test")
        (retry_root / "README.md").write_text("# Retry fixture\\n")
        git(retry_root, "add", "README.md")
        git(retry_root, "commit", "-m", "retry fixture baseline")
        planned = orbit_tasks.plan(self.db, {
            "project": retry_project, "task_key": "api", "step": "IMPLEMENT",
            "role": "backend", "goal": "Add the API implementation",
            "reason": "Bounded reviewer-directed retry fixture",
            "write_paths": ["src/api/"], "depends_on": [],
            "confirm_write": True,
        }, retry_root)
        self.assertEqual(planned["status"], "PLANNED")
        fields = dict(self.charter_fields)
        fields.update({
            "mission_id": retry_mission,
            "objective": "Complete one API task with one bounded reviewer-directed retry",
            "branch": "feat/mission-test",
            "task_keys": ["api"],
            "allowed_paths": ["src/api/"],
            "max_attempts_per_task": 2,
        })
        preview = orbit_autopilot.charter(
            self.db, retry_root, retry_project, {**fields, "action": "preview"})
        activated = orbit_autopilot.charter(
            self.db, retry_root, retry_project,
            {**fields, "action": "activate",
             "expected_digest": preview["charter_digest"],
             "approval_reference": "bounded-rework-approval-reference",
             "confirm_write": True})
        self.assertEqual(activated["status"], "CHARTER_RECORDED")
        before = mission._task(self.db, retry_root, retry_project, "api")
        original_spec = (before["goal"], before["reason"],
                         before["write_paths"], before["depends_on"])
        prompts = []
        review_count = 0

        def launch(work, prompt, logs, executable):
            prompts.append(prompt)
            return self.launch(work, prompt, logs, executable)

        def review_wait(_seconds):
            nonlocal review_count
            job = runner._job(self.db, retry_root, retry_project, retry_mission)
            task = mission._task(self.db, retry_root, retry_project, job["task_key"])
            if review_count == 0:
                result = orbit_tasks.review(self.db, {
                    "project": retry_project, "task_key": job["task_key"],
                    "expected_revision": task["revision"], "verdict": "REWORK",
                    "review_evidence": "Correct the API response contract while staying inside src/api/.",
                    "confirm_write": True,
                }, retry_root)
                self.assertEqual(result["status"], "REWORK")
            else:
                self.reviewer_and_commit(
                    retry_mission, root=retry_root, project=retry_project)
            review_count += 1

        result = mission.run_mission(
            self.db, retry_root, retry_project, retry_mission, 1,
            operator_confirmed=True, codex_path=str(self.codex),
            max_seconds=30, review_wait_seconds=5, poll_seconds=0.05,
            launch=launch, sleep=review_wait)
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(review_count, 2)
        self.assertEqual(len(prompts), 2)
        self.assertIn("Correct the API response contract", prompts[1])
        self.assertIn("does not authorize any change to the approved goal", prompts[1])
        after = mission._task(self.db, retry_root, retry_project, "api")
        self.assertEqual((after["goal"], after["reason"],
                          after["write_paths"], after["depends_on"]), original_spec)
        history = self.db.execute(
            "SELECT review_verdict FROM orbit_autopilot_runner_history "
            "WHERE project=? AND project_root=? AND mission_id=? ORDER BY started_at",
            (retry_project, str(retry_root), retry_mission)).fetchall()
        self.assertEqual([row[0] for row in history], ["REWORK", "ACCEPT"])
        state = mission.status(self.db, retry_root, retry_project, retry_mission)
        requeued = [item for item in state["timeline"]
                    if item["event"] == "TASK_REWORK_REQUEUED"]
        self.assertEqual(len(requeued), 1)
        self.assertTrue(requeued[0]["payload"]["write_scope_unchanged"])
        self.assertTrue(requeued[0]["payload"]["task_spec_unchanged"])

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
