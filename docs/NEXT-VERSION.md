# Orbit Core roadmap — v0.25.0 release candidate acceptance

The focus is **a trustworthy local orchestrator inside existing coding IDEs**, not duplicating an entire cloud app-building platform. This is a prioritized engineering backlog, not an automated promise of completed features.

## P0: release and host acceptance

- Validate Windows Antigravity/Codex/Claude Code setup from **downloaded, signed-in, authorized machines**, including preview/backup of customized files, restart, actual tool discovery and user decision flow.
- Run real Windows Edge/Chrome browser QA and native Android/iOS flows where applicable; optional Playwright tests may be skipped in CI and **must not** be described as live acceptance.
- Build the unpublished **v0.25.0** candidate ZIP and desktop bundle in CI with strict runtime parity; download the Actions artifacts into a disposable host and verify fresh install, backed-up v0.24.1-to-v0.25.0 update, and resumed older SQLite build. The old `v0.24.1` prerelease remains immutable. See [release acceptance](RELEASE-ACCEPTANCE-v0.25.0.md).

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
