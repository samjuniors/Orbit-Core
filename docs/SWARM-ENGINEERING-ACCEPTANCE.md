# v0.27.0 — Orbit-native Agent Swarm: engineering acceptance

## 2026-10-31 — release consolidation after Codex recovery fix merge

**Verified source:** focused [PR #66](https://github.com/samjuniors/Orbit-Core-MCP/pull/66)
merged into the `release/v0.27.0-candidate` branch at
`ced0a370040d57d939433b787e6c5ea6e984a460`.
The [exact merge-commit Windows/Linux CI #41175033914](https://github.com/samjuniors/Orbit-Core-MCP/actions/runs/41175033914)
completed **5/5 PASS** on Ubuntu Python 3.10–3.13 and Windows
Python 3.12. Existing v0.26.0 published tag and assets are unchanged.

**PASS — native task work:** Antigravity two independent specialists
created verified `alpha.txt` and `beta.txt`; both task records are
`REVIEW_ACCEPTED` revision 5, with real native transcript IDs in
the original synthetic fixture. Codex spawned two native agents, with
`beta` verified accepted, and `alpha` correctly identified as
an incomplete objective. The Codex recovery fix passed 376 Windows
tests (19 skips, no failures), 46-tool package smoke, original-alpha
ledger **copy-only** replay and the merge-commit CI above.

**PASS — bounded internal safety contract only:** A new isolated
Windows test against this exact merged source exercised Orbit's
`HOST_PERMISSION_DENIED` release, fresh-approval requirement,
pre-invocation `USER_CANCELLED`, unknown/wrong native session
reconciliation HOLD, matching caller-reported terminal cancellation,
and stale-revision rejection. All assertions passed; no denied/cancelled
file was created. These are **synthetic, caller-reported tests**, not
proof that any genuine native host dialog was denied or that a live
worker was interrupted. A separate real Codex CLI read-only session
with approvals disabled left its temporary file absent but produced
**no recorded native command attempt**: host UI denial **NOT VERIFIED**.

**RELEASE GATES STILL OPEN:**
- Genuine Codex/Antigravity *host* approval prompt denied by user
  with confirmed no unauthorized write, distinct from chat refusal
  or a no-write model response — **NOT VERIFIED**.
- Actual native worker cancellation and process/session restart
  recovery with exact session IDs and preserved retry/checkpoint
  history — **NOT RUN** in signed-in hosts.
- Actual installed-user migration/rollback, independent security
  and publisher signing/provenance, second-PC recovery, and other
  supported-host certification beyond the owner-scoped Codex/
  Antigravity acceptance — **NOT VERIFIED / NOT RUN**.
- The separately supported Claude Code host was intentionally
  excluded from this owner-scoped test; **NOT CERTIFIED**.

**Release decision: HOLD / DRAFT PR #63 / NOT PUBLISHED.** Passing
a caller-supplied permission field, synthetic cancellation, CI or
successful native work is not a signed host consent attestation.
Do not automatically un-draft, merge to main or publish while these
gates remain open. The owner must review specific unverified risk
exceptions and explicitly approve a *prerelease* (not a production
certification) if publication is desired before all host tests.


## 2026-10-31 — Antigravity real host acceptance: six PASS, two gates open

**Source tested:** `v0.27.0` candidate at `110de679b16955cc556ecee8aadee0371632326a`,
through a dedicated local Antigravity MCP entry `orbit-v027-acceptance`
with 46 tools. The fixture was the existing temporary directory
`%TEMP%\\Orbit-v027-Antigravity-cf02fc346e\\project`, with its own SQLite
`antigravity-acceptance.sqlite3`. See the preserved readback file
`project/evidence/ANTIGRAVITY-RESULT.md`; it is a host test record,
not a source-controlled assertion.

**Read-only, independent post-test verification (DESKTOP-AND1FUJ):**
- **PASS — 46-tool Orbit connection and read-only previews.** The real
  Antigravity test reported successful `orbit_project_scan`,
  `orbit_swarm_preview(NO_READY_TASKS, agent_spawned=false)` and
  `orbit_swarm_draft_preview(DRAFT_VALIDATED, two disjoint scopes)`.
  An earlier separate protocol invocation using the exact workspace
  MCP command independently confirmed version `0.27.0`, 46 tools and
  read-only `orbit_swarm_preview` with no registered tasks.
- **PASS — actual native specialist sessions and objective files.** The
  actual host reported Antigravity native `invoke_subagent` workers
  `8c74f139-5d5b-4bb7-b74c-034945a7565d` (`orbit-backend`,
  alpha) and `9f2fdee5-6961-417e-a858-287ce6791383`
  (`orbit-frontend`, beta). The **exact two reported native
  transcript files exist** under the host's session directory and
  contain multiple actual recorded events, including test-file path
  mentions. These observations support genuine native host activity;
  they do not attest host permission dialogs.
- **PASS — file contents and size verified independently.**
  `alpha.txt` contains exactly 16 bytes `ORBIT_ALPHA_PASS`;
  `beta.txt` contains exactly 15 bytes `ORBIT_BETA_PASS`.
- **PASS — durable task lifecycle.** A read-only SQLite query of the
  fixture's original database found **two** `orbit_agent_tasks`
  records scoped to the exact fixture project (`orbit-acceptance`),
  each `REVIEW_ACCEPTED` revision 5, changed paths respectively
  `["alpha.txt"]` and `["beta.txt"]`, and native session values
  matching the two reported transcript IDs. Each task has one
  persisted attempt with host-reported completed disposition.
  This independently supports the host report's transitions
  `PLANNED → RESERVED → RUNNING → REPORTED_DONE → REVIEW_ACCEPTED`.
- **Conversation refusal respected, but host UI denial NOT VERIFIED.**
  The owner explicitly **DENIED** the separate `task-denied`
  proposal in chat; no corresponding task exists in the ledger and
  `denied.txt` is absent. **No native IDE permission prompt was
  denied**; therefore permission enforcement is NOT VERIFIED and must
  not be called a host-security PASS.
- **Cancellation/restart NOT RUN** by explicit scope; the owner did
  not authorize native worker interruption. Interactive denial and
  cancellation/recovery remain open for Codex/Antigravity.
- Original fixture files, database, and native transcripts were only
  **read** in the independent verification. No global host
  configuration, installed user environment, permission grant,
  or two-PC recovery received production certification from this test.

**Gate summary:** Antigravity gates 1–6 **PASS (verified)**;
gate 7 **NOT VERIFIED**; gate 8 **NOT RUN**. Codex separately
passed a real native two-worker run with beta accepted, but alpha
blocked and a supposed denial action **actually approved**. The
focused guarded alpha reconciliation is staged in
[PR #66](https://github.com/samjuniors/Orbit-Core-MCP/pull/66),
base `release/v0.27.0-candidate`, and its exact original
Windows/Linux CI was **5/5 PASS**. Do not confuse CI, genuine native
execution, user-chat denial, and host permission enforcement.
The v0.27.0 **release remains on HOLD / PR #63 remains a draft**;
nothing here authorizes silent merging or publication.

## 2026-10-31 — real approved Codex two-worker acceptance: recovery gap reproduced

The owner explicitly approved synthetic Codex task registration, reservation,
native execution, task report and evidence writing in a TEMP-only project. The
actual host returned `/root/alpha` and `/root/beta` from native subagent
spawns; `orbit_task_plan` and `orbit_task_reserve` succeeded for both,
and preflight/handoff requested actual host invocation.

**Verified original v0.27.0 fixture evidence:**
- **BETA PASS (limited):** actual worker completed, `beta.txt` exists
  and independent file read returned `ORBIT_BETA_PASS` (15 bytes); Orbit
  marked beta `REVIEW_ACCEPTED`, revision 5. These are task/objective
  acceptance results, not a native UI permission attestation.
- **ALPHA BLOCKED:** worker `/root/alpha` ended without writing;
  independent lookup of `alpha.txt` returned ENOENT. Orbit's
  `orbit_task_report` rejected `outcome=BLOCKED, host_state=COMPLETED`
  as `HOLD_HOST_RECONCILIATION`, leaving alpha `RUNNING` at revision
  3. This is a host-end-versus-task-objective mismatch, not proof the
  worker is still active.
- **DENIAL NOT VERIFIED / intended no-write FAIL:** an escalated
  permission request to create `permission-denied.txt` was **approved**,
  not denied; the command returned exit 0 and the file exists containing
  `ORBIT_PERMISSION_TEST`. An approval does not exercise or prove
  refusal enforcement. No new denial result was assumed.
- **Host shell BLOCKED:** ordinary Codex exec intermittently failed
  `CryptUnprotectData failed: 2148073483`; no credential bypass
  attempted. Cancellation and restart **NOT RUN**.
- The exact original SQLite attempt records, files and evidence were
  preserved. No direct database edits, deletions or fake host states
  are authorized by this report.

**Candidate fix merged into this v0.27 candidate by PR #66:**
Allow a native session with observed state `COMPLETED` to report an
**incomplete objective** as `BLOCKED` only with matching exact session,
`objective_completed=false`, zero reported changed paths, explicit
evidence and `confirm_write=true`; retain original host session, attempt
history and `HOST_REPORTED_NOT_ATTESTED` boundaries. The failed objective
cannot be reviewed ACCEPTED. Any subsequent `BLOCKED` retry requires
a *fresh* approval reference, not reuse of a previous permission grant.
Missing, mismatched or ambiguous evidence **HOLD** and does not unlock
the task's active write scope.

The fix passed nine focused regressions, the full Windows suite (376 tests,
19 skipped, zero failures), and [exact-head Windows/Linux CI 5/5](https://github.com/samjuniors/Orbit-Core-MCP/actions/runs/41172499805).
The source fix was integrated after owner request and exact-head 5/5 CI; genuine host safety acceptance remains separate. Applying the fix
to the **original alpha SQLite row** is a separate, explicit,
human-authorized host-state reconciliation; do not silently manipulate
the user's test ledger. Genuine denial and host cancel/restart checks
remain required for acceptance. See existing release gate below.

## 2026-10-31 — focused Codex + Antigravity follow-up (owner-scoped test round)

The owner narrowed **this acceptance round** to Codex and Antigravity.
Claude Code is **not in scope for this round**; its existing unverified
support/permission limits are **not certified or silently waived**.

**Codex native subagent evidence upgraded to PASS (limited):**
- With Codex CLI `0.154.0`, `multi_agent=true`, a **normal
  non-ephemeral** read-only Codex session actually called the native
  `spawn_agent` tool and subsequently `wait_agent` twice, each on a
  distinct synthetic microtask (uppercase `orbit` and count its
  characters). The concise `codex exec --json` stream omitted the
  `spawn_agent` item even though the full session rollout **did contain**
  the `response_item/function_call` and successful
  `response_item/function_call_output`. The spawn responses contained
  independent task names `/root/uppercase_specialist` and
  `/root/count_orbit`; the wait responses recorded completion.
- Targeted read-only queries of Codex's `thread_spawn_edges` table
  showed **one concrete child thread attached to each exact parent
  synthetic session**. Both child rollout files exist, contain an actual
  assistant message and a child-result event. This is independent
  proof of native child execution, not merely a model assertion.
  The links remained `open` in the session table; terminal cancellation,
  explicit child shutdown/recovery and integration with Orbit task
  review are **not certified**.
- An earlier ephemeral `codex exec` attempt failed
  `no thread with id`; the normal run avoided that host CLI lifecycle
  failure. Upstream Codex [JSON event omission #34919](https://github.com/openai/codex/issues/34919)
  and [ephemeral thread failure #41474](https://github.com/openai/codex/issues/41474)
  are external diagnostic references only, not Orbit dependencies.
- Separately, the candidate `orbit_swarm_preview` MCP tool ran inside
  signed-in Codex and returned `NO_READY_TASKS` for an empty synthetic
  project, explicitly `agent_spawned=false` and
  `approval_verified=false`. This does **not** establish integrated
  Orbit reservation/handoff/native-worker/task-report review or host
  consent; these gates remain **NOT VERIFIED**.

**Antigravity synthetic acceptance fixture PREPARED, host UI NOT RUN:**
- On the connected Windows PC, cloned exact candidate
  `8fb603764590b7786e6c920596d6f4a5dc5ebf1b` into a new temp
  folder `%TEMP%\\Orbit-v027-Antigravity-*\\source`, and created
  separate `project`, `evidence`, and workspace-local
  `.agents/mcp_config.json` with a single
  `orbit-v027-acceptance` stdio server. Only that temp project is an
  allowed trusted root, with a dedicated temp SQLite database; **no
  global Antigravity MCP config or existing project was changed**.
- Direct JSON-RPC initialize/tools-list of that exact workspace
  config **PASS**: runtime version `0.27.0`, **46 tools** and
  `orbit_swarm_preview` present.
- Inside the fixture, `ANTIGRAVITY-ACCEPTANCE.md` provides a
  reviewed, scoped end-to-end plan: native host tool discovery,
  two independent worker tasks, real permission approval and deliberate
  denial, result evidence, and optional cancel/restart. The agent must
  record actual observed evidence in
  `evidence/ANTIGRAVITY-RESULT.md`, which currently says NOT RUN.
  Antigravity was running on the PC but its interactive permission
  screen was **not controlled** from the terminal-only connection;
  an attempted new-window launch did not establish that this fixture
  was actually opened. A real user-host IDE session remains needed.
- The tests above never authorize unattended native tool approval or
  changes outside the disposable project.

**Gate status:** Codex `spawn_agent`+child result **PASS (native smoke)**;
Codex full Orbit lifecycle and permission-denial/cancel/resume
**NOT VERIFIED**. Antigravity fixture/MCP protocol **PASS** but real
IDE native-worker/approval/denial/cancellation **NOT RUN**. No merge,
publication, or production certification authorized by this evidence.

## 2026-10-31 — real coding-host CLI acceptance (PARTIAL PASS; RELEASE HOLD)

**Test source:** `release/v0.27.0-candidate` at
`24dbc7c99bcc88386ca7416111646122b02aea6e`, Windows
build 26200; Python 3.12.10, Codex CLI 0.154.0, Claude Code 2.1.307.
All testing used an isolated `%TEMP%/Orbit-v027-RealHost-*` synthetic
project, a temporary project-specific stdio MCP configuration and
non-persistent/read-only host commands. The existing installed Orbit,
personal IDE configurations and real projects were not modified.
Antigravity was running, but its permission UI was not available through
the terminal-only access in this session.

| Gate | Actual observed evidence | Status |
| --- | --- | --- |
| Codex genuine MCP connectivity | `codex mcp list` recognized temporary `orbit_v027`. A signed-in Codex session actually called `orbit_swarm_preview` once; its tool event ended `completed` and the returned result was `NO_READY_TASKS` with zero tasks, `agent_spawned=false`, `approval_verified=false`, `host_liveness_verified=false`. | **PASS — read-only MCP invocation only** |
| Codex native delegation | A separate read-only `spawn_agent` probe exposed a native host tool, but actual invocation failed with `no thread with id: ...`. No worker was created or accepted. This was an `--ephemeral` CLI session; check whether the failure is a CLI/session limitation before attributing it to Orbit. | **BLOCKED — no successful worker** |
| Claude Code genuine MCP delegation | `claude auth status` reported a connected OAuth session, but a print-mode MCP session returned `authentication_failed` / `Not logged in — Please run /login`; an ordinary one-turn read-only authentication probe then timed out after 50 seconds. No actual Claude MCP/Agent invocation or consent prompt was observed. Do not change user tokens or auth settings without approval. | **BLOCKED — host authentication/session** |
| Antigravity native UI and permissions | Antigravity running, but no authorized GUI control to inspect real agent approval/denial or session lifecycle. No claims of successful delegation. | **NOT RUN** |
| Disposable install and uninstall | `orbit_setup.py` preview, explicit `install --apply`, uninstall preview and `uninstall --apply` all exited successfully in a fake current-user profile and disposable project. Custom `AGENTS.md`, `.orbit/STATE.md` and local memory sentinel survived unchanged. | **PASS — isolated setup/uninstall data preservation** |
| Candidate archive hygiene | Local 0.27.0 ZIPs passed byte/checksum sidecars, ZIP member path/duplicate/symlink and selected sensitive-filename checks; Claude Desktop MCPB contained expected source metadata and is SHA256-hashed by the official release workflow at publication, not by source ZIP builder. | **PASS — bounded content checks, not provenance/security certification** |
| Actual native permission denial, cancellation/restart, two worker integration and owner-installed rollback | Not performed. Caller-reported approval fields and a successful read-only MCP call do not certify permission UI or native worker outcomes. | **NOT VERIFIED** |
| Cross-computer recovery | Second enrolled PC offline during test; no two-PC transfer run. | **NOT RUN** |
| Independent security/provenance sign-off | No signed publisher attestation or independent assessment. The existing security Issue #9 remains open for these risks. | **NOT VERIFIED** |

**Decision: HOLD.** Automated [exact-head CI 5/5 PASS](https://github.com/samjuniors/Orbit-Core-MCP/actions/runs/41168999283),
367 local tests (19 skips, zero failures), 46-tool disposable ZIP/MCP
smoke and published v0.26.0→candidate upgrade regression remain valid.
This new testing adds authentic Codex **MCP discovery and read-only use**
and disposable setup/uninstall evidence; it does **not** close native
delegation, denied-permission, cancellation/recovery or independent
security gates. Before un-drafting PR #63 and publishing, resolve
Codex native spawn thread failure, establish Claude Code signed-in
MCP session, observe actual approval/denial and worker completion in
at least the supported hosts, and validate a real-user-like backup
and rollback/restart in an isolated host profile.


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

## 2026-10-31 — Reconciled v0.27.0 release-candidate evidence

**Source status: DRAFT release candidate, NOT published / NOT production-certified.**
The original `dev/v0.27.0` 46-tool Swarm work and prior candidate were
reconciled through a normal Git merge with reviewed [v0.26.0 published
`main`](https://github.com/samjuniors/Orbit-Core-MCP/releases/tag/v0.26.0)
and merged release-quality [PR #65](https://github.com/samjuniors/Orbit-Core-MCP/pull/65).
See [draft release PR #63](https://github.com/samjuniors/Orbit-Core-MCP/pull/63),
now based on `main`, and integration merge SHA
`00c2d978a9b52cc2ceafb6d6fd802e369fdd5761`. All v0.26.0
published tag/assets are preserved; `VERSION=0.27.0`,
`NEXT_VERSION=0.28.0`. The release guide, structured public
`CHANGELOG.md` notes, desktop metadata normalization and CI/publication
readiness validator were retained from PR #65.

On connected Windows Python 3.12.10 in an **isolated TEMP checkout**:
- **PASS:** 367 unit tests, 19 skips, zero failures; release readiness,
  strict desktop version/source parity, all three versioned ZIP builds and
  the extracted ZIP stdio smoke test exposing **46 local MCP tools**.
- **PASS:** New disposable upgrade rehearsal from the **actual immutable
  v0.26.0 tag** to the v0.27.0 candidate, retaining customized `AGENTS.md`,
  `.orbit/STATE.md`, prior database bytes and the old versioned runtime.
  The regression first caught a missing recognized stock hash for the
  official v0.26.0 `TASK-LIFECYCLE.md`, which was fixed via a **single
  exact SHA-256** after confirming the immutable tag content. Existing
  owner-edited stock still blocks upgrade as designed.
- **PASS (bounded):** No actual personal host registration, installed Orbit,
  owner project, SQLite memory or native IDE permission state was modified.
- **NOT VERIFIED:** The final exact PR-head Windows/Linux CI and authentic
  native subagent/permission, installed-user rollback, security/provenance
  and second-computer acceptance must still be checked independently.

This record distinguishes **software automated PASS** from **host/production
acceptance NOT VERIFIED**. The next release must not be published solely
because a source branch or packaged MCP smoke test passed.

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

**2026-10-30 handoff:** six feature/fix PRs #49–54 are MERGED into `dev/v0.27.0` (not `main`). The merged source tree SHA `471a0d3e3fd59068c22b8915adcfbed9dec9e8c7` matches PR #54's [cross-platform 5/5 CI PASS](https://github.com/samjuniors/Orbit-Core-MCP/actions/runs/41069244024), including packaged MCP smoke. At that historical #54 checkpoint there were **45** development tools. **Current development inventory is 46**, including the additive read-only source-bound integration review (#61); Project Pulse is opt-in on `orbit_project_resume`, not a new tool. This evidence does not certify real host-native parallelism, permission dialogs, security, installer upgrades or publication.


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
- [x] Disposable CI checks for cross-process SQLite contention, Unicode/casefold
  aliases, Windows trailing-dot/space and symlink/protected scope validation
  (PRs #57–58); not equivalent to two-PC or live-host acceptance.
- [ ] Real multi-host/two-PC recovery, host-path behavior and permission review.
- [x] Source/preview-bound browser freshness, read-only task integration
  readiness, and transitive failure/rework propagation in disposable CI
  (PRs #60–61). Local records remain caller-reported and unverified.
- [ ] Real source-bound *integration test execution* and independently observed
  native-host QA, session cancellation and review.
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

## Remaining acceptance after source development

1. Test actual Antigravity, Codex and Claude Code host-native parallel workers,
   scoped approvals/denials/cancellation/restart, and serial host-lead fallback.
2. Run real independent combined-task integration tests against the exact
   Git/source revision; inspect Git diffs and browser/native QA in the host.
3. Measure Project Pulse UX and actual model context in signed-in hosts; verify
   two-PC portable recovery, installer migration/rollback, security and release
   provenance. Do not infer these results from disposable CI.

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

**Verification:** [PR #58](https://github.com/samjuniors/Orbit-Core-MCP/pull/58) merged to development commit `7130eb381ccdbc3d1792b55b2889e139385c9dbf`, with [exact-head CI 5/5 PASS](https://github.com/samjuniors/Orbit-Core-MCP/actions/runs/41082050055) on Ubuntu Python 3.10–3.13 and Windows Python 3.12. Linux and Windows Python 3.12 each ran 346 tests, 3 skipped, zero failures, and the seven new symlink tests all passed. [Post-merge dev CI 5/5 PASS](https://github.com/samjuniors/Orbit-Core-MCP/actions/runs/41082365287) verified the exact integrated development commit `7130eb381ccdbc3d1792b55b2889e139385c9dbf` on Ubuntu Python 3.10–3.13 and Windows Python 3.12. This is a point-in-time path guard, **not** a confinement sandbox; a host may mutate symlinks after reservation. Native host sandbox/permission enforcement, real two-PC acceptance, host-session cancellation, integration QA and release review remain OPEN.

## v0.27 development follow-up — failed prerequisites, path aliases and serial fallback

**Candidate branch:** `feat/v027-swarm-recovery-readiness`, based on verified
`dev/v0.27.0` HEAD `3976ada5a046eb5c8acedda06a96af2236bfa8b4`.

- The existing read-only `orbit_swarm_preview` now distinguishes a direct or transitive
  `FAILED` / `REWORK` / `CANCELLED` / `BLOCKED` prerequisite from a merely
  unreviewed `REPORTED_DONE` task. Dependent tasks HOLD until a reviewer
  actually accepts the prerequisite; independent ready work can still proceed.
- Scheduling proposals compare both lexical and current resolved writable path
  scopes, and HOLD rather than expose symlink escapes. Reservations and native
  handoffs remain separately checked; resolution is not host sandboxing.
- Without a supported reported native agent tool, one deterministic candidate
  is offered as `MANUAL_SERIAL_REVIEW_ONLY`, not a running task or permission.
  The host lead must obtain separate actual authorization, implement only within
  scope, inspect real tests and record the outcome honestly. No automatic status
  transition, fabricated worker, reservation or third-party fallback runner.
- **Candidate verification:** six disposable regression cases; source/CI
  verification is pending. Do not claim live host consent, test execution, cost
  savings or project completion from this proposal-only response.

## v0.27 — source-bound Swarm integration QA gate (merged development source)

**Branch:** `feat/v027-swarm-source-bound-integration-gate`, based on
`89afb04a0811cb2fa42c1042f1cde8c6cb4362fd`.
The additive read-only `orbit_swarm_integration_review` checks up to 12
revision-guarded `REVIEW_ACCEPTED` tasks against the **current bounded
local source snapshot**, per-task scoped `changed_paths` and accepted
dependencies. Any same-root active reservation or running record, even under
another project key, requires genuine host reconciliation first without
exposing private task identities. For a web build, it also requires the latest existing
`browser_results` PASS to be source-matched, interactive, unblocked and
consistent with the same project's build. Source changes or newer FAIL
records invalidate an older PASS. An unavailable/unscannable source, no
recorded QA, stale revisions or malformed evidence HOLD rather than
claiming success. No new persistent table, network call, executable tool,
agent, model or project write.

A positive result is **`READY_FOR_INDEPENDENT_REVIEW`** rather than
PASS or verification. Neither host permission nor session, Git diff,
native mobile QA or test execution is authenticated by these local
records; the host/human must independently run tests and inspect source
changes. Actual browser QA already belongs to the existing
`orbit_browser_qa` path; this new read-only tool never runs it.
Native Android/iOS/desktop QA remains a separate host review gate.

**Verification:** [PR #61](https://github.com/samjuniors/Orbit-Core-MCP/pull/61)
MERGED to `dev/v0.27.0` commit `0d231b3508cf7c69bef85412a8efb2f02c714382`.
[Exact PR-head CI 5/5 PASS](https://github.com/samjuniors/Orbit-Core-MCP/actions/runs/41085894528)
on Ubuntu Python 3.10–3.13 and Windows Python 3.12 (361 tests,
3 skips, zero failures on Ubuntu 3.12). The separate [post-merge dev CI](https://github.com/samjuniors/Orbit-Core-MCP/actions/runs/41086243865)
requires final verification. The development inventory is 46 tools;
no release or real-host integration acceptance is implied.
