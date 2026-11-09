"""Orbit Autopilot Phase 1: bounded project mission charter and safe next-step review.

A saved approval_reference is CALLER-REPORTED; an MCP cannot authenticate the
founder, host permission, native model, Git branch or test execution. No
background worker, native subagent, Git operation or user project code runs here.
The active mission only permits read-only suggestions for host-side review.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone

import orbit_swarm
import orbit_tasks

DECISIONS = frozenset({
    "task_order", "implementation_detail", "ui_polish", "bounded_retry",
})
FOUNDER_ONLY = frozenset({
    "roadmap_change", "scope_expansion", "dependency_install", "credential_access",
    "new_spend", "permission_change", "data_deletion", "security_policy_change",
    "merge", "release", "deploy",
})
STATES = frozenset({"ACTIVE", "PAUSED", "STOPPED"})
MAX_MISSION_TASKS = 12


def utc_now():
    return datetime.now(timezone.utc)


def _timestamp():
    return utc_now().isoformat(timespec="seconds")


def setup(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS orbit_autopilot_missions (
        project TEXT NOT NULL, project_root TEXT NOT NULL, mission_id TEXT NOT NULL,
        state TEXT NOT NULL, revision INTEGER NOT NULL,
        charter_json TEXT NOT NULL, approval_reference TEXT NOT NULL,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        PRIMARY KEY (project, project_root, mission_id)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS orbit_autopilot_events (
        project TEXT NOT NULL, project_root TEXT NOT NULL, mission_id TEXT NOT NULL,
        revision INTEGER NOT NULL, action TEXT NOT NULL,
        occurred_at TEXT NOT NULL,
        PRIMARY KEY (project, project_root, mission_id, revision)
    )""")
    conn.commit()


def _bounded(value, name, low, high):
    if not isinstance(value, str) or not low <= len(value.strip()) <= high:
        raise ValueError(name + " must contain bounded text")
    return value.strip()


def _mission_id(a):
    name = _bounded(a.get("mission_id"), "mission_id", 1, 80)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", name):
        raise ValueError("Invalid mission_id")
    return name


def _branch(value):
    name = _bounded(value, "branch", 6, 150)
    if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", name)
            or ".." in name or "//" in name or name.endswith((".lock", "/", "."))
            or not name.startswith(("feat/", "fix/", "dev/", "autopilot/", "test/"))):
        raise ValueError("Autopilot requires a bounded non-protected feature branch")
    return name


def _expiry(value):
    value = _bounded(value, "expires_at", 20, 20)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        raise ValueError("expires_at must be UTC YYYY-MM-DDTHH:MM:SSZ")
    try:
        expires = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("Invalid expires_at timestamp") from None
    now = utc_now()
    if not now < expires <= now + timedelta(days=30):
        raise ValueError("Charter expiry must be in the next 30 days")
    return value


def _digest(body):
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _within(path, allowed):
    norm = orbit_tasks._norm(path)
    return any(norm == orbit_tasks._norm(scope) or
               (scope.endswith("/") and norm.startswith(orbit_tasks._norm(scope)))
               for scope in allowed)


def _registered_specs(conn, root, project, keys, allowed_paths):
    """Bind an entire mission to the already-registered immutable task scope.

    Existing tasks can advance statuses/revisions without invalidating the
    mission, but changed goals, owners, paths or dependencies HOLD it.
    """
    rows = []
    permitted = orbit_tasks._scopes(allowed_paths)
    resolved_permitted = orbit_tasks._resolved_scopes(root, permitted)
    for key in keys:
        item = conn.execute(
            """SELECT task_key,step,role,goal,reason,write_paths,depends_on
               FROM orbit_agent_tasks
               WHERE project=? AND project_root=? AND task_key=?""",
            (project, str(root), key),
        ).fetchone()
        if item is None:
            raise ValueError("Mission task not registered in selected project: " + key)
        task = dict(item)
        try:
            writes = orbit_tasks._scopes(json.loads(task["write_paths"]))
            deps = json.loads(task["depends_on"])
        except (ValueError, TypeError, json.JSONDecodeError):
            raise ValueError("Invalid existing task scope/dependencies") from None
        if not isinstance(deps, list) or any(dep not in keys for dep in deps):
            raise ValueError("Every task dependency must belong to the charter")
        resolved = orbit_tasks._resolved_scopes(root, writes)
        if any(not _within(path, permitted) for path in writes):
            raise ValueError("Mission writable scope does not cover the registered task")
        if any(not _within(path, resolved_permitted) for path in resolved):
            raise ValueError("Mission resolved writable scope does not cover the task")
        rows.append({k: task[k] for k in ("task_key", "step", "role", "goal", "reason")}
                    | {"write_paths": writes, "depends_on": deps,
                       "resolved_write_paths": resolved})
    return _digest(sorted(rows, key=lambda row: row["task_key"])), resolved_permitted


def _charter(conn, root, project, a):
    objective = _bounded(a.get("objective"), "objective", 24, 750)
    roadmap_ref = _bounded(a.get("roadmap_ref"), "roadmap_ref", 8, 220)
    roadmap_revision = _bounded(a.get("roadmap_revision"), "roadmap_revision", 8, 128)
    branch = _branch(a.get("branch"))
    expires_at = _expiry(a.get("expires_at"))
    keys = a.get("task_keys")
    if (not isinstance(keys, list) or not 1 <= len(keys) <= MAX_MISSION_TASKS
            or any(not isinstance(key, str) or
                   not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", key)
                   for key in keys) or len(keys) != len(set(keys))):
        raise ValueError("Charter requires 1..12 unique existing task keys")
    paths = orbit_tasks._scopes(a.get("allowed_paths", []))
    if len(paths) > 24:
        raise ValueError("Too many writable paths")
    decisions = a.get("allowed_decisions")
    if (not isinstance(decisions, list) or not decisions or
            len(decisions) != len(set(decisions)) or set(decisions) - DECISIONS):
        raise ValueError("Allowed decisions must be a nonempty subset of low-risk choices")
    concurrency = a.get("max_parallel", 1)
    retries = a.get("max_attempts_per_task", 1)
    if type(concurrency) is not int or not 1 <= concurrency <= 2:
        raise ValueError("max_parallel must be 1..2")
    if type(retries) is not int or not 1 <= retries <= 3:
        raise ValueError("max_attempts_per_task must be 1..3")
    signature, resolved = _registered_specs(conn, root, project, sorted(keys), paths)
    return {
        "objective": objective, "roadmap_ref": roadmap_ref,
        "roadmap_revision_reported": roadmap_revision, "branch": branch,
        "expires_at": expires_at, "task_keys": sorted(keys),
        "allowed_paths": paths, "resolved_allowed_paths": resolved,
        "allowed_decisions": sorted(decisions), "max_parallel": concurrency,
        "max_attempts_per_task": retries, "task_spec_fingerprint": signature,
        "irreversible_actions_allowed": False, "host_permissions_granted": False,
        "autonomous_runner_enabled": False,
    }


def _load(conn, root, project, mission):
    row = conn.execute(
        """SELECT * FROM orbit_autopilot_missions
           WHERE project=? AND project_root=? AND mission_id=?""",
        (project, str(root), mission),
    ).fetchone()
    return dict(row) if row else None


def _public(row):
    if row is None:
        return {"status": "NO_MISSION", "approval_authenticated": False,
                "execution_allowed": False, "agent_invoked": False}
    body = json.loads(row["charter_json"])
    now = utc_now()
    expiry = datetime.fromisoformat(body["expires_at"].replace("Z", "+00:00"))
    effective = "EXPIRED" if row["state"] == "ACTIVE" and now >= expiry else row["state"]
    return {
        "status": effective, "recorded_state": row["state"], "revision": row["revision"],
        "project": row["project"], "project_root": row["project_root"],
        "mission_id": row["mission_id"], "charter": body,
        "owner_approval_reference_caller_reported": bool(row["approval_reference"]),
        "approval_authenticated": False, "host_permissions_verified": False,
        "execution_allowed": False, "agent_invoked": False, "state_written": False,
        "note": "Mission charter records only caller-reported approval. Real host, owner and tool permissions remain mandatory.",
    }


def charter(conn, root, project, a):
    mission = _mission_id(a)
    action = a.get("action")
    if action not in {"preview", "activate", "status", "pause", "resume", "stop"}:
        raise ValueError("Invalid charter action")
    row = _load(conn, root, project, mission)
    if action == "status":
        return _public(row)
    if action in {"preview", "activate"}:
        body = _charter(conn, root, project, a)
        digest = _digest(body)
        if row is not None:
            return {**_public(row), "status": "HOLD_MISSION_ID_ALREADY_USED",
                    "state_written": False}
        if action == "preview" or a.get("confirm_write") is not True:
            return {"status": "PREVIEW_ONLY", "mission_id": mission,
                    "charter": body, "charter_digest": digest,
                    "approval_authenticated": False, "execution_allowed": False,
                    "state_written": False, "next": "Review the bound tasks, path/branch limits, expiration and host permission policy before activation."}
        if a.get("expected_digest") != digest:
            raise ValueError("Approved charter digest mismatch: preview again before activation")
        approval = _bounded(a.get("approval_reference"), "approval_reference", 8, 200)
        # Approval strings are not proof of consent. All writes stay local
        # and do not change any host/agent or task execution state.
        conn.execute("BEGIN IMMEDIATE")
        try:
            if _load(conn, root, project, mission):
                conn.rollback()
                return {"status": "HOLD_MISSION_ID_ALREADY_USED", "state_written": False}
            other = conn.execute(
                """SELECT 1 FROM orbit_autopilot_missions
                   WHERE project_root=? AND state IN ('ACTIVE','PAUSED')
                   LIMIT 1""", (str(root),),
            ).fetchone()
            if other:
                conn.rollback()
                return {"status": "HOLD_EXISTING_MISSION_IN_WORKSPACE", "state_written": False}
            active = conn.execute(
                """SELECT 1 FROM orbit_agent_tasks
                   WHERE project_root=? AND status IN ('RESERVED','RUNNING') LIMIT 1""",
                (str(root),),
            ).fetchone()
            if active:
                conn.rollback()
                return {"status": "HOLD_HOST_RECONCILIATION", "state_written": False}
            current = _charter(conn, root, project, a)
            if _digest(current) != digest:
                conn.rollback()
                return {"status": "HOLD_CHARTER_CHANGED", "state_written": False}
            when = _timestamp()
            conn.execute(
                """INSERT INTO orbit_autopilot_missions
                   (project, project_root, mission_id, state, revision,
                    charter_json, approval_reference, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (project, str(root), mission, "ACTIVE", 1,
                 json.dumps(body, sort_keys=True), approval, when, when),
            )
            conn.execute(
                """INSERT INTO orbit_autopilot_events
                   (project,project_root,mission_id,revision,action,occurred_at)
                   VALUES (?,?,?,?,?,?)""",
                (project, str(root), mission, 1, "ACTIVATE", when),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        return {**_public(_load(conn, root, project, mission)),
                "status": "CHARTER_RECORDED",
                "state_written": True, "next": "Use read-only orbit_autopilot_next. No host agent, scheduler or permission was enabled."}

    if row is None:
        return {**_public(row), "status": "HOLD_MISSION_NOT_FOUND"}
    expected = a.get("expected_revision")
    if type(expected) is not int or expected != row["revision"]:
        return {**_public(row), "status": "HOLD_STALE_REVISION"}
    state = row["state"]
    if action == "pause" and state != "ACTIVE":
        return {**_public(row), "status": "HOLD_INVALID_TRANSITION"}
    if action == "resume" and state != "PAUSED":
        return {**_public(row), "status": "HOLD_INVALID_TRANSITION"}
    if action == "stop" and state == "STOPPED":
        return {**_public(row), "status": "ALREADY_STOPPED"}
    if action == "resume":
        deadline = datetime.fromisoformat(json.loads(row["charter_json"])["expires_at"].replace("Z", "+00:00"))
        if utc_now() >= deadline:
            return {**_public(row), "status": "HOLD_EXPIRED"}
    if a.get("confirm_write") is not True:
        return {**_public(row), "status": "PREVIEW_ONLY", "requested_action": action}
    reference = row["approval_reference"]
    if action == "resume":
        reference = _bounded(a.get("approval_reference"), "approval_reference", 8, 200)
        if reference == row["approval_reference"]:
            raise ValueError("Resume requires a fresh caller-reported approval reference")
    target = {"pause": "PAUSED", "resume": "ACTIVE", "stop": "STOPPED"}[action]
    conn.execute("BEGIN IMMEDIATE")
    try:
        now = _load(conn, root, project, mission)
        if now is None or now["revision"] != expected or now["state"] != state:
            conn.rollback()
            return {"status": "HOLD_STALE_REVISION", "state_written": False}
        timestamp = _timestamp()
        cursor = conn.execute(
            """UPDATE orbit_autopilot_missions
               SET state=?,revision=revision+1,approval_reference=?,updated_at=?
               WHERE project=? AND project_root=? AND mission_id=?
                 AND revision=? AND state=?""",
            (target, reference, timestamp, project, str(root), mission, expected, state),
        )
        if cursor.rowcount != 1:
            conn.rollback()
            return {"status": "HOLD_STALE_REVISION", "state_written": False}
        conn.execute(
            """INSERT INTO orbit_autopilot_events
               (project,project_root,mission_id,revision,action,occurred_at)
               VALUES (?,?,?,?,?,?)""",
            (project, str(root), mission, expected + 1, action.upper(), timestamp),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return {**_public(_load(conn, root, project, mission)),
            "status": target, "state_written": True,
            "next": "Host must separately verify permission and session state; this does not stop running agents."}


def _guard(conn, root, project, a):
    row = _load(conn, root, project, _mission_id(a))
    current = _public(row)
    if row is None or current["status"] != "ACTIVE":
        return None, current, "HOLD_MISSION_INACTIVE"
    if type(a.get("expected_revision")) is not int or a["expected_revision"] != row["revision"]:
        return None, current, "HOLD_STALE_REVISION"
    body = current["charter"]
    try:
        signature, resolved = _registered_specs(
            conn, root, project, body["task_keys"], body["allowed_paths"])
        if signature != body["task_spec_fingerprint"] or resolved != body["resolved_allowed_paths"]:
            return None, current, "HOLD_CHARTER_SOURCE_DRIFT"
    except (ValueError, TypeError):
        return None, current, "HOLD_CHARTER_SOURCE_DRIFT"
    if a.get("reported_branch") != body["branch"]:
        return None, current, "HOLD_BRANCH_MISMATCH"
    return body, current, None


def _attempts(conn, root, project, task):
    return conn.execute(
        """SELECT COUNT(*) FROM orbit_task_attempts
           WHERE project=? AND project_root=? AND task_key=?
             AND disposition!='RELEASED_UNUSED'""",
        (project, str(root), task),
    ).fetchone()[0]


def next_task(conn, root, project, a):
    """Safe selection against the existing DAG; never reserves or executes."""
    body, state, error = _guard(conn, root, project, a)
    base = {
        "mission_id": _mission_id(a), "project": project,
        "project_root": str(root), "execution_allowed": False,
        "native_agent_invoked": False, "host_permission_verified": False,
        "owner_approval_authenticated": False, "git_branch_verified": False,
        "run_loop_started": False, "state_written": False,
    }
    if error:
        return {**base, "status": error, "mission": state}
    # Existing Orbit scheduling validates DAG cycles, dependency review,
    # workspace read-only mode, symlinked paths and cross-project reservations.
    scheduler = orbit_swarm.preview(conn, root, project, {
        "host": a.get("host", "generic"),
        "available_host_tools": a.get("available_host_tools", []),
        "host_workspace_mode": a.get("host_workspace_mode", "unknown"),
        "max_parallel": body["max_parallel"],
    })
    if scheduler["status"] != "READY_FOR_HOST_REVIEW":
        return {**base, "status": scheduler["status"], "scheduler": scheduler,
                "next": "Resolve scheduler/host gate before continuation."}
    allowed = set(body["task_keys"])
    ready = []
    for candidate in scheduler["ready_now"]:
        if candidate["task_key"] not in allowed:
            continue
        if _attempts(conn, root, project, candidate["task_key"]) >= body["max_attempts_per_task"]:
            continue
        ready.append(candidate)
    if not ready:
        return {**base, "status": "HOLD_NO_CHARTER_READY_TASKS",
                "next": "Review approved task order, attempts and external task conflicts."}
    return {**base, "status": "NEXT_TASK_REVIEW_REQUIRED",
            "mission_revision": state["revision"],
            "ready_now": ready, "allowed_decisions": body["allowed_decisions"],
            "max_parallel": body["max_parallel"],
            "recorded_approval_only": True,
            "next": ("The signed-in coding host must independently verify Git branch, "
                     "user approval, actual tool capability, scope and permissions. "
                     "Then use normal revision-guarded Orbit task reservation and "
                     "genuine host-native invocation. Never infer consent from this response.")}


def decision(conn, root, project, a):
    """Classify a proposed choice; never execute it or make a founder override."""
    category = a.get("category")
    if category not in DECISIONS | FOUNDER_ONLY:
        raise ValueError("Unknown decision category")
    body, state, error = _guard(conn, root, project, a)
    common = {"status": "HOLD_FOUNDER_REVIEW",
              "owner_approval_authenticated": False,
              "host_permission_verified": False, "execution_allowed": False,
              "state_written": False, "decision_implemented": False,
              "category": category}
    if error:
        return {**common, "status": error}
    if category in FOUNDER_ONLY or category not in body["allowed_decisions"]:
        return {**common, "reason": "This category was not delegated within the Mission Charter."}
    task = a.get("task_key")
    if task not in body["task_keys"]:
        return {**common, "reason": "Decision targets a task outside the Mission Charter."}
    if category == "bounded_retry" and _attempts(conn, root, project, task) >= body["max_attempts_per_task"]:
        return {**common, "status": "HOLD_ATTEMPT_LIMIT"}
    return {**common, "status": "DELEGATED_DECISION_REVIEW_REQUIRED",
            "mission_revision": state["revision"],
            "task_key": task, "decision_category_allowed": True,
            "reason": "A low-risk proposal is within the recorded charter; the actual coding host must enforce permissions, evidence and review before taking any action."}
