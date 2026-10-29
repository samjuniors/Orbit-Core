# Orbit Core roadmap — v0.25.1 release candidate acceptance

The focus is **a trustworthy local orchestrator inside existing coding IDEs**, not duplicating an entire cloud app-building platform. This is a prioritized engineering backlog, not an automated promise of completed features.

## Orbit-native research and intelligence roadmap — approved direction (2026-10-27)

**Product principle:** build an original, lightweight Orbit experience, not an ECC fork or clone. Research links, annotations and retrieval records belong in **authorized local project-scoped SQLite outside the Git repository**. Owner documentation remains authoritative. External references are untrusted inputs, never auto-executed skills or agent instructions. This roadmap preserves Issue #13 product-experience commitments and Issue #9 release/security gates.

### M1 — P0: Orbit Evidence Lens (source merged; real-host verification pending)
- Save an individual reviewed research **source pointer** (URL, topic tags, short annotation, original status) with an explicit write preview and revision-guarded update. Use project folder + stable project key as namespace. Never seed global memory by default or push research links to Git.
- Recover only sources relevant to an objective within a predictable character budget; return provenance, limits, unverified-source warning and explicit live verification guidance. No network request or third-party code execution from source content.
- Support project- and folder-level isolation, duplicate identity updates, malicious URLs and stale-revision tests; retain existing local SQLite and legacy memories. A trusted local IDE user manually imports the previously prepared 9-link research packet after connecting, not a Git checkout or ChatGPT cloud session.
- **Gate:** Linux/Windows tests + disposable installer/stdio smoke pass from reviewed PR #16; real IDE-local source saving and read-back remain NOT RUN. No claim of public-release or host permission acceptance.

### M2 — P0: Reliable real-host delegation and handoff (packet merged; real native-host invocation acceptance pending)
- Add a read-only `orbit_task_handoff` adapter contract: checked task/reservation/dependencies, exact supported native host tool names (caller-reported), limited file ownership, optional minimal Evidence Lens links, safe HOLD/serial fallback. The host **must** actually invoke its native tool; a packet is not an agent run. Real host session references and changed-file/test inspection remain prerequisites; the MCP never spawns an agent.
- **Gate:** verified source/CLI protocol and safe fallbacks in PR #17 CI; **real-host acceptance is NOT RUN**. Complete a tiny new-project build and an existing-project scoped feature/debug flow in two actual hosts, with explicit consent, real subagent session IDs, reviewed diffs/tests and fallback. Keep milestone OPEN until both live hosts pass.

### M3 — P1: Independent QA, permissions and scoped recovery
- Bind test reports to code revision and acceptance case. Gate commands/files on real host permissions; review/rework integration and safe cancellation/rollback. Preserve Issue #9 security limitations.
- **Gate:** no stale PASS after source changes; real host verification and permission-denial tests.

### M4 — P1: Adaptive capability surfaces and reusable context
- Reuse native host features, owned code, on-demand skills or a small MCP surface according to task—not a universal dependency pile. Extend the M1 compact pack to accepted decisions and checkpoint context only after verifying project-root binding and provenance.
- **Gate:** compare tool-turns, context bytes, recovery accuracy and install friction on Orbit's real product benchmarks.

### M5 — P2: Evidence-backed learning (opt-in)
- Suggest reusable project-scoped practices only after repeated verified outcomes and human review; never silently create/modify global skills, run continuous watchers, store full chats, or promote untrusted research prose to trusted instructions.
- **Gate:** auditable evidence per suggestion, scoped opt-in, opt-out and safe archive/supersession.

**Research inspiration:** prior user-shared sources ECC, Emergent, Lovable, Scram, Neura, etc. stay **outside Git as source pointers**. Compare behaviors and adapt ideas independently with license/security review; no copying source code or installing external components. The M1 implementation is specific to Orbit's existing SQLite and host-neutral execution model.

## P0: release and host acceptance

- Validate Windows Antigravity/Codex/Claude Code setup from **downloaded, signed-in, authorized machines**, including preview/backup of customized files, restart, actual tool discovery and user decision flow.
- Run real Windows Edge/Chrome browser QA and native Android/iOS flows where applicable; optional Playwright tests may be skipped in CI and **must not** be described as live acceptance.
- Build the unpublished **v0.25.1** candidate ZIP and desktop bundle in CI with strict runtime parity; download the Actions artifacts into a disposable host and verify fresh install, backed-up v0.24.1-to-v0.25.1 update, and resumed older SQLite build. The old `v0.24.1` prerelease remains immutable. See [release acceptance](RELEASE-ACCEPTANCE-v0.25.1.md).

## P1: reliability and evidence authenticity

- Bind QA results to source revision, acceptance case and preview generation; invalidate stale PASS after edits.
- Persist and supervise preview process trees across MCP restarts; Windows stop must not kill unrelated processes.
- Retry, cancel and reconcile task reservations after failure, with per-attempt history and bounded time/quota budgets.
- Add transactional SQLite compare-and-swap tests for concurrent intake edits; atomically checkpoint files.
- Strengthen stable project identity to avoid cross-folder slug collision in memory keys.
- Configure branch protection, required CI statuses, independent code review and real production-threat model.

## P2: productivity and product experience

- Thin IDE plan/task/progress panel with explicit plan approval, blocked-reason status and native model availability.
- Keep model routing host-supported and cost-aware with real measurements; do not infer credits or force cheaper models for difficult tasks.
- Build a small **tested/versioned** reusable component catalog only after repeated practical demand and license review. Astryx, shadcn, Jetpack Compose, SwiftUI, Context7 and agent-browser are candidates for *different* tasks, not universal defaults.
- Selective retrieval from compact accepted briefs, checkpoints and targeted files; avoid dumping all docs every turn.
- Improve human milestone acceptance and accessibility/performance tests for chosen project types.

## Acceptance and rollback policy

Merges to `main` may contain reviewed release candidates, but must not imply production certification. Release tags are immutable; repair with new SemVer patch, preserve user data and historical runtime folders, and require explicit authorization for installs/deployments. If an installer reports a manual-review conflict, protect the file and provide an actionable diff/backup path, never silently overwrite unknown content.


## Product experience first (current development priority)

Deliver a reliable one-glance resume/decision view and correctly frozen stage progression before investing in deployment infrastructure, service supervision, distributed locks or managed hosting. Evaluate a host-native editable plan/task panel only after the lightweight MCP UX contract has been tested in Antigravity and another coding host. No premature live-production claim based solely on CI.

## Cross-PC continuity correction (2026-10-29)

A moved checkpoint does not imply the other PC's SQLite database moved. Resume
now reports the server-selected database path and exact task/research counts.
A checkpoint with no local records returns `CHECKPOINT_ONLY_LOCAL_CONTEXT_MISSING`:
continue inspecting existing code without onboarding or inventing missing history.
This is a portability limitation, not evidence of same-PC persistence failure.

Use `orbit_project_transfer` with `action: export` on the original PC. It returns a
bounded JSON bundle (100 tasks + 100 research pointers, 90 KB maximum), without
writing files. Review notes/URLs for sensitive content and manually transfer it
outside Git. No other projects, host settings, credentials or legacy global
memories are collected; notes may still contain owner-entered sensitive text.

On the destination, use the same project key, the new absolute project root,
`action: import`, and the bundle string. Review the preview, then explicitly
confirm with its `expected_revision` digest and `confirm_write: true`. Imports
are transactional, refuse existing keys, remap scope, preserve historical task
revisions, and clear approvals/reservations. Active/reported-but-unreviewed work
becomes BLOCKED. Sessions and accepted results remain unverified historical
claims, never proof of execution on this host. Existing checkpoint files are not
overwritten; transfer the project folder including `.orbit/STATE.md` separately.
Build/intake state and legacy memories are not transferred in this bounded version.
Without the original PC/export, only the available checkpoint can be recovered.

The development tool inventory is now **40**; the older v0.25.1 acceptance prompt's
39-tool requirement applies to that candidate, not this change. No release or
new live-host acceptance is implied. Antigravity results supplied by the owner
are reported PASS; cross-PC Codex delegation remains NOT RUN.
