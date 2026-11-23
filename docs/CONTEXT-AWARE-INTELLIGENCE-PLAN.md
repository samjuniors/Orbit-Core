# v0.34.0 proposal — Context-Aware Intelligence & Continuity

**Status:** PROPOSAL / AUDIT-FIRST / NO RUNTIME IMPLEMENTATION  
**Audit base:** `main` at `2fdf4f329774b9644e75ac0df4d89738a7cd625f` (2026-11-23)  
**Working branch:** `feat/v034-context-aware-intelligence-20261123`  
**Version context observed on main:** `VERSION=0.33.1`, `NEXT_VERSION=0.34.0`  
**Host implementation target:** Claude Code first; provider-neutral Orbit Core contracts retained.  
**Authority:** GitHub is implementation truth. Existing Orbit Core Notion decisions remain product-decision truth.

This document proposes a new v0.34 capability. It does not authorize merging, release, installation, host configuration changes, permission changes, or autonomous execution.

---

## 1. Product objective

When a user asks Orbit to implement a task, Orbit should first understand the actual project and its current state, identify material gaps, build a proportionate implementation plan, and help the active coding host execute that plan with the right context and model. During long work, it should preserve recoverable progress and warn about approaching limits when the host exposes reliable signals.

The intended lifecycle is:

1. Resolve project, repository, branch, working tree, host and current task.
2. Determine whether project context is absent, stale or current.
3. Run a bounded, read-only project discovery scan when required.
4. Audit relevant code, architecture, tests, security boundaries, dependencies and documentation for evidence-backed gaps.
5. Convert accepted findings into a prioritized plan and task DAG using existing Orbit task/build primitives.
6. Recommend the model/effort and specialist strategy appropriate to each task, using only host-reported capabilities.
7. Let Claude Code perform implementation through its native tools and permissions.
8. Observe execution, validation, model-switch and limit signals where available.
9. Checkpoint before compaction, session termination or a credible interruption risk.
10. On resume, reconcile checkpoint claims against the actual repository, diff, task ledger and test evidence before continuing.

Orbit remains a coordinator and local state/evidence layer. The connected host remains responsible for model inference, code editing, native agents, tools, permissions and actual execution.

## 2. Main-branch audit — verified findings

### 2.1 Existing foundations to reuse

| Area | Existing main implementation | Audit conclusion |
|---|---|---|
| Intake and project profile | `source/runtime/orbit_intake.py` | Persists project type, complexity, maturity, goal, audience, constraints, stack and risk; has a bounded document-name inventory. It is not a full source-code audit. |
| Engineering quality baseline | `source/runtime/orbit_delivery.py` | Proposes proportionate security, reliability, maintainability, performance and other checks. It marks applicability for review; it does not discover and prove concrete defects in source. |
| Model recommendations | `source/runtime/orbit_decisions.py` and `orbit_model_route` | Recommends a model tier from caller/host-reported model names and host guidance. It explicitly does not switch models and has no real-time quota, pricing, entitlement or benchmark data. |
| Task and build state | `source/runtime/orbit_tasks.py`, `orbit_build.py` | Provides a task ledger, dependencies, build stages, source fingerprinting and recovery briefs. A source fingerprint is an identity/freshness aid, not an architecture/security audit. |
| Autopilot | `source/runtime/orbit_autopilot.py` and `orbit_autopilot_runner.py` | Provides bounded mission planning and a separately constrained local runner path. It is not a Claude Code-native general-purpose execution controller or a quota monitor. |
| Capabilities and skills | `source/runtime/orbit_capabilities.py`, `orbit_skill_plan.py` | Discovers local skill/config candidates and returns bounded recommendations. Presence/configuration does not prove host connectivity, trust or permission. |
| Specialist coordination | `orbit_delegation.py`, `orbit_team_builder.py`, team-event modules | Prepares host-native handoffs and coordination. Actual agent invocation and authority remain with the host. |
| Claude Code integration | `CLAUDE.md`, `source/skills/orbit/SKILL.md`, published plugin workflow in README | Claude Code is already a supported host. A host-specific lifecycle adapter is the logical first integration point. |

### 2.2 Material gaps relative to the requested capability

1. **No unified project-readiness state machine.** Intake and document inventory exist, but the current flow does not consistently answer: has this exact project root been scanned, what source revision was scanned, what changed, and which audit results are stale?
2. **No comprehensive evidence-backed code-gap audit.** Existing quality baselines and source fingerprints are not equivalent to an audit of implementation, architecture, tests, dependencies, security controls and documentation against the actual project.
3. **No first-class audit-to-plan reconciliation.** Delivery previews and task DAGs exist, but findings need stable identities, evidence, severity/confidence, disposition and traceable links to implementation tasks.
4. **No common policy-driven hook engine.** Claude Code has native lifecycle hooks, but Orbit's provider-neutral runtime does not yet define a safe event/policy/action contract with host-specific adapters.
5. **No actual model selection execution.** `orbit_model_route` is advisory. Main-session switching, per-subagent model overrides, observed model changes and host capability discovery are not unified.
6. **No reliable quota/usage telemetry abstraction.** Existing local runner launch-count budgets are not token budgets or provider account quotas. Orbit cannot infer a plan's remaining quota.
7. **Checkpointing is not yet tied to host lifecycle signals.** Existing build/task checkpoints are useful, but need a Claude Code adapter for pre-compaction, session-end, quota notifications and task-boundary capture, with clear evidence semantics.

### 2.3 Existing adaptive execution work must be reconciled, not duplicated

Draft PR [#141 — opt-in evidence-gated adaptive execution preview](https://github.com/samjuniors/Orbit-Core/pull/141) already extends the existing `orbit_model_route` with a deterministic single/cascade/critique recommendation. It is read-only and does not switch models or invoke reviewers.

A live compare of PR #141 head `63881cd850a1c3328b93cad92ca1cbafc0372d40` against audited main showed **diverged: 6 commits ahead and 187 behind**, with merge base `f6b7b4d81198142f121e5793fb9a06fbee195892`. Do not merge or cherry-pick the entire stale branch blindly. Review its focused changes and tests, then port/reconcile the minimal useful delta onto current main if still appropriate.

### 2.4 Repository documentation drift

The audited main contains `VERSION=0.33.1` and `NEXT_VERSION=0.34.0`. However, `docs/ARCHITECTURE.md` still describes a v0.29 architecture and 47-tool inventory, while `docs/NEXT-VERSION.md` still presents a v0.33 checkpoint with older main/version assumptions. The README also contains dated release-status text that should be reconciled against live Releases and the current acceptance record before a v0.34 release cut. This is a documentation consistency gap, not evidence that runtime code is broken.

**Audit scope limitation:** This was a remote source/document review of selected main files and GitHub metadata. It was not a full local checkout, full line-by-line review of every repository file, live Claude Code session test, or inspection of the owner's local SQLite/host state. No local test suite was run in this audit.

---

## 3. Proposed architecture

Add a provider-neutral core contract with a thin Claude Code adapter. Reuse current SQLite, task ledger, build ledger, intake, capability discovery, model recommendation and checkpoint functions wherever they fit. Avoid a second database, duplicate task system, standalone LLM router or background agent daemon.

### Core services

- **Project Context Resolver:** stable project identity, root trust, Git branch/HEAD/dirty state, host identity, task identity, context revision and scan freshness.
- **Read-only Discovery & Audit:** bounded file inventory and source evidence collection; detects missing/inconsistent docs, untested modules, suspicious architecture boundaries, dependency/version drift, security review gaps and implementation/spec mismatches. Static heuristics are leads, not confirmed defects.
- **Finding Ledger / Reconciliation:** normalized findings with stable ID, category, severity, confidence, affected paths/lines, evidence digest, source revision, status, disposition and linked task IDs. Prefer extending existing records over creating a duplicate ledger.
- **Policy & Hook Engine:** event → context predicate → allowed action → approval class → result/evidence. Deterministic and declarative; no arbitrary project-provided hook execution.
- **Adaptive Execution Planner:** maps the approved goal and accepted audit findings to task dependencies, file ownership, verification and review gates.
- **Model/Host Capability Router:** separates recommendation from host action; supports per-task model and specialist recommendations, capability discovery, model-switch observation and fallback policy.
- **Capacity & Continuity Monitor:** distinguishes context-window pressure, account usage limits, API spend, rate limits and generic host interruption. Creates revision-bound checkpoints and resume packets.

### Finding contract (conceptual)

Each audit finding should include: `finding_id`, `project_id`, `category`, `severity`, `confidence`, `summary`, `evidence_refs[]`, `affected_paths[]`, `source_snapshot`, `first_seen`, `last_verified`, `status`, `disposition`, `linked_task_ids[]`.

A finding is not actionable merely because a model generated it. It must include inspectable evidence and be classified as confirmed, suspected, accepted risk, false positive, not applicable or unresolved. Findings become tasks only after review/approval appropriate to their risk.

---

## 4. Claude Code first adapter

Claude Code has native hooks for session, prompt, tool, compaction, notification, model-switch and task/subagent lifecycle events. Its current hook reference includes `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `PostCompact`, `SessionEnd`, `Notification`, `PreModelSwitch`, `PostModelSwitch`, `SubagentStart/Stop` and task lifecycle events. Hook handlers run with host-provided capabilities; they must be treated as privileged integration code.

Recommended initial mapping:

| Claude Code event | Orbit response |
|---|---|
| `SessionStart` | Resolve root and branch; inspect Orbit project registration; recover a current checkpoint; scan only if missing/stale. |
| `UserPromptSubmit` | Classify whether prompt begins a new task, resumes work or changes scope; inject only compact relevant context. |
| `PreToolUse` | Apply narrow policy checks for selected high-impact operations; do not replace Claude Code permission controls. |
| `PostToolUse` / `PostToolUseFailure` | Record bounded task/evidence signals; avoid logging secrets or full command output by default. |
| `PreCompact` | Capture a structured continuity checkpoint before context is compacted. |
| `PostCompact` | Reconcile compacted summary with saved task state; avoid duplicate or stale context. |
| `Notification` | Observe relevant quota/rate-limit/permission notifications when supplied; do not assume they provide advance quota percentages. |
| `PreModelSwitch` / `PostModelSwitch` | Record requested/observed model transition and re-evaluate task fit; never silently change the user's main model. |
| `SubagentStart/Stop`, `TaskCreated/Completed` | Correlate native specialist lifecycle with Orbit task IDs and evidence; distinguish reported events from verified outcomes. |
| `SessionEnd` / `Stop` | Save final checkpoint and pending work summary when possible; never claim a hook ran if it did not. |

Start with the smallest safe hook set: SessionStart, PreCompact, PostCompact, SessionEnd, and model-switch observation. Add tool/task hooks only after measuring overhead and proving value. Prefer the plugin-scoped configuration and existing MCP interface over new global user settings.

**Hook safety:** explicit opt-in; preview exact installed hook files; allowlisted commands only; no shell evaluation of project text; no auto-execution of `package.json`, Makefile, setup scripts or project hooks; bounded input/output/time; secret redaction; fail-open for advisory enrichment and fail-closed only for explicitly approved Orbit policy checks. Hook installation/update/rollback requires user review. A hook must not bypass Claude Code's native permission prompts or auto-approve tools.

### Claude Code model selection

Use Claude Code's native per-subagent model selection where supported and confirmed by the running host. A task-specific model recommendation should consider task class, complexity, risk, required context, host-reported available model aliases, latency/cost preference and whether independent review is required.

- Default to the existing session model for ordinary work.
- Recommend a lighter model for bounded read-only work and a stronger model for architecture/security/high-assurance review when available.
- Use per-invocation or agent-definition model overrides for isolated subagents where supported; do not rewrite the main session model or user settings automatically.
- Treat `PreModelSwitch` / `PostModelSwitch` as observation and policy hooks, not permission to choose a model unilaterally.
- If the requested model is unavailable, inherit the current host model or ask the user. Never switch account/provider or bypass a permission/usage denial.

Primary references: [Claude Code hooks](https://code.claude.com/docs/en/hooks), [Claude Code subagents](https://code.claude.com/docs/en/sub-agents), [Claude Code usage, models and limits](https://support.claude.com/en/articles/14552983-models-usage-and-limits-in-claude-code).

---

## 5. Quota, context and interruption model

Do not collapse these into one generic percentage:

1. **Context-window pressure:** remaining context for the current conversation/model; may be visible through host context indicators/hooks.
2. **Plan/account usage limit:** subscription usage pool and reset time; often not exposed as a reliable machine-readable remaining percentage.
3. **API spend:** token/dollar cost for API-key sessions; host commands such as `/cost` and provider dashboards may be the authoritative source.
4. **Rate limit / overload:** actual host response or notification, not necessarily predictable from prior token count.
5. **Orbit's own execution budget:** local run/task attempt caps; never label this as provider quota.

The provider interface should return value, unit, source, timestamp, confidence, reset time (if supplied), and whether it is predictive or merely reactive. Missing telemetry must return `UNKNOWN`, not a fabricated estimate.

Checkpoint triggers:
- before automatic/manual compaction when hook delivery permits;
- after meaningful task milestones and before yielding to a specialist;
- on a host quota/rate-limit warning or failure;
- on session termination;
- when the task is likely to exceed the current available context or session budget, but only when a credible signal exists.

Checkpoint payload: project/root identity, branch and HEAD, dirty-worktree summary, task and build revisions, completed/pending steps, decisions, blockers, changed paths, actual verification commands/results, host/model/session metadata that is safe to retain, source snapshot, and one precise resume instruction.

Recovery must re-inspect Git and relevant files, compare current source/task revisions, identify uncommitted changes, and re-run stale or unverified checks. A checkpoint is not proof that a task is correct or complete.

---

## 6. Delivery plan

### Phase 0 — Reconcile and specify (first)
- Read the current Notion decision hub and reconcile this proposal with adopted decisions.
- Reconcile PR #141's useful source/tests against current main; do not merge its 187-commit-stale branch.
- Update the architecture inventory and identify the exact existing MCP tools/schema paths to reuse.
- Freeze data contracts, trust boundaries, hook event mapping and explicit non-goals.

### Phase 1 — Project readiness and scan/audit (P0)
- Add a project readiness state: UNKNOWN, SCAN_REQUIRED, SCANNING, SCANNED_CURRENT, STALE, BLOCKED.
- Build bounded read-only discovery, source snapshot and incremental invalidation.
- Audit implementation/spec alignment, architecture, docs, tests, dependencies and proportionate security/reliability areas.
- Emit evidence-backed findings and confidence labels; never call heuristic signals confirmed vulnerabilities.
- Handle new, existing-unscanned, previously scanned, changed, dirty and partially inaccessible projects.

### Phase 2 — Audit-to-plan (P0)
- Deduplicate findings and connect accepted findings to the existing task ledger.
- Generate a prioritized task DAG with dependencies, file ownership, acceptance criteria and verification gates.
- Keep speculative recommendations separate from confirmed gaps.
- Require approval for scope expansion, dependency installs, migrations, destructive changes and other consequential actions.

### Phase 3 — Claude Code lifecycle adapter (P0)
- Package opt-in, plugin-scoped hooks and bounded MCP integration.
- Start with session recovery, scan freshness, compaction checkpointing, session-end checkpointing and model-switch observation.
- Add schema/version compatibility checks and exact install/update/uninstall preview/rollback.
- Test hooks in a disposable Claude Code project before enabling any default behavior.

### Phase 4 — Adaptive model/specialist routing (P1)
- Reconcile/port PR #141's evidence-gated execution preview.
- Add task-specific recommendations and Claude Code per-subagent model hints.
- Observe actual host model changes and execution outcomes.
- Measure quality, latency and cost on disposable representative tasks before considering automatic per-subagent selection.

### Phase 5 — Capacity and continuity protection (P1)
- Add host capacity-provider contract and confidence semantics.
- Use real Claude Code context/notification signals where exposed; support explicit user-reported usage only as unverified.
- Implement proactive checkpoint thresholds only where telemetry supports them.
- Validate recovery after compaction, quota stop, session end, host restart and model switch.

### Phase 6 — Generalize host adapters (P2)
- Add Codex/Antigravity/other adapters only after the core event and policy contracts prove stable.
- Do not assume hook parity or permission equivalence across hosts.

---

## 7. Non-goals and safety invariants

- Orbit does not become a hosted LLM, model proxy, provider-account switcher or unrestricted background daemon.
- No automatic installation of dependencies, skills, agents, hooks or host configuration.
- No execution of project-provided setup scripts during discovery.
- No auto-approval, sandbox bypass, permission escalation or provider fallback after denial.
- No invented quota percentages, remaining tokens, model entitlements or test results.
- No automatic merge, push, release, deployment, migration or destructive action.
- No new SQLite event store or duplicate project/task ledger unless a concrete audited need is demonstrated.
- Repository text, audit input and skill metadata remain untrusted data, never instructions or approval.
- Host-reported signals are labelled as such; actual outcomes require independent evidence/reconciliation.

## 8. Acceptance gates

A phase is not complete because source code or tests were authored. Require:

1. **Correctness:** deterministic tests for project-state transitions, stale scans, finding identity/deduplication, task links and checkpoint recovery.
2. **Security:** prompt-injection fixtures, path traversal/symlink/hard-link/TOCTOU cases, secret redaction, oversized files, malicious hooks, no project-script execution and project isolation.
3. **Compatibility:** current Claude Code plugin manifest and hook schema validation; supported Claude Code versions tested in disposable environments.
4. **Host behavior:** actual SessionStart, compaction, model-switch, notification and SessionEnd evidence; denied permission and hook-failure behavior.
5. **Model routing:** host-reported model availability, unavailable model, high-risk review, user-selected model and no silent main-session change.
6. **Quota honesty:** unknown telemetry remains unknown; distinguish context pressure, account usage, API spend and rate-limit errors.
7. **Continuity:** recover after compaction, limit interruption and host restart without losing uncommitted work or replaying side effects.
8. **Repository quality:** full existing unit suite, package parity, disposable plugin install/update/rollback, exact-head Linux/Windows CI.
9. **Independent review:** source/security review and explicit owner acceptance before merge or release.

## 9. Phase 1 implementation checkpoint — started

**Implemented on `feat/v034-context-aware-intelligence-20261123`:**

- Added `source/runtime/orbit_project_audit.py`, a bounded read-only filesystem metadata inventory.
- Extended existing `orbit_project_scan` and the full `orbit_project_resume` path to include structural audit results; no duplicate scan tool or database ledger was introduced.
- Added heuristic review leads for missing conventional README, test structure, architecture documentation in larger source trees, dependency lockfiles, high-assurance security documentation and CI configuration.
- Findings include category, severity, confidence, evidence paths, recommendation and explicit `is_confirmed_defect=false`.
- Scan reports a metadata-only snapshot digest, scan limits, incomplete/truncated status, skipped symlinks, inventory summary and explicit non-execution/non-write semantics.
- Added `tests/test_project_audit.py` for basic findings, test/CI discovery, high-assurance profile behavior, no-write behavior and symlink-root rejection.

**Safety and scope:** This first slice does not read source contents, execute project scripts, install dependencies, persist a scan baseline, create implementation tasks or claim semantic/security verification. It is a structural inventory and gap-signal layer only. The next slice should add reviewed findings and plan/task linkage after test execution and security review.

**Phase 1 follow-on — finding reconciliation implemented on the same branch:**

- Added `source/runtime/orbit_findings.py`, a project-root-scoped SQLite ledger keyed by stable finding ID.
- Added lifecycle states `NEW`, `OPEN`, `RECURRING`, `STALE`, and `RESOLVED`, plus owner-review dispositions `UNREVIEWED`, `ACCEPTED`, `FALSE_POSITIVE`, `RISK_ACCEPTED`, and `NOT_APPLICABLE`.
- A complete scan can resolve a previously observed finding; an incomplete scan only marks active findings stale and never resolves them.
- Evidence changes reset a prior disposition to `UNREVIEWED`; revision-guarded review updates reject stale writes.
- Added `orbit_project_findings` with `reconcile`, `list`, and `review` actions. Reconciliation persists only in Orbit's local SQLite database; it does not write into the project.
- Added tests for new/persistent/resolved/recurring transitions, incomplete-scan safety, revision conflicts, evidence-change re-review and project/root isolation.
- Task creation and finding-to-task linkage remain intentionally unimplemented in this slice. Review dispositions do not prove a defect and do not create tasks.

**Verification status:** Source and tests were committed and re-fetched from GitHub. The tests are authored, not passed: no local test execution has been performed. Exact-head CI status must be checked before treating this slice as verified.

---

## 10. Immediate next actions

1. Execute the new tests and the full existing suite on the exact feature-branch head; add adversarial cases for scan truncation, duplicate IDs, path normalization and SQLite concurrency.
2. Review the finding lifecycle and disposition semantics against actual product decisions.
3. Implement finding-to-task preview using the existing task ledger, with dependency/verification criteria and explicit write confirmation; never create tasks merely because a heuristic finding exists.
4. Continue Claude Code lifecycle work only after the scan/finding contract is tested and stable.
5. Keep main unchanged; do not open a PR until tests, exact-head CI and review are complete.

**Current branch:** Phase 1 structural audit plus persistent finding reconciliation are implemented in source. No merge, PR, release, hook installation or host-setting change has been performed.
