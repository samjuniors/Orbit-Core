"""Charter-bound, audit-only team staffing and handoff events for Orbit Core.

The event journal is an adjunct to the EXISTING project task ledger, never a
second task database or peer chat system. Nothing here starts/stops agents,
installs skills, invokes tools, sends messages, or authenticates human approval.
"""
from __future__ import annotations

import hashlib
import json
import re

import orbit_autopilot
import orbit_capabilities
import orbit_delegation
import orbit_skill_plan
import orbit_tasks
import orbit_team_builder

MAX_EVENTS = 48
EVENT_KEY = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")
NO_WORKER_DELEGATION = frozenset({
    "invoke_subagent", "collaboration.spawn_agent", "spawn_agent",
    "collaboration.interrupt_agent", "collaboration.send_message",
    "collaboration.followup_task", "Agent", "Task",
})


def setup(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS orbit_team_events (
        project TEXT NOT NULL, project_root TEXT NOT NULL, mission_id TEXT NOT NULL,
        event_key TEXT NOT NULL, event_type TEXT NOT NULL,
        task_key TEXT NOT NULL, peer_task_key TEXT NOT NULL DEFAULT '',
        content_sha256 TEXT NOT NULL, payload_json TEXT NOT NULL,
        recorded_at TEXT NOT NULL,
        PRIMARY KEY (project, project_root, mission_id, event_key)
    )""")
    conn.execute("""CREATE INDEX IF NOT EXISTS idx_orbit_team_event_scope
                    ON orbit_team_events(project, project_root, mission_id, event_type)""")
    conn.commit()


def _has_table(conn):
    return conn.execute("""SELECT 1 FROM sqlite_master
                           WHERE type='table' AND name='orbit_team_events'""").fetchone() is not None


def _digest(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")).hexdigest()


def _event_key(a):
    name = a.get("event_key")
    if not isinstance(name, str) or not EVENT_KEY.fullmatch(name):
        raise ValueError("event_key must be a bounded stable event slug")
    return name


def _text(a, name, lo=1, hi=280):
    value = a.get(name)
    if not isinstance(value, str) or not lo <= len(value.strip()) <= hi:
        raise ValueError(name + " must contain bounded plain text")
    value = value.strip()
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError(name + " cannot contain control characters")
    return value


def _task(conn, root, project, key, revision):
    if not isinstance(key, str):
        raise ValueError("task key must be text")
    orbit_tasks.key({"task_key": key})
    row = conn.execute(
        """SELECT * FROM orbit_agent_tasks
           WHERE project=? AND project_root=? AND task_key=?""",
        (project, str(root), key),
    ).fetchone()
    if row is None:
        return None, "HOLD_TASK_MISSING"
    item = dict(row)
    if type(revision) is not int or revision != item["revision"]:
        return None, "HOLD_STALE_TASK_REVISION"
    return item, None


def _common(mission, root, project, action):
    return {
        "project": project, "project_root": str(root), "mission_id": mission,
        "action": action, "execution_allowed": False,
        "worker_spawned": False, "worker_stopped": False,
        "skill_installed": False, "tool_permission_granted": False,
        "peer_message_sent": False, "founder_identity_authenticated": False,
        "host_permissions_verified": False, "native_session_verified": False,
        "state_written": False, "journal_type": "PROJECT_SCOPED_ADJUNCT_EVENT_LOG",
    }


def _history(conn, root, project, mission, task_key=None):
    if not _has_table(conn):
        return []
    query = """SELECT event_key,event_type,task_key,peer_task_key,
                      content_sha256,payload_json,recorded_at
               FROM orbit_team_events WHERE project=? AND project_root=?
               AND mission_id=?"""
    params = [project, str(root), mission]
    if task_key:
        query += " AND (task_key=? OR peer_task_key=?)"
        params += [task_key, task_key]
    query += " ORDER BY recorded_at,event_key LIMIT ?"
    params.append(MAX_EVENTS)
    return [dict(r) for r in conn.execute(query, params)]


def _lookup(conn, root, project, mission, event_key):
    if not _has_table(conn):
        return None
    row = conn.execute(
        """SELECT * FROM orbit_team_events
           WHERE project=? AND project_root=? AND mission_id=? AND event_key=?""",
        (project, str(root), mission, event_key),
    ).fetchone()
    return dict(row) if row else None


def _staff(conn, root, project, a, charter):
    item, error = _task(conn, root, project, a.get("task_key"), a.get("task_revision"))
    if error:
        return error, None
    if item["task_key"] not in charter["task_keys"]:
        return "HOLD_TASK_OUTSIDE_CHARTER", None
    if item["status"] not in {"PLANNED", "REWORK", "FAILED", "BLOCKED"}:
        return "HOLD_TASK_NOT_ELIGIBLE_FOR_STAFFING", None
    kind = a.get("worker_kind")
    if kind not in {"agent", "bot"}:
        raise ValueError("worker_kind must be agent or bot")
    host = a.get("host")
    if host not in orbit_skill_plan.HOSTS or host == "unknown":
        raise ValueError("Choose a declared supported coding host")
    listed = orbit_delegation.validate_reported_tools(
        host, a.get("available_host_tools", []))
    requested = a.get("requested_tool_names", [])
    if (not isinstance(requested, list) or len(requested) > 6 or
            any(not isinstance(n, str) for n in requested) or
            len(set(requested)) != len(requested)):
        raise ValueError("Up to six unique proposed tool names required")
    if set(requested) - set(listed):
        return "HOLD_UNADVERTISED_TOOL", None
    if set(requested) & NO_WORKER_DELEGATION:
        return "HOLD_RECURSIVE_OR_PRIVILEGED_TOOL", None
    skills = a.get("requested_skill_names", [])
    if (not isinstance(skills, list) or len(skills) > 3 or
            any(not isinstance(s, str) for s in skills)):
        raise ValueError("At most three proposed project skill names")
    profile = orbit_skill_plan._profile(a.get("project_profile"))
    permission = a.get("permission_state", "UNKNOWN")
    if permission not in {"APPROVED", "UNKNOWN", "DENIED"}:
        raise ValueError("Unknown caller-reported host permission state")
    if permission == "DENIED":
        return "HOLD_PERMISSION_DENIED", None
    objective = item["role"] + ": " + item["goal"][:1350]
    selection = orbit_skill_plan.preview(
        root, objective, orbit_capabilities.discover(root),
        project_profile=profile, requested_skill_names=skills,
        review_manifest=a.get("review_manifest"),
        permission_state=permission, host=host)
    if selection["status"].startswith("HOLD_"):
        return selection["status"], None
    # Only inventory hashes and untrusted tool labels are retained; never
    # import/install skill contents or copy credentials into agent prompts.
    payload = {
        "event_type": "STAFF_REQUEST", "task_key": item["task_key"],
        "task_revision": item["revision"], "role": item["role"],
        "lead": orbit_team_builder.LEADS[item["role"]],
        "worker_kind": kind, "host": host, "requested_tool_names": sorted(requested),
        "requested_skill_names": skills, "skill_manifest": selection["manifest"],
        "profile": profile, "host_permission_reported": permission,
        "skill_fit_verified": False, "host_tool_grants": [],
        "profile_creation": "REUSE_EXISTING_PROFILE_FIRST",
        "charter_grants_spawn": False,
    }
    # Stronger confirmation on writes: must pin and revalidate the exact
    # tree/location snapshot returned by a previous preview.
    if a.get("confirm_write") is True and (
        a.get("review_manifest") != selection["manifest"] or
        selection["revalidation"]["status"] != "PINS_MATCH_CURRENT_PREVIEW_ONLY"
    ):
        return "HOLD_SKILL_PINS_NOT_REVALIDATED", None
    return "STAFFING_REQUEST_REVIEW", payload


def _handoff(conn, root, project, a, charter):
    source, error = _task(conn, root, project,
                          a.get("task_key"), a.get("task_revision"))
    if error:
        return error, None
    target, error = _task(conn, root, project,
                          a.get("peer_task_key"), a.get("peer_revision"))
    if error:
        return error, None
    if (source["task_key"] not in charter["task_keys"]
            or target["task_key"] not in charter["task_keys"]):
        return "HOLD_TASK_OUTSIDE_CHARTER", None
    if source["task_key"] == target["task_key"]:
        return "HOLD_SELF_HANDOFF", None
    try:
        deps = json.loads(target["depends_on"])
    except (ValueError, TypeError):
        return "HOLD_INVALID_TASK_DEPENDENCIES", None
    if source["task_key"] not in deps:
        return "HOLD_NOT_A_TASK_DEPENDENCY", None
    if source["status"] != "REVIEW_ACCEPTED" or not source["review_evidence"]:
        return "HOLD_UPSTREAM_INDEPENDENT_REVIEW", None
    if target["status"] not in {"PLANNED", "REWORK", "FAILED", "BLOCKED"}:
        return "HOLD_DOWNSTREAM_NOT_READY", None
    summary = _text(a, "summary", 20, 280)
    evidence = _text(a, "evidence_ref", 8, 200)
    payload = {
        "event_type": "HANDOFF_RECORDED",
        "task_key": source["task_key"],
        "peer_task_key": target["task_key"],
        "source_revision": source["revision"],
        "target_revision": target["revision"],
        "summary_untrusted": summary,
        "evidence_ref_caller_reported": evidence,
        "review_evidence_present_unverified": True,
        "delivered_to_host": False, "native_peer_message_sent": False,
    }
    return "HANDOFF_REVIEW", payload


def _retire(conn, root, project, a, charter):
    task, error = _task(conn, root, project, a.get("task_key"), a.get("task_revision"))
    if error:
        return error, None
    if task["task_key"] not in charter["task_keys"]:
        return "HOLD_TASK_OUTSIDE_CHARTER", None
    if task["status"] in {"RUNNING", "RESERVED"}:
        return "HOLD_NATIVE_WORKER_RECONCILIATION", None
    if task["status"] not in {"REVIEW_ACCEPTED", "FAILED", "BLOCKED", "CANCELLED"}:
        return "HOLD_TASK_NOT_TERMINAL", None
    # Neither a saved request nor an empty task session is evidence that a
    # native worker ever existed; never claim such a worker was retired.
    if not task["host_session"]:
        return "HOLD_NO_RECORDED_HOST_SESSION", None
    if not any(
        row["event_type"] == "STAFF_REQUEST" and row["task_key"] == task["task_key"]
        for row in _history(conn, root, project, a["mission_id"])
    ):
        return "HOLD_NO_STAFF_REQUEST_FOR_WORKER", None
    observed = a.get("host_terminal_state")
    if observed not in {"COMPLETED", "FAILED", "CANCELLED", "STOPPED"}:
        return "HOLD_HOST_TERMINAL_OBSERVATION_REQUIRED", None
    reference = a.get("observed_host_session")
    if task["host_session"] and reference != task["host_session"]:
        return "HOLD_HOST_SESSION_MISMATCH", None
    if not task["host_session"] and reference:
        return "HOLD_NO_RECORDED_HOST_SESSION", None
    payload = {
        "event_type": "RETIRE_NOTE",
        "task_key": task["task_key"], "task_revision": task["revision"],
        "task_status": task["status"],
        "host_terminal_state_caller_reported": observed,
        "host_session_reference_present": bool(task["host_session"]),
        "native_host_termination_verified": False,
        "native_process_killed": False, "profile_deleted": False,
        "audit_history_preserved": True,
    }
    return "RETIRE_NOTE_REVIEW", payload


def record(conn, root, project, a):
    """Preview or append an immutable proposal/evidence event within the charter."""
    action = a.get("action")
    if action not in {"staff", "handoff", "retire", "inbox"}:
        raise ValueError("Unknown team event action")
    mission = orbit_autopilot._mission_id(a)
    common = _common(mission, root, project, action)

    if action == "inbox":
        scope = a.get("task_key")
        if scope is not None:
            orbit_tasks.key({"task_key": scope})
        # Browsing never renews a paused, expired or stopped charter.
        if orbit_autopilot._load(conn, root, project, mission) is None:
            return {**common, "status": "HOLD_MISSION_NOT_FOUND", "events": []}
        events = _history(conn, root, project, mission, scope)
        return {
            **common, "status": "TEAM_EVENT_HISTORY", "event_count": len(events),
            "events": [
                {"event_key": e["event_key"], "event_type": e["event_type"],
                 "task_key": e["task_key"], "peer_task_key": e["peer_task_key"],
                 "content_sha256": e["content_sha256"],
                 "recorded_at": e["recorded_at"], "source_verified": False,
                 "host_delivered": False}
                for e in events
            ],
        }

    charter, state, reason = orbit_autopilot._guard(conn, root, project, a)
    if reason:
        return {**common, "status": reason}
    if action == "staff":
        status, payload = _staff(conn, root, project, a, charter)
    elif action == "handoff":
        status, payload = _handoff(conn, root, project, a, charter)
    else:
        status, payload = _retire(conn, root, project, a, charter)
    if payload is None:
        return {**common, "status": status}
    event = _event_key(a)
    digest = _digest(payload)
    out = {
        **common, "status": status, "event_key": event,
        "payload": payload, "review_digest": digest,
        "approval_reference_is_caller_reported": True,
    }
    if a.get("confirm_write") is not True:
        return {**out, "next": "Review this exact digest; local recording is not host execution."}
    if a.get("expected_digest") != digest:
        return {**out, "status": "HOLD_DIGEST_MISMATCH"}
    # Append only under IMMEDIATE; recheck live charter and exact task revisions
    # inside the transaction before committing any actor or evidence claim.
    setup(conn)
    conn.execute("BEGIN IMMEDIATE")
    try:
        fresh, _, error = orbit_autopilot._guard(conn, root, project, a)
        if error or fresh != charter:
            conn.rollback()
            return {**common, "status": error or "HOLD_CHANGED_CHARTER"}
        if action == "staff":
            check, current = _staff(conn, root, project, a, fresh)
        elif action == "handoff":
            check, current = _handoff(conn, root, project, a, fresh)
        else:
            check, current = _retire(conn, root, project, a, fresh)
        if current is None or _digest(current) != digest:
            conn.rollback()
            return {**common, "status": "HOLD_STALE_EVENT_PAYLOAD"}
        existing = _lookup(conn, root, project, mission, event)
        if existing:
            conn.rollback()
            return {**common, "status": ("ALREADY_RECORDED" if
                       existing["content_sha256"] == digest else
                       "HOLD_EVENT_KEY_CONFLICT"), "state_written": False}
        history = _history(conn, root, project, mission)
        if len(history) >= MAX_EVENTS:
            conn.rollback()
            return {**common, "status": "HOLD_EVENT_BUDGET"}
        if action == "staff" and any(
            e["event_type"] == "STAFF_REQUEST" and e["task_key"] == payload["task_key"]
            for e in history
        ):
            conn.rollback()
            return {**common, "status": "HOLD_EXISTING_STAFF_REQUEST"}
        conn.execute(
            """INSERT INTO orbit_team_events
               (project,project_root,mission_id,event_key,event_type,task_key,
                peer_task_key,content_sha256,payload_json,recorded_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (project, str(root), mission, event, payload["event_type"],
             payload["task_key"], payload.get("peer_task_key", ""), digest,
             json.dumps(payload, sort_keys=True, separators=(",", ":")),
             orbit_tasks.utc_now()),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return {**out, "status": {
        "staff": "STAFF_REQUEST_RECORDED",
        "handoff": "HANDOFF_EVENT_RECORDED",
        "retire": "RETIRE_NOTE_RECORDED",
    }[action], "state_written": True,
            "next": "Host must separately verify permission, source evidence, and worker lifecycle. No native action was performed."}
