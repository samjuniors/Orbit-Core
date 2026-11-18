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
5. `orbit_autopilot_charter(action="pause" | "resume" | "stop")` requires the exact mission revision and a separate confirmed write. **In the v0.33 development branch**, resume first requires a read-only preview with `reported_branch`, a **fresh caller-reported** `approval_reference` and `expected_revision`. Only then can the caller supply the returned `resume_review_digest` as `expected_resume_digest` in a second, confirmed call. Orbit rechecks current task source/scope, branch claim, expiry, revision and unresolved reservations; it holds if these change. Pause/stop update Orbit state **only**; they cannot terminate external host workers. A stopped mission cannot silently restart.

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


## v0.33 draft improvement — replay-safe resume and redacted local timeline

**Status: source implemented in [draft PR #132](https://github.com/samjuniors/Orbit-Core/pull/132), NOT MERGED / NOT RELEASED.** Original security design informed by [OpenAI Agents SDK human-in-the-loop patterns](https://github.com/openai/openai-agents-python/tree/e7ce15a25b336bb3d0840ad16dee597f69a6e6d3), without importing the SDK.

### Updated pause/resume usage (only when this branch is actually connected)

1. The existing `pause` request must use the active mission's exact revision and `confirm_write=true`. Stop/terminate any live native worker through real host APIs separately; changing the local charter state **does not stop OS processes**.
2. In the paused state, call `orbit_autopilot_charter(action="resume", expected_revision=N, reported_branch="feat/approved-branch", approval_reference="actual-new-review-ref", confirm_write=false)`. Inspect its `resume_review_digest` and exact task/branch/path/expiration evidence. The string is caller-reported, **not authenticated owner permission**.
3. After the actual owner/host independently reviews and authorizes that exact continuation, call `action="resume", expected_revision=N, reported_branch=..., approval_reference=..., expected_resume_digest=<the-preview-digest>, confirm_write=true`.
4. The existing SQLite transaction rechecks mission state/revision, registered task fingerprint, path scope, approved feature branch claim and absence of active or reserved tasks in the workspace. A unique index on the **existing** mission event journal holds previously recorded activation/resume approval hashes across all missions in the same project root; it does not store a second approval database.
5. The resulting `ACTIVE` is still an **advisory recorded charter state**. The host remains the only authority for model selection, worker execution, filesystem access, permissions, true branch verification, user authentication and owner approval. Never infer consent from a hash/digest, copied approval reference or `ACTIVE` status.

### Local timeline and safety limitations

`orbit_autopilot_charter(action="timeline", mission_id=..., limit=20)` reads bounded, redacted activation/pause/resume/stop events from the **existing journal**. It returns a deterministic local `trace_id`, ordered `revision`, event type, timestamp and whether a one-use approval fingerprint is recorded. It never returns raw approval references, emits remote telemetry or proves that a worker executed. `host_execution_verified=false`, `owner_authenticated=false` and `state_written=false` are intentional.

The new journal column `approval_sha256` migrates additively. **Legacy events did not retain reference fingerprints**; their historical uniqueness cannot be reconstructed or claimed. New activation/resume references are checked atomically under SQLite's `BEGIN IMMEDIATE` lock and a unique project-root index. SHA-256 provides duplicate detection/binding, **not cryptographic owner identity or signed authorization**. An authenticated owner-checked, single-use consent channel cannot be implemented by an MCP that only receives caller-provided strings; true host support remains future work.

This is a **deliberate resume API contract change**. Older hosts and scripts must preview+commit and be tested before upgrade; no silent compatibility fallback may bypass the review digest. `action="timeline"` is read-only and adds no MCP tool. Tests and real-host gates: `tests/test_autopilot_charter.py`, `tests/test_autopilot_runner.py`, Windows/Linux CI, and actual signed-in Codex/Antigravity permission/stop/resume evidence. Do not release until verified and founder-approved.
