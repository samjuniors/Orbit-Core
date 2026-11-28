# Autopilot Phase 3 - Bounded Multi-Task Mission Supervisor

**Status:** Development implementation; not a release certification.
**Branch:** `feat/v034-autonomous-mission-supervisor-20261127`
**Execution adapter:** Provider-neutral one-task contract; current implementation is local Codex CLI, foreground process, isolated temporary Git clones. No Claude Code or Antigravity adapter is implemented.

## What changed

Phase 2 could execute one Codex turn and then stop. Phase 3 adds a durable mission supervisor that can advance through the task keys already fixed in an active Mission Charter.

A single interactive local confirmation authorizes the bounded charter. The supervisor then:

1. Revalidates the active charter revision, branch, task specification fingerprint and expiry.
2. Selects only a DAG-ready task already named in the charter.
3. Passes an immutable task context through the provider-neutral execution-adapter contract. The only implemented adapter delegates to the existing Codex CLI runner in a disposable local clone with its existing sandbox and time/output limits.
4. Records the actual isolated changed paths in the existing task ledger as `REPORTED_DONE`.
5. Stops and waits for a reviewer to record acceptance or request rework.
6. Requires the exact reviewed isolated diff to be committed to the approved source branch.
7. Advances only after the existing review ledger says `REVIEW_ACCEPTED` and the source handoff is independently reconciled.
8. Repeats within the original charter; completion never implies merge, release or deployment.

The supervisor has a local durable run record, a best-effort local serialization lock, and an append-only event timeline whose hash covers event metadata as well as payload. Issue [#189](https://github.com/samjuniors/Orbit-Core/issues/189) remediation: on POSIX the per-user lock directory is pinned by descriptor and validated (not a symlink, owned by the effective user, no group/other permissions) and the lock file is created relative to that descriptor with `O_NOFOLLOW` and checked for owner and single link; on Windows the lock is a machine-wide (`Global\`) named kernel mutex with no filesystem path, so supervisors in different Terminal Services sessions also serialize; another local user can squat the name, which fails closed. Any validation failure returns `HOLD_MISSION_LOCK_UNSAFE`. The lock remains local serialization, not a multi-user security boundary, until independent review accepts it. The local mission command remains a development CLI; it is not exposed as an MCP action, stable installed command or background service.

## Run it

First create and activate an Orbit Mission Charter using the existing `orbit_autopilot_charter` preview/activate flow. Confirm the exact project root, feature branch, task keys, allowed paths, expiry and attempt limits.

From a real interactive PowerShell terminal:

```powershell
py -3.12 scripts\orbit_autopilot_local.py mission --project-root "C:\path\to\clean\feature-branch" --project "your-project-key" --mission-id "your-mission-id" --revision 1
```

The command displays the complete charter scope and requires the exact phrase:

```text
RUN MISSION <mission-id> <revision>
```

After a review-wait timeout, rerun the same command with the same revision; it reuses the existing mission-level approval rather than asking for approval per task. After an explicit pause/resume, use the new revision shown by the charter status. Inspect current state and the event timeline with:

```powershell
py -3.12 scripts\orbit_autopilot_local.py status --project-root "..." --project "..." --mission-id "..." --revision 1
py -3.12 scripts\orbit_autopilot_local.py timeline --project-root "..." --project "..." --mission-id "..." --revision 1
```

## Required review handoff

For each task, the supervisor records `REPORTED_DONE` with the actual isolated diff paths. The operator/reviewer must:

- Inspect the isolated workspace diff.
- Run the trusted tests appropriate to the task.
- Use the normal Orbit task review workflow to record `REVIEW_ACCEPTED` or `REWORK`.
- If accepted, copy/commit the exact reviewed changes to the charter's approved source branch.
- If `REWORK` is recorded, the supervisor archives the rejected isolated attempt and may retry the same task only while the charter's total attempt limit remains. The reviewer feedback is passed to the next isolated attempt as data; it cannot change the approved goal, dependencies or writable paths.
- When a task exhausts its attempt limit, it remains in `REWORK`. The supervisor may continue other DAG-ready tasks that do not depend on it; dependent tasks remain deferred. Once no eligible work remains, the mission blocks with the unresolved task/dependency summary. The task graph is never rewritten automatically.
- Resume the mission command.

The supervisor checks that the source commit is a descendant of the task's original HEAD and that its changed paths and file bytes match the isolated worker output. For a rejected attempt, it verifies that the source branch has not moved and that the rejected isolated diff still matches the recorded task report before archiving it. It does not create the commit itself. Review verdicts and reviewer identity are caller-reported; the supervisor does not authenticate the human reviewer.

## Explicit limitations

- The adapter contract is provider-neutral, but only CodexCLIAdapter is implemented. Claude Code and Antigravity adapters are not implemented or host-verified; no provider/model switching is performed.
- The process is foreground-only. It cannot continue when the terminal/PC is shut down.
- The local approval is operator input, not cryptographic identity proof.
- Task acceptance is never inferred from model output. A separate review step and exact source handoff remain mandatory; the local ledger records the caller-reported verdict but does not authenticate reviewer identity.
- Reviewer-directed rework can retry the same task within the charter attempt limit; after exhaustion, only independent DAG-ready tasks may continue. Failed/ambiguous host runs still stop for reconciliation; automatic retry of uncertain worker failures and autonomous scope expansion are not enabled.
- The mission lock fails closed (`HOLD_MISSION_LOCK_UNSAFE`) when its POSIX directory or lock file cannot be pinned and validated, or when the Windows mutex cannot be created; see [#189](https://github.com/samjuniors/Orbit-Core/issues/189). POSIX adversarial tests run in CI; the Windows mutex path is covered only by the existing concurrent-supervisor test on Windows CI. Independent security review is still required.
- Persisted PID values are never killed after a supervisor restart. Possible orphan processes fail closed for manual host reconciliation.
- Model recommendations remain advisory; no model switching, quota claims or fabricated cost/token telemetry.
- Merge, release, publish, deployment, secrets, permission changes, deletion and scope expansion remain outside the charter.

## Verification

Synthetic tests use disposable Git repositories and fake Codex process adapters. They verify a three-task dependency chain under one mission approval, review gates, exact source handoff, no auto-acceptance, bounded reviewer-directed rework with preserved scope/feedback, independent-task continuation after attempt exhaustion, dependency blocking without graph mutation, and append-only event records. Passing synthetic tests does not certify the real Codex host, Windows process-tree behavior, security boundaries, reviewer identity, or release readiness.
