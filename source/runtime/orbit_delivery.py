"""Read-only adaptive end-to-end software delivery blueprint.

Orbit generates reviewable *intent*, never code, approvals, host sessions or
an imported agent harness. The host provides genuine native specialists,
permissions, model choices and independent test evidence.
"""
from __future__ import annotations

import re
import orbit_intake
import orbit_swarm_draft
import orbit_tasks

OPERATIONS = frozenset({
    "build", "add-feature", "fix", "debug", "redesign", "maintain", "resume"
})
MATURITY = frozenset({
    "new", "partially_built", "existing", "completed", "maintained", "stalled"
})
VISUAL = frozenset({"website", "web-app", "desktop-app", "mobile-app", "game"})
SERVICES = frozenset({"web-app", "desktop-app", "mobile-app", "api-service",
                      "os-platform", "plugin-mcp", "data-automation", "game"})
DATA = frozenset({"web-app", "mobile-app", "desktop-app", "api-service",
                  "data-automation", "game"})
STAGES = {
    "audit": "DISCOVER", "scope": "PLAN", "reproduce": "TEST",
    "experience": "DESIGN", "contracts": "DATA",
    "service": "IMPLEMENT", "interface": "IMPLEMENT",
    "implementation": "IMPLEMENT", "repair": "IMPLEMENT",
    "integration": "INTEGRATE", "quality": "QA",
    "security": "SECURITY", "review": "REVIEW",
    "handoff": "DOCS", "release": "RELEASE",
}


# The platform matrix describes host checks, not installed toolchains or
# preapproved skills. It extends existing roles instead of adding 71 agents.
PLATFORM_TARGETS = {
    "mobile-app": frozenset({"android", "ios", "mobile-cross-platform"}),
    "desktop-app": frozenset({"windows", "linux", "macos", "desktop-cross-platform"}),
    "os-platform": frozenset({"windows", "linux", "macos", "embedded"}),
    "game": frozenset({"web", "android", "ios", "windows", "linux", "macos", "console"}),
}
TARGET_PLATFORMS = frozenset().union(*PLATFORM_TARGETS.values()) | {"server"}
TECHNOLOGIES = frozenset({
    "unspecified", "flutter", "swiftui", "kotlin-compose", "react-native",
    "rust", "tauri", "electron", "dotnet", "pytorch", "unity", "unreal", "other"
})


def _platform_profile(kind, target, technology):
    """A read-only responsibility overlay, never evidence of a working SDK."""
    if target != "unspecified" and target not in TARGET_PLATFORMS:
        raise ValueError("Unsupported target platform")
    if technology not in TECHNOLOGIES:
        raise ValueError("Unsupported technology classification")
    allowed = PLATFORM_TARGETS.get(kind)
    if allowed and target == "unspecified":
        return {"status": "NEEDS_PLATFORM_CLASSIFICATION",
                "allowed_target_platforms": sorted(allowed),
                "next": "Inspect the existing code and ask for the actual target platform; do not assume web, iOS or Android."}
    if allowed and target not in allowed:
        raise ValueError("Target platform is incompatible with product type")

    checks = []
    roles = {}
    notes = {}
    if kind == "mobile-app":
        checks.extend(["Verify target mobile SDK and native host tools",
                       "Execute UI, accessibility and lifecycle tests on a real emulator or device",
                       "Review platform permissions, signing and distribution"])
        roles = {"frontend": "native-mobile-ui", "qa": "mobile-device-qa",
                 "devops": "mobile-build-and-distribution"}
        notes = {
            "interface": "Use the existing mobile framework and platform-native UI/lifecycle conventions, not assumed React DOM.",
            "quality": "Require actual mobile build and emulator/device evidence; otherwise report BLOCKED, not PASS.",
            "release": "Review signing, store rules and install/rollback on the actual target device.",
            "service": "Check the existing mobile application's service boundary; remove this suggested backend task if no service is required."
        }
    elif kind in {"desktop-app", "os-platform"}:
        checks.extend(["Verify the target OS compiler, SDK, runtime and host permissions",
                       "Run native integration and packaging tests on the target OS",
                       "Review filesystem, installation and update/rollback safety"])
        roles = {"frontend": "native-desktop-ui", "backend": "native-runtime",
                 "qa": "target-os-integration-qa"}
        notes = {
            "interface": "Use the confirmed native desktop toolkit, not a default web UI.",
            "implementation": "Follow the actual target OS and language ABI/toolchain rather than a browser-oriented scaffold.",
            "quality": "Verify the real target OS runtime and install/upgrade evidence; browser QA alone is insufficient.",
            "release": "Confirm OS package signatures, installation permissions and rollback."
        }
    elif kind == "game":
        checks.extend(["Identify the actual game engine and platform SDK",
                       "Run gameplay/input/performance tests with the target engine",
                       "Verify asset licensing and distribution"])
        roles = {"frontend": "engine-native-gameplay", "qa": "gameplay-and-performance-qa"}
        notes = {
            "interface": "Use the actual game engine/input loop; do not assume a React web interface.",
            "quality": "Require real engine/build/gameplay results rather than web-only screenshots.",
            "release": "Review target-engine packaging, assets and distribution licensing."
        }
    elif kind in {"cli", "sdk-library", "plugin-mcp"}:
        checks.append("Run target-language build, API compatibility and CLI/library tests")
        roles = {"backend": "language-specific-implementation", "qa": "target-language-regression-qa"}
        notes = {"quality": "Use native language/unit/compatibility tests rather than a browser-only QA gate."}

    if technology in {"flutter", "swiftui", "kotlin-compose", "react-native"}:
        checks.append("Check installed framework/compiler, mobile lifecycle and target build tooling")
        notes["interface"] = ("Use the declared "+technology+" conventions and approved existing code; "
                              "never install its SDK or switch frameworks without consent.")
    if technology in {"rust", "tauri", "electron", "dotnet"}:
        checks.append("Check actual language/runtime build and OS-specific compatibility")
    if technology == "pytorch":
        checks.extend(["Check reproducible evaluation, data lineage, model artifacts and data-leakage boundaries",
                       "Verify inference quality and privacy using executed tests, not model assertions"])
        roles["qa"] = "reproducible-ml-evaluation"
        notes["quality"] = "Use independent held-out evaluation, data-leakage checks and reproducible model artifacts."
    if technology in {"unity", "unreal"}:
        checks.append("Run actual engine project build and licensed asset validation")
    if target == "embedded":
        checks.append("Verify actual device toolchain, hardware/firmware behavior and safe recovery")

    return {
        "status": "PROFILE_READY",
        "target_platform": target,
        "technology": technology,
        "profile_source": "CALLER_DECLARED_NOT_INSPECTED",
        "suggested_role_modes": roles,
        "required_host_checks": list(dict.fromkeys(checks)),
        "goal_overlays": notes,
        "host_toolchains_verified": False,
        "skills_installed": False,
        "native_agents_invoked": False,
    }


def _task(key, role, title, goal, reason, dependencies=()):
    return {
        "task_key": key, "step": STAGES[key], "role": role,
        "goal": goal, "reason": reason, "write_paths": [],
        "depends_on": list(dependencies),
    }


def _workflow(product_type, operation, maturity, objective, constraints, *, limited=False, focus_role=None):
    """Build a bounded DAG of host-native specialist assignments.

    Empty write scopes are deliberate: this is *not* a file-editing
    authorization and callers must inspect actual project paths first.
    """
    existing = maturity != "new"
    incident = operation in {"fix", "debug"}
    visual = product_type in VISUAL
    # A redesign proposes a bounded UI/UX slice, not unapproved schema or API rewrites.
    # Preserve existing behavior and defer backend/data changes until code inspection
    # proves they are necessary and the owner extends the reviewed scope.
    redesign = operation == "redesign" and visual
    service = product_type in SERVICES and not redesign
    data = product_type in DATA and not redesign

    tasks = []
    checks = {}

    def add(key, role, title, goal, reason, deps=(), evidence=""):
        tasks.append(_task(key, role, title, goal, reason, deps))
        checks[key] = {
            "title": title, "owner_role": role,
            "review_evidence": evidence,
            "write_scope": "REQUIRES_OWNER_AND_CODEBASE_REVIEW",
        }

    add("audit", "research", "Understand real project context",
        ("Inspect current source, Git branch, documentation, tests, host capabilities "
         "and checkpoint for this exact project. Identify reusable existing code; "
         "do not install or execute untrusted ECC or other third-party code. "
         "Objective: " + objective),
        "Reuse existing project decisions and assess maturity (" + maturity + ").",
        evidence="Source references, existing test baseline, verified maturity and missing decisions.")
    add("scope", "architect", "Approve requirements and vertical-slice plan",
        ("Produce a concise product brief with user journeys or API use cases, "
         "non-goals, platform, acceptance criteria, architecture choices and "
         "a sequence of thin, deployable vertical slices. Specify the actual "
         "test runner and a failing or baseline test for changed behavior before "
         "implementing when feasible; otherwise explain why test-first is blocked. "
         + ("Reproduce the bug first and state expected behavior. " if incident else "")
         + ("Preserve current user functionality and data. " if existing else "")
         + ("Honor constraints: " + constraints if constraints else "Avoid unapproved stack and hosting decisions.")),
        "The host must obtain genuine user approval before implementing.",
        ["audit"], "User-reviewed scope, priority and approval reference. No inferred permission.")

    if incident:
        add("reproduce", "qa", "Reproduce and bound the defect",
            "Write or execute an isolated failing regression for the exact observed defect; preserve original files. Distinguish real test evidence from descriptions.",
            "Debugging and fixes must start from actual evidence.", ["scope"],
            "Reproduction command/output tied to source commit, or BLOCKED if unavailable.")
        implement_deps=["reproduce"]
    else:
        implement_deps=["scope"]

    if visual and not incident:
        add("experience", "ux", "Map accessible experience",
            "Design the first complete user journey with responsive states, keyboard/focus access, feedback, error/empty/loading behavior, and reduced-motion handling. Reuse UI components compatible with the existing stack. For redesign, preserve behavior and existing service/data contracts unless separately approved.",
            "Choose interaction patterns before implementing visuals.", implement_deps,
            "Approved UX states, accessible acceptance and actual platform constraint.")
        implement_deps=["experience"]

    if data and not incident:
        add("contracts", "data", "Design persistent data contracts",
            "Specify model/schema changes, migration/backups, data boundaries and one end-to-end user-flow contract. Avoid assuming cloud storage.",
            "Keep data compatibility and validation explicit.", implement_deps,
            "Schema, migration/rollback review and contract tests.")
        implement_deps=["contracts"]

    if service and not incident:
        add("service", "backend", "Build service vertical slice",
            "Before implementation, establish a failing or baseline contract test when feasible. Implement the smallest working service/business-domain path with tests, error handling and declared write scopes only after host approval; rerun and report the test evidence.",
            "Produce a demonstrable domain path rather than disconnected scaffolding.", implement_deps,
            "Executed service contract tests and actual changed paths.")
        implement_deps=["service"]

    if visual and not incident:
        add("interface", "frontend", "Build the first UI vertical slice",
            "Before implementation, establish a failing or baseline UI interaction test when feasible. Implement the smallest functional user journey against the existing data/service contract or an approved local-only substitute; preserve those contracts during redesign. Include keyboard support, responsive error/empty/loading states and appropriate design-system reuse; rerun and report the tests.",
            "A tested end-to-end experience is more valuable than a set of static screens.", implement_deps,
            "Real interaction tests, user journey result and source-backed component review.")
        implement_deps=["interface"]
    elif not service and not incident:
        add("implementation", "backend", "Implement first functional slice",
            "Establish a failing or baseline test before implementation when feasible. Build a working CLI/library/website/API-path vertical slice for the approved scope using the existing stack; document public contracts and execute relevant tests.",
            "Deliver useful functionality without creating an unnecessary UI runtime.", implement_deps,
            "Executed target-language/unit tests and documented public contract.")
        implement_deps=["implementation"]

    if incident:
        add("repair", focus_role or ("backend" if service or not visual else "frontend"), "Apply minimal evidence-based repair",
            "Fix the reproduced defect within an approved code scope. Preserve all unaffected behavior and user data, then rerun the previously failing test.",
            "Avoid speculative rewrites or bypassing host permissions.", implement_deps,
            "Regression changes from FAIL to PASS on the same source baseline.")
        implement_deps=["repair"]

    add("integration", "integrator", "Review integrated behavior",
        "Independently inspect the merged working slice, dependency compatibility, actual changed paths and real-host results. Do not merge/publish automatically.",
        "Integration must be reviewed after actual implementation.", implement_deps,
        "Source diff, integration execution, no scope conflicts; HOLD on unsupported host tools.")

    add("quality", "qa", "Verify quality gates",
        "Run relevant unit, contract, integration and end-to-end/visual tests using the actual available host and target device. Report PASS, FAIL, BLOCKED or NOT RUN separately; never infer from agent claims.",
        "A completed task is not proof of a tested product.", ["integration"],
        "Test commands, environment, real output and inspected artifacts.")

    add("security", "security", "Security and privacy review",
        "Review auth/permissions, inputs, filesystem, secrets, dependencies, data protection and threat boundaries appropriate to the current application. Require actual fixes for serious findings.",
        "Security is a release gate, not an automatic scanner approval.", ["integration"],
        "Findings, reproduction/fix evidence and explicit unresolved-risk decision.")

    add("review", "reviewer", "Independent quality and security review",
        "Inspect code, architecture, regression evidence and security findings from a fresh perspective. Hold on unresolved critical issues or missing executed test evidence.",
        "The implementer must not be the only source of acceptance.", ["quality", "security"],
        "Review verdict with independent references and user-relevant limitations.")

    add("handoff", "writer", "Document operation and recovery",
        "Update existing canonical project docs only where necessary: user setup, tested architecture, support/rollback steps, checks and remaining risks. Preserve historical decisions.",
        "Avoid duplicate or conflicting project documentation.", ["review"],
        "Reviewed documentation and recovery plan, not just generated prose.")

    if not limited:
        add("release", "devops", "Prepare release and deployment approval",
            "Verify artifact reproducibility, CI, migration and rollback, supported hosts and owner publication consent. Never publish, deploy or merge as part of this preview.",
            "Shipping requires separate owner authorization and real acceptance evidence.", ["handoff"],
            "Exact commit CI, packages/checksums, rollback and explicit owner release approval.")

    assert len(tasks) <= orbit_swarm_draft.MAX_DRAFT_TASKS
    return tasks, checks


def preview(conn, root, project, a):
    """Derive a read-only reviewable blueprint; reuses existing DAG validation."""
    operation = a.get("operation", "build")
    maturity = a.get("maturity", "existing")
    if operation not in OPERATIONS or maturity not in MATURITY:
        raise ValueError("Unsupported operation or project maturity")

    approved = orbit_intake.status(conn, root, {"project": project})
    profile = approved.get("profile", {}) if approved.get("status") == "APPROVED" else {}
    kind = a.get("product_type") or profile.get("type")
    if not kind:
        return {"status": "NEEDS_PROJECT_CLASSIFICATION",
                "mode": "READ_ONLY_DELIVERY_BLUEPRINT",
                "project": project, "project_root": str(root),
                "next": "Review existing project stack or approve a product intake first.",
                "state_written": False, "agent_spawned": False}
    if kind not in orbit_intake.TYPES:
        raise ValueError("Unknown software product type")
    platform = a.get("target_platform", "unspecified")
    technology = a.get("technology", "unspecified")
    profile_check = _platform_profile(kind, platform, technology)
    if profile_check["status"] != "PROFILE_READY":
        return {
            "status": profile_check["status"],
            "mode": "READ_ONLY_DELIVERY_BLUEPRINT",
            "project": project, "project_root": str(root),
            "product_type": kind,
            "allowed_target_platforms": profile_check["allowed_target_platforms"],
            "next": profile_check["next"],
            "state_written": False, "agent_spawned": False,
            "tests_verified": False,
        }
    objective = a["objective"].strip()
    constraints = a.get("constraints", "").strip()
    slice_key = a.get("slice_key", "")
    if slice_key and not re.fullmatch("[a-z][a-z0-9-]{0,23}",slice_key):
        raise ValueError("slice_key must be a simple 1..24 character lowercase slug")
    focus_role = a.get("focus_role")
    if focus_role and operation not in {"fix", "debug"}:
        raise ValueError("focus_role is only for fixes or debugging tasks")
    if focus_role and focus_role not in {"frontend", "backend", "data", "devops", "security", "qa"}:
        raise ValueError("Unsupported focus role")
    # Do not leak untrusted source text as a verified requirement.
    tasks, contracts = _workflow(kind, operation, maturity, objective, constraints,
                                 limited=operation in {"fix", "debug"},
                                 focus_role=focus_role)
    # Task goals stay within the existing ledger contract and are not proof
    # of a working target SDK. Roles are unchanged; host adapters decide tools.
    for item in tasks:
        advice = profile_check["goal_overlays"].get(item["task_key"])
        if advice:
            item["goal"] += " Platform-specific review: " + advice
    if slice_key:
        # Fresh keys preserve all existing accepted task history.
        keys = {item["task_key"]: slice_key+"-"+item["task_key"] for item in tasks}
        for item in tasks:
            item["depends_on"] = [keys[dep] for dep in item["depends_on"]]
            item["task_key"] = keys[item["task_key"]]
        contracts = {keys[key]: value for key, value in contracts.items()}
    graph = orbit_swarm_draft.preview(conn, root, project, {"tasks": tasks})
    return {
        "status": ("BLUEPRINT_READY" if graph["status"] == "DRAFT_VALIDATED"
                   else "HOLD_DRAFT_"+graph["status"]),
        "mode": "READ_ONLY_DELIVERY_BLUEPRINT",
        "project": project, "project_root": str(root),
        "product_type": kind, "operation": operation, "maturity": maturity,
        "platform_assessment": {k: v for k, v in profile_check.items()
                                if k != "goal_overlays"},
        "slice_key": slice_key, "focus_role": focus_role,
        "objective": objective, "constraints": constraints,
        "selected_from_approved_intake": bool(not a.get("product_type") and profile),
        "proposed_tasks": tasks, "acceptance_contracts": contracts,
        "draft_review": {
            "status": graph["status"],
            "waves": graph.get("review_waves", []),
            "reason": graph.get("reason", ""),
            "conflicting_keys": graph.get("conflicting_keys", []),
            "missing_dependency_keys": graph.get("missing_dependency_keys", []),
        },
        "implementation_ready": False,
        "needs_owner_approval": True,
        "needs_write_scope_selection": True,
        "host_native_agent_required": True,
        "agent_spawned": False, "state_written": False,
        "model_selected": False, "approval_verified": False,
        "execution_verified": False, "tests_verified": False,
        "next": ("Audit and revise the proposal with the user, assign real non-overlapping "
                 "project-relative write paths, rerun orbit_swarm_draft_preview on the "
                 "final task DAG, and only then register tasks individually through "
                 "orbit_task_plan with consent. Native host invocation, independent "
                 "reviews, test evidence, and final release approval remain separate."),
        "warning": ("Task goals derive from user input/metadata, NOT verified code or a "
                    "live ECC harness. No third-party agents, models, skills, commands "
                    "or templates have been downloaded, installed or executed."),
    }
