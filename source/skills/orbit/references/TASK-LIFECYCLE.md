# Orbit native specialist task ledger — v0.21.0

**Only the connected coding host** may invoke a native subagent. Antigravity may expose `invoke_subagent`; Codex may expose `spawn_agent`; Claude Code may expose `Agent` or `Task`. Availability is session-specific: check the active host's real tool inventory, do not infer it from repository agent files or installed configs. VS Code, Claude Desktop and generic hosts require a demonstrated invocation API before delegation. Orbit's stdio MCP only coordinates records and produces read-only handoffs; it cannot invoke host agents, clone worktrees, commit, merge or attest user approval. See the host's official documentation for currently supported arguments.

## Native delegation contract

1. Inspect current project docs/ADR/source and the bounded `.orbit/STATE.md` checkpoint. Identify one ready milestone step; use only the authorized workspace path and stable project slug.
2. `orbit_task_list` to recover real registered tasks. Never mistake a task ledger entry for a currently running host agent; reconcile reported status with the host's actual agent panel before acting.
3. `orbit_task_plan`: declare stable task_key, step, role, exact outcome, reason, `write_paths` (relative file/directory ownership; `[]` means read-only), and accepted dependencies. Default is preview. Only register with `confirm_write=true` when authorized and useful. Reuse the existing task_key; don't create duplicate work.
4. **Before spawning**: obtain actual user/host permission if required and use `orbit_task_reserve` with the task's latest integer `revision`, `approval_reference`, `confirm_write=true`. This enforces local advisory budgets: max **2** active reservations/runs, **3** recorded attempts per milestone step, and **12** recorded reservations per UTC day. **Each reservation attempt is counted**, including retries of the same task. Review the returned `attempt_number`/`attempt_budget`; only an unstarted slot explicitly released through `orbit_task_release` is refunded. A genuinely started attempt still counts after failure, cancellation, rework, or recovery. Retry limits are project-root-local SQLite guards, not authenticated host quotas. Existing legacy task history may be incomplete and is conservatively counted as one historical attempt when relevant. Its reference is caller-supplied and not an authentication token. The host remains the real permission boundary.
5. **After reservation**, call `orbit_task_handoff` with the real host label and only the native tools genuinely available to the host. The tool checks the reserved task, accepted prerequisites, scope and optional M1 research pointers, then returns `HOST_INVOCATION_REQUIRED` with the bounded handoff only if the reported host-tool name matches the adapter. A reported tool list is **not authenticated** by MCP. The lead host must invoke that exact **native** tool itself, with its real parameters and permission prompts, then independently observe the session/agent ID. If the host returns `HOLD_NATIVE_TOOL_UNAVAILABLE`, do serial host work or an explicit user handoff and release any unused reservation; no fabricated session or external CLI. Never treat the handoff as an agent launch. `orbit_task_release` cannot stop a running agent.
6. After a real host session/reference is returned, call `orbit_task_started` with that reference and latest revision. **Do not** mark running from an imagined reference. Host agent status remains authoritative; this ledger is an observational record.
7. On resume/restart, inspect `orbit_task_list.host_reconciliation` or `orbit_project_resume.host_reconciliation`: any `RESERVED` or `RUNNING` task needs an actual host check, regardless of local timestamps. Never auto-expire a native worker. When the real host confirms completion/failed/stopped, compare its scope with the true Git diff and run appropriate tests/visual validation. `orbit_task_scope_check` checks *caller-provided* changed paths; always gather them from actual Git. For `orbit_task_report`, supply the existing exact `observed_host_session`, a compatible `host_state` (`COMPLETED` for `REPORTED_DONE`; `FAILED` for `FAILED`; `FAILED`/`CANCELLED`/`STOPPED` for `BLOCKED`; `CANCELLED`/`STOPPED` for `CANCELLED`), actual `evidence`, and fresh `expected_revision`. Any `UNKNOWN`, `RUNNING`, missing or mismatched observation returns `HOLD_HOST_RECONCILIATION`, preserving the running scope. If cancellation was requested, stop and verify the agent **in the host UI/native controls first**, then report. The status is still host-reported, not attested by MCP.
8. Run a **separate review** against real source/tests and user criteria. `orbit_task_review` records ACCEPT or REWORK with review evidence; it cannot verify source evidence, approve deployment, or merge a branch. ACCEPT is stored as `REVIEW_ACCEPTED` (reviewer-reported, not a proof). A dependent task requires this state; normal milestone and human approvals remain separate.
9. Update `.orbit/STATE.md` using the existing revision-guarded `orbit_project_checkpoint` only after confirming the task result and explicit authorized write; never rewrite canonical owner docs or ADRs.

### Boundaries

- The ledger locks **declared write-path strings**, not the filesystem. Other agents or users can still edit these paths. Git worktrees are isolation for version-control convenience, *not a security sandbox*. Inspect the actual diff before review and merge.
- Reject writes to `.git`, `.orbit`, `.agents`, paths containing `..`, absolute paths, secret/config directories. No wildcard ownership (`*`) is accepted. Directory write scopes end in `/`.
- The host might execute an agent successfully even if the MCP ledger call fails. Treat this as untracked; stop/reconcile it using the host controls, never start a duplicate worker.
- No server-side principal identity or cryptographic approval verification is provided. The `approval_reference`, `host_session`, `evidence`, and `review_evidence` are **reported values only**. The Antigravity host's actual permissions and user approvals are decisive.
- `RESERVED` is a slot held before invoking the native host. If a real host denies permission, its tool is unavailable, or invocation fails **before a session exists**, call `orbit_task_release` with the fresh revision, true reason and `reason_code=HOST_PERMISSION_DENIED`, `HOST_TOOL_UNAVAILABLE` or `HOST_INVOCATION_FAILED`. The task becomes `BLOCKED` (not `CANCELLED`) and releases its unstarted slot. A rejected approval reference must not be reused on a subsequent reservation; renewed real host/user consent is required. For an actual user cancellation, omit `reason_code` (legacy default `USER_CANCELLED`) or set it explicitly; the task becomes `CANCELLED`.
- This is caller-reported refusal evidence, **not** an authenticated host permission decision. Never automatically retry denied permission through another browser, provider or host, and do not attempt to terminate a task with a real running host session through `orbit_task_release`. Reconcile the host first; its session is authoritative.
- The existing `orbit_agent_tasks` table is preserved and an additive `orbit_task_attempts` table records every new approved reservation and its reported outcome. On retry, keep the previous session reference in its attempt history and clear the current task's session until the host actually starts a new worker. The task/research/export and checkpoint stores are not automatically synchronized; no cross-PC quota, remote sync, automatic agent termination, or background task runner is implied. Historic attempted runs may exceed reconstructible totals; never claim their exact count.

## Example native task split

Task `m2-frontend`: role `frontend`, `write_paths=["src/ui/"]`, goal implement accessible UI, no editing backend. Task `m2-backend`: role `backend`, `write_paths=["src/api/"]`, goal implement validated endpoint. Both may be reserved concurrently when host permission permits. Integration task `m2-integration` with `depends_on=["m2-frontend","m2-backend"]` may start only after each has separately reported completion and review acceptance. A reviewer should verify the actual diffs, tests and generated assets before any merge.

## v0.27 bounded Swarm integration check

Before an integration decision on multiple accepted specialists, request a read-only `orbit_swarm_integration_review` with 1–12 exact task keys/current revisions, the expected bounded source fingerprint from a previous inspection and, for web apps with an Orbit-recorded browser QA run, `build_id`. The gate rejects stale code, missing/reworked task reviews, scope violations and stale or failed recorded browser QA. It **does not** execute Git, tests or a browser and never attests user consent or worker sessions. Its strongest outcome is `READY_FOR_INDEPENDENT_REVIEW`; the host integrator must still inspect real Git diffs and run tests before accepting the milestone. Mobile/desktop/native test evidence requires real host acceptance, not fabricated browser records.


## v0.30 draft: stage-aware host-native coordination (optional)

For a multi-specialist goal, the read-only
`orbit_native_coordination_preview` combines existing task-DAG draft review,
current ledger readiness, independent-reported-task review and all-or-nothing
native-host reservation preflight. See
`references/NATIVE-COORDINATION.md` for the three input modes and safe
host-owned handoff sequence. It is **not** an automatic batch reservation,
agent invocation, skill loader or session monitor. Every task registration,
reservation, source change, test execution, review and merge still requires
its existing independent authorization and evidence gate.

When the native tool is unavailable, report `HOLD_NATIVE_TOOL_UNAVAILABLE`
and propose only genuine permission-gated serial host work. When any
`RESERVED`/`RUNNING` record is found after restart, reconcile it with
the real host before further reservation. Do not reuse old approval tokens,
invent session references, bypass workspace-read-only restrictions, or
auto-accept dependencies merely because an agent reports completion.

When every task is review accepted, the v0.30 coordinator returns
`integration_review_batches` containing the **complete accepted task set**
in 1–12-task groups (up to the 40-task graph ceiling). These are read-only
`orbit_swarm_integration_review` *suggestions*, not invocations or a
passing aggregate gate. Inspect one consistent live source snapshot, each
task's exact revision and file scope, real QA/security results, and every
batch before accepting integrated work. The browser integration guard rejects
QA from a stale active build revision; a later stage requires a recorded
`BROWSER_QA` PASS transition as well as current source identity. Browser
QA is not a substitute for device/desktop/native target-platform tests.
For native/mobile/desktop work, explicitly select qa_mode=native on a build
with the NATIVE_QA stage. For CLI, SDK/library and scoped non-browser work,
select qa_mode=host on a VERIFY-only build. Source and build-revision pins
are recorded by orbit_build_advance only after a structured reported PASS;
these are not proof of host execution or independently verified test results.
Review actual device, SDK and command output before acceptance. Never
fabricate browser records or silently infer platform QA acceptance.

**Development status:** v0.30 source only, 48-tool development inventory,
automated and host acceptance NOT RUN at owner direction. Previously
published installations may not expose this tool; continue the existing
manual lifecycle safely when it is absent.
