# Orbit native specialist task ledger — v0.21.0

The **Antigravity desktop host** alone may spawn/stop a subagent through its real native tools (`invoke_subagent` when exposed). Orbit MCP is a separate **bookkeeping** tool server: no subprocess launching, Git initialization, worktree creation, commits, merges, or IDE API calls.

## Native delegation contract

1. Inspect current project docs/ADR/source and the bounded `.orbit/STATE.md` checkpoint. Identify one ready milestone step; use only the authorized workspace path and stable project slug.
2. `orbit_task_list` to recover real registered tasks. Never mistake a task ledger entry for a currently running host agent; reconcile reported status with the host's actual agent panel before acting.
3. `orbit_task_plan`: declare stable task_key, step, role, exact outcome, reason, `write_paths` (relative file/directory ownership; `[]` means read-only), and accepted dependencies. Default is preview. Only register with `confirm_write=true` when authorized and useful. Reuse the existing task_key; don't create duplicate work.
4. **Before spawning**: obtain actual user/host permission if required and use `orbit_task_reserve` with the task's latest integer `revision`, `approval_reference`, `confirm_write=true`. This enforces local advisory budgets: max **2** active reservations/runs, **3** attempts per milestone step, and **12** reservations per UTC day. Its reference is caller-supplied and not an authentication token. The host remains the real permission boundary.
5. If reservation succeeds, invoke the genuine Antigravity-native specialist (`invoke_subagent` only if actually listed and allowed). Pass canonical context, specific read/write scope, prohibited actions, dependencies, acceptance checks, and report format. If native invocation isn't available, use one serial agent and **release** any reserved slot; never invent a spawned agent or use external model CLIs. `orbit_task_release` cancels a reservation; it cannot stop a running agent.
6. After a real host session/reference is returned, call `orbit_task_started` with that reference and latest revision. **Do not** mark running from an imagined reference. Host agent status remains authoritative; this ledger is an observational record.
7. Once the host actually reports completion (or confirmed failure/cancellation), compare its scope with the true Git diff and run appropriate tests/visual validation. `orbit_task_scope_check` checks *caller-provided* changed paths; always gather them from actual Git. `orbit_task_report` records `REPORTED_DONE`, `FAILED`, `BLOCKED`, or `CANCELLED` and relevant evidence.
8. Run a **separate review** against real source/tests and user criteria. `orbit_task_review` records ACCEPT or REWORK with review evidence; it cannot verify source evidence, approve deployment, or merge a branch. ACCEPT is stored as `REVIEW_ACCEPTED` (reviewer-reported, not a proof). A dependent task requires this state; normal milestone and human approvals remain separate.
9. Update `.orbit/STATE.md` using the existing revision-guarded `orbit_project_checkpoint` only after confirming the task result and explicit authorized write; never rewrite canonical owner docs or ADRs.

### Boundaries

- The ledger locks **declared write-path strings**, not the filesystem. Other agents or users can still edit these paths. Git worktrees are isolation for version-control convenience, *not a security sandbox*. Inspect the actual diff before review and merge.
- Reject writes to `.git`, `.orbit`, `.agents`, paths containing `..`, absolute paths, secret/config directories. No wildcard ownership (`*`) is accepted. Directory write scopes end in `/`.
- The host might execute an agent successfully even if the MCP ledger call fails. Treat this as untracked; stop/reconcile it using the host controls, never start a duplicate worker.
- No server-side principal identity or cryptographic approval verification is provided. The `approval_reference`, `host_session`, `evidence`, and `review_evidence` are **reported values only**. The Antigravity host's actual permissions and user approvals are decisive.
- `RESERVED` is a slot held before invoking the native host. If the host call fails, call `orbit_task_release` with the fresh revision and true reason; do not let reservations silently accumulate.
- Version v0.21 adds one SQLite `orbit_agent_tasks` table without modifying existing Orbit `memories` or owner documentation. All operations are project-root scoped; no remote sync or background task runner.

## Example native task split

Task `m2-frontend`: role `frontend`, `write_paths=["src/ui/"]`, goal implement accessible UI, no editing backend. Task `m2-backend`: role `backend`, `write_paths=["src/api/"]`, goal implement validated endpoint. Both may be reserved concurrently when host permission permits. Integration task `m2-integration` with `depends_on=["m2-frontend","m2-backend"]` may start only after each has separately reported completion and review acceptance. A reviewer should verify the actual diffs, tests and generated assets before any merge.
