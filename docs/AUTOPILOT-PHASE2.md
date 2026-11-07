# Orbit Autopilot Phase 2 — opt-in local supervisor (development prototype)

**Status: UNRELEASED, NOT ACTIVATED.** This is a *first single-task runner prototype*, not an always-on autonomous founder substitute. It stacks on [Phase 1 Mission Charter](AUTOPILOT-PHASE1.md) and uses only Codex CLI's documented non-interactive interface. No new LLM, cloud executor, scheduler, plugin install, permission bypass, merge or release is provided.

## Capability and trust boundary

The source module is `source/runtime/orbit_autopilot_runner.py`. The developer operator CLI is `scripts/orbit_autopilot_local.py`. It is **not an MCP tool**, background daemon, Windows service, scheduled task or something started by the Universal Setup. It does not start until a local terminal operator requests `run`, reviews a bound plan and types the exact one-task confirmation. This proves a local console interaction, **not cryptographically authenticated founder identity or host approval**.

Preflight checks the ACTIVE, unexpired Mission Charter and revision; immutable registered task-spec fingerprint; exact source Git repository root, non-protected feature branch, clean checkout and commit; DAG dependencies and active reservation conflicts; task attempt limit; and absence of an unresolved runner lease. Caller approval references are not independently authenticated.

For an actual run, Orbit creates a new **isolated temporary Git clone** without Git object hardlinks, verifies the branch and commit, rejects symlinked files and overly large trees, removes the clone's `origin` remote, then invokes only the available Codex CLI:

```text
codex exec --ephemeral --json --sandbox workspace-write --ask-for-approval never -C <isolated-clone> <bounded-task-prompt>
```

No `--yolo`, `--dangerously-bypass-approvals-and-sandbox`, `danger-full-access`, external model provider, extra writable directory or permission override. If an action requires an approval that the headless host cannot obtain, the host must deny it and the runner reports BLOCKED; Orbit never switches tools to bypass the denial. Codex CLI is **not** assumed to have Codex desktop Browser/Computer Use plugins or native specialists.

Structured Codex output is size-limited and must include a genuine completed turn without failure/denial events, even if the process returns exit code 0. The runner independently enumerates changed/untracked paths in the clone; changes outside charter scope cause BLOCKED. It never applies the changes to the original checkout or auto-accepts the task. A scoped successful result is `REVIEW_REQUIRED` pending independent diff/test review.

## Controls

- **Preview:** read-only charter/Git/task readiness check; does not clone or start a process
- **Run:** locally typed interactive confirmation; one task, one process, maximum 600-second elapsed time and no automatic retry or quota assertion
- **Status:** current project/root/mission-scoped SQLite job record and clone reference; not independently verified OS-process liveness
- **Stop:** records STOP_REQUESTED; an attached supervisor polls it and attempts to terminate **only its own spawned process group/tree**. Expired/stopped/paused charters also trigger termination. If the supervisor crashes, unresolved RUNNING or STOP_REQUESTED leases HOLD new work for manual OS-process reconciliation; never kill a PID merely because it was stored in SQLite
- **Review:** source remains intact, isolated clone remains for independent Git diff, trusted tests and normal Orbit task review. No commit/push/merge/release/deploy

Codex's sandbox, not Orbit's natural-language prompt, governs actual permissions. The local clone is **not a VM or a complete security boundary**. It does not protect against all plugin/MCP side effects or credential reads; the operator must review host configuration. OS child-tree termination after a parent crash is **not guaranteed** by this prototype. Founder identity through an interactive shell string is not cryptographically authenticated. PC-off execution is not supported.

## Developer-only commands (disposable fixture)

Use this *only on a disposable, explicitly approved test project*, with a genuine already-recorded Phase 1 charter in its selected SQLite database. From an isolated source checkout:

```powershell
py -3.12 scripts/orbit_autopilot_local.py preview --project-root C:\Temp\disposable-orbit-qa --project qa-lab --mission-id reviewed-mission --revision 1
py -3.12 scripts/orbit_autopilot_local.py status --project-root C:\Temp\disposable-orbit-qa --project qa-lab --mission-id reviewed-mission
py -3.12 scripts/orbit_autopilot_local.py stop --project-root C:\Temp\disposable-orbit-qa --project qa-lab --mission-id reviewed-mission
```

The separate `run` action requires a real interactive TTY; there is no headless approval-pipe or bypass flag. `--local-db` is available for an isolated disposable SQLite file. These commands are **development interfaces only**, not installed or activated for users in v0.31.

## Verified and remaining acceptance

Focused synthetic tests check clean feature branch/commit, isolated clone without `origin`, one-task scopes, denial/false completion, out-of-scope edits, concurrent/stale leases, stop-flag races, expired/paused charter holds, absence of real model calls and documented sandbox flags. Exact-head Linux/Windows CI and real signed-in Codex/Antigravity acceptance are separate gates.

**Still required for a truly autonomous roadmap loop:** trusted independent QA and task advancement, measured daily model quota/cost controls, authenticated founder one-time mission delegation, robust Windows Job Object / POSIX orphan handling, automatic crash recovery with safe reconciliation, Antigravity permission-respecting adapter, visible enable/pause/stop UI, and real-host acceptance. Until then, this initial runner stops after one task for reviewer inspection and cannot claim continuous founder-away operation.

References: [Codex non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode), [Codex sandbox and approvals](https://learn.chatgpt.com/docs/agent-approvals-security) and [Antigravity headless mode](https://antigravity.google/docs/cli/headless/). These are documentation references, not Orbit dependencies.
