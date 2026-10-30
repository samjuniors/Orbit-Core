# v0.27.0 — Orbit-native Agent Swarm: engineering acceptance

**Source scope:** First independent v0.27.0 engineering slice on
`feat/v027-swarm-dag-preview`, targeting `dev/v0.27.0`.
**Status:** READ-ONLY PLAN IMPLEMENTED; REAL NATIVE DELEGATION NOT VERIFIED.
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

## Next slices (not implemented by this PR)

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
