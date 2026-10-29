# Orbit Core roadmap — M1/M2 accepted for core use; M3 next (2026-10-29)

The focus is **a trustworthy local orchestrator inside existing coding IDEs**, not duplicating an entire cloud app-building platform. This is a prioritized engineering backlog, not an automated promise of completed features.

## Orbit-native research and intelligence roadmap — approved direction (2026-10-27)

**Product principle:** build an original, lightweight Orbit experience, not an ECC fork or clone. Research links, annotations and retrieval records belong in **authorized local project-scoped SQLite outside the Git repository**. Owner documentation remains authoritative. External references are untrusted inputs, never auto-executed skills or agent instructions. This roadmap preserves Issue #13 product-experience commitments and Issue #9 release/security gates.

### M1 — P0: Orbit Evidence Lens (core scope OWNER-REPORTED PASS; source and CI verified)
- Save an individual reviewed research **source pointer** (URL, topic tags, short annotation, original status) with an explicit write preview and revision-guarded update. Use project folder + stable project key as namespace. Never seed global memory by default or push research links to Git.
- Recover only sources relevant to an objective within a predictable character budget; return provenance, limits, unverified-source warning and explicit live verification guidance. No network request or third-party code execution from source content.
- Support project- and folder-level isolation, duplicate identity updates, malicious URLs and stale-revision tests; retain existing local SQLite and legacy memories. A trusted local IDE user manually imports the previously prepared 9-link research packet after connecting, not a Git checkout or ChatGPT cloud session.
- **Gate / acceptance update (2026-10-29):** PR #16 merged and the source/bundle regression matrix passed. The owner reported Antigravity research-pointer save/readback and checkpoint recovery as PASS. Treat M1's core functionality as **OWNER-ACCEPTED**, not independently attested host consent or proof of automatically synchronized Notion references. Evidence: [v0.25.1 release host reports](https://github.com/samjuniors/Orbit-Core-MCP/releases/tag/v0.25.1) and [Evidence Lens tests](../tests/test_evidence_lens.py).

### M2 — P0: Reliable real-host delegation and handoff (core scope OWNER-REPORTED PASS; extended checks open)
- Add a read-only `orbit_task_handoff` adapter contract: checked task/reservation/dependencies, exact supported native host tool names (caller-reported), limited file ownership, optional minimal Evidence Lens links, safe HOLD/serial fallback. The host **must** actually invoke its native tool; a packet is not an agent run. Real host session references and changed-file/test inspection remain prerequisites; the MCP never spawns an agent.
- **Gate / acceptance update (2026-10-29):** [PR #17](https://github.com/samjuniors/Orbit-Core-MCP/pull/17) merged with passing automated host-handoff tests. The owner's actual-host reports record **Antigravity PASS** (native delegation, Todo checks, restart/resume) and **Codex PASS** (native delegation, 14 regression checks, `todo-filter-codex` REVIEW_ACCEPTED revision 5, checkpoint/files restored after restart). Those reports are documented in the [v0.25.1 release](https://github.com/samjuniors/Orbit-Core-MCP/releases/tag/v0.25.1); the MCP cannot independently attest host session/consent. Mark **M2 core two-host acceptance OWNER-ACCEPTED**, without claiming every new-project/existing-project or denial/fallback scenario was independently verified. Any untested scenario remains a targeted M3 follow-up, not an assumed PASS.

### M3 — P1: Independent QA, permissions and scoped recovery (NEXT ACTIVE MILESTONE; NOT IMPLEMENTED/VERIFIED AS A WHOLE)
- **Objective:** Make verification evidence independently checkable where host capabilities permit, ensure permission/denial behavior is accurately represented, and recover from interrupted or cross-host work without fabricating PASS.
- **M3.1 — QA freshness:** Attach QA/test records to source revision, acceptance case, execution environment and preview generation; invalidate stale PASS after code changes. Include regression tests for stale evidence.
- **M3.2 — Host permissions:** Verify real host consent/denial paths; do not treat `confirm_write`, reported tool names or supplied session IDs as authenticated consent. Retain HOLD/serial fallback when native delegation cannot be attested.
- **M3.3 — Scoped recovery:** Exercise interrupted, cancelled, failed and rework task paths with revision checks, safe file ownership, and rollback/backup review on Windows and Linux. Do not alter older accepted task history.
- **M3.4 — Portability limitations:** [PR #22](https://github.com/samjuniors/Orbit-Core-MCP/pull/22) merged portable task/research export/import and checkpoint-only detection; **live cross-PC transfer remains NOT VERIFIED**. Test on two actual hosts/PCs only with approved, disposable project data; imported approvals and sessions remain untrusted historical records. Build/intake and legacy memory are not included.
- **Acceptance gate:** real revised-code QA (including stale-PASS rejection), host denied-permission evidence, interrupted/rework recovery, independently inspected Git diffs/tests, and an explicitly recorded cross-PC test result (PASS/FAIL/DEFERRED). Separate optional platform/GUI, provenance/signing and Issue #9 security gates are not silently closed.
- **Start with:** a read-only M3 gap audit against existing QA, host approvals, task ledger and portability tests; implement focused regression tests on a feature branch before changing runtime behavior.

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
- **v0.25.1 was published as a prerelease on 2026-10-29** with four ZIP/MCPB/checksum assets after passing CI. This is not production security, GUI or independent native-host acceptance. Preserve v0.24.1 assets and verify real device/installer/backup/rollback separately. See [published release](https://github.com/samjuniors/Orbit-Core-MCP/releases/tag/v0.25.1) and [release acceptance](RELEASE-ACCEPTANCE-v0.25.1.md).

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

The published v0.25.1 and current development tool inventory are **40** tools.
The older 39-tool acceptance prompt predates the portable-transfer feature.
The owner reported Antigravity and Codex same-PC native delegation/restart PASS;
**live cross-PC transfer and native delegation on the destination are NOT VERIFIED**.
Neither published prerelease nor these host reports constitute production certification.
