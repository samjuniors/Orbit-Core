"""Bounded, durable multi-task mission supervisor for the local Codex adapter.

A single local approval authorizes only the immutable Orbit mission charter.
Each task still stops for independent review and a source-commit handoff before
any dependent task can run. This is a foreground process, not a daemon.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

import orbit_autopilot
import orbit_autopilot_runner as runner
import orbit_tasks

MAX_PROCESS_SECONDS = 3600
MAX_POLL_SECONDS = 2.0
DEFAULT_REVIEW_WAIT_SECONDS = 3600


@dataclass(frozen=True)
class MissionTaskContext:
    """Provider-neutral, immutable task scope passed to an execution adapter."""

    project_root: Path
    project: str
    mission_id: str
    mission_revision: int
    task_key: str
    max_seconds: int
    rework_feedback: str = ""


class MissionExecutionAdapter(Protocol):
    """Contract for one bounded task invocation; adapters cannot accept/review work."""

    adapter_id: str
    provider_id: str
    host_native: bool

    def execute_task(self, conn, context: MissionTaskContext) -> dict:
        """Execute exactly one task and return the existing runner result envelope."""
        ...


class CodexCLIAdapter:
    """Current implementation: existing local Codex runner, not an IDE-native worker."""

    adapter_id = "codex-cli-isolated-clone"
    provider_id = "codex"
    host_native = False

    def __init__(self, *, codex_path=None, launch=runner._codex_process):
        self.codex_path = codex_path
        self.launch = launch

    def execute_task(self, conn, context: MissionTaskContext) -> dict:
        return runner.run_once(
            conn, context.project_root, context.project, context.mission_id,
            context.mission_revision, operator_confirmed=True,
            codex_path=self.codex_path, max_seconds=context.max_seconds,
            launch=self.launch, rework_feedback=context.rework_feedback)


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value):
    return hashlib.sha256(_json(value).encode("utf-8")).hexdigest()


def setup(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS orbit_autopilot_mission_runs (
        project TEXT NOT NULL, project_root TEXT NOT NULL, mission_id TEXT NOT NULL,
        run_id TEXT NOT NULL, charter_digest TEXT NOT NULL, mission_revision INTEGER NOT NULL,
        state TEXT NOT NULL, completed_tasks INTEGER NOT NULL DEFAULT 0,
        last_task_key TEXT NOT NULL DEFAULT '', started_at TEXT NOT NULL,
        heartbeat_at TEXT NOT NULL, updated_at TEXT NOT NULL, result TEXT NOT NULL DEFAULT '',
        PRIMARY KEY(project, project_root, mission_id)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS orbit_autopilot_mission_events (
        event_id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL,
        project TEXT NOT NULL, project_root TEXT NOT NULL, mission_id TEXT NOT NULL,
        event_type TEXT NOT NULL, task_key TEXT NOT NULL DEFAULT '',
        state TEXT NOT NULL, recorded_at TEXT NOT NULL, payload_json TEXT NOT NULL,
        payload_sha256 TEXT NOT NULL, event_sha256 TEXT NOT NULL DEFAULT ''
    )""")
    event_columns = {row[1] for row in conn.execute(
        "PRAGMA table_info(orbit_autopilot_mission_events)")}
    if "event_sha256" not in event_columns:
        conn.execute("""ALTER TABLE orbit_autopilot_mission_events
            ADD COLUMN event_sha256 TEXT NOT NULL DEFAULT ''""")
    conn.execute("""CREATE INDEX IF NOT EXISTS orbit_autopilot_mission_events_lookup
        ON orbit_autopilot_mission_events(project, project_root, mission_id, event_id)""")
    conn.execute("""CREATE TRIGGER IF NOT EXISTS orbit_autopilot_mission_events_no_update
        BEFORE UPDATE ON orbit_autopilot_mission_events
        BEGIN SELECT RAISE(ABORT, 'mission events are append-only'); END""")
    conn.execute("""CREATE TRIGGER IF NOT EXISTS orbit_autopilot_mission_events_no_delete
        BEFORE DELETE ON orbit_autopilot_mission_events
        BEGIN SELECT RAISE(ABORT, 'mission events are append-only'); END""")
    conn.commit()


def _run(conn, root, project, mission):
    row = conn.execute("""SELECT * FROM orbit_autopilot_mission_runs
        WHERE project=? AND project_root=? AND mission_id=?""",
        (project, str(root), mission)).fetchone()
    return dict(row) if row else None


def _event(conn, run, event_type, state, *, task_key="", payload=None):
    body = payload if isinstance(payload, dict) else {}
    raw = _json(body)
    stamp = _now()
    envelope = {
        "run_id": run["run_id"], "project": run["project"],
        "project_root": run["project_root"], "mission_id": run["mission_id"],
        "event_type": event_type, "task_key": task_key, "state": state,
        "recorded_at": stamp, "payload": body,
    }
    with conn:
        conn.execute("""INSERT INTO orbit_autopilot_mission_events
            (run_id,project,project_root,mission_id,event_type,task_key,state,
             recorded_at,payload_json,payload_sha256,event_sha256)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (run["run_id"], run["project"], run["project_root"], run["mission_id"],
             event_type, task_key, state, stamp, raw,
             hashlib.sha256(raw.encode("utf-8")).hexdigest(), _digest(envelope)))


def _set_state(conn, run, state, *, revision=None, completed=None,
               task_key=None, result=None):
    fields = ["state=?", "heartbeat_at=?", "updated_at=?"]
    values = [state, _now(), _now()]
    if revision is not None:
        fields.append("mission_revision=?")
        values.append(revision)
    if completed is not None:
        fields.append("completed_tasks=?")
        values.append(completed)
    if task_key is not None:
        fields.append("last_task_key=?")
        values.append(task_key)
    if result is not None:
        fields.append("result=?")
        values.append(str(result)[:300])
    values.extend([run["project"], run["project_root"], run["mission_id"], run["run_id"]])
    with conn:
        changed = conn.execute("UPDATE orbit_autopilot_mission_runs SET " +
            ",".join(fields) +
            " WHERE project=? AND project_root=? AND mission_id=? AND run_id=?",
            values).rowcount
    if changed != 1:
        raise RuntimeError("Mission run identity changed")
    fresh = _run(conn, run["project_root"], run["project"], run["mission_id"])
    return fresh


def _task(conn, root, project, key):
    row = conn.execute("""SELECT * FROM orbit_agent_tasks
        WHERE project=? AND project_root=? AND task_key=?""",
        (project, str(root), key)).fetchone()
    return dict(row) if row else None


def _record_local_report(conn, root, project, job):
    """Bridge a completed local Codex run into the existing review ledger."""
    task = _task(conn, root, project, job["task_key"])
    if task is None:
        return {"status": "HOLD_TASK_DISAPPEARED"}
    if job["state"] != "REVIEW_REQUIRED" or not job["workspace"] or not job["source_head"]:
        return {"status": "HOLD_LOCAL_RUN_PROVENANCE"}
    try:
        recorded = json.loads(job["changed_paths"])
        allowed = json.loads(task["write_paths"])
        if (not isinstance(recorded, list) or not recorded
                or any(not isinstance(path, str) for path in recorded)
                or not isinstance(allowed, list)):
            return {"status": "HOLD_LOCAL_RUN_PATH_EVIDENCE"}
        safe, actual, reason = runner._review_changes(
            Path(job["workspace"]), allowed, expected_head=job["source_head"])
        if not safe or actual != recorded:
            return {"status": "HOLD_LOCAL_RUN_WORKSPACE_REVIEW",
                    "review_status": reason}
        scope = orbit_tasks.scope_report(allowed, actual)
        if not scope["allowed"]:
            return {"status": "HOLD_LOCAL_RUN_SCOPE_VIOLATION"}
        if task["status"] == "REPORTED_DONE" or task["status"] == "REVIEW_ACCEPTED":
            try:
                ledger_paths = json.loads(task["changed_paths"])
            except (TypeError, ValueError, json.JSONDecodeError):
                return {"status": "HOLD_LOCAL_RUN_PATH_EVIDENCE"}
            if ledger_paths != actual:
                return {"status": "HOLD_TASK_PATH_LEDGER_MISMATCH"}
            return {"status": task["status"], "task_revision": task["revision"],
                    "changed_paths": actual}
        if task["status"] in {"REWORK", "FAILED", "BLOCKED", "CANCELLED"}:
            return {"status": task["status"]}
        if task["status"] != "PLANNED":
            return {"status": "HOLD_TASK_NOT_PLANNED",
                    "recorded_task_status": task["status"]}
        evidence = ("LOCAL_CODEX_RUN_COMPLETED run_id=" + job["run_id"]
                    + "; independent review and tests are still required")
        note = (task["note"] or "") + ("; " if task["note"] else "") + (
            "LOCAL_CODEX_RUN_REPORTED:" + job["run_id"])
        updated = orbit_tasks._update(
            conn, task, "REPORTED_DONE", evidence=evidence,
            changed_paths=_json(actual), note=note)
        return {"status": "REPORTED_DONE", "task_revision": updated["revision"],
                "changed_paths": actual, "reviewer_verification": False}
    except (ValueError, TypeError, OSError, json.JSONDecodeError):
        return {"status": "HOLD_LOCAL_RUN_EVIDENCE_INVALID"}


def _all_accepted(conn, root, project, keys):
    for key in keys:
        task = _task(conn, root, project, key)
        if task is None or task["status"] != "REVIEW_ACCEPTED":
            return False
    return True


def _task_state_summary(conn, root, project, keys):
    summary = []
    for key in keys:
        task = _task(conn, root, project, key)
        if task is None:
            summary.append({"task_key": key, "status": "MISSING",
                            "depends_on": []})
            continue
        try:
            dependencies = json.loads(task["depends_on"])
            if not isinstance(dependencies, list) or any(
                    not isinstance(item, str) for item in dependencies):
                dependencies = ["UNREADABLE"]
        except (TypeError, ValueError, json.JSONDecodeError):
            dependencies = ["UNREADABLE"]
        summary.append({
            "task_key": key, "status": task["status"],
            "depends_on": dependencies,
        })
    return summary


def status(conn, root, project, mission):
    run = _run(conn, root, project, mission)
    if run is None:
        return {"status": "NO_MISSION_RUN", "worker_running_verified": False}
    events = conn.execute("""SELECT run_id,project,project_root,mission_id,
        event_type,task_key,state,recorded_at,payload_json,payload_sha256,event_sha256
        FROM orbit_autopilot_mission_events
        WHERE project=? AND project_root=? AND mission_id=? ORDER BY event_id DESC LIMIT 30""",
        (project, str(root), mission)).fetchall()
    timeline = []
    warnings = 0
    for row in reversed(events):
        item = dict(row)
        try:
            payload = json.loads(item["payload_json"])
            envelope = {
                "run_id": item["run_id"], "project": item["project"],
                "project_root": item["project_root"], "mission_id": item["mission_id"],
                "event_type": item["event_type"], "task_key": item["task_key"],
                "state": item["state"], "recorded_at": item["recorded_at"],
                "payload": payload,
            }
            good = (
                isinstance(payload, dict)
                and hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()
                    == item["payload_sha256"]
                and _digest(envelope) == item["event_sha256"]
            )
        except (TypeError, ValueError):
            good = False
        if not good:
            warnings += 1
        timeline.append({
            "event": item["event_type"] if good else "UNTRUSTED_EVENT",
            "task_key": item["task_key"] if good else "",
            "state": item["state"] if good else "INTEGRITY_WARNING",
            "recorded_at": item["recorded_at"],
            "payload_integrity_matches": good,
            "payload": payload if good else {},
        })
    return {
        "status": run["state"], "run_id": run["run_id"],
        "mission_id": mission, "mission_revision": run["mission_revision"],
        "completed_tasks": run["completed_tasks"], "last_task_key": run["last_task_key"],
        "started_at": run["started_at"], "heartbeat_at": run["heartbeat_at"],
        "worker_running_verified": False, "event_integrity_warnings": warnings,
        "timeline": timeline, "result": run["result"],
    }


def _run_mission_locked(conn, root, project, mission, revision, *,
                         operator_confirmed=False, codex_path=None,
                         max_seconds=MAX_PROCESS_SECONDS,
                         review_wait_seconds=DEFAULT_REVIEW_WAIT_SECONDS,
                         poll_seconds=0.5, launch=runner._codex_process,
                         sleep=time.sleep):
    """Run charter tasks serially, pausing at each independent review gate.

    The local operator confirms once for the bounded charter. A task's output
    is never accepted automatically: the existing task-review API must mark
    it REVIEW_ACCEPTED, and the exact isolated diff must be committed to the
    approved source branch before the next dependent task starts.
    """
    if operator_confirmed is not True:
        return {"status": "HOLD_LOCAL_OPERATOR_CONFIRMATION_REQUIRED"}
    if type(revision) is not int or revision < 1:
        raise ValueError("A current positive mission revision is required")
    if type(max_seconds) is not int or not 1 <= max_seconds <= MAX_PROCESS_SECONDS:
        raise ValueError("Mission process duration exceeds its bound")
    if type(review_wait_seconds) is not int or not 1 <= review_wait_seconds <= MAX_PROCESS_SECONDS:
        raise ValueError("Review wait must be 1..3600 seconds")
    if not isinstance(poll_seconds, (int, float)) or not 0.05 <= poll_seconds <= MAX_POLL_SECONDS:
        raise ValueError("Poll interval must be 0.05..2 seconds")

    setup(conn)
    mission_row = orbit_autopilot._load(conn, root, project, mission)
    if not mission_row:
        return {"status": "HOLD_NO_MISSION"}
    charter = json.loads(mission_row["charter_json"])
    charter_digest = _digest(charter)
    if mission_row["revision"] != revision:
        return {"status": "HOLD_STALE_REVISION",
                "current_revision": mission_row["revision"]}
    if orbit_autopilot._public(mission_row)["status"] != "ACTIVE":
        return {"status": "HOLD_MISSION_NOT_ACTIVE",
                "mission_status": orbit_autopilot._public(mission_row)["status"]}

    run = _run(conn, root, project, mission)
    if run is None:
        stamp = _now()
        run = {
            "project": project, "project_root": str(root), "mission_id": mission,
            "run_id": secrets.token_hex(16), "charter_digest": charter_digest,
            "mission_revision": revision, "state": "RUNNING", "completed_tasks": 0,
            "last_task_key": "", "started_at": stamp, "heartbeat_at": stamp,
            "updated_at": stamp, "result": "",
        }
        with conn:
            conn.execute("""INSERT INTO orbit_autopilot_mission_runs
                (project,project_root,mission_id,run_id,charter_digest,mission_revision,
                 state,completed_tasks,last_task_key,started_at,heartbeat_at,updated_at,result)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                tuple(run[key] for key in (
                    "project","project_root","mission_id","run_id","charter_digest",
                    "mission_revision","state","completed_tasks","last_task_key",
                    "started_at","heartbeat_at","updated_at","result")))
        _event(conn, run, "MISSION_STARTED", "RUNNING",
               payload={"charter_digest": charter_digest,
                        "task_count": len(charter["task_keys"]),
                        "approval_authenticated": False})
    else:
        if run["charter_digest"] != charter_digest:
            return {"status": "HOLD_CHARTER_REVISION_CHANGED"}
        if run["state"] in {"COMPLETED", "STOPPED", "EXPIRED", "BLOCKED", "RECOVERY_REQUIRED"}:
            return {"status": "HOLD_TERMINAL_MISSION_RUN",
                    "mission_run": status(conn, root, project, mission)}
        existing_job = runner._job(conn, root, project, mission)
        if existing_job and existing_job["state"] in {runner.RUNNING, "STOP_REQUESTED"}:
            return {"status": "HOLD_RECONCILE_POSSIBLE_HOST_PROCESS",
                    "worker_running_verified": False}
        if run["state"] == "PAUSED" and mission_row["state"] == "ACTIVE":
            if not _observed_pause_resume(
                    conn, root, project, mission, run["mission_revision"], revision):
                run = _set_state(
                    conn, run, "RECOVERY_REQUIRED",
                    result="mission resumed without recorded pause/resume events")
                _event(conn, run, "MISSION_REVISION_MISMATCH", run["state"])
                return {"status": run["state"]}
            run = _set_state(conn, run, "RUNNING", revision=revision)
            _event(conn, run, "MISSION_RESUMED", "RUNNING",
                   payload={"mission_revision": revision})
        elif run["state"] not in {"WAITING_REVIEW", "RUNNING", "PAUSED"}:
            return {"status": "HOLD_MISSION_RUN_STATE"}

    started = time.monotonic()
    review_started = None
    completed = run["completed_tasks"]
    task_limit = min(len(charter["task_keys"]), orbit_autopilot.MAX_MISSION_TASKS)

    while time.monotonic() - started < max_seconds:
        mission_row = orbit_autopilot._load(conn, root, project, mission)
        if not mission_row:
            run = _set_state(conn, run, "RECOVERY_REQUIRED", result="mission charter disappeared")
            _event(conn, run, "MISSION_RECOVERY_REQUIRED", run["state"])
            return {"status": run["state"]}
        current = orbit_autopilot._public(mission_row)
        if current["status"] == "EXPIRED":
            run = _set_state(conn, run, "EXPIRED", result="charter expiry reached")
            _event(conn, run, "MISSION_EXPIRED", run["state"])
            return {"status": run["state"]}
        if current["status"] == "STOPPED":
            run = _set_state(conn, run, "STOPPED", result="charter stopped by operator")
            _event(conn, run, "MISSION_STOPPED", run["state"])
            return {"status": run["state"]}
        if current["status"] == "PAUSED":
            if run["state"] != "PAUSED":
                # Keep the last approved active revision so a later resume
                # can verify both the PAUSE and RESUME charter events.
                run = _set_state(conn, run, "PAUSED")
                _event(conn, run, "MISSION_PAUSED", "PAUSED",
                       payload={"mission_revision": mission_row["revision"]})
            sleep(float(poll_seconds))
            continue
        if current["status"] != "ACTIVE":
            run = _set_state(conn, run, "BLOCKED", result="mission is not active")
            _event(conn, run, "MISSION_BLOCKED", run["state"])
            return {"status": run["state"]}
        if mission_row["revision"] != run["mission_revision"]:
            # A changed revision is adopted only after a recorded pause/resume.
            observed_resume = _observed_pause_resume(
                conn, root, project, mission, run["mission_revision"],
                mission_row["revision"])
            if not observed_resume:
                run = _set_state(conn, run, "RECOVERY_REQUIRED",
                                 result="mission revision changed without observed pause/resume")
                _event(conn, run, "MISSION_REVISION_MISMATCH", run["state"])
                return {"status": run["state"]}
            run = _set_state(conn, run, "RUNNING", revision=mission_row["revision"])
            _event(conn, run, "MISSION_RESUMED", "RUNNING",
                   payload={"mission_revision": mission_row["revision"]})

        job = runner._job(conn, root, project, mission)
        if job:
            if job["state"] in {runner.RUNNING, "STOP_REQUESTED"}:
                run = _set_state(conn, run, "RECOVERY_REQUIRED",
                                 result="stored worker may still be running; no PID kill attempted")
                _event(conn, run, "WORKER_RECONCILIATION_REQUIRED", run["state"],
                       task_key=job["task_key"])
                return {"status": run["state"], "worker_running_verified": False}
            if job["state"] != "REVIEW_REQUIRED":
                run = _set_state(conn, run, "BLOCKED",
                                 result="previous local task did not reach independent review")
                _event(conn, run, "TASK_RUN_BLOCKED", run["state"],
                       task_key=job["task_key"], payload={"runner_state": job["state"]})
                return {"status": run["state"], "runner": runner._public(job)}

            report = _record_local_report(conn, root, project, job)
            if report["status"] == "REWORK":
                archived = runner.archive_rework(
                    conn, root, project, mission, mission_row["revision"],
                    confirm_write=True)
                if archived["status"] == "REWORK_ARCHIVED_REQUEUED":
                    run = _set_state(
                        conn, run, "RUNNING", task_key=job["task_key"],
                        result="reviewer-directed rework requeued within charter")
                    _event(
                        conn, run, "TASK_REWORK_REQUEUED", run["state"],
                        task_key=job["task_key"],
                        payload={
                            "attempt_number": archived["attempt_number"],
                            "attempt_limit": archived["attempt_limit"],
                            "review_evidence_sha256": hashlib.sha256(
                                _task(conn, root, project, job["task_key"])[
                                    "review_evidence"].encode("utf-8")).hexdigest(),
                            "write_scope_unchanged": True,
                            "task_spec_unchanged": True,
                            "reviewer_identity_authenticated": False,
                            "new_operator_approval_required": False,
                        })
                    review_started = None
                    continue
                if archived["status"] == "REWORK_ARCHIVED_ATTEMPT_LIMIT":
                    run = _set_state(
                        conn, run, "RUNNING", task_key=job["task_key"],
                        result="attempt limit exhausted for this task; continue only DAG-ready independent tasks")
                    _event(
                        conn, run, "TASK_RETRY_LIMIT_REACHED", run["state"],
                        task_key=job["task_key"],
                        payload={
                            "attempt_number": archived["attempt_number"],
                            "attempt_limit": archived["attempt_limit"],
                            "task_left_in_rework": True,
                            "independent_tasks_may_continue": True,
                            "reviewer_identity_authenticated": False,
                        })
                    review_started = None
                    continue
                run = _set_state(conn, run, "BLOCKED",
                                 result="rework provenance or archive gate failed")
                _event(conn, run, "TASK_REWORK_ARCHIVE_BLOCKED", run["state"],
                       task_key=job["task_key"], payload=archived)
                return {"status": run["state"], "task_status": "REWORK",
                        "retry": archived}
            if report["status"] in {"FAILED", "BLOCKED", "CANCELLED"}:
                run = _set_state(conn, run, "BLOCKED",
                                 result="worker failure requires explicit reconciliation")
                _event(conn, run, "TASK_RUN_FAILURE_REQUIRES_RECONCILIATION",
                       run["state"], task_key=job["task_key"],
                       payload={"task_status": report["status"]})
                return {"status": run["state"], "task_status": report["status"]}
            if report["status"] not in {"REPORTED_DONE", "REVIEW_ACCEPTED"}:
                run = _set_state(conn, run, "BLOCKED", result=report["status"])
                _event(conn, run, "TASK_REPORT_BLOCKED", run["state"],
                       task_key=job["task_key"], payload=report)
                return {"status": run["state"], "task_report": report}
            if report["status"] == "REPORTED_DONE":
                _event(conn, run, "TASK_REVIEW_REQUIRED", "WAITING_REVIEW",
                       task_key=job["task_key"],
                       payload={"task_revision": report["task_revision"],
                                "changed_paths": report["changed_paths"],
                                "independent_review_required": True})
            task = _task(conn, root, project, job["task_key"])
            if task and task["status"] == "REVIEW_ACCEPTED":
                handoff = runner.advance_reviewed(
                    conn, root, project, mission, mission_row["revision"],
                    confirm_write=True)
                if handoff["status"] != "REVIEW_HANDOFF_RECORDED":
                    run = _set_state(conn, run, "BLOCKED", result=handoff["status"])
                    _event(conn, run, "TASK_HANDOFF_BLOCKED", run["state"],
                           task_key=job["task_key"], payload=handoff)
                    return {"status": run["state"], "handoff": handoff}
                completed += 1
                run = _set_state(conn, run, "RUNNING", completed=completed,
                                 task_key=job["task_key"])
                _event(conn, run, "TASK_REVIEW_ACCEPTED", "RUNNING",
                       task_key=job["task_key"],
                       payload={"review_handoff_recorded": True,
                                "next_task_may_be_considered": True})
                review_started = None
                continue
            if task and task["status"] in {"REWORK", "FAILED", "BLOCKED", "CANCELLED"}:
                run = _set_state(conn, run, "BLOCKED",
                                 result="task review requires explicit rework/replanning")
                _event(conn, run, "TASK_REWORK_REQUIRED", run["state"],
                       task_key=job["task_key"],
                       payload={"task_status": task["status"]})
                return {"status": run["state"], "task_status": task["status"]}

            if review_started is None:
                review_started = time.monotonic()
            run = _set_state(conn, run, "WAITING_REVIEW", task_key=job["task_key"])
            if time.monotonic() - review_started >= review_wait_seconds:
                _event(conn, run, "REVIEW_WAIT_TIMEOUT", run["state"],
                       task_key=job["task_key"])
                return {"status": "WAITING_REVIEW",
                        "task_key": job["task_key"],
                        "task_revision": task["revision"] if task else None,
                        "changed_paths": report.get("changed_paths", []),
                        "next": "Inspect the isolated diff, run trusted tests, record REVIEW_ACCEPTED or REWORK, then commit the exact reviewed changes to the approved source branch and resume this mission."}
            sleep(float(poll_seconds))
            continue

        if _all_accepted(conn, root, project, charter["task_keys"]):
            run = _set_state(conn, run, "COMPLETED", completed=task_limit,
                             result="all charter tasks independently review-accepted and handed off")
            _event(conn, run, "MISSION_COMPLETED", run["state"])
            return {"status": run["state"], "completed_tasks": task_limit,
                    "release_authorized": False, "merge_performed": False}
        if completed >= task_limit:
            run = _set_state(conn, run, "COMPLETED", completed=completed)
            _event(conn, run, "MISSION_COMPLETED", run["state"])
            return {"status": run["state"], "completed_tasks": completed,
                    "release_authorized": False, "merge_performed": False}

        plan = runner.preview(conn, root, project, mission, mission_row["revision"])
        if plan["status"] != "READY_FOR_LOCAL_OPERATOR_REVIEW":
            if _all_accepted(conn, root, project, charter["task_keys"]):
                run = _set_state(conn, run, "COMPLETED", completed=task_limit)
                _event(conn, run, "MISSION_COMPLETED", run["state"])
                return {"status": run["state"], "completed_tasks": task_limit}
            task_states = _task_state_summary(
                conn, root, project, charter["task_keys"])
            rework_tasks = [
                item["task_key"] for item in task_states
                if item["status"] == "REWORK"
            ]
            if rework_tasks:
                run = _set_state(
                    conn, run, "BLOCKED",
                    result="unresolved REWORK tasks block only their dependent DAG paths")
                _event(
                    conn, run, "MISSION_BLOCKED_BY_REWORK", run["state"],
                    payload={
                        "scheduler_status": plan["status"],
                        "rework_tasks": rework_tasks,
                        "unresolved_tasks": task_states,
                        "task_graph_changed": False,
                    })
                return {
                    "status": run["state"], "block_reason": "REWORK",
                    "scheduler": plan, "tasks": task_states,
                    "completed_tasks": completed,
                }
            run = _set_state(conn, run, "BLOCKED", result=plan["status"])
            _event(conn, run, "MISSION_SCHEDULER_BLOCKED", run["state"],
                   payload={"scheduler_status": plan["status"],
                            "unresolved_tasks": task_states})
            return {"status": run["state"], "scheduler": plan,
                    "tasks": task_states, "completed_tasks": completed}

        adapter: MissionExecutionAdapter = CodexCLIAdapter(
            codex_path=codex_path, launch=launch)
        task_record = _task(conn, root, project, plan["task_key"])
        if task_record is None:
            run = _set_state(conn, run, "BLOCKED",
                             result="scheduled task disappeared before adapter launch")
            _event(conn, run, "MISSION_TASK_DISAPPEARED", run["state"],
                   task_key=plan["task_key"])
            return {"status": run["state"]}
        task_context = MissionTaskContext(
            project_root=Path(root), project=project, mission_id=mission,
            mission_revision=mission_row["revision"], task_key=plan["task_key"],
            max_seconds=min(runner.MAX_SECONDS, max(1, max_seconds -
                int(time.monotonic() - started))),
            rework_feedback=task_record["review_evidence"] or "")
        result = adapter.execute_task(conn, task_context)
        _event(conn, run, "TASK_RUN_FINISHED", result["status"],
               task_key=result.get("task_key", plan["task_key"]),
               payload={"runner_status": result["status"],
                        "execution_adapter": adapter.adapter_id,
                        "provider_id": adapter.provider_id,
                        "host_native": adapter.host_native,
                        "model_selection_verified": False,
                        "provider_usage_verified": False,
                        "worker_killed_verified": result.get("worker_killed_verified", False)})
        if result["status"] == "REVIEW_REQUIRED":
            review_started = time.monotonic()
            continue
        if result["status"] == "STOPPED" and result.get("worker_killed_verified") is True:
            stopped_job = runner._job(conn, root, project, mission)
            if (stopped_job and stopped_job["state"] == "STOPPED"
                    and stopped_job["run_id"]):
                _event(conn, run, "WORKER_STOPPED_VERIFIED", "PAUSED",
                       task_key=plan["task_key"],
                       payload={"run_id": stopped_job["run_id"],
                                "process_termination_verified": True,
                                "workspace_preserved": True})
                # This deletion is permitted only in the still-attached
                # supervisor after run_once verified its owned child exited.
                # A restarted process never infers liveness or kills a PID.
                with conn:
                    conn.execute("""DELETE FROM orbit_autopilot_runner_jobs
                        WHERE project=? AND project_root=? AND mission_id=?
                          AND run_id=? AND state='STOPPED'""",
                        (project, str(root), mission, stopped_job["run_id"]))
            run = _set_state(conn, run, "PAUSED",
                             result="owned worker terminated and stopped run archived")
            continue
        run = _set_state(conn, run, "BLOCKED", result=result["status"])
        _event(conn, run, "TASK_RUN_BLOCKED", run["state"],
               task_key=plan["task_key"], payload={"runner_status": result["status"]})
        return {"status": run["state"], "runner": result}

    latest = orbit_autopilot._load(conn, root, project, mission)
    paused = bool(latest and orbit_autopilot._public(latest)["status"] == "PAUSED")
    terminal_state = "PAUSED" if paused else "WAITING_REVIEW"
    run = _set_state(conn, run, terminal_state,
                     result="foreground supervisor time budget reached")
    _event(conn, run, "MISSION_PROCESS_BUDGET_REACHED", run["state"])
    return {"status": terminal_state,
            "mission_run": status(conn, root, project, mission)}


def timeline(conn, root, project, mission):
    return status(conn, root, project, mission)


@contextmanager
def _mission_lock(root, project, mission):
    """OS-released exclusive lock; a crashed supervisor cannot leave a stale lease."""
    identity = "\\0".join((str(Path(root).resolve()), project, mission))
    name = hashlib.sha256(identity.encode("utf-8")).hexdigest() + ".lock"
    folder = Path(tempfile.gettempdir()) / "orbit-mission-locks"
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = folder / name
    flags = os.O_CREAT | os.O_RDWR | getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    acquired = False
    unlock = None
    try:
        if not os.path.isfile(path):
            yield False
            return
        if os.name == "nt":
            import msvcrt
            if os.fstat(fd).st_size == 0:
                os.write(fd, b"\\0")
                os.fsync(fd)
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            unlock = lambda: msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            unlock = lambda: fcntl.flock(fd, fcntl.LOCK_UN)
        acquired = True
        yield True
    except (OSError, ImportError):
        if not acquired:
            yield False
        else:
            raise
    finally:
        if unlock is not None:
            try:
                unlock()
            except OSError:
                pass
        os.close(fd)


def run_mission(conn, root, project, mission, revision, *,
                operator_confirmed=False, codex_path=None,
                max_seconds=MAX_PROCESS_SECONDS,
                review_wait_seconds=DEFAULT_REVIEW_WAIT_SECONDS,
                poll_seconds=0.5, launch=runner._codex_process,
                sleep=time.sleep):
    """Serialize mission supervisors across processes on this machine."""
    with _mission_lock(root, project, mission) as acquired:
        if not acquired:
            return {"status": "HOLD_SUPERVISOR_ALREADY_RUNNING",
                    "worker_running_verified": False}
        return _run_mission_locked(
            conn, root, project, mission, revision,
            operator_confirmed=operator_confirmed, codex_path=codex_path,
            max_seconds=max_seconds,
            review_wait_seconds=review_wait_seconds,
            poll_seconds=poll_seconds, launch=launch, sleep=sleep)


def _observed_pause_resume(conn, root, project, mission, old_revision, new_revision):
    """Require the charter's own revisioned event ledger to show pause then resume."""
    rows = conn.execute("""SELECT revision,action FROM orbit_autopilot_events
        WHERE project=? AND project_root=? AND mission_id=? AND revision>?
          AND revision<=? ORDER BY revision""",
        (project, str(root), mission, old_revision, new_revision)).fetchall()
    if not rows or rows[-1]["revision"] != new_revision:
        return False
    paused = False
    resumed = False
    for row in rows:
        if row["action"] == "PAUSE":
            paused = True
        elif row["action"] == "RESUME" and paused:
            paused = False
            resumed = True
        else:
            return False
    return resumed and not paused
