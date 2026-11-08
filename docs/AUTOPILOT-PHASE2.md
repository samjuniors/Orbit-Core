# Orbit Autopilot Phase 2 — opt-in local supervisor (development prototype)

**Status: UNRELEASED, NOT ACTIVATED.** This is a *first single-task runner prototype*, not an always-on autonomous founder substitute. It stacks on [Phase 1 Mission Charter](AUTOPILOT-PHASE1.md) and uses only Codex CLI's documented non-interactive interface. No new LLM, cloud executor, scheduler, plugin install, permission bypass, merge or release is provided.

## Capability and trust boundary

The source module is `source/runtime/orbit_autopilot_runner.py`. The developer operator CLI is `scripts/orbit_autopilot_local.py`. It is **not an MCP tool**, background daemon, Windows service, scheduled task or something started by the Universal Setup. It does not start until a local terminal operator requests `run`, reviews a bound plan and types the exact one-task confirmation. This proves a local console interaction, **not cryptographically authenticated founder identity or host approval**.

Preflight checks the ACTIVE, unexpired Mission Charter and revision; immutable registered task-spec fingerprint; exact source Git repository root, non-protected feature branch, clean checkout and commit; DAG dependencies and active reservation conflicts; task attempt limit; and absence of an unresolved runner lease. Caller approval references are not independently authenticated.

For an actual run, Orbit creates a new **isolated temporary Git clone** without Git object hardlinks, verifies the branch and commit, rejects symlinked files and overly large trees, removes the clone's `origin` remote, then invokes only the available Codex CLI:

```text
codex --ask-for-approval never exec --ephemeral --json --sandbox workspace-write -C <isolated-clone> <bounded-task-prompt>
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

## Phase 2 follow-up: review-bound sequential handoff (unreleased)

After a successful isolated Codex turn, `REVIEW_REQUIRED` remains an enforced stop.
A new `review-handoff` developer CLI action **previews** whether the exact
isolated changed paths and file contents have been independently integrated into
a new clean source Git commit on the chartered feature branch. It also requires
the corresponding pre-existing Orbit task-ledger row to be `REVIEW_ACCEPTED`
with reviewer evidence. The recorded source must descend from the run's original
source head, and no unrelated committed path may appear in that reviewed range.

`review-handoff --apply` requires a real local TTY and exact one-run
confirmation. Its append-only runner history retains the previous run ID,
source/accepted commit, changed paths, isolated workspace and reviewer-reported
evidence before clearing the single-run slot. The *next* approved dependency
may then appear in `preview`, but **no second task is auto-executed**; a
fresh explicit operator confirmation remains required to run it. The reviewer
evidence and founder identity are still caller-reported—not authenticated
by Orbit—and a Git content comparison is not independent code QA.

Unsafe, uncommitted, different-content, unrelated-change, stale charter or
unreviewed states HOLD without deleting run state. Existing disposable
Phase 2 databases migrate additively; legacy runs lacking exact source
provenance cannot be silently advanced. This implements a **safe sequential
handoff foundation**, not founder-away multi-task autonomy or an always-on bot.

Synthetic tests cover advancing to a second dependency only after actual
source integration and ledger review, unreviewed/mismatching/denied
runs holding, and headless handoff refusing mutation. CI and genuine
signed-in execution remain separate gates.


## Adaptive Team Builder: read-only v0.32 development slice

The stacked development branch now adds `orbit_team_preview` as a **non-executing** MCP capability. It inspects up to six already registered, exact-revision tasks in one project/root, maps roles to Delivery/Engineering/Quality leads, and proposes task-specific **agent or bot** types. The suggested type is a proposal, not a new process or an activated profile. Delivery/Engineering/Quality are coordination responsibilities, not three additional always-running models.

For each task, Orbit reuses the existing local `orbit_capabilities` inventory and `orbit_skill_plan` fingerprinting logic to propose project-local skill candidates and versioned hash manifests. Candidate skill names, declared project profile and advertised host tools remain **untrusted hints**; no skill text is adopted as instruction, activated, installed or given permissions. The plan may recommend an existing role profile before any new agent profile is drafted. At most two host-native worker reservations are supported by the existing ledger; this preview does not reserve them.

The preview derives bounded agent→agent, agent→bot, bot→agent and bot→bot *handoff proposals* solely from saved task dependencies. Only an upstream `REVIEW_ACCEPTED` task receives the `REVIEWABLE_HANDOFF` gate. A gate is not a sent message, and it is never an authorization to invoke a host worker; real delivery remains Orbit-mediated through accepted task evidence and host permission. Tasks from other project keys or roots are never selected. No new chat store, task DB, worker scheduler, bot executor, deletion API, recursion or founder-away autonomy is introduced.

**Remaining implementation work:** Review-driven staffing requests and explicit charter checks, verified host-native activation, per-worker capability leasing and revocation, structured event persistence/replay using the existing scoped ledger, safe native stop/retire and independent task-level QA. The current design needs real Codex and Antigravity host acceptance and cross-platform release/package testing before any merge or release.


## Charter-scoped team event journal (v0.32 development, NOT activated)

The next review-only Team Builder slice adds `orbit_team_event` alongside `orbit_team_preview`. It reuses the **existing** task ledger and Phase 1 immutable Mission Charter, with a small append-only `orbit_team_events` SQLite audit journal keyed by project root, project and mission. This table is **not** a competing task registry, independent message broker or worker runtime.

- **staff:** A specialist lead can propose a task-scoped agent or bot. Orbit checks an ACTIVE unexpired charter, exact mission revision and feature-branch claim, immutable task specification, role and task revision, and existing tool hints. It prefers existing role profiles. The selected local skill names use the existing skill-discovery inventory and v2 tree/location SHA-256 manifests; a saved staffing request requires a previously previewed exact digest and revalidated pinned manifest. Unavailable, stale or denied skills hold. Delegation, recursive spawn, interrupt and private agent messaging tools cannot be included in worker tool requests. **Requested skills and tools remain untrusted metadata, not activation grants.**
- **handoff:** A source task may request to pass a short untrusted evidence summary to a downstream task only if both belong to the charter, the downstream task directly depends on the upstream one, exact revisions match, and the upstream source is `REVIEW_ACCEPTED` with review evidence. A handoff event is **recorded, not delivered** to another host model/agent or CLI session; that requires a separate authorized adapter and independent source inspection.
- **retire:** A task-level retirement *note* may be recorded only for a terminal task with a previously recorded staffing request, a matching caller-observed host session, and a terminal host-state claim. It does **not** kill a native process, authenticate its true liveness, delete profiles, release a reservation or erase evidence. The host must independently verify stop/cleanup.
- **inbox:** Bounded metadata-only historical query, even when the charter is paused. Stored free-text summaries are never returned as trusted instructions or forwarded to agents by this tool.

All writes are explicit `confirm_write=true` plus an exact reviewed content digest and are guarded by SQLite's immediate transaction with live charter/task revalidation. Event keys are unique; conflicting replays HOLD; duplicate staffing per mission/task and event-budget overflow HOLD. Caller-reported founder approval and claimed host permissions remain **unverified**. No automatic retries, third-party installations, native agent invocation, peer chat loop, unlimited hiring, merge/release/deploy or PC-off continuation.

**Remaining:** real host-native agent/bot activation under per-worker scoped capability leases; actual host authorization and identity; structured host-delivery acknowledgement; reliable native worker stop/reconciliation and retained audit; independently executed Codex/Antigravity acceptance. Existing v0.31 remains unchanged and this milestone stays in a stacked draft PR.


## Worker capability intent and routed receipt protocol (v0.32 development, NOT a grant)

This stacked source extension reuses the **same** `orbit_team_event` MCP and project/mission-scoped `orbit_team_events` journal. It does not add a new MCP surface, task table, chat network, privilege token or worker process. Its three actions are reviewable and recoverable events only:

- **`lease`** produces a worker-specific **capability intent**, not a host-issued lease token. It must point to the exact previously recorded `staff` event, match the task revision while the task is `PLANNED` or `RESERVED`, stay within that staff request's originally reviewed tool names and installed skill candidates, and revalidate the v2 skill tree/location pins against the currently discovered local source. Selected tool names must also be in the caller-reported *current* host inventory; native agent spawning and privileged worker-management tools are blocked. The requested working mode is `read-only` or `workspace-write`, and expiry is limited to 24 hours and no later than the active Mission Charter expiry. Actual host workspace constraints, file permissions, source trust, license acceptance, cost limits and founder approval remain outside this metadata record and must be independently verified/enforced before any native call.
- **`revoke`** writes a separate immutable *host revocation request* pointing to a stored capability intent, including an exact preview digest. It can still be recorded if the mission has paused, stopped or expired, so the audit/request path is not blocked by ordinary mission suspension. It never claims the native host removed the tool grant, cancelled a running session, invalidated credentials or stopped a process. The host adapter must carry out and confirm revocation, and Orbit must reconcile any live task.
- **`receipt`** records a caller-reported downstream native worker acknowledgment of an existing reviewed `handoff`. Orbit requires a recorded recipient task with `RUNNING` status, the exact current revision and matching host-session reference, current `REVIEW_ACCEPTED` upstream dependency and an unread (unacknowledged) handoff event. This does not send the message, independently attest native receipt or constitute downstream QA acceptance. Host/session references remain caller-reported.
- **`inbox`** remains metadata-only. It now includes time-bounded capability-intent statuses and whether a host revocation request was recorded, plus outstanding handoffs lacking a reported receipt. It never exposes raw skill instructions as worker commands or treats an acknowledgment as authenticated delivery.

All new writes use the existing ACTIVE/unexpired/branch/revision-bound charter guard except emergency `revoke`, which accepts a matching mission identity, branch claim and latest charter revision even after pause/stop/expiry. No global permissions, recursive agent spawning, automatic installation, execution loops, auto-merges or self-updating policies have been introduced.

**Host integration still required:** authenticated active host identity and native session inventory; permission-grant adapter with non-bypassable tool allowlists and model quotas; actual per-task tools/skills activation and revocation; explicit host-native handoff delivery and acknowledgment; independent QA and task retirement. A GitHub CI PASS cannot establish any of these live conditions.


## Native Team Dispatch: permission-gated handoff packet (v0.32 draft)

`orbit_team_event(action="dispatch")` is **read-only** and adds no MCP tool, native process, root permission, runner loop or database. It connects the previous separately reviewed `staff` and `lease` events to the existing task-ledger `RESERVED` state and `orbit_swarm_host.review` native-host preflight.

A packet is returned **only if**:

1. The active, unexpired founder Mission Charter still covers the task's immutable scope, caller-declared feature branch and exact mission revision. The exact **unstarted** task is already reserved, has no host session and is at precisely the first revision after the recorded staff/capability request. Old/retried reservations cannot silently reuse a worker capability intent.
2. The referenced staff/lease events have their saved content hashes intact, are for the exact task and host, and the capability intent has not expired or received a revocation request. No other unresolved intent for that task is present. Worker tool candidates are still advertised by the declared host and never include recursive spawning/interrupt/messaging powers.
3. The effective host working mode matches the reviewed capability intent. A read-only intent cannot dispatch a writable task, while writable intents must match the current task write scopes; real alias and conflict checks run through the existing native preflight. Local skill source tree/location SHA pins are rechecked immediately before packet creation.
4. Every task dependency has current `REVIEW_ACCEPTED` evidence and exactly one previously recorded Orbit-routed handoff bound to the accepted upstream revision and the downstream pre-reservation revision; stale or ambiguous handoffs fail closed. The packet includes only event pointers/digests—not arbitrary peer instructions as trusted prompts.
5. `orbit_swarm_host.review` accepts the exact reserved task without another active conflicting reservation, symlink/path escape, exceeded two-worker capacity, unavailable native tool or inconsistent host workspace mode. It returns a validated native invocation hint; **actual availability, consent and execution remain host-controlled**.

The `dispatch_packet` includes the task/mission/host/skill pins, proposed tool **names not grants**, reviewed evidence pointers, exact allowed paths, native host handoff payload and explicit host-side rechecks. It never calls `collaboration.spawn_agent`, Antigravity's `invoke_subagent`, any model, an installer or an OS process. `confirm_write=true` is refused for dispatch; use the existing real host-native tool and then `orbit_task_started` with the genuine returned session. No agent/bot can bypass Orbit's founder/host authority through this API.

**Acceptance still needed:** permission attestation from the actual host, actual native tool invocation and per-worker tool enforcement, native session lifecycle/stop, delivered bounded messages and acknowledgments, hostile-source security tests and signed-in Codex/Antigravity acceptance. Source-level GitHub CI is necessary but does not substitute for these.
