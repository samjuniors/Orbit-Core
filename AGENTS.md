# Orbit Core MCP — instructions for coding agents and release maintainers

This repository is **Orbit Core MCP**, not Helm, Aro, SamjuniorsOS or a separate personal-planning plugin.

## Source-of-truth boundaries

- **GitHub** is authoritative for code, branches, PRs, CI, published tags, release assets and engineering evidence.
- The dedicated **Orbit Core Notion hub** records product decisions, roadmap, durable research, release intent and version status: https://app.notion.com/p/4074f681d48881a7a407c3bdc2054409
- Project-scoped **SQLite and `.orbit`** hold local execution history, checkpoints and recovery. These systems do not synchronize automatically.

## Model-independent development handoffs

Use the one canonical [cross-agent continuity and active-state handoff](docs/AGENT-HANDOFF.md) when moving work between ChatGPT, Claude Code, Codex, Antigravity and other authorized hosts. `CLAUDE.md` is a Claude Code entry point to these same rules, not a separate policy.

- On exit, record the **exact workstream, branch and HEAD**, status of uncommitted work, changes, tests with source SHA and real evidence, blockers, approved scope, local Orbit checkpoint/task revision **if actually accessible**, and one safe next step.
- On entry, **revalidate live** GitHub/Notion/host availability and the project-scoped SQLite/`.orbit` state before resuming. If they differ, reconcile without losing work or replaying uncertain side effects. No host permission or hidden model session state transfers automatically.
- Use reviewed PR/branch records for redacted engineering handoffs; the **existing** Notion hub for durable product decisions; local ignored SQLite/`.orbit` for operational details. Never commit private host settings, credentials, approval tokens, raw WAL files or unrelated project data.
- Don't let two agents concurrently write the same workstream or assume a previous host's unverified result was a PASS. Retain the owner's final authority. **Orbit Commander is separately paused and outside this repository.**

## Every release — required workflow

**Read and follow [docs/RELEASE-PROCESS.md](docs/RELEASE-PROCESS.md) before working on a version.** It contains the single canonical release checklist and public changelog template. Do not invent a competing release guide or rely on a prior chat summary as proof of current release state.

1. Verify GitHub `main`, the intended release/development branch, latest immutable tags/assets, active PRs and version-specific acceptance record; reconcile with the latest Orbit Core Notion decision.
2. Use a separate reviewed branch; update `VERSION`, `NEXT_VERSION`, source installer/MCP, desktop metadata, existing `CHANGELOG.md`, current README, quickstart and host package documentation as required. New public notes use the existing changelog section and never require manual copy/paste into a GitHub release form.
3. Run `python scripts/prepare_release_candidate.py`, `python scripts/check_release_readiness.py`, full unit tests, `python scripts/check_version.py --strict-bundle`, reproducible builds and disposable ZIP/MCP smoke. Run exact-head Linux/Windows CI, previous-version upgrade preservation and applicable native IDE consent, cancellation, installer, security and rollback acceptance. State **PASS / FAIL / BLOCKED / SKIPPED / NOT RUN / NOT VERIFIED** precisely.
4. Do **not** equate green CI with native-host permission, successful user install, security certification or production readiness. Never overwrite customized host settings, SQLite/WAL, owner documents, or personal projects while testing.
5. The **owner has final merge and publication authority**. Never silently merge, tag, push a release, install dependencies, modify user machines or rerun publication after a failure. A PR merge is not itself publication approval. Follow the official `Publish versioned release` workflow only once approved and gated.
6. After publishing, verify exact public tag and source commit, actual release notes, expected four ZIP/MCPB packages and four checksum sidecars, integrity, updater discovery and a disposable install. Record linked evidence and remaining limitations in the **existing** version acceptance record and Notion hub. Preserve all prior immutable tags and assets; use a new SemVer version for changed binaries.

When asked to "release the next version", execute the checklist and report blockers or concrete results; do not ask the owner to reconstruct the workflow. Only request explicit approval for genuinely risky or outstanding decisions.
