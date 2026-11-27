# Autopilot Phase 3 - Bounded Multi-Task Mission Supervisor

**Status:** Development implementation; not a release certification.
**Branch:** `feat/v034-autonomous-mission-supervisor-20261127`
**Execution adapter:** Local Codex CLI, foreground process, isolated temporary Git clones.

## What changed

Phase 2 could execute one Codex turn and then stop. Phase 3 adds a durable mission supervisor that can advance through the task keys already fixed in an active Mission Charter.

A single interactive local confirmation authorizes the bounded charter. The supervisor then:

1. Revalidates the active charter revision, branch, task specification fingerprint and expiry.
2. Selects only a DAG-ready task already named in the charter.
3. Runs the existing Codex CLI adapter in a disposable local clone with the existing sandbox and time/output limits.
4. Records the actual isolated changed paths in the existing task ledger as `REPORTED_DONE`.
5. Stops and waits for an independent reviewer to accept or request rework.
6. Requires the exact reviewed isolated diff to be committed to the approved source branch.
7. Advances only after the existing review ledger says `REVIEW_ACCEPTED` and the source handoff is independently reconciled.
8. Repeats within the original charter; completion never implies merge, release or deployment.

The supervisor has a local durable run record, an exclusive OS-released process lock, and an append-only event timeline whose hash covers event metadata as well as payload. The local mission command remains a development CLI; it is not exposed as an MCP action, stable installed command or background service.

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
- Resume the mission command.

The supervisor checks that the source commit is a descendant of the task's original HEAD and that its changed paths and file bytes match the isolated worker output. It does not create the commit itself.

## Explicit limitations

- This is not native Claude Code, Antigravity or IDE subagent spawning. The first adapter is a local Codex CLI process.
- The process is foreground-only. It cannot continue when the terminal/PC is shut down.
- The local approval is operator input, not cryptographic identity proof.
- Task acceptance is never inferred from model output. Independent review and source handoff remain mandatory.
- Failed/ambiguous runs stop for reconciliation; automatic retries and autonomous scope expansion are not enabled.
- Persisted PID values are never killed after a supervisor restart. Possible orphan processes fail closed for manual host reconciliation.
- Model recommendations remain advisory; no model switching, quota claims or fabricated cost/token telemetry.
- Merge, release, publish, deployment, secrets, permission changes, deletion and scope expansion remain outside the charter.

## Verification

Synthetic tests use disposable Git repositories and fake Codex process adapters. They verify a three-task dependency chain under one mission approval, independent review gates, exact source handoff, no auto-acceptance, and append-only event records. Passing synthetic tests does not certify the real Codex host, Windows process-tree behavior, security boundaries, or release readiness.
