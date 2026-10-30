# v0.27.0 — Orbit-native Agent Swarm: engineering acceptance

**Source scope:** Source integration on `dev/v0.27.0` through reviewed
Project Pulse [PR #49](https://github.com/samjuniors/Orbit-Core-MCP/pull/49),
Swarm [PRs #50–53](https://github.com/samjuniors/Orbit-Core-MCP/pulls?q=is%3Apr+is%3Amerged+swarm)
and reservation safety [PR #54](https://github.com/samjuniors/Orbit-Core-MCP/pull/54),
OS-process/Windows alias hardening [PR #57](https://github.com/samjuniors/Orbit-Core-MCP/pull/57),
and symlink containment [PR #58](https://github.com/samjuniors/Orbit-Core-MCP/pull/58).
**Status:** DEVELOPMENT SOURCE MERGED / AUTOMATED CI PASS; REAL NATIVE DELEGATION,
SECURITY REVIEW, HOST ACCEPTANCE AND RELEASE NOT VERIFIED.
**External reference:** [Claude Swarm](https://github.com/affaan-m/claude-swarm)
(MIT, reviewed as ideas only; no copied code or SDK dependency).

## Product contract

Orbit remains a project-scoped coordinator, never a model provider or
unrestricted agent runtime. Existing M2 `orbit_task_plan`, `orbit_task_reserve`,
`orbit_task_handoff`, `orbit_task_started`, `orbit_task_report` and review
paths remain authoritative for writes, genuine host invocation and acceptance.

The new **`orbit_swarm_preview`** reads *registered* tasks from one normalized
project root and project key. It returns a deterministic **at-most-two**
non-conflicting, dependency-accepted candidate group, plus deferred reasons.
The host must supply its actual native capability and separately authorize
each reservation and invocation. Caller-reported tool names are *not* proof
that host tools are available, permissions were granted or work occurred.

A plan with missing dependencies, cycles, malformed/path-protected tasks,
more than 40 records or preexisting reservations/running records must HOLD.
Other projects' active work at the same root blocks proposals without leaking
their private task names. `REPORTED_DONE` does not satisfy prerequisites;
`REVIEW_ACCEPTED` is local task bookkeeping, not independently verified Git or
test evidence. No inference from timestamps to host liveness.

**Usage example** (read only; never initiates work):

```json
{
  "project_root": "C:/example/my-project",
  "project": "my-project",
  "host": "antigravity",
  "available_host_tools": ["invoke_subagent"],
  "max_parallel": 2
}
```

The preview contains a task revision to pass to `orbit_task_reserve` **only
after** real approval. Before a host invokes a worker, `orbit_task_handoff`
must check live task status, accepted dependencies and reported host capabilities.
Execution and cancellation stay with the authorized host; no automatic
`claude-agent-sdk`, CLI, API key, model switch, billing or sandbox override.

## Acceptance gates

**2026-10-30 handoff:** six feature/fix PRs #49–54 are MERGED into `dev/v0.27.0` (not `main`). The merged source tree SHA `471a0d3e3fd59068c22b8915adcfbed9dec9e8c7` matches PR #54's [cross-platform 5/5 CI PASS](https://github.com/samjuniors/Orbit-Core-MCP/actions/runs/41069244024), including packaged MCP smoke. Current development tool inventory: **45** (three additional read-only Swarm tools over v0.26.0 source); Project Pulse is opt-in on `orbit_project_resume`, not a new tool. This evidence does not certify real host-native parallelism, permission dialogs, security, installer upgrades or publication.


- [x] New project-scope DAG preview with bounded (40-task) reads, cycle/missing
  dependency validation, protected-path and casefolded directory/file overlap
  detection, hard candidate cap of 2, active-host reconciliation HOLD.
- [x] Read-only MCP schema/annotations and explicit no-execution/no-approval
  flags; no added SQLite schema, extra host dependency or background worker.
- [x] 13 focused disposable Windows regression cases; exact PR head and
  packaging matrix must be separately checked before marking CI PASS.
- [ ] Real Antigravity host: register two independent tasks, obtain separate
  approvals, invoke native subagents, inspect real sessions, verify workspace
  scope, capture source diffs and test evidence, review both tasks.
- [ ] Real Codex native `spawn_agent` acceptance, and Claude Code `Agent`/Task
  where actually supported, with denial, unsupported host and serial fallback.
- [ ] Interrupted, crashed and cancelled host sessions: no false completion;
  explicit recovery before next reservation; safe retry and rework.
- [ ] Concurrent and cross-process SQLite reservation/identity stress, Unicode
  and Windows/Linux path alias tests, symlinks, protected controls and scopes.
- [ ] Independent QA tied to exact source revisions, stale-result invalidation,
  partial failure propagation and integration test execution.
- [ ] Measure actual context / usage and user experience, then decide whether
  native host progress visualization is beneficial.
- [ ] Owner review of the feature and next release cutline. No automatic merge
  to main, release tag, deployment or upgrade of installed Orbit.

## Phase 2 — bounded user/host-proposed DAG preflight (stacked feature PR)

**Status: MERGED TO `dev/v0.27.0` via PR #51; real-host acceptance remains NOT RUN.**
The additive read-only `orbit_swarm_draft_preview` MCP tool (44-tool
development candidate) accepts **one to twelve user- or host-proposed
structured tasks** with the same task identity, role, bounded text,
dependencies and protected relative write-path rules as `orbit_task_plan`.
The coding host may draft suggested tasks through its ordinary model, but
Orbit does not call any model or claim that these tasks were generated by
Orbit itself. Custom user tasks are equally valid.

The preflight refuses duplicate or previously registered task keys,
unresolved dependencies, self/cyclic dependencies, unaccepted existing
prerequisites, graphs exceeding 40 combined existing + proposed task nodes,
protected/invalid paths,
and active same-root host reservations that require actual reconciliation.
A validated graph produces **deterministic review waves (maximum two tasks
per wave)**, serializing overlapping scopes and waiting for real
`REVIEW_ACCEPTED` evidence between dependent waves. It never changes
the SQLite ledger, creates tasks, invokes native agents, grants permission
or interprets task text as executable instructions.

**Workflow:** user supplies or edits the draft → read-only preflight →
owner reviews and separately authorizes individual `orbit_task_plan`
registrations → re-read task revisions and perform actual host/native
permission checks → use `orbit_swarm_preview` and normal safe reservations
when suitable. There is **no bulk approval or execution shortcut**.

The following remain OPEN: real IDE acceptance, cross-host agent
delegation, denied permissions and cancellation, stale QA rejection,
cross-process contention, interruption/restart recovery and actual
usage/token measurements. Version `0.27.0` is provisional; no merge to
main or new release is authorized.

## Phase 3 — batch host-native handoff preflight (stacked feature PR)

**Status: MERGED TO `dev/v0.27.0` via PR #52; actual native host execution NOT RUN.**
The new `orbit_swarm_host_preflight` is an all-or-nothing, **read-only**
review of one or two existing, `RESERVED` tasks before the connected host
invokes any specialist. Every selected task must have a fresh revision, no
already recorded host session, valid bounded writable scopes, accepted
prerequisites and an existing `orbit_task_handoff` result of
`HOST_INVOCATION_REQUIRED`. The caller must report host-native tools for
Antigravity, Codex or Claude Code; Orbit never treats those claims as
authenticated capability or permission.

**Fail-closed batch behavior:** If any selected task is stale, missing,
unreserved, running, previously denied, scope-conflicting or has an
unavailable native tool, Orbit returns `HOLD_HOST_PREFLIGHT` with **zero**
runnable handoffs. It also holds if an unrelated task at the same workspace
root still has a RESERVED/RUNNING record; it does not reveal another
project's task identity. Never infer a host worker was stopped from an
MCP restart, timestamp or local status.

**Native host action remains explicit:**
1. Preview proposed specialist tasks; obtain owner approval separately,
   register individually, then reserve each with current revision and
   caller-reported approval reference.
2. Call `orbit_swarm_host_preflight` with each reserved task key and exact
   revision; review its all-or-nothing packets.
3. For EACH packet, the connected host independently checks capability and
   user permission, invokes its true native subagent tool and captures the
   real session reference; use `orbit_task_started` only after invocation.
4. If host permission is denied or invocation fails **before starting**,
   call the existing revision-guarded `orbit_task_release` with
   `HOST_PERMISSION_DENIED`, `HOST_TOOL_UNAVAILABLE` or
   `HOST_INVOCATION_FAILED` and explicit confirmation. Do not reuse
   denied consent.
5. If a task is already RUNNING, inspect the actual host session and
   host-confirmed terminal state before calling `orbit_task_report`.
   No automatic cancellation, process control or silent forced recovery.

**This is coordination guidance, NOT proof of running parallel agents.**
The tool does not spawn agents, grant permissions, write SQLite, enforce
the host's tool registry, measure real token costs or certify test results.
The next mission must test actual host invocation and denial/recovery with
the owner's authorized disposable fixture.

## v0.27 safety follow-up — reservation error privacy and shared SQLite contention

**Feature branch:** `fix/v027-swarm-reservation-isolation` (development only).
`orbit_task_reserve` must reject an overlapping write scope from any active
reservation at the same root, **without exposing other projects' task keys,
private paths or project labels** in a public error. Same-project diagnostics
may identify the conflicting scoped task.

An isolated regression suite uses separate simultaneous SQLite connections to
exercise overlapping writes, disjoint writes within the two-slot cap, duplicate
stale-revision races and cross-project error redaction. The existing
`BEGIN IMMEDIATE` write transaction is reused; no added SQLite table,
permanent file, agent runner or automatic permission is introduced.

**Verification:** [exact integrated-tree CI 5/5 PASS](https://github.com/samjuniors/Orbit-Core-MCP/actions/runs/41069244024) on PR #54, with SHA tree equal to development commit `7420da3675ddc1ffc330192fcc982081722a027d`. This is shared-file, multi-connection concurrency,
**not** evidence of independent OS processes, actual host approval/session
liveness, networked agents or two-PC portability. Those gates remain open.

## Next slices (beyond the validated draft preflight)

1. **Swarm mission input and bounded DAG draft preview:** accept a user-defined
   task decomposition as *untrusted data*, validate schema, roots, cycles and
   file ownership; obtain approval before committing individual task records.
2. **Orchestration state machine:** safe per-host ready queue with genuine
   session evidence, serialized fallback, transactional reservations and
   permission failure handling. Do not spawn from the MCP.
3. **Review and observability:** stale-QA rejection, project-scoped redacted
   history and a compact, accessible progress surface. Reuse Project Pulse
   once its separate PR is reviewed; avoid competing task databases.

**Research/decisions:** Orbit Core's existing Notion Research & References and
Project Decisions hub; do not copy external harness code by default.

## Candidate follow-up — OS-process reservations and Windows alias hardening

**Feature branch:** `fix/v027-swarm-path-alias-process-tests` from exact `dev/v0.27.0` commit `6d3e21f4112f4a98e5dfff9177155e49d408dfc5`.

- Reject writable scope path components ending in dots or spaces, because Windows can resolve those aliases to the same file while the scope comparer otherwise regards them as different paths. Existing casefold/Unicode-normalized collision rules remain in place.
- Add disposable regression tests that launch independent Python interpreters against one SQLite database to check same-scope/Unicode collisions, the two-reservation cap, stale-revision races, cross-project error redaction and unchanged attempts after rejected reservations. No native agents are started or stopped.
- **Verified merged to development:** [PR #57](https://github.com/samjuniors/Orbit-Core-MCP/pull/57) merge commit `ec3f49bf00dcd1c60c7ce5c51f1fff82e24c67f3`; [PR-head CI 5/5](https://github.com/samjuniors/Orbit-Core-MCP/actions/runs/41079246959) and [post-merge development CI 5/5](https://github.com/samjuniors/Orbit-Core-MCP/actions/runs/41081386868) passed on Ubuntu Python 3.10–3.13 and Windows Python 3.12. This is one-machine OS-process coverage; real IDE permission, agents, cancellation, two-PC portability and release gates remain OPEN.

## Merged development hardening — existing symlink scope containment and alias collision

**Branch:** `fix/v027-swarm-symlink-scope-isolation`, based on merged development commit `ec3f49bf00dcd1c60c7ce5c51f1fff82e24c67f3`.

Task registration previews and confirmations inspect current filesystem aliases for proposed writable scopes. Reservation checks again under its SQLite transaction, rejecting links escaping the selected workspace or resolving into protected control files. It also detects when two differently spelled assignments resolve to the same underlying path and holds the second reservation. A native handoff packet is withheld if the assigned path becomes unsafe after reservation. Rejections are generic and do not print external link targets.

**Verification:** [PR #58](https://github.com/samjuniors/Orbit-Core-MCP/pull/58) merged to development commit `7130eb381ccdbc3d1792b55b2889e139385c9dbf`, with [exact-head CI 5/5 PASS](https://github.com/samjuniors/Orbit-Core-MCP/actions/runs/41082050055) on Ubuntu Python 3.10–3.13 and Windows Python 3.12. Linux and Windows Python 3.12 each ran 346 tests, 3 skipped, zero failures, and the seven new symlink tests all passed. [Post-merge dev run](https://github.com/samjuniors/Orbit-Core-MCP/actions/runs/41082365287) is a distinct final integration check; do not claim it passed until verified. This is a point-in-time path guard, **not** a confinement sandbox; a host may mutate symlinks after reservation. Native host sandbox/permission enforcement, real two-PC acceptance, host-session cancellation, integration QA and release review remain OPEN.
