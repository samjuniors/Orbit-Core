"""Phase 2 local supervisor synthetic acceptance (no real models or host calls)."""
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
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source" / "runtime"))

import orbit_autopilot
import orbit_autopilot_runner as runner
import orbit_tasks


class FakeExited:
    pid = 987654
    returncode = 0

    def poll(self):
        return 0


class FakeLive:
    pid = 987654
    returncode = None

    def poll(self):
        return None


def git(root, *params):
    result = subprocess.run(["git", "-C", str(root), *params], capture_output=True,
                            stdin=subprocess.DEVNULL, check=False)
    if result.returncode:
        raise AssertionError(result.stderr.decode(errors="replace")[-200:])
    return result.stdout


class AutopilotRunnerTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name, "approved-repository").resolve()
        self.root.mkdir()
        # Synthetic repository owned by this test, never a real project.
        git(self.root, "init", "-b", "feat/test-autopilot")
        git(self.root, "config", "user.email", "orbit-qa@example.invalid")
        git(self.root, "config", "user.name", "Orbit QA")
        (self.root / "README.md").write_text("# Synthetic approved project\n")
        git(self.root, "add", "README.md")
        git(self.root, "commit", "-m", "Synthetic baseline")
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.addCleanup(self.db.close)
        orbit_tasks.setup(self.db)
        orbit_autopilot.setup(self.db)
        runner.setup(self.db)
        self.project = "autopilot-test"
        self.mission = "approved-roadmap"
        self.fake_executable = Path(folder.name, "fake-codex-executable")
        self.fake_executable.write_text("not executed")
        plan = orbit_tasks.plan(self.db, {
            "project": self.project, "task_key": "api", "step": "IMPLEMENT",
            "role": "backend", "goal": "Add a minimal reviewed API source file to this fixture",
            "reason": "Deliver a contained and independently testable change",
            "write_paths": ["src/api/"], "depends_on": [],
            "confirm_write": True,
        }, self.root)
        self.assertEqual(plan["status"], "PLANNED")
        followup = orbit_tasks.plan(self.db, {
            "project": self.project, "task_key": "docs", "step": "IMPLEMENT",
            "role": "writer", "goal": "Document the reviewed API in the fixture after it passes review",
            "reason": "Demonstrate approval-bound sequential milestone progression",
            "write_paths": ["docs/"], "depends_on": ["api"],
            "confirm_write": True,
        }, self.root)
        self.assertEqual(followup["status"], "PLANNED")
        self.fields = {
            "mission_id": self.mission,
            "objective": "Implement one safe approved task in the synthetic roadmap",
            "roadmap_ref": "docs/ROADMAP.md",
            "roadmap_revision": "approved-rev-synthetic",
            "branch": "feat/test-autopilot",
            "expires_at": (datetime.now(timezone.utc)+timedelta(days=2)).
                strftime("%Y-%m-%dT%H:%M:%SZ"),
            "task_keys": ["api", "docs"],
            "allowed_paths": ["src/api/", "docs/"],
            "allowed_decisions": ["implementation_detail"],
            "max_attempts_per_task": 1,
        }
        digest = orbit_autopilot.charter(
            self.db, self.root, self.project,
            {**self.fields, "action": "preview"})["charter_digest"]
        approved = orbit_autopilot.charter(
            self.db, self.root, self.project,
            {**self.fields, "action": "activate", "expected_digest": digest,
             "approval_reference": "test-operator-claim-not-authenticated",
             "confirm_write": True})
        self.assertEqual(approved["status"], "CHARTER_RECORDED")

    def preview(self, rev=1):
        return runner.preview(self.db, self.root, self.project, self.mission, rev)

    def job(self):
        return runner._job(self.db, self.root, self.project, self.mission)

    def invoke(self, launch, **kwargs):
        return runner.run_once(
            self.db, self.root, self.project, self.mission, 1,
            operator_confirmed=True, codex_path=str(self.fake_executable),
            launch=launch, **kwargs)

    @staticmethod
    def launch_success(work, prompt, logs, executable):
        assert "Task: api" in prompt
        assert executable
        target = work / "src" / "api"
        target.mkdir(parents=True)
        (target / "api.py").write_text("def health(): return True\n")
        (logs / "codex-events.jsonl").write_text(
            json.dumps({"type": "thread.started", "thread_id": "fake"})
            + "\n" + json.dumps({"type": "turn.completed"})
            + "\n")
        return FakeExited()

    @staticmethod
    def launch_denied(work, prompt, logs, executable):
        (logs / "codex-events.jsonl").write_text(
            json.dumps({"type": "turn.completed"}) + "\n"
            + json.dumps({"type": "turn.failed", "error": {"message": "denied"}}) + "\n")
        return FakeExited()

    @staticmethod
    def launch_rogue(work, prompt, logs, executable):
        (work / "not-approved.py").write_text("print('should be blocked')\n")
        (logs / "codex-events.jsonl").write_text(json.dumps({"type": "turn.completed"})+"\n")
        return FakeExited()

    def test_preview_exact_branch_clean_and_nonmutating(self):
        before = self.db.total_changes
        p = self.preview()
        self.assertEqual(p["status"], "READY_FOR_LOCAL_OPERATOR_REVIEW")
        self.assertEqual(p["task_key"], "api")
        self.assertEqual(p["source_branch_verified"], "feat/test-autopilot")
        self.assertEqual(p["source_head_verified"], os.fsdecode(git(self.root, "rev-parse", "HEAD")).strip())
        self.assertEqual(p["max_tasks_per_run"], 1)
        self.assertFalse(p["execution_started"])
        self.assertEqual(self.db.total_changes, before)

    def test_no_operator_confirmation_never_claims_or_launches(self):
        result = runner.run_once(
            self.db, self.root, self.project, self.mission, 1,
            codex_path=str(self.fake_executable),
            launch=lambda *args: self.fail("launch must not run"))
        self.assertEqual(result["status"], "HOLD_LOCAL_OPERATOR_CONFIRMATION_REQUIRED")
        self.assertIsNone(self.job())

    def test_missing_codex_binary_holds_without_run(self):
        result = runner.run_once(
            self.db, self.root, self.project, self.mission, 1,
            operator_confirmed=True,
            codex_path=str(self.root / "not-present"))
        self.assertEqual(result["status"], "HOLD_CODEX_CLI_NOT_AVAILABLE")
        self.assertIsNone(self.job())

    def test_one_successful_isolated_task_stops_for_independent_review(self):
        result = self.invoke(self.launch_success)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertEqual(result["changed_paths"], ["src/api/api.py"])
        self.assertFalse(result["task_accepted"])
        self.assertFalse(result["tests_independently_verified"])
        self.assertFalse(result["release_authorized"])
        self.assertEqual(self.job()["state"], "REVIEW_REQUIRED")
        self.assertEqual(git(self.root, "status", "--porcelain"), b"")
        self.assertFalse((self.root / "src/api/api.py").exists())
        self.assertTrue((Path(result["workspace"]) / "src/api/api.py").is_file())
        self.assertEqual(self.preview()["status"], "HOLD_REVIEW_PREVIOUS_RUN")

    def test_caller_claimed_host_denial_cannot_pass_completed_event(self):
        self.assertEqual(self.invoke(self.launch_denied)["status"], "BLOCKED")
        self.assertEqual(self.job()["state"], "BLOCKED")
        self.assertEqual(self.preview()["status"], "HOLD_PREVIOUS_RUN")

    def test_worker_git_commit_cannot_hide_changed_files(self):
        def launch(work, prompt, logs, executable):
            process = self.launch_success(work, prompt, logs, executable)
            git(work, "add", "src/api/api.py")
            git(work, "-c", "user.name=Test", "-c", "user.email=qa@example.invalid",
                "commit", "-m", "worker must not commit")
            return process
        result = self.invoke(launch)
        self.assertEqual(result["status"], "HOLD_ISOLATED_GIT_HEAD_DRIFT")
        self.assertEqual(self.job()["state"], "BLOCKED")
        self.assertFalse((self.root / "src/api/api.py").exists())

    def test_worker_added_git_remote_does_not_pass_review(self):
        def launch(work, prompt, logs, executable):
            process = self.launch_success(work, prompt, logs, executable)
            git(work, "remote", "add", "origin", "https://example.invalid/blocked.git")
            return process
        result = self.invoke(launch)
        self.assertEqual(result["status"], "HOLD_ISOLATED_GIT_REMOTE_ADDED")
        self.assertEqual(self.job()["state"], "BLOCKED")

    def test_in_scope_tracked_deletion_is_not_auto_reviewable(self):
        old = self.root / "src/api/previous.py"
        old.parent.mkdir(parents=True)
        old.write_text("preserve historical source\\n")
        git(self.root, "add", "src/api/previous.py")
        git(self.root, "commit", "-m", "Fixture tracked file for deletion test")
        def launch(work, prompt, logs, executable):
            result = self.launch_success(work, prompt, logs, executable)
            (work / "src/api/previous.py").unlink()
            return result
        result = self.invoke(launch)
        self.assertEqual(result["status"], "HOLD_UNSAFE_CHANGED_FILE", result)
        self.assertEqual(self.job()["state"], "BLOCKED")
        self.assertTrue(old.is_file())

    def test_in_scope_symlink_cannot_alias_another_file(self):
        def launch(work, prompt, logs, executable):
            result = self.launch_success(work, prompt, logs, executable)
            target = work / "src/api/symlink.py"
            try:
                target.symlink_to(work / "README.md")
            except (OSError, NotImplementedError) as exc:
                self.skipTest("Host forbids disposable symlink creation: " + str(exc))
            return result
        result = self.invoke(launch)
        self.assertEqual(result["status"], "HOLD_UNSAFE_CHANGED_FILE")
        self.assertEqual(self.job()["state"], "BLOCKED")

    def test_in_scope_hardlink_cannot_alias_another_file(self):
        def launch(work, prompt, logs, executable):
            result = self.launch_success(work, prompt, logs, executable)
            try:
                os.link(work / "README.md", work / "src/api/linked.py")
            except (OSError, NotImplementedError) as exc:
                self.skipTest("Host forbids disposable hardlink creation: " + str(exc))
            return result
        result = self.invoke(launch)
        self.assertEqual(result["status"], "HOLD_UNSAFE_CHANGED_HARDLINK")
        self.assertEqual(self.job()["state"], "BLOCKED")

    def test_out_of_scope_code_never_autoreviewed_or_applied(self):
        result = self.invoke(self.launch_rogue)
        self.assertEqual(result["status"], "HOLD_OUT_OF_SCOPE_CHANGES")
        self.assertEqual(self.job()["state"], "BLOCKED")
        self.assertEqual(result["changed_paths"], ["not-approved.py"])
        self.assertFalse((self.root / "not-approved.py").exists())

    def test_dirty_source_and_wrong_branch_hold_without_claim(self):
        (self.root / "do-not-touch.txt").write_text("owner data")
        self.assertEqual(self.preview()["status"], "HOLD_UNCLEAN_OR_INVALID_GIT")
        self.assertIsNone(self.job())
        (self.root / "do-not-touch.txt").unlink()
        git(self.root, "checkout", "-b", "feat/different-branch")
        self.assertEqual(self.preview()["status"], "HOLD_BRANCH_MISMATCH")
        self.assertIsNone(self.job())

    def test_paused_charter_and_stale_revision_hold(self):
        self.assertEqual(self.preview(4)["status"], "HOLD_STALE_REVISION")
        paused = orbit_autopilot.charter(self.db, self.root, self.project, {
            "action": "pause", "mission_id": self.mission,
            "expected_revision": 1, "confirm_write": True})
        self.assertEqual(paused["status"], "PAUSED")
        self.assertEqual(self.preview(2)["status"], "HOLD_MISSION_INACTIVE")
        self.assertIsNone(self.job())

    def test_expired_charter_holds(self):
        with patch.object(orbit_autopilot, "utc_now",
                          return_value=datetime.now(timezone.utc)+timedelta(days=5)):
            self.assertEqual(self.preview()["status"], "HOLD_MISSION_INACTIVE")

    def test_stale_active_job_blocks_relaunch_and_requests_reconciliation(self):
        p = self.preview()
        token = runner._claim(self.db, self.root, self.project, self.mission, p)
        self.assertIsNotNone(token)
        self.assertEqual(self.preview()["status"],
                         "HOLD_RECONCILE_POSSIBLE_HOST_PROCESS")
        self.assertEqual(runner.stop(self.db, self.root, self.project, self.mission)["status"],
                         "STOP_REQUESTED")
        self.assertEqual(self.job()["state"], "STOP_REQUESTED")
        self.assertFalse(runner._heartbeat(self.db, self.root,
                                            self.project, self.mission, token))
        self.assertEqual(self.job()["state"], "STOP_REQUESTED")
        self.assertEqual(self.preview()["status"],
                         "HOLD_RECONCILE_POSSIBLE_HOST_PROCESS")

    def test_concurrent_claim_does_not_overwrite_first_run(self):
        p = self.preview()
        first = runner._claim(self.db, self.root, self.project, self.mission, p)
        self.assertTrue(first)
        self.assertIsNone(runner._claim(self.db, self.root, self.project, self.mission, p))
        self.assertEqual(self.job()["run_id"], first)

    def test_stop_of_absent_or_reviewed_job_does_not_kill_pid(self):
        self.assertEqual(runner.stop(self.db, self.root, self.project, self.mission)["status"],
                         "NO_RUN")
        self.invoke(self.launch_success)
        with patch.object(runner, "_terminate_child",
                          side_effect=AssertionError("must not kill arbitrary saved PID")):
            result = runner.stop(self.db, self.root, self.project, self.mission)
        self.assertEqual(result["status"], "NO_RUNNING_ATTACHED_WORKER")

    def test_stop_during_launch_never_clears_request_and_terminates(self):
        def launch(work, prompt, logs, executable):
            r = runner.stop(self.db, self.root, self.project, self.mission)
            self.assertEqual(r["status"], "STOP_REQUESTED")
            return FakeLive()
        with patch.object(runner, "_terminate_child", return_value=True) as kill:
            result = self.invoke(launch)
        self.assertEqual(result["status"], "STOPPED")
        self.assertEqual(self.job()["state"], "STOPPED")
        self.assertTrue(kill.called)

    def test_turn_output_malformed_or_denied_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder, "events.jsonl")
            for body in (
                "not JSON",
                json.dumps({"type": "turn.completed", "denied_actions": [1]}),
                json.dumps({"type": "turn.failed"}),
                json.dumps({"type": "item.failed", "item": {"type": "mcp_tool_call"}}),
                json.dumps({"type": "item.completed", "item": {"type": "command_execution", "exit_code": 1}})
                  + "\n" + json.dumps({"type": "turn.completed"}),
                json.dumps({"type": "item.completed", "item": {"type": "command_execution", "status": "denied"}})
                  + "\n" + json.dumps({"type": "turn.completed"}),
                json.dumps({"type": "thread.started"}),
            ):
                path.write_text(body+"\n")
                self.assertFalse(runner._completed(path), body)
            path.write_text(json.dumps({"type": "turn.completed"}) + "\n")
            self.assertTrue(runner._completed(path))

    def test_approved_timeout_bound(self):
        with self.assertRaises(ValueError):
            self.invoke(self.launch_success, max_seconds=runner.MAX_SECONDS+1)
        self.assertIsNone(self.job())

    def test_real_codex_invocation_flags_never_bypass_host_policy(self):
        with tempfile.TemporaryDirectory() as folder:
            work = Path(folder, "work")
            work.mkdir()
            logdir = Path(folder)
            with patch.object(runner.subprocess, "Popen") as spawn:
                spawn.return_value = FakeExited()
                runner._codex_process(work, "Read-only fixture task", logdir, "codex")
                argv = spawn.call_args.args[0]
            self.assertEqual(argv[:4], ["codex", "--ask-for-approval", "never", "exec"])
            self.assertIn("workspace-write", argv)
            self.assertIn("--ephemeral", argv)
            self.assertIn("--ask-for-approval", argv)
            self.assertEqual(argv[argv.index("--ask-for-approval")+1], "never")
            self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", argv)
            self.assertNotIn("danger-full-access", argv)
            self.assertFalse((logdir / "codex-events.jsonl").read_bytes())
            self.assertTrue((logdir / "codex-stderr.log").is_file())

    def test_runner_status_never_attests_os_liveness(self):
        self.assertEqual(runner._public(None)["status"], "NO_RUN")
        self.invoke(self.launch_success)
        status = runner._public(self.job())
        self.assertFalse(status["worker_running_verified"])
        self.assertTrue(status["worker_pid_recorded"])

    def test_changed_git_commit_between_preview_and_claim_is_rejected(self):
        first = self.preview()
        (self.root / "README.md").write_text("# Changed after operator reviewed\n")
        git(self.root, "add", "README.md")
        git(self.root, "commit", "-m", "Synthetic post-review drift")
        self.assertEqual(self.preview()["status"], "READY_FOR_LOCAL_OPERATOR_REVIEW")
        self.assertIsNone(runner._claim(
            self.db, self.root, self.project, self.mission, first))
        self.assertIsNone(self.job())

    def test_public_cli_refuses_headless_run_without_launching_codex(self):
        with tempfile.TemporaryDirectory() as folder:
            dbpath = Path(folder, "qa.sqlite3")
            external = sqlite3.connect(str(dbpath))
            try:
                self.db.backup(external)
            finally:
                external.close()
            cli = ROOT / "scripts" / "orbit_autopilot_local.py"
            command = [
                sys.executable, str(cli), "run",
                "--project-root", str(self.root),
                "--project", self.project, "--mission-id", self.mission,
                "--revision", "1", "--local-db", str(dbpath),
            ]
            outcome = subprocess.run(
                command, stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=20, check=False)
            self.assertEqual(outcome.returncode, 2,
                             outcome.stderr.decode(errors="replace")[-2000:])
            self.assertIn(b"interactive local terminal", outcome.stderr)
            self.assertEqual(git(self.root, "status", "--porcelain"), b"")

    def test_clone_separate_clean_git_and_existing_files_unchanged(self):
        isolated = runner._clone_local(self.root)
        self.assertNotEqual(isolated, self.root)
        self.assertEqual(runner._source_branch(isolated), "feat/test-autopilot")
        self.assertEqual(git(isolated, "remote"), b"")
        self.assertEqual(git(isolated, "rev-parse", "HEAD"),
                         git(self.root, "rev-parse", "HEAD"))
        self.assertEqual((isolated / "README.md").read_bytes(),
                         (self.root / "README.md").read_bytes())
        self.assertEqual(git(self.root, "status", "--porcelain"), b"")


    def review_fixture_as_accepted(self, result, *, same_content=True):
        # Synthetic external reviewer and source integration, not a model claim.
        target = self.root / "src" / "api"
        target.mkdir(parents=True, exist_ok=True)
        source = Path(result["workspace"]) / "src" / "api" / "api.py"
        value = source.read_bytes() if same_content else b"not the worker's source\n"
        (target / "api.py").write_bytes(value)
        git(self.root, "add", "src/api/api.py")
        git(self.root, "commit", "-m", "Synthetic reviewer source integration")
        self.db.execute(
            """UPDATE orbit_agent_tasks
               SET status='REVIEW_ACCEPTED', revision=revision+1,
                   review_evidence='Synthetic reviewer independently ran fixture QA'
               WHERE project=? AND project_root=? AND task_key='api'""",
            (self.project, str(self.root)))
        self.db.commit()

    def test_review_handoff_enables_next_task_only_after_matching_commit(self):
        result = self.invoke(self.launch_success)
        self.assertEqual(runner.advance_reviewed(
            self.db, self.root, self.project, self.mission, 1)["status"],
            "HOLD_REVIEWED_SOURCE_NOT_COMMITTED")
        self.review_fixture_as_accepted(result)
        before = self.db.total_changes
        ready = runner.advance_reviewed(self.db, self.root, self.project, self.mission, 1)
        self.assertEqual(ready["status"], "REVIEW_HANDOFF_READY")
        self.assertEqual(self.db.total_changes, before)
        recorded = runner.advance_reviewed(
            self.db, self.root, self.project, self.mission, 1, confirm_write=True)
        self.assertEqual(recorded["status"], "REVIEW_HANDOFF_RECORDED")
        self.assertFalse(recorded["next_worker_started"])
        self.assertIsNone(self.job())
        history = self.db.execute(
            "SELECT * FROM orbit_autopilot_runner_history WHERE run_id=?",
            (result.get("run_id", ready["run_id"]),)).fetchone()
        self.assertIsNotNone(history)
        next_plan = self.preview()
        self.assertEqual(next_plan["status"], "READY_FOR_LOCAL_OPERATOR_REVIEW")
        self.assertEqual(next_plan["task_key"], "docs")
        self.assertFalse(next_plan["execution_started"])

    def test_handoff_rejects_unreviewed_or_mismatched_source(self):
        result = self.invoke(self.launch_success)
        self.review_fixture_as_accepted(result, same_content=False)
        response = runner.advance_reviewed(
            self.db, self.root, self.project, self.mission, 1, confirm_write=True)
        self.assertEqual(response["status"], "HOLD_REVIEWED_SOURCE_MISMATCH")
        self.assertEqual(self.job()["state"], "REVIEW_REQUIRED")
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM orbit_autopilot_runner_history").fetchone()[0], 0)

    def test_handoff_requires_ledger_acceptance_not_a_claim(self):
        result = self.invoke(self.launch_success)
        target = self.root / "src" / "api"
        target.mkdir(parents=True)
        (target / "api.py").write_bytes(
            (Path(result["workspace"]) / "src/api/api.py").read_bytes())
        git(self.root, "add", "src/api/api.py")
        git(self.root, "commit", "-m", "Synthetic source integration without review")
        response = runner.advance_reviewed(
            self.db, self.root, self.project, self.mission, 1, confirm_write=True)
        self.assertEqual(response["status"], "HOLD_INDEPENDENT_REVIEW_REQUIRED")
        self.assertIsNotNone(self.job())

    def test_handoff_noninteractive_apply_never_consumes_review(self):
        result = self.invoke(self.launch_success)
        self.review_fixture_as_accepted(result)
        with tempfile.TemporaryDirectory() as folder:
            dbpath = Path(folder, "synthetic-db.sqlite3")
            out = sqlite3.connect(str(dbpath))
            try:
                self.db.backup(out)
            finally:
                out.close()
            cli = ROOT / "scripts" / "orbit_autopilot_local.py"
            response = subprocess.run(
                [sys.executable, str(cli), "review-handoff", "--apply",
                 "--project-root", str(self.root), "--project", self.project,
                 "--mission-id", self.mission, "--revision", "1",
                 "--local-db", str(dbpath)],
                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, timeout=20, check=False)
            self.assertEqual(response.returncode, 2)
            self.assertIn(b"interactive local terminal", response.stderr)
        self.assertIsNotNone(self.job())

    def test_handoff_refuses_stopped_or_failed_previous_run(self):
        self.assertEqual(runner.advance_reviewed(
            self.db, self.root, self.project, self.mission, 1)["status"],
            "HOLD_NO_REVIEWED_RUN")
        self.invoke(self.launch_denied)
        self.assertEqual(runner.advance_reviewed(
            self.db, self.root, self.project, self.mission, 1)["status"],
            "HOLD_NO_REVIEWED_RUN")


if __name__ == "__main__":
    unittest.main()
