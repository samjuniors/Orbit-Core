"""Read-only adaptive Team Builder over Orbit's existing project task ledger.

No new agent registry, chat database, host invocation, skill installation, or
permission grant. Skills and host tools are candidate hints, NOT trusted powers.
"""
from __future__ import annotations

import json

import orbit_capabilities
import orbit_delegation
import orbit_skill_plan
import orbit_tasks

MAX_TEAM_TASKS = 6
MAX_HANDOFFS = 24
LEADS = {
    "project-manager": "delivery",
    "research": "delivery",
    "writer": "delivery",
    "creative-director": "delivery",
    "ux": "delivery",
    "architect": "engineering",
    "software-engineer": "engineering",
    "frontend": "engineering",
    "backend": "engineering",
    "data": "engineering",
    "devops": "engineering",
    "integrator": "engineering",
    "qa": "quality",
    "reviewer": "quality",
    "security": "quality",
}
BOT_WORDS = frozenset({"repeatable", "repeated", "lint", "format", "snapshot",
                        "routine", "batch", "scheduled", "generated"})


def _selection(args):
    selected = args.get("tasks")
    if not isinstance(selected, list) or not 1 <= len(selected) <= MAX_TEAM_TASKS:
        raise ValueError("Choose 1..6 existing task keys with exact revisions")
    result = {}
    for item in selected:
        if not isinstance(item, dict) or set(item) - {"task_key", "expected_revision", "kind"}:
            raise ValueError("Invalid team worker selection")
        key = orbit_tasks.key(item)
        rev = item.get("expected_revision")
        kind = item.get("kind", "adaptive")
        if type(rev) is not int or rev < 1 or kind not in ("adaptive", "agent", "bot"):
            raise ValueError("Worker requires current revision and adaptive/agent/bot kind")
        if key in result:
            raise ValueError("Duplicate team worker")
        result[key] = {"revision": rev, "kind": kind}
    return result


def _worker_kind(task, requested):
    if requested != "adaptive":
        return requested, "CALLER_REQUESTED_NOT_ACTIVATED"
    words = set(task["goal"].lower().replace("-", " ").split())
    if task["role"] in {"qa", "writer", "devops", "research"} and words & BOT_WORDS:
        return "bot", "HEURISTIC_SUGGESTION_ONLY"
    return "agent", "DEFAULT_SUGGESTION_ONLY"


def preview(conn, root, project, args):
    """Propose project-local team, skill/tool hints, and safe dependency handoffs."""
    selected = _selection(args)
    host = args.get("host", "unknown")
    if host not in orbit_skill_plan.HOSTS:
        raise ValueError("Unsupported team host")
    permission = args.get("permission_state", "UNKNOWN")
    if permission not in ("UNKNOWN", "APPROVED", "DENIED"):
        raise ValueError("Invalid reported permission state")
    tools = orbit_delegation.validate_reported_tools(
        host if host in orbit_delegation.HOST_NATIVE_TOOLS else "generic",
        args.get("available_host_tools", []))
    profile = orbit_skill_plan._profile(args.get("project_profile"))
    base = {
        "project": project,
        "project_root": str(root),
        "mode": "READ_ONLY_TEAM_BUILDER",
        "principal": "FOUNDER",
        "chief": "ORBIT",
        "lead_authority": "STAFFING_REQUEST_ONLY",
        "max_active_native_workers": orbit_tasks.MAX_CONCURRENT,
        "selected_worker_count": len(selected),
        "state_written": False,
        "worker_spawned": False,
        "bot_started": False,
        "skill_installed": False,
        "host_permission_verified": False,
        "charter_verified": False,
        "native_worker_sessions_verified": False,
        "host_tools_caller_reported": True,
        "orbit_native_invocation_hints": [
            t for t in orbit_delegation.HOST_NATIVE_TOOLS.get(host, ()) if t in tools
        ],
        "team_activation_allowed": False,
        "permission_state_caller_reported": permission,
        "coordination": "ORBIT_ROUTED_TASK_DEPENDENCIES_NOT_PEER_CHAT",
    }
    rows = {}
    for key, spec in selected.items():
        row = conn.execute(
            """SELECT task_key, role, goal, status, revision, depends_on
               FROM orbit_agent_tasks
               WHERE project=? AND project_root=? AND task_key=?""",
            (project, str(root), key)).fetchone()
        if row is None:
            return {**base, "status": "HOLD_TASK_MISSING", "task_key": key,
                    "workers": [], "handoffs": []}
        row = dict(row)
        if row["revision"] != spec["revision"]:
            return {**base, "status": "HOLD_STALE_TASK",
                    "task_key": key, "current_revision": row["revision"],
                    "workers": [], "handoffs": []}
        if row["role"] not in orbit_tasks.ROLES:
            return {**base, "status": "HOLD_UNKNOWN_ROLE",
                    "workers": [], "handoffs": []}
        try:
            deps = json.loads(row["depends_on"])
            if not isinstance(deps, list) or len(deps) > 8 or any(
                    not isinstance(d, str) or not d or len(d) > 80 for d in deps):
                raise ValueError("Invalid stored task dependency")
        except (ValueError, TypeError):
            return {**base, "status": "HOLD_INVALID_DEPENDENCIES",
                    "workers": [], "handoffs": []}
        row["depends_on"] = deps
        rows[key] = row

    # Reuse the same existing skill scanner and versioned integrity planner.
    # Skill metadata/description remains untrusted; do not expose raw instructions.
    available = orbit_capabilities.discover(root)
    chosen_kinds = {}
    workers = []
    for key in sorted(rows):
        row = rows[key]
        requested = selected[key]["kind"]
        kind, kind_source = _worker_kind(row, requested)
        chosen_kinds[key] = kind
        objective = row["role"] + ": " + row["goal"][:1350]
        skill = orbit_skill_plan.preview(
            root, objective, available, project_profile=profile,
            permission_state=permission, host=host)
        workers.append({
            "task_key": key, "revision": row["revision"],
            "task_status": row["status"],
            "role": row["role"], "lead": LEADS[row["role"]],
            "proposed_kind": kind, "kind_basis": kind_source,
            "profile_policy": "REUSE_EXISTING_HOST_OR_ORBIT_PROFILE_FIRST",
            "candidate_skill_names": [s["name"] for s in skill["shortlist"]],
            "candidate_skill_pins": skill["manifest"],
            "skill_status": skill["status"],
            "skill_fitness_verified": False,
            "worker_tool_grants": [],
            "worker_tool_intents": "REQUIRES_INDEPENDENT_TASK_CAPABILITY_REVIEW",
            "tool_permission_verified": False,
            "staffing_action": "ORBIT_CHARTER_AND_HOST_REVIEW_REQUIRED",
            "spawn_allowed": False,
            "retire_action": "ONLY_AFTER_HOST_CONFIRMED_TERMINATION",
        })

    # Derived solely from existing same-project ledger dependencies, not a
    # hidden worker-to-worker message bus or unbounded AI conversation.
    handoffs = []
    for key in sorted(rows):
        for dependency in rows[key]["depends_on"]:
            source = rows.get(dependency)
            if source is None:
                source_row = conn.execute(
                    """SELECT status FROM orbit_agent_tasks
                       WHERE project=? AND project_root=? AND task_key=?""",
                    (project, str(root), dependency)).fetchone()
                source_status = source_row["status"] if source_row else "MISSING"
                channel = "ORBIT_TO_WORKER"
            else:
                source_status = source["status"]
                channel = (chosen_kinds[dependency].upper() + "_TO_" +
                           chosen_kinds[key].upper())
            handoffs.append({
                "from_task": dependency, "to_task": key,
                "channel": channel,
                "via": "ORBIT_TASK_LEDGER",
                "upstream_status": source_status,
                "gate": ("REVIEWABLE_HANDOFF" if source_status == "REVIEW_ACCEPTED"
                         else "HOLD_UPSTREAM_REVIEW"),
                "message_sent": False,
                "content_trusted": False,
                "host_delivery_allowed": False,
                "separate_host_authorization_required": True,
            })
            if len(handoffs) > MAX_HANDOFFS:
                return {**base, "status": "HOLD_HANDOFF_BUDGET",
                        "workers": [], "handoffs": []}

    return {
        **base,
        "status": ("HOLD_PERMISSION_DENIED" if permission == "DENIED"
                   else "TEAM_REVIEW_READY"),
        "workers": workers,
        "handoffs": handoffs,
        "next": ("Review existing native workers, pinned skill candidates, "
                 "actual host permissions and mission charter. Route reviewed "
                 "task evidence via Orbit; never run or message workers from "
                 "this read-only plan."),
    }
