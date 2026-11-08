"""Charter-bound, audit-only team staffing and handoff events for Orbit Core.

The event journal is an adjunct to the EXISTING project task ledger, never a
second task database or peer chat system. Nothing here starts/stops agents,
installs skills, invokes tools, sends messages, or authenticates human approval.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone

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


def _existing_event(conn, root, project, mission, event_key, expected_type):
    if not isinstance(event_key, str) or not EVENT_KEY.fullmatch(event_key):
        raise ValueError("Referenced event key must be a bounded stable slug")
    event = _lookup(conn, root, project, mission, event_key)
    if event is None:
        return None, "HOLD_EVENT_NOT_FOUND"
    if event["event_type"] != expected_type:
        return None, "HOLD_EVENT_TYPE_MISMATCH"
    try:
        body = json.loads(event["payload_json"])
    except (ValueError, TypeError):
        return None, "HOLD_UNREADABLE_EVENT"
    if _digest(body) != event["content_sha256"]:
        return None, "HOLD_EVENT_INTEGRITY_CHANGED"
    return body, None


def _list_names(value, name, max_items):
    if (not isinstance(value, list) or len(value) > max_items
            or any(not isinstance(v, str) or not v
                   or not orbit_delegation.ALLOWED_TOOL_PATTERN.fullmatch(v)
                   for v in value)
            or len(set(value)) != len(value)):
        raise ValueError(name + " must contain distinct bounded names")
    return value


def _lease_expiry(when, charter):
    if not isinstance(when, str) or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", when):
        raise ValueError("lease_expires_at must be UTC ISO timestamp")
    try:
        end = datetime.fromisoformat(when.replace("Z", "+00:00"))
        charter_end = datetime.fromisoformat(
            charter["expires_at"].replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Invalid lease expiry time") from None
    now = orbit_autopilot.utc_now()
    if not (now < end <= min(now + timedelta(hours=24), charter_end)):
        return "HOLD_LEASE_EXPIRY_OUTSIDE_CHARTER"
    return None


def _lease(conn, root, project, a, charter):
    """Request a time-boxed capability *intent*; no host token or ACL is issued."""
    task, error = _task(conn, root, project, a.get("task_key"),
                        a.get("task_revision"))
    if error:
        return error, None
    if task["task_key"] not in charter["task_keys"]:
        return "HOLD_TASK_OUTSIDE_CHARTER", None
    if task["status"] not in {"PLANNED", "RESERVED"}:
        return "HOLD_WORKER_ALREADY_RUNNING_OR_TERMINAL", None
    staff_key = a.get("staff_event_key")
    staff, error = _existing_event(conn, root, project, a["mission_id"],
                                  staff_key, "STAFF_REQUEST")
    if error:
        return error, None
    if (staff["task_key"] != task["task_key"]
            or staff["task_revision"] != task["revision"]):
        return "HOLD_STAFF_TASK_REVISION_DRIFT", None
    host = staff["host"]
    listed = orbit_delegation.validate_reported_tools(
        host, a.get("available_host_tools", []))
    selected_tools = a.get("lease_tool_names", [])
    _list_names(selected_tools, "lease_tool_names", 3)
    if set(selected_tools) & NO_WORKER_DELEGATION:
        return "HOLD_PRIVILEGED_WORKER_CAPABILITY", None
    if not set(selected_tools) <= set(staff["requested_tool_names"]):
        return "HOLD_CAPABILITY_SCOPE_EXPANSION", None
    if not set(selected_tools) <= set(listed):
        return "HOLD_HOST_TOOL_NOT_CURRENTLY_REPORTED", None
    selected_skills = a.get("lease_skill_names", [])
    if not isinstance(selected_skills, list):
        raise ValueError("lease_skill_names must be a list")
    orbit_skill_plan._validate_requested(selected_skills)
    if len(selected_skills) > 3 or not set(selected_skills) <= set(
            staff["requested_skill_names"]):
        return "HOLD_SKILL_SCOPE_EXPANSION", None
    permission = a.get("permission_state", "UNKNOWN")
    if permission not in {"UNKNOWN", "APPROVED", "DENIED"}:
        raise ValueError("Unknown caller-reported permission state")
    if permission == "DENIED":
        return "HOLD_PERMISSION_DENIED", None
    # Recheck exact manifest against the local current skill tree, even when
    # this particular lease selects a subset of the staff request's skills.
    source = orbit_skill_plan.preview(
        root, task["role"] + ": " + task["goal"][:1350],
        orbit_capabilities.discover(root),
        project_profile=staff["profile"],
        requested_skill_names=staff["requested_skill_names"],
        review_manifest=staff["skill_manifest"],
        permission_state=permission, host=host)
    if source["revalidation"]["status"] != "PINS_MATCH_CURRENT_PREVIEW_ONLY":
        return "HOLD_SKILL_SOURCE_CHANGED", None
    if source["status"].startswith("HOLD_"):
        return source["status"], None
    selected_pins = [
        pin for pin in staff["skill_manifest"]["skills"]
        if pin["name"] in set(selected_skills)
    ]
    if len(selected_pins) != len(selected_skills):
        return "HOLD_SKILL_PINS_INCOMPLETE", None
    deadline = a.get("lease_expires_at")
    if _lease_expiry(deadline, charter):
        return "HOLD_LEASE_EXPIRY_OUTSIDE_CHARTER", None
    mode = a.get("host_workspace_mode", "read-only")
    if mode not in ("read-only", "workspace-write"):
        raise ValueError("Unknown proposed host workspace mode")
    try:
        scopes = orbit_tasks._scopes(json.loads(task["write_paths"]))
        orbit_tasks._resolved_scopes(root, scopes)
    except (ValueError, TypeError):
        return "HOLD_CHANGED_WRITABLE_SCOPE", None
    payload = {
        "event_type": "CAPABILITY_INTENT",
        "task_key": task["task_key"], "task_revision": task["revision"],
        "staff_event_key": staff_key, "staff_event_digest": _digest(staff),
        "host": host, "worker_kind": staff["worker_kind"],
        "host_workspace_mode_requested": mode,
        "requested_tool_names": sorted(selected_tools),
        "skill_pins": selected_pins,
        "task_write_paths": scopes if mode == "workspace-write" else [],
        "lease_expires_at": deadline,
        "host_permission_reported": permission,
        "host_tool_grants": [], "host_skill_activation": False,
        "host_lease_token_issued": False, "native_worker_invoked": False,
    }
    return "CAPABILITY_INTENT_REVIEW", payload


def _revoke(conn, root, project, a, charter):
    """A revoke request can be recorded even after mission pause/stop/expiry."""
    lease_key = a.get("lease_event_key")
    lease, error = _existing_event(conn, root, project, a["mission_id"],
                                  lease_key, "CAPABILITY_INTENT")
    if error:
        return error, None
    if lease["task_key"] not in charter["task_keys"]:
        return "HOLD_TASK_OUTSIDE_CHARTER", None
    if a.get("task_key") != lease["task_key"]:
        return "HOLD_REVOKE_TASK_MISMATCH", None
    if any(e["event_type"] == "CAPABILITY_REVOKE_REQUEST"
           and e["peer_task_key"] == lease_key
           for e in _history(conn, root, project, a["mission_id"])):
        return "HOLD_REVOKE_ALREADY_REQUESTED", None
    reason = _text(a, "summary", 12, 280)
    return "CAPABILITY_REVOKE_REVIEW", {
        "event_type": "CAPABILITY_REVOKE_REQUEST",
        "task_key": lease["task_key"], "peer_task_key": lease_key,
        "lease_digest": _digest(lease), "reason_untrusted": reason,
        "host_revocation_verified": False,
        "native_worker_stopped": False, "token_invalidated_by_orbit": False,
    }


def _receipt(conn, root, project, a, charter):
    """Only record a caller-reported native recipient observation; no send."""
    target, error = _task(conn, root, project, a.get("task_key"),
                          a.get("task_revision"))
    if error:
        return error, None
    if target["task_key"] not in charter["task_keys"]:
        return "HOLD_TASK_OUTSIDE_CHARTER", None
    if target["status"] != "RUNNING" or not target["host_session"]:
        return "HOLD_RECIPIENT_NATIVE_SESSION_NOT_RUNNING", None
    observed = a.get("observed_host_session")
    if observed != target["host_session"]:
        return "HOLD_NATIVE_SESSION_MISMATCH", None
    source_key = a.get("handoff_event_key")
    handoff, error = _existing_event(conn, root, project, a["mission_id"],
                                    source_key, "HANDOFF_RECORDED")
    if error:
        return error, None
    if handoff["peer_task_key"] != target["task_key"]:
        return "HOLD_WRONG_HANDOFF_RECIPIENT", None
    source = conn.execute(
        """SELECT status,depends_on FROM orbit_agent_tasks
           WHERE project=? AND project_root=? AND task_key=?""",
        (project, str(root), handoff["task_key"]),
    ).fetchone()
    if source is None or source["status"] != "REVIEW_ACCEPTED":
        return "HOLD_SOURCE_REVIEW_NO_LONGER_VALID", None
    if any(e["event_type"] == "HANDOFF_RECEIPT" and
           e["peer_task_key"] == source_key
           for e in _history(conn, root, project, a["mission_id"])):
        return "HOLD_HANDOFF_ALREADY_ACKNOWLEDGED", None
    try:
        dependencies = json.loads(target["depends_on"])
    except (ValueError, TypeError):
        return "HOLD_INVALID_TASK_DEPENDENCIES", None
    if handoff["task_key"] not in dependencies:
        return "HOLD_HANDOFF_DEPENDENCY_REMOVED", None
    note = _text(a, "summary", 12, 280)
    payload = {
        "event_type": "HANDOFF_RECEIPT",
        "task_key": target["task_key"], "peer_task_key": source_key,
        "task_revision": target["revision"],
        "handoff_digest": _digest(handoff),
        "observed_host_session_caller_reported": observed,
        "receipt_note_untrusted": note,
        "host_delivery_verified": False, "peer_message_sent_by_orbit": False,
        "task_accepted": False,
    }
    return "HANDOFF_RECEIPT_REVIEW", payload


def _revoke_guard(conn, root, project, a):
    """Fail closed on stale identity but permit emergency revoke after pause."""
    row = orbit_autopilot._load(conn, root, project,
                                orbit_autopilot._mission_id(a))
    if row is None:
        return None, "HOLD_MISSION_NOT_FOUND"
    if (type(a.get("expected_revision")) is not int
            or a["expected_revision"] != row["revision"]):
        return None, "HOLD_STALE_REVISION"
    try:
        charter = json.loads(row["charter_json"])
    except (TypeError, ValueError):
        return None, "HOLD_INVALID_CHARTER"
    if a.get("reported_branch") != charter["branch"]:
        return None, "HOLD_BRANCH_MISMATCH"
    return charter, None


def record(conn, root, project, a):
    """Preview or append an immutable proposal/evidence event within the charter."""
    action = a.get("action")
    if action not in {"staff", "handoff", "retire", "inbox", "lease", "revoke", "receipt"}:
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
        all_events = _history(conn, root, project, mission)
        events = (_history(conn, root, project, mission, scope)
                  if scope else all_events)
        receipts = {e["peer_task_key"] for e in all_events
                    if e["event_type"] == "HANDOFF_RECEIPT"}
        revoked = {e["peer_task_key"] for e in all_events
                   if e["event_type"] == "CAPABILITY_REVOKE_REQUEST"}
        leases = []
        for e in events:
            if e["event_type"] != "CAPABILITY_INTENT":
                continue
            try:
                body = json.loads(e["payload_json"])
                deadline = datetime.fromisoformat(
                    body["lease_expires_at"].replace("Z", "+00:00"))
                expired = orbit_autopilot.utc_now() >= deadline
            except (KeyError, TypeError, ValueError):
                # Corrupt saved events cannot imply a valid lease.
                expired = True
            leases.append({
                "event_key": e["event_key"], "task_key": e["task_key"],
                "intent_expired": expired,
                "host_revocation_requested": e["event_key"] in revoked,
                "host_permission_verified": False, "actual_lease_granted": False,
            })
        pending = [
            {"event_key": e["event_key"], "to_task": e["peer_task_key"],
             "host_delivered": False, "receipt_reported": False}
            for e in events if e["event_type"] == "HANDOFF_RECORDED"
            and e["event_key"] not in receipts
        ]
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
            "capability_intents": leases,
            "handoffs_without_reported_receipts": pending,
            "host_receipts_authenticated": False,
        }

    if action == "revoke":
        charter, reason = _revoke_guard(conn, root, project, a)
    else:
        charter, state, reason = orbit_autopilot._guard(conn, root, project, a)
    if reason:
        return {**common, "status": reason}
    if action == "staff":
        status, payload = _staff(conn, root, project, a, charter)
    elif action == "handoff":
        status, payload = _handoff(conn, root, project, a, charter)
    elif action == "retire":
        status, payload = _retire(conn, root, project, a, charter)
    elif action == "lease":
        status, payload = _lease(conn, root, project, a, charter)
    elif action == "revoke":
        status, payload = _revoke(conn, root, project, a, charter)
    else:
        status, payload = _receipt(conn, root, project, a, charter)
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
        if action == "revoke":
            fresh, error = _revoke_guard(conn, root, project, a)
        else:
            fresh, _, error = orbit_autopilot._guard(conn, root, project, a)
        if error or fresh != charter:
            conn.rollback()
            return {**common, "status": error or "HOLD_CHANGED_CHARTER"}
        if action == "staff":
            check, current = _staff(conn, root, project, a, fresh)
        elif action == "handoff":
            check, current = _handoff(conn, root, project, a, fresh)
        elif action == "retire":
            check, current = _retire(conn, root, project, a, fresh)
        elif action == "lease":
            check, current = _lease(conn, root, project, a, fresh)
        elif action == "revoke":
            check, current = _revoke(conn, root, project, a, fresh)
        else:
            check, current = _receipt(conn, root, project, a, fresh)
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
        if action == "lease" and any(
            e["event_type"] == "CAPABILITY_INTENT" and e["task_key"] == payload["task_key"]
            and not any(r["event_type"] == "CAPABILITY_REVOKE_REQUEST"
                        and r["peer_task_key"] == e["event_key"]
                        for r in history)
            for e in history
        ):
            conn.rollback()
            return {**common, "status": "HOLD_EXISTING_CAPABILITY_INTENT"}
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
        "lease": "CAPABILITY_INTENT_RECORDED",
        "revoke": "CAPABILITY_REVOKE_REQUEST_RECORDED",
        "receipt": "HANDOFF_RECEIPT_RECORDED",
    }[action], "state_written": True,
            "next": "Host must separately verify permission, source evidence, and worker lifecycle. No native action was performed."}
