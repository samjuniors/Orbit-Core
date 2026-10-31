# Orbit v0.28 — adaptive software delivery with native specialist roles

**Status:** development-source capability; real host execution and permissions
remain distinct. This is an Orbit-native implementation inspired by
[affaan-m/ECC](https://github.com/affaan-m/ECC) patterns, not an ECC install,
fork, command runner, copied agent library, or external model backend.

## When to use

For a substantial new product, stalled project, feature, redesign or defect:
resume the existing Orbit project first; verify the current branch, source,
tests, approved intake and relevant historical decisions. For small changes,
use a focused plan and targeted tests instead of an all-product workflow.

Call `orbit_software_delivery_preview(project_root,project,objective,product_type,
operation,maturity,constraints)` with truthful user decisions. If
`product_type` is omitted, the tool only reuses an actually approved intake;
otherwise it returns `NEEDS_PROJECT_CLASSIFICATION`. The result is a
**read-only proposed delivery plan**, not a validated requirement, agent
invocation, accepted design, running service or release-ready product.

## Read the return values carefully

- `proposed_tasks`: a bounded 9–12-task DAG for the first useful **end-to-end
  vertical slice** and its implementation/verification/release handoffs. Tasks
  use actual existing Orbit specialist roles, not ECC model names.
- `acceptance_contracts`: what each role must prove with actual files,
  diffs, commands, accessibility evidence, user review and host approvals.
- `draft_review`: real Orbit draft-DAG validator result. **HOLD**
  on existing task-key collisions, unreconciled running agents or oversized
  graphs; do not silently overwrite project state.
- `write_paths=[]` on EVERY task: intentionally **no writable source scope
  is inferred** from an unfamiliar codebase. The host and owner must
  select paths after actually inspecting the repo. For read-only tasks,
  keep empty paths. For write tasks, specify real bounded paths.
- `implementation_ready=false`, `agent_spawned=false`,
  `approval_verified=false`, `model_selected=false` and
  `tests_verified=false` are honest state boundaries.

## Approved software creation flow

1. **Discover & approve.** Resume and audit project/source first. Review
   proposed user requirements, stack, data/privacy, architecture, UX and
   non-goals. Owner approves the first *vertical slice* and the permission
   boundary; ask one consequential question if essential.
2. **Scope and register.** Adjust specialist tasks/roles/dependencies to the
   verified project (web/mobile/desktop/API/CLI/plugin/game or other),
   assign bounded non-overlapping write scopes, and run
   `orbit_swarm_draft_preview`. Only then use `orbit_task_plan` with
   `confirm_write=true` after real host/user approval.
3. **Execute by native host.** Reserve no more than two tasks per wave with
   actual user approval. The lead host invokes its *real*
   `invoke_subagent`, `spawn_agent`, or supported delegation API; no
   fallback secretly starts another CLI, model, ECC command, or cloud backend.
   Serial execution is valid when native agents are unavailable.
4. **Verify between waves.** Record exact real host session references,
   run independent tests, check diff and file scopes, and separately review
   each task. A completed native session is not a successful task objective.
   STOP/HOLD on permission refusal, unverified liveness, failed tests, missing
   dependencies or unresolved critical security findings. Only reviewed and
   accepted dependencies enable subsequent waves.
5. **Ship by separate decision.** QA tests, security reviews, operational
   documentation, backup/rollback and final release approval have distinct
   evidence. `orbit_swarm_integration_review` is read-only and does not
   independently prove host or UI QA. Never publish, merge or deploy because
   a blueprint exists or a model reported PASS.
6. **Iterate and resume.** After the first accepted vertical slice, inspect
   what was actually delivered and create a new approved plan for the next
   slice. Use existing Orbit checkpoints and task ledger, not invented
   historical progress. Future features/fixes are new scoped work, not a
   rerun that overwrites already accepted tasks.

## ECC research boundary and reuse policy

ECC's `orch-pipeline`, `orch-build-mvp`, planner/TDD/reviewer agent maps
are useful **conceptual references** for right-sized planning, vertical
slices, implementation, independent review and gating. ECC's license is MIT
on the inspected repository; **no ECC code/agents or license text is copied
into Orbit by this change**. Its Claude-specific model names, plugin
installer, shell scripts, automatic edits, third-party CLIs and repeated
generator/evaluator agent loops are not Orbit dependencies and are not
approved. If a future contributor proposes copying a specific ECC file,
first inspect its exact version/license/attribution, security, host
compatibility and ability to preserve model/permission neutrality, then
seek an explicit owner decision.

This original Orbit workflow remains portable and project-scoped: GitHub
source confirms implementation, Notion holds product decisions/research, and
local SQLite/.orbit stores only its operational state. No automatic sync.

## Evidence-first delivery and targeted redesign (v0.28 follow-up)

For new builds and feature work, the architect identifies the actual test runner
and the acceptance behavior **before** assigning implementation. Each implementing
specialist should establish an appropriate failing or baseline test first, then
make the bounded change, rerun the same check, and report the exact command,
source ref and result. When test-first is infeasible (for example an untestable
host integration), explicitly mark the verification blocked and name the
authorized alternative; never invent a RED/GREEN result or impose a universal
coverage threshold. QA and independent review remain separate release gates.

For a visual `redesign`, preserve the current application contracts and scope
the initial slice to UX and frontend behavior. Do **not** propose automatic schema
migration or backend rewriting merely because the app normally has services
or storage. If source inspection proves that a backend/data change is necessary,
revise the blueprint and file scopes with owner consent before proceeding.
This avoids unnecessary rewrites while preserving functional UI testing.

## M2 parallel-agent filesystem safety

Before proposing parallel native-agent work, `orbit_swarm_draft_preview`
now evaluates both declared project-relative write paths and their
symlink-resolved targets in the selected workspace. Paths escaping the
workspace or resolving to protected control files fail closed; two
different-looking paths resolving to the same directory are scheduled in
separate review waves, not approved as parallel edits.

Before returning **any** native invocation packet for a selected batch,
`orbit_swarm_host_preflight` rechecks the saved scopes and current
resolved targets. If a link was retargeted after reservation, or imported
reservation records overlap physically, the whole batch returns HOLD with
no partial handoffs. Neither preview nor preflight is a filesystem sandbox:
the coding host must separately enforce write permissions at the time of
actual execution. These guards never launch, stop or impersonate agents.

## Repeated slices and targeted fixes

Use a fresh, explicitly reviewed lowercase slice_key (such as alerts) for each later vertical slice. Each task and dependency key gets that prefix; original accepted tasks and append-only attempts remain untouched. Without a new key, a collision returns HOLD. For a fix or debug operation, focus_role may be frontend, backend, data, devops, security or qa after inspecting the actual affected code. Stage-specific ledger step labels preserve per-step reservation limits. No model switching or host permission occurs during the preview.
