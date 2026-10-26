# Reusable components, prebuilt capabilities and safety

Scram (https://www.scram.com/) describes assembling applications from pretested blocks instead of regenerating every subsystem. **This is design inspiration; Scram's private blocks are not part of Orbit.**

For each task, assess (1) audited existing project modules and native APIs, (2) approved, version-pinned reusable blocks with working tests, (3) one relevant maintained external package or skill, and (4) small justified custom implementation if needed. Don't install dependencies because a preferred name is listed.

An approved reusable block must declare: purpose, supported runtimes, source/version/license, public contract, deterministic tests, known security limitations, maintainer and migration/rollback guidance. Keep these records in the project's existing docs; .orbit only points to them. Do not build or claim a huge component catalog without verified blocks.

For a specialist, call `orbit_capability_select` with `orbit-<role>:` in objective and inspect `role_skill_preferences` (names, official sources, conditional applicability, local status). Verify actual installed content and permissions. If missing, use current host-native tools and working project code. Request explicit owner approval for installs and new MCP connections; no automatic downloads, remote scripts or global permission escalation.

Always research relevant domain invariants. A habit tracker needs tests for skipped calendar dates, weekly targets, timezone boundaries, duplicate IDs, unsafe HTML interpolation, invalid backups and persistence. An accessibility/browser smoke test alone is not enough evidence for production readiness.


## Approved component choices and source review

`orbit_decision_route` now includes researched options for Meta Astryx (React 19+; themeable, extensible, MIT/beta), shadcn open-code custom registry, Radix/React Aria primitives, Expo/Flutter cross-platform, SwiftUI and Jetpack Compose native components. These are **review candidates**; check installed versions, licenses, runtime target and security before use. `Custom` is always possible with real acceptance and accessibility tests. Context7 only supplies up-to-date library docs if connected; Impeccable design skill and agent-browser QA are not UI component frameworks. Source matrix: `docs/ADAPTIVE-DECISION-ENGINE.md`. Do not force framework migration solely to satisfy a curated skill list.
