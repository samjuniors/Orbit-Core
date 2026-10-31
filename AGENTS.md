# Orbit Core MCP — instructions for coding agents and release maintainers

This repository is **Orbit Core MCP**, not Helm, Aro, SamjuniorsOS or a separate personal-planning plugin.

## Source-of-truth boundaries

- **GitHub** is authoritative for code, branches, PRs, CI, published tags, release assets and engineering evidence.
- The dedicated **Orbit Core Notion hub** records product decisions, roadmap, durable research, release intent and version status: https://app.notion.com/p/4074f681d48881a7a407c3bdc2054409
- Project-scoped **SQLite and `.orbit`** hold local execution history, checkpoints and recovery. These systems do not synchronize automatically.

## Every release — required workflow

**Read and follow [docs/RELEASE-PROCESS.md](docs/RELEASE-PROCESS.md) before working on a version.** It contains the single canonical release checklist and public changelog template. Do not invent a competing release guide or rely on a prior chat summary as proof of current release state.

1. Verify GitHub `main`, the intended release/development branch, latest immutable tags/assets, active PRs and version-specific acceptance record; reconcile with the latest Orbit Core Notion decision.
2. Use a separate reviewed branch; update `VERSION`, `NEXT_VERSION`, source installer/MCP, desktop metadata, existing `CHANGELOG.md`, current README, quickstart and host package documentation as required. New public notes use the existing changelog section and never require manual copy/paste into a GitHub release form.
3. Run `python scripts/prepare_release_candidate.py`, `python scripts/check_release_readiness.py`, full unit tests, `python scripts/check_version.py --strict-bundle`, reproducible builds and disposable ZIP/MCP smoke. Run exact-head Linux/Windows CI, previous-version upgrade preservation and applicable native IDE consent, cancellation, installer, security and rollback acceptance. State **PASS / FAIL / BLOCKED / SKIPPED / NOT RUN / NOT VERIFIED** precisely.
4. Do **not** equate green CI with native-host permission, successful user install, security certification or production readiness. Never overwrite customized host settings, SQLite/WAL, owner documents, or personal projects while testing.
5. The **owner has final merge and publication authority**. Never silently merge, tag, push a release, install dependencies, modify user machines or rerun publication after a failure. A PR merge is not itself publication approval. Follow the official `Publish versioned release` workflow only once approved and gated.
6. After publishing, verify exact public tag and source commit, actual release notes, expected four ZIP/MCPB packages and four checksum sidecars, integrity, updater discovery and a disposable install. Record linked evidence and remaining limitations in the **existing** version acceptance record and Notion hub. Preserve all prior immutable tags and assets; use a new SemVer version for changed binaries.

When asked to "release the next version", execute the checklist and report blockers or concrete results; do not ask the owner to reconstruct the workflow. Only request explicit approval for genuinely risky or outstanding decisions.
