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



QA_MODES = frozenset({"web", "native", "host"})


def _review_host_qa(build, fingerprint, build_id, qa_mode, base):
    """Inspect existing source-pinned build evidence; never execute host tests.

    Native mode requires the real NATIVE_QA lifecycle stage (mobile/desktop).
    Host mode uses the existing structured VERIFY stage of CLI/libraries,
    scoped fixes and other products without a browser/native QA stage.
    """
    stage_name = "NATIVE_QA" if qa_mode == "native" else "VERIFY"
    flow = orbit_build.flow_for(build)
    if (stage_name not in flow
            or (qa_mode == "native" and "BROWSER_QA" in flow)
            or (qa_mode == "host"
                and ("NATIVE_QA" in flow or "BROWSER_QA" in flow))):
        return {**base, "status": "HOLD_QA_MODE_MISMATCH",
                "source_matches": True,
                "reason": "This build flow does not support the requested host QA mode; inspect the actual approved product lifecycle."}
    if flow.index(build["stage"]) <= flow.index(stage_name):
        return {**base, "status": "HOLD_HOST_QA_STAGE",
                "source_matches": True,
                "recorded_build_stage": build["stage"],
                "reason": "Host QA must be reported and advanced in the same build before integration review."}
    try:
        saved = json.loads(build["evidence_json"])
        report = saved[stage_name] if isinstance(saved, dict) else None
        if not isinstance(report, dict):
            raise ValueError("Missing structured host QA report")
        qa_revision = report.get("qa_build_revision")
        evidence = report.get("evidence")
        valid = (
            report.get("outcome") == "PASS"
            and report.get("verification") == "caller-reported-not-attested"
            and report.get("source_identity_kind") ==
                "BOUNDED_LOCAL_FILES_FINGERPRINT"
            and report.get("source_fingerprint") == fingerprint
            and type(qa_revision) is int and qa_revision >= 1
            and qa_revision < build["revision"]
            and report.get("evidence_independently_verified") is False
            and report.get("host_execution_attested") is False
            and isinstance(evidence, str)
            and orbit_build.valid_stage_evidence(stage_name, evidence)
            and not any(isinstance(note, dict) and note.get("status") == "OPEN"
                        for note in saved.get("__orbit_feedback", []))
        )
        if not valid:
            raise ValueError("Host QA source or revision is stale")
        details = json.loads(evidence)
    except (KeyError, TypeError, ValueError, AttributeError):
        return {**base, "status": "HOLD_STALE_OR_INVALID_QA",
                "source_matches": True,
                "reason": ("Missing, malformed, unpinned or stale host-reported "
                           "QA. Re-run checks in the real host and record "
                           "evidence against the current source and build revision.")}
    result = {
        **base, "status": "READY_FOR_INDEPENDENT_REVIEW",
        "source_matches": True,
        "qa_mode": qa_mode,
        "recorded_qa_stage": stage_name,
        "recorded_qa_build_id": build_id,
        "recorded_build_stage": build["stage"],
        "recorded_host_qa_source_matches": True,
        "recorded_host_qa_reported_commands": len(details["commands"]),
        "host_qa_reporter_unverified": True,
        "actual_platform_execution_verified": False,
        "host_test_results_independently_verified": False,
        "merge_performed": False,
        "reason": ("The selected project's host-reported QA record is "
                   "structurally complete and bound to the current source and "
                   "build revision. Independently inspect actual OS/device/SDK "
                   "sessions, commands, exit codes, code diffs, permissions "
                   "and QA output before any acceptance."),
    }
    if qa_mode == "native":
        result["recorded_platforms_unverified"] = details["platforms"]
        result["recorded_interaction_count"] = len(details["interactions"])
        result["recorded_accessibility_count"] = len(details["accessibility"])
    return result


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
    qa_mode = args.get("qa_mode", "web")
    if qa_mode not in QA_MODES:
        raise ValueError("qa_mode must be web, native or host")
    base = {
        "project": project, "project_root": str(root),
        "task_count": len(selected), "task_keys": sorted(selected),
        "mode": "READ_ONLY_INTEGRATION_REVIEW",
        "qa_mode": qa_mode,
        "state_written": False, "agent_spawned": False,
        "git_diff_verified": False, "tests_independently_verified": False,
        "host_permission_verified": False, "approval_verified": False,
        "source_identity_kind": "BOUNDED_LOCAL_FILES_FINGERPRINT",
        "source_identity_is_git_commit": False,
        "qa_record_host_reported": True,
        "next": ("Independently inspect actual Git changes, platform-specific QA "
                 "and tests, host sessions and user approval. Do not merge or "
                 "accept based only on local ledger or QA records."),
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
                "reason": "Provide an existing project build with source-bound QA for the explicitly selected web/native/host mode."}
    orbit_build.validate_key(build_id)
    if not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='build_runs'"
    ).fetchone():
        return {**base, "status": "HOLD_INDEPENDENT_QA",
                "source_matches": True,
                "reason": "No matching build record is available."}
    build = conn.execute(
        "SELECT revision,stage,evidence_json FROM build_runs "
        "WHERE project=? AND root=? AND build_id=?",
        (project, str(root), build_id)).fetchone()
    if build is None:
        return {**base, "status": "HOLD_INDEPENDENT_QA",
                "source_matches": True,
                "reason": "This exact project has no such build."}
    if qa_mode in {"native", "host"}:
        return _review_host_qa(build, fingerprint, build_id, qa_mode, base)
    if not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='browser_results'"
    ).fetchone():
        return {**base, "status": "HOLD_INDEPENDENT_QA",
                "source_matches": True,
                "reason": "No local QA record table exists for this project."}
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
        if not isinstance(qa, dict):
            raise ValueError("Malformed browser QA report")
        actions = qa["actions"]
        evidence = json.loads(build["evidence_json"])
        qa_revision = qa.get("qa_build_revision")
        # A stored PASS must belong to this *build generation*. An older
        # record cannot be reused while still on BROWSER_QA after a failed
        # advance, feedback or other revision change. Normal successful
        # advancement from BROWSER_QA increments the build revision, so in
        # later stages require the recorded BROWSER_QA PASS transition,
        # rather than insisting on equality to the current revision.
        qa_transition = (evidence.get("BROWSER_QA")
                         if isinstance(evidence, dict) else None)
        qa_revision_valid = (
            type(qa_revision) is int and qa_revision >= 1
            and (
                (build["stage"] == "BROWSER_QA"
                 and qa_revision == build["revision"])
                or
                (build["stage"] in {"NATIVE_QA", "REVIEW", "CHECKPOINT", "DONE"}
                 and qa_revision < build["revision"]
                 and isinstance(qa_transition, dict)
                 and qa_transition.get("outcome") == "PASS"
                 and qa_transition.get("verification") == "browser-tool")
            )
        )
        correct = (isinstance(qa, dict)
                   and qa.get("source_fingerprint") == fingerprint
                   and qa_revision_valid
                   and isinstance(qa.get("preview_id"), str)
                   and bool(qa["preview_id"])
                   and isinstance(qa.get("preview_started_at"), (int, float))
                   and not isinstance(qa.get("preview_started_at"), bool)
                   and isinstance(actions, list) and bool(actions)
                   and all(isinstance(action, dict) and action.get("status") == "PASS"
                           for action in actions)
                   and not qa.get("errors") and not qa.get("failures")
                   and not qa.get("blocked_remote_hosts"))
    except (ValueError, TypeError, KeyError, AttributeError):
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
