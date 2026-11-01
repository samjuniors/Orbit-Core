# Orbit v0.30 — host-native coordination preview

**Status:** development source only. The existing host invokes real coding
agents and controls permissions. Orbit is **not** a model, agent runner,
automated installer, owner-approval authenticator, Git merge bot or release
publisher. No source changes, reservations, sessions or test results are created
by this tool.

## Why this entry point exists

Orbit v0.28 supplies adaptive software-delivery blueprints, v0.27 supplies
task/DAG/host preflight, and v0.29 supplies a read-only installed-skill review.
Previously the lead agent had to manually reconstruct which of those existing
tools to use after a plan or during restart. `orbit_native_coordination_preview`
is a **bounded, read-only decision bridge** over those exact existing tools.
It neither bypasses them nor introduces a second task ledger.

Use it only with an already selected and authorized `project_root` and
project key, the real current Git/source state and caller-reported host
tool names. Recover the project before planning. A missing native host tool
does not authorize external CLIs, another model or a fake subagent session.

## Three modes (one tool)

1. **Draft**: Pass `draft_tasks` (1–12 full task records with role,
   goal, reason, dependencies and explicit safe writable paths). Reuses the
   existing `orbit_swarm_draft_preview` validator and 2-worker wave scheduler.
   Returns `DRAFT_REVIEW_REQUIRED` and preview-only `orbit_task_plan` input
   with `confirm_write=false`, or `HOLD_DRAFT_REVIEW` with no registration
   suggestions. Registration suggestions are now ordered according to the
   draft's validated dependency waves, **not alphabetical task keys**;
   registration order is a convenience, not permission to execute or accept
   the later waves. The owner and actual IDE must inspect real file ownership,
   requirements and task scopes, then explicitly register one task at a time.
   Never copy a blueprint's empty scopes into writable engineering work
   without checking what each worker will actually change.
2. **Registered task ledger**: Omit both `draft_tasks` and
   `reserved_tasks`. Reuses `orbit_swarm_preview`, task ledger and
   independent review history. A safe ready wave returns
   `RESERVATION_REVIEW_REQUIRED` with up to two exact keys/revisions,
   role/scope and `confirm_write=false`; no approval reference is created.
   Actual `orbit_task_reserve` happens separately after genuine owner/host
   authorization. Pending reported tasks return
   `INDEPENDENT_TASK_REVIEW_REQUIRED`; all reviewed tasks return
   `INTEGRATION_REVIEW_REQUIRED`, **not** test PASS or permission to merge.
   The complete accepted-task inventory is grouped into
   `integration_review_batches` of at most 12 tasks, matching the separate
   `orbit_swarm_integration_review` gate limit. Even a 40-task project must
   review **every batch** against an independently obtained, consistent source
   fingerprint, actual changed files, executed tests, source ownership and
   host QA. The coordinator never calls the integration tool itself and
   `integration_batches_reviewed=false` until independent review occurs;
   no batch or all-task list grants merge/release authority.
   Failed, blocked, rework or cancelled work returns bounded
   `recovery_reviews` with only task key/revision, state, a safe next-action
   classification and explicit `retry_authorized=false`. If nothing is
   runnable, the coordinator returns `RECOVERY_REVIEW_REQUIRED`, not a
   generic or silently retried task. Unrelated approved planned work may
   remain eligible while failures get reviewed; cancelled work remains
   cancelled until the owner explicitly scopes a **new** task. Raw past
   notes, consent references and historical host session IDs are not echoed.
   Interrupted running/reserved sessions and root-sharing work from other
   projects return HOLD without disclosing those other projects' identities.
3. **Reserved host preflight**: Pass `reserved_tasks` (1–2 exact keys and
   fresh revisions) alongside the reported `host`,
   `available_host_tools` and `host_workspace_mode`. Reuses the existing
   all-or-nothing `orbit_swarm_host_preflight` checks. Only after all selected
   reservations pass does it return the original host-native handoff packets
   and `HOST_INVOCATIONS_REQUIRED`. If a task is stale, already running,
   unreserved, conflicts on a real/path-alias scope, violates read-only
   permissions or lacks a native tool, **no partial handoffs** are returned.
   The connected host uses its own real `invoke_subagent`, `spawn_agent`,
   or `Agent/Task` interface; only after receiving the genuine host session
   should it separately call `orbit_task_started` with a fresh revision.

The tool accepts `max_parallel=1|2` (default 2) and never permits more
selected reserved tasks than that width. A host can always choose fewer workers
when the task is small, unsafe to parallelize or native tooling is absent.

## Responsibilities and failure recovery

- `orbit_task_report` requires the exact observed host session and a valid
  actual terminal state; `orbit_task_review` requires separately inspected
  source diff, changed files, actual QA and relevant acceptance evidence.
  The MCP cannot inspect the private IDE session or attest reported results.
- A task is not ready merely because a model claims it completed. A
  `REPORTED_DONE` record needs independent review; dependencies only unlock
  after `REVIEW_ACCEPTED`. Failed, reworked and blocked tasks are **not**
  offered for automatic native invocation. Diagnose host failures, partial
  source changes and test evidence before a separately authorized attempt.
  The task ledger rejects replaying the previous approval reference for
  `FAILED`, `REWORK` and `BLOCKED` reservations; a new caller reference
  is still **not cryptographic proof** of actual host/user consent. `CANCELLED`
  remains non-retryable as the same task.
- An interrupted `RESERVED` or `RUNNING` state must be reconciled with
  the actual IDE; no automatic timeout, worker termination, cancellation,
  resurrection or fabricated session is allowed. An unavailable native tool
  gives only a permission-gated manual serial fallback.
- For an accepted wave, use real source fingerprints, independent platform
  tests, QA/security and `orbit_swarm_integration_review` before integration.
  The existing integration gate checks **web browser QA** tied to source and
  build revision. When the build is still in `BROWSER_QA`, the latest QA record
  must match its current revision; after a successful transition to a later
  stage, it must carry an explicit recorded `BROWSER_QA` PASS transition.
  Source-matching QA from a different active build revision must HOLD.
  The gate checks local records only and cannot independently certify
  actual Git/host activity. **Native/mobile/desktop/CLI QA is not browser
  QA**: select explicit `qa_mode=native` or `qa_mode=host` for the
  matching frozen build flow, with source-pinned host-reported QA evidence;
  independent target-platform test review remains mandatory. Actual
  merge/publish remains a separate owner decision.
- `include_skill_review=true` only suggests later **read-only**
  `orbit_capability_select` checks for ready task objectives; the actual host
  must inspect the codebase, declare truthful product/platform/technology,
  inspect complete third-party skill text/license and separately authorize any
  activation. For hosts the skill selector does not recognize (such as
  generic VS Code), the hint uses `host=unknown` and
  `host_fit_unverified=true`, not a fabricated compatible IDE provider.
  This preview installs/loads no skills.

## Native-platform and CLI QA integration — source-pinned host evidence

Select the existing `orbit_swarm_integration_review` **`qa_mode`** for the
actual frozen build flow, not by guessing that a browser or native SDK ran:

- `web` (default, backwards compatible): the selected build must include
  `BROWSER_QA` and the latest Orbit-recorded Playwright browser result must
  match current source and build revision/recorded passing transition.
- `native`: for a build whose frozen flow includes `NATIVE_QA` (normally
  mobile/desktop). The actual IDE runs approved platform-specific commands,
  real device/emulator interaction and accessibility checks. The host records
  a structured `orbit_build_advance` `NATIVE_QA` PASS containing **1–3
  platforms** drawn from Android/iOS/macOS/Windows/Linux, **1–8 actual command
  strings with reported zero exit codes**, and bounded interaction and
  accessibility observations. The build ledger pins the **current bounded
  source fingerprint** and **exact pre-advance build revision**, and records
  `host_execution_attested=false`. Only after the build advances beyond
  `NATIVE_QA` may the integration gate return
  `READY_FOR_INDEPENDENT_REVIEW`. Legacy unpinned QA, changed source,
  invalid reports or unavailable SDKs remain HOLD.
- `host`: for CLI, SDK/library, API, OS-platform and other **non-browser**
  builds whose frozen flow contains `VERIFY` but neither `BROWSER_QA`
  nor `NATIVE_QA`. Record structured `VERIFY` PASS with real host-observed
  command/exit-code, edge-case and security notes. The same source/revision pin
  is saved by `orbit_build_advance`; `orbit_swarm_integration_review`
  checks it only after the build advances beyond VERIFY. A scoped native fix
  that uses the shorter VERIFY lifecycle belongs to this mode, not a
  fabricated NATIVE_QA or browser run.

An explicit `build_id`, exact selected-project task revisions and
`expected_source_fingerprint` are required for every mode. Native/host
build-stage evidence is additionally pinned to the exact `qa_project`,
`qa_build_id` and `qa_stage` so copying a matching source/QA report into
a different build cannot silently pass integration. Damaged frozen-flow
metadata, invalid platform types, malformed feedback or unsupported QA modes
must HOLD or reject cleanly; old unpinned reports need new real host evidence.
These pins are consistency checks, **not** cryptographic proof of host
permission or test execution. The `integration_review_batches` proposals
label the supported choices and require the host to inspect the persisted
build flow before selecting one. No automatic batch invocation occurs. A web QA record **cannot
substitute** for native/host verification; a host/native QA record cannot
substitute for Playwright browser QA in a web flow.

The structured platform and command fields are **caller-reported evidence**:
Orbit cannot independently tell whether a terminal command executed, whether
an emulator/device was used, or whether the output was reviewed. Even if the
bounded source and build revision match, the strongest status is
`READY_FOR_INDEPENDENT_REVIEW`, with `tests_independently_verified=false`,
`actual_platform_execution_verified=false` and `merge_performed=false`.
The host reviewer still inspects real command output, source diff, target
OS/SDK/device version, permission prompts, regressions, credentials/security
and user acceptance. The source snapshot is **not** a Git-commit signature
or a complete install/runtime attestation.

The current built-in NATIVE_QA evidence validator has a known bounded
five-platform list. Embedded targets, console/game-engine runs, or an
unsupported host/SDK must be explicitly documented as BLOCKED/NOT RUN until
an appropriate platform-specific acceptance path is independently reviewed.
Do not silently relabel them Android/web merely to make a gate succeed.

## Suggested source-only sequence

```text
orbit_project_resume
  -> orbit_software_delivery_preview (only for substantial work)
  -> orbit_native_coordination_preview(draft_tasks=[...])
  -> owner reviews actual repo, task scopes, and specialist responsibilities
  -> orbit_task_plan individually (confirmed only after consent)
  -> orbit_native_coordination_preview() for registered tasks
  -> orbit_task_reserve individually (confirmed only after consent)
  -> orbit_native_coordination_preview(reserved_tasks=[...])
  -> connected host invokes its actual supported native tool
  -> orbit_task_started (only with real returned session)
  -> orbit_task_report (only with observed terminal state)
  -> independent source/diff/test review, then orbit_task_review
  -> next approved wave, integration gate, separate release authorization
```

**Quality state:** source and synthetic regression cases are authored on a
v0.30 draft branch. The owner postponed automated and real-host acceptance;
the presence of regression tests or tool annotations must not be reported as
executed PASS. Windows, Linux, real Codex/Antigravity/Claude invocation,
permission-denial and recovery acceptance remain pending. No v0.30 release
exists from this development work.
