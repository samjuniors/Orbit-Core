"""Read-only integration readiness over actual source bytes and local QA records.

This is a pre-review guard for a bounded Swarm batch, not a test runner or
publisher attestations. Host-reported task and browser metadata remain
untrusted until a human/host independently inspects execution and Git diffs.
"""
from __future__ import annotations

import json
import re

import orbit_build
import orbit_tasks


def review(conn, root, project, args):
    choices = args["tasks"]
    if not isinstance(choices, list) or not 1 <= len(choices) <= 12:
        raise ValueError("Select 1..12 tasks for integration review")
    selected = {}
    for choice in choices:
        if not isinstance(choice, dict):
            raise ValueError("Each task selection must be an object")
        key = orbit_tasks.key(choice)
        revision = choice.get("expected_revision")
        if type(revision) is not int or revision < 1:
            raise ValueError("Expected a positive integer task revision")
        if key in selected:
            raise ValueError("Duplicate selected task key")
        selected[key] = revision

    expected = args["expected_source_fingerprint"]
    if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise ValueError("expected_source_fingerprint must be lowercase SHA-256")
    base = {
        "project": project, "project_root": str(root),
        "task_count": len(selected), "task_keys": sorted(selected),
        "mode": "READ_ONLY_INTEGRATION_REVIEW",
        "state_written": False, "agent_spawned": False,
        "git_diff_verified": False, "tests_independently_verified": False,
        "host_permission_verified": False, "approval_verified": False,
        "source_identity_kind": "BOUNDED_LOCAL_FILES_FINGERPRINT",
        "source_identity_is_git_commit": False,
        "qa_record_host_reported": True,
        "next": ("Independently inspect actual Git changes, tests, host agent "
                 "sessions and user approval. Do not merge or accept based only "
                 "on local ledger states or a stored browser record."),
    }
    # Even a perfect stored QA record must not certify a workspace in which
    # another native worker may still be editing. Never expose the other
    # project's task/session identities in this scope-wide safeguard.
    active = conn.execute(
        "SELECT COUNT(*) FROM orbit_agent_tasks "
        "WHERE project_root=? AND status IN ('RESERVED','RUNNING')",
        (str(root),)).fetchone()[0]
    if active:
        return {**base, "status": "HOLD_HOST_RECONCILIATION",
                "active_records_same_root": active,
                "reason": "Inspect and reconcile active host sessions before integration."}

    fingerprint = orbit_build.code_fingerprint(root)
    if fingerprint is None:
        return {**base, "status": "HOLD_SOURCE_UNSCANNABLE",
                "source_matches": False,
                "reason": "A bounded non-symlinked source snapshot was unavailable."}
    if fingerprint != expected:
        return {**base, "status": "HOLD_STALE_SOURCE",
                "source_matches": False,
                "reason": "Source files changed after the reviewed fingerprint. Rerun QA."}

    issues = []
    for key in sorted(selected):
        row = conn.execute(
            "SELECT revision,status,write_paths,changed_paths,depends_on "
            "FROM orbit_agent_tasks WHERE project=? AND project_root=? AND task_key=?",
            (project, str(root), key)).fetchone()
        if row is None:
            issues.append({"task_key": key, "reason": "MISSING_TASK"})
            continue
        if row["revision"] != selected[key]:
            issues.append({"task_key": key, "reason": "STALE_TASK_REVISION",
                           "current_revision": row["revision"]})
            continue
        if row["status"] != "REVIEW_ACCEPTED":
            issues.append({"task_key": key, "reason": "TASK_REVIEW_REQUIRED",
                           "recorded_status": row["status"]})
            continue
        try:
            assigned = orbit_tasks._scopes(json.loads(row["write_paths"]))
            changed = orbit_tasks._scopes(
                json.loads(row["changed_paths"]), limit=60, allow_protected=True)
            assigned_resolved = orbit_tasks._resolved_scopes(root, assigned)
            changed_resolved = orbit_tasks._resolved_scopes(root, changed)
            scope = orbit_tasks.scope_report(assigned, changed)
            resolved_scope = orbit_tasks.scope_report(assigned_resolved, changed_resolved)
            deps = json.loads(row["depends_on"])
            if not isinstance(deps, list) or len(deps) > 8 or any(
                    not isinstance(dep, str) for dep in deps):
                raise ValueError("Invalid dependency data")
        except (TypeError, ValueError, json.JSONDecodeError):
            issues.append({"task_key": key, "reason": "INVALID_TASK_RECORD"})
            continue
        if not scope["allowed"] or not resolved_scope["allowed"]:
            issues.append({"task_key": key, "reason": "UNSAFE_CHANGED_PATHS"})
            continue
        for dep in deps:
            state = conn.execute(
                "SELECT status FROM orbit_agent_tasks "
                "WHERE project=? AND project_root=? AND task_key=?",
                (project, str(root), dep)).fetchone()
            if not state or state["status"] != "REVIEW_ACCEPTED":
                issues.append({"task_key": key, "reason": "DEPENDENCY_REVIEW_REQUIRED"})
                break
    if issues:
        return {**base, "status": "HOLD_TASK_INTEGRATION",
                "source_matches": True, "issues": issues,
                "next": "Resolve scoped task revisions, review statuses and path violations before integration QA."}

    build_id = args.get("build_id")
    if build_id is None:
        return {**base, "status": "HOLD_INDEPENDENT_QA",
                "source_matches": True,
                "reason": "Provide an existing web build with recorded source-bound browser QA; native/mobile QA still requires separate host-verified evidence."}
    orbit_build.validate_key(build_id)
    if not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='browser_results'"
    ).fetchone():
        return {**base, "status": "HOLD_INDEPENDENT_QA",
                "source_matches": True,
                "reason": "No local QA record table exists for this project."}
    if not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='build_runs'"
    ).fetchone():
        return {**base, "status": "HOLD_INDEPENDENT_QA",
                "source_matches": True,
                "reason": "No matching build record is available."}
    build = conn.execute(
        "SELECT revision,stage FROM build_runs "
        "WHERE project=? AND root=? AND build_id=?",
        (project, str(root), build_id)).fetchone()
    if build is None:
        return {**base, "status": "HOLD_INDEPENDENT_QA",
                "source_matches": True,
                "reason": "This exact project has no such build."}
    row = conn.execute(
        "SELECT status,summary FROM browser_results "
        "WHERE project=? AND root=? AND build_id=? ORDER BY id DESC LIMIT 1",
        (project, str(root), build_id)).fetchone()
    if row is None or row["status"] != "PASS":
        return {**base, "status": "HOLD_INDEPENDENT_QA",
                "source_matches": True,
                "reason": "Latest recorded browser run is missing or not passing."}
    try:
        qa = json.loads(row["summary"])
        actions = qa["actions"]
        correct = (isinstance(qa, dict)
                   and qa.get("source_fingerprint") == fingerprint
                   and isinstance(qa.get("qa_build_revision"), int)
                   and qa["qa_build_revision"] >= 1
                   and isinstance(qa.get("preview_id"), str)
                   and bool(qa["preview_id"])
                   and isinstance(qa.get("preview_started_at"), (int, float))
                   and not isinstance(qa.get("preview_started_at"), bool)
                   and isinstance(actions, list) and bool(actions)
                   and all(isinstance(action, dict) and action.get("status") == "PASS"
                           for action in actions)
                   and not qa.get("errors") and not qa.get("failures")
                   and not qa.get("blocked_remote_hosts"))
    except (ValueError, TypeError, KeyError):
        correct = False
    if not correct:
        return {**base, "status": "HOLD_STALE_OR_INVALID_QA",
                "source_matches": True,
                "reason": "Latest browser QA is stale, malformed, or lacks successful interactive evidence."}
    return {**base, "status": "READY_FOR_INDEPENDENT_REVIEW",
            "source_matches": True, "recorded_browser_qa_matches_source": True,
            "recorded_qa_build_id": build_id, "recorded_build_stage": build["stage"],
            "reason": ("Local records match the current bounded source snapshot. "
                       "The host must still independently inspect actual Git "
                       "diffs, browser/test execution and integrated behavior."),
            "merge_performed": False}
