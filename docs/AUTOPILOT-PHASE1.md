# Orbit Autopilot — Phase 1 mission and founder-delegated decisions

**Status: v0.32 DEVELOPMENT CANDIDATE ONLY.** This is not yet an unattended coding agent, installed update, signed-in host acceptance or published release. The released Orbit Core v0.31.0 has no Autopilot MCP tools. The coding host retains control of the model, filesystem, permissions and native agents.

## Product contract

An owner can approve a **bounded Mission Charter** one time, and the active host can consult it while following a previously registered roadmap task DAG. The charter is bound to:

- Exactly one canonical project root, project key and unique mission ID.
- An objective, informational roadmap reference and **caller-reported** roadmap revision.
- A non-protected feature branch name. The actual Git branch is separately verified by the coding host; reporting a branch string to Orbit is not Git evidence.
- One to twelve existing, registered tasks and their task/dependency/role/source-scope fingerprint. Every dependency must be included in the same charter.
- Allowed repository-relative writable paths; original and resolved path scopes must fit the approved charter. Protected control/credential paths and symlink escapes are refused.
- A subset of the low-risk decisions `task_order`, `implementation_detail`, `ui_polish` and `bounded_retry`.
- A UTC expiry within 30 days, no more than two concurrent task recommendations and at most three attempts per approved task.

The approval is stored in **existing project-scoped SQLite** with immutable charter content and a revisioned event journal. It does **not** write roadmap or Git files, install tools, reserve tasks, spawn models, run tests or change host permissions.

## MCP workflow

Register and review tasks normally with `orbit_task_plan` (no automatic creation). Then:

1. Call `orbit_autopilot_charter(action="preview")` with a specific task list, project root/key, mission ID, objective, roadmap reference/revision, feature branch, allowed paths/decisions, expiration and budgets. Inspect the returned `charter_digest`, tasks and path/branch constraints.
2. After actual owner/host review, call `orbit_autopilot_charter(action="activate", confirm_write=true, expected_digest=...)` with the **same** charter and an actual caller-reported approval reference. This records `CHARTER_RECORDED` and revision 1. Orbit cannot cryptographically authenticate the person who supplied the string.
3. Call `orbit_autopilot_next` with the mission revision, **caller-reported** branch, actual available native tool names, host name and workspace mode. It rechecks expiry, exact task/paths fingerprint, DAG/dependencies, attempt budget, native tool availability, read-only workspace and competing active reservations. Its successful result is `NEXT_TASK_REVIEW_REQUIRED`, **not** a started native worker.
4. Use `orbit_autopilot_decision` to classify proposed routine choices. Allowed charter categories return `DELEGATED_DECISION_REVIEW_REQUIRED`. Founder-only actions such as roadmap expansion, dependencies, credentials, spend, permissions, destructive changes, security-policy changes, merge, release and deploy return `HOLD_FOUNDER_REVIEW`. This tool never implements a decision.
5. `orbit_autopilot_charter(action="pause" | "resume" | "stop")` requires the exact current mission revision and an explicit confirmed write; resume also requires a fresh caller-reported approval reference. Pause/stop update Orbit state **only**; they cannot terminate an external host worker. A stopped mission cannot be silently restarted.

**Read-only calls:** `status`, `next`, `decision` and `preview` do not modify the mission or task database. A recorded ACTIVE charter does **not** authenticate approval: every tool response sets `approval_authenticated=false`, `host_permissions_verified=false` and `execution_allowed=false`, and never claims to have launched a background runner.

## Safe stop/hold examples

| Observed state | Autopilot behavior |
| --- | --- |
| Paused, expired or stopped charter | HOLD, never issue next-task execution instruction |
| Missing or unapproved task, changed goal/paths/dependencies | Reject charter or HOLD on task fingerprint drift |
| Different branch claimed by caller | HOLD; even a matching branch claim is not verified Git status |
| No genuine host-native agent tool or read-only host workspace | HOLD; never switch provider to bypass a denial |
| Attempt budget exhausted, unresolved dependencies or active host reservations | HOLD |
| Founder-only decision, broadening scope or dependency installation | HOLD for real founder approval |
| Host quota exhausted, detached process, failed test or permission rejection | Remains BLOCKED until a separate host-authorized recovery; no invented success |
| Local PC powered off / model session ended | No background work, no runner persistence or cloud continuation |

## Next phases — separate approval and verification

**Phase 2 (not implemented):** An optional local supervisor, authenticated host approval integration and actual supported Codex/Antigravity execution adapter; task leases, idempotency, per-day budget accounting, real test/QA evidence, visible Stop/Pause/Resume and crash recovery. Explicitly test Windows and Linux, and do not bypass host UI permissions. The plain MCP is **not** itself a scheduler or native agent executor.

**Phase 3 (not implemented):** Founder-away progress and decision notifications, with any remote/cloud runner handled as a separate, opt-in cost and privacy project. No claim of execution when the PC is offline.

A future runner must enforce the charter as a true **execution precondition**, not merely trust the natural-language agent prompt or a self-reported consent token. Existing `orbit_task_reserve` and host APIs still have their own normal authorization gates; Phase 1 is an advisory policy record, not an unconditional sandbox.

## Verification

Unit tests must cover no implicit activation; preview digest mismatch; closed scopes, protected paths and feature branch; expiration and pauses; optimistic revisions, replay attempts, cross-project separation and same-root conflicts; stale task fingerprint; host/tool permissions; retry counts; founder-only HOLD; and proof that there are no background, Git or native model actions. Repository CI and independent signed-in real-host acceptance are separate. The published v0.31.0 release and existing local SQLite must not be modified or retroactively tagged.
