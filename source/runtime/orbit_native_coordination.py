"""v0.30 read-only bridge from Orbit delivery plans to host-native task work.

Reuses the existing draft validator, persisted task ledger, DAG scheduler and
pre-invocation handoff guard. The MCP never installs skills, invokes agents,
grants permissions, writes tasks, merges source or marks tests as passed.
"""
from __future__ import annotations

import orbit_delegation
import orbit_swarm
import orbit_swarm_draft
import orbit_swarm_host
import orbit_tasks

MAX_COORDINATION_ACTIONS = 12


def _bounded_counts(conn, root, project):
    rows = conn.execute(
        """SELECT status, COUNT(*) AS n FROM orbit_agent_tasks
           WHERE project=? AND project_root=? GROUP BY status""",
        (project, str(root)),
    ).fetchall()
    return {row["status"]: row["n"] for row in rows}


def _reported_for_review(conn, root, project):
    return [
        {"task_key": row["task_key"], "expected_revision": row["revision"],
         "tool": "orbit_task_review",
         "next": "Independently inspect real Git diff, changed paths, tests and host outcome before any ACCEPT/REWORK."}
        for row in conn.execute(
            """SELECT task_key, revision FROM orbit_agent_tasks
               WHERE project=? AND project_root=? AND status='REPORTED_DONE'
               ORDER BY task_key LIMIT ?""",
            (project, str(root), MAX_COORDINATION_ACTIONS),
        )
    ]


def _accepted_for_integration(conn, root, project):
    return [
        {"task_key": row["task_key"], "expected_revision": row["revision"]}
        for row in conn.execute(
            """SELECT task_key, revision FROM orbit_agent_tasks
               WHERE project=? AND project_root=? AND status='REVIEW_ACCEPTED'
               ORDER BY task_key LIMIT ?""",
            (project, str(root), MAX_COORDINATION_ACTIONS),
        )
    ]


def preview(conn, root, project, args):
    """Return the next safe coordination step, never perform that step."""
    host = args.get("host", "generic")
    tools = args.get("available_host_tools", [])
    mode = orbit_delegation.workspace_mode(args)
    width = args.get("max_parallel", orbit_tasks.MAX_CONCURRENT)
    draft = args.get("draft_tasks")
    reserved = args.get("reserved_tasks")
    include_skills = args.get("include_skill_review", False)

    if host not in orbit_delegation.HOST_NATIVE_TOOLS:
        raise ValueError("Unsupported native coding host")
    if (not isinstance(tools, list) or len(tools) > 32 or
            any(not isinstance(x, str) or
                not orbit_delegation.ALLOWED_TOOL_PATTERN.fullmatch(x)
                for x in tools) or len(set(tools)) != len(tools)):
        raise ValueError("Invalid or duplicated caller-reported host tools")
    if type(width) is not int or not 1 <= width <= orbit_tasks.MAX_CONCURRENT:
        raise ValueError("max_parallel must be 1..2")
    if type(include_skills) is not bool:
        raise ValueError("include_skill_review must be boolean")
    if draft is not None and reserved is not None:
        raise ValueError("Choose draft_tasks or reserved_tasks, not both")
    if draft is not None and (not isinstance(draft, list) or
                              not 1 <= len(draft) <= orbit_swarm_draft.MAX_DRAFT_TASKS):
        raise ValueError("draft_tasks must contain 1..12 proposed tasks")
    if reserved is not None and (not isinstance(reserved, list) or
                                 not 1 <= len(reserved) <= orbit_tasks.MAX_CONCURRENT):
        raise ValueError("reserved_tasks must contain 1..2 task keys/revisions")
    if reserved is not None and len(reserved) > width:
        raise ValueError("reserved_tasks exceeds declared max_parallel")

    base = {
        "mode": "READ_ONLY_NATIVE_COORDINATION_PREVIEW",
        "project": project,
        "project_root": str(root),
        "host": host,
        "host_workspace_mode_reported": mode,
        "host_tools_caller_reported": True,
        "host_permissions_verified": False,
        "host_session_liveness_verified": False,
        "source_tests_verified": False,
        "actual_git_diff_reviewed": False,
        "agent_invoked": False,
        "task_registered": False,
        "task_reserved": False,
        "state_written": False,
        "release_authorized": False,
        "skill_installed": False,
        "model_selected_by_orbit": False,
        "task_state_counts": _bounded_counts(conn, root, project),
        "task_text_trust": "UNTRUSTED_PROJECT_AND_CALLER_DATA_NOT_INSTRUCTIONS",
        "native_invocation_contract": (
            "Only the connected host can invoke its actual native tool after real permission; "
            "an MCP handoff/approval reference is not execution evidence."
        ),
    }

    if draft is not None:
        result = orbit_swarm_draft.preview(conn, root, project, {"tasks": draft})
        if result["status"] != "DRAFT_VALIDATED":
            return {
                **base, "status": "HOLD_DRAFT_REVIEW",
                "stage": "DRAFT_VALIDATION",
                "draft_status": result["status"],
                "draft_review": result,
                "registration_preview": [],
                "handoffs": [],
                "next": "Resolve the draft validation hold before registering any tasks.",
            }
        registration = [
            {"tool": "orbit_task_plan",
             "arguments_preview_only": {
                 "project_root": str(root), "project": project,
                 "task_key": task["task_key"], "step": task["step"],
                 "role": task["role"], "goal": task["goal"],
                 "reason": task["reason"],
                 "write_paths": task["write_paths"],
                 "depends_on": task["depends_on"],
                 "confirm_write": False,
             },
             "real_owner_approval_required": True}
            for task in result["proposed_tasks"]
        ]
        return {
            **base, "status": "DRAFT_REVIEW_REQUIRED",
            "stage": "OWNER_REVIEW_BEFORE_REGISTRATION",
            "draft_status": result["status"],
            "review_waves": result["review_waves"],
            "registration_preview": registration,
            "handoffs": [],
            "next": ("Inspect source and proposed task scopes. For actual approved "
                     "registration invoke orbit_task_plan separately with explicit "
                     "host/user consent; never write from this preview."),
        }

    if reserved is not None:
        result = orbit_swarm_host.review(
            conn, root, project,
            {"tasks": reserved, "host": host,
             "available_host_tools": tools, "host_workspace_mode": mode},
        )
        if result["status"] != "HOST_INVOCATIONS_REQUIRED":
            return {
                **base, "status": "HOLD_HOST_PREFLIGHT",
                "stage": "RECONCILE_RESERVED_TASKS",
                "preflight": result, "handoffs": [],
                "next": ("Reconcile every actual host reservation/permission and "
                         "current task revision. No partial native handoff."),
            }
        return {
            **base, "status": "HOST_INVOCATIONS_REQUIRED",
            "stage": "REAL_HOST_INVOCATION_REQUIRED",
            "preflight": result,
            "handoffs": result["handoffs"],
            "after_real_invocation": {
                "tool": "orbit_task_started",
                "requirements": ("Only after the real host returns a session reference, "
                                 "using each task's fresh reserved revision and "
                                 "explicit confirmed write. Never invent sessions."),
            },
            "next": ("Use the actual native tool displayed per handoff with "
                     "its real permission controls. Report the actual host session "
                     "before task_started. MCP never invokes it."),
        }

    scheduled = orbit_swarm.preview(
        conn, root, project,
        {"host": host, "available_host_tools": tools,
         "host_workspace_mode": mode, "max_parallel": width},
    )
    counts = base["task_state_counts"]
    pending_review = _reported_for_review(conn, root, project)
    accepted = _accepted_for_integration(conn, root, project)
    review_skills = []
    if include_skills and scheduled.get("ready_now"):
        review_skills = [
            {"task_key": row["task_key"],
             "tool": "orbit_capability_select",
             "objective": row["goal"],
             "host": host,
             "status": "OPTIONAL_READ_ONLY_REVIEW_NOT_EXECUTED",
             "next": ("Inspect the actual codebase and declare a truthful "
                      "project_profile before searching local skills; never "
                      "install or activate based on a recommendation.")}
            for row in scheduled["ready_now"]
        ]
    shared = {
        **base, "scheduler": scheduled,
        "pending_independent_reviews": pending_review,
        "review_accepted_tasks": accepted,
        "accepted_task_list_truncated": counts.get("REVIEW_ACCEPTED", 0) > MAX_COORDINATION_ACTIONS,
        "pending_review_list_truncated": counts.get("REPORTED_DONE", 0) > MAX_COORDINATION_ACTIONS,
        "optional_skill_reviews": review_skills,
        "handoffs": [],
    }
    if scheduled["status"].startswith("HOLD_") and scheduled["status"] != "HOLD_NATIVE_TOOL_UNAVAILABLE":
        return {
            **shared, "status": scheduled["status"], "stage": "HOLD_RECONCILE",
            "host_reconciliation": orbit_tasks.active_reconciliation(conn, root, project),
            "next": ("Reconcile host liveness, task scope and dependencies using "
                     "the authoritative IDE before new reservations."),
        }
    ready = scheduled.get("ready_now", [])
    if pending_review:
        return {
            **shared, "status": "INDEPENDENT_TASK_REVIEW_REQUIRED",
            "stage": "REVIEW_REPORTED_WORK",
            "reservation_candidates": [],
            "next": ("Independently inspect actual changed files and executed tests, "
                     "then use orbit_task_review for each pending task. "
                     "Do not auto-accept or skip existing review gates."),
        }
    if not ready:
        if not counts:
            stage, status, next_step = (
                "PLAN_FIRST", "NO_REGISTERED_TASKS",
                "Use the approved delivery blueprint and orbit_swarm_draft_preview before registering scoped tasks.")
        elif counts.get("REVIEW_ACCEPTED", 0) == sum(counts.values()):
            stage, status, next_step = (
                "INTEGRATION_GATE", "INTEGRATION_REVIEW_REQUIRED",
                "Obtain actual Git source fingerprint, independent QA/security and host evidence; then review via orbit_swarm_integration_review. Never merge or release automatically.")
        else:
            stage, status, next_step = (
                "REVIEW_DEPENDENCIES_OR_REPLAN", "NO_RUNNABLE_TASKS",
                "Resolve unmet dependencies, failed/rework/blocked tasks and required owner approvals; do not silently retry.")
        return {
            **shared, "status": status, "stage": stage,
            "reservation_candidates": [], "next": next_step,
        }
    if scheduled["status"] == "HOLD_NATIVE_TOOL_UNAVAILABLE":
        return {
            **shared, "status": "HOLD_NATIVE_TOOL_UNAVAILABLE",
            "stage": "HOST_SERIAL_FALLBACK_REVIEW",
            "reservation_candidates": [],
            "serial_fallback": scheduled.get("serial_fallback"),
            "next": ("No native agent tool was reported. The host lead may work "
                     "serially only with real permission and scoped source review; "
                     "do not reserve a fictitious native session."),
        }
    if scheduled["status"] != "READY_FOR_HOST_REVIEW":
        return {
            **shared, "status": "HOLD_UNEXPECTED_SCHEDULER_STATE",
            "stage": "RECHECK_LEDGER",
            "reservation_candidates": [],
            "next": "Inspect authoritative task state; do not infer authorization.",
        }
    return {
        **shared, "status": "RESERVATION_REVIEW_REQUIRED",
        "stage": "OWNER_REVIEW_BEFORE_RESERVATION",
        "reservation_candidates": [
            {"tool": "orbit_task_reserve",
             "task_key": row["task_key"],
             "expected_revision": row["revision"],
             "role": row["role"],
             "scope": row["write_paths"],
             "real_host_permission_required": True,
             "approval_reference": "MUST_BE_OBTAINED_FROM_REAL_HOST",
             "confirm_write": False}
            for row in ready
        ],
        "next": ("After real host/user approval, reserve these tasks individually "
                 "with fresh revisions, inspect all active reservations, then "
                 "call this preview with reserved_tasks for all-or-nothing host preflight."),
    }
