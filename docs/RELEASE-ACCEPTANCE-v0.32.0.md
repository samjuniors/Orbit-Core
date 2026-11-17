# Orbit Core v0.32.0 — Release candidate acceptance

**Status:** RELEASE HOLD — local source/package and upgrade verification performed; real Antigravity, native workers, permissions, and final exact-head CI remain open. **Date:** 2026-11-17.

**Source:** candidate branch `release/v0.32.0-candidate-local-qa` based on Orbit Core draft [PR #128](https://github.com/samjuniors/Orbit-Core/pull/128) head `d05b1a5f98f351c0ed54e9c9cfeebc0069cddee3`; its base is draft [PR #125](https://github.com/samjuniors/Orbit-Core/pull/125). This candidate includes v0.32 source version metadata, draft public notes and the fixed stock v0.31 installer upgrade allowlist. The installed v0.31.0 prerelease and tag remain immutable.

## Verified on Windows (isolated test workspace, Python 3.12)

- Current exact PR #128 head: GitHub CI 5/5 PASS (Ubuntu Python 3.10–3.13, Windows Python 3.12); source suite on Windows exit 0. These runs are **not** CI of the newly versioned v0.32 candidate.
- Candidate `prepare_release_candidate.py`: PASS; desktop v0.32 bundle manifest and runtime parity verified.
- `check_release_readiness.py` and `check_version.py --strict-bundle`: PASS.
- Candidate `build_release.py --verify`: PASS; generated Universal Setup ZIP, Antigravity plugin ZIP, Plugin Suite ZIP, and matching SHA-256 sidecars in disposable `dist/`. Old generated stale suite ZIP and checksum were preserved as `.pre-fix-qa-backup` when rebuilding.
- Candidate `smoke_release_zip.py`: `DISPOSABLE_INSTALL_AND_STDIO_SMOKE_PASS`, 57 MCP tools.
- Previous immutable v0.30.0 → candidate v0.32.0 disposable upgrade: PASS.
- **Initial immutable v0.31.0 → candidate v0.32.0: FAIL (reproduced)** — installer rejected unrecognized unmodified `orbit_cli.py`. Source traced to 7 missing exact SHA-256 stock file digests.
- **Fixed v0.31.0 → v0.32.0: PASS** after collecting 12 installed stock digests from the actual immutable `v0.31.0` tag and adding only 7 missing exact hashes. `tests/test_universal.py` now checks the official stock digests. Owner-edited stock file still triggers refusal before writes; unchanged `AGENTS.md`, `.orbit/STATE.md`, DB bytes and prior runtime survive.
- **Codex CLI 0.166.0 actual MCP invocation: PASS** in ephemeral read-only isolated session. Server `orbit-v032-qa` exposed 57 tools; `orbit_capability_discover` returned `isError=false`, with 15 local-unverified skills and 8 configured-not-connection-verified MCP entries. No write action was requested.
- Candidate full regression: first complete Windows Python 3.12 run **PASS** (693 tests, 29 skipped); repeat run **FAIL** with one transient `WinError 32` in `test_browser_build` temporary directory teardown (693 tests, 29 skipped). Targeted Windows cleanup now retries only explicit file-in-use PermissionError codes for a bounded period, without swallowing persistent failures. Focused `test_browser_build.py` 17-test suite PASS in 3 consecutive Windows runs (3 skipped each). Exact candidate commit CI and another complete suite remain the final authority.

## Not verified / release blockers

1. Actual signed-in Antigravity IDE v0.32 plugin connection, native specialist sessions, cancellation, permission prompts/denial, restart/checkpoint continuity and browser/GUI acceptance: **NOT VERIFIED**. The Codex read-only discovery call does not substitute for native worker acceptance.
2. Exact candidate-head GitHub CI: draft [PR #129](https://github.com/samjuniors/Orbit-Core/pull/129) opened; Ubuntu matrix 4/4 initially PASS, Windows job PENDING on the first candidate commit. The updated Windows cleanup patch must be pushed and rechecked at its new exact head. Merged-main CI, release-tag equality, download and updater verification remain **NOT RUN** pending owner-approved merge/publication.
3. Actual installed-user upgrade, GUI scaling, interactive rollback and cross-device compatibility: **NOT VERIFIED**. Disposable previous-tag upgrade is not a real-user validation.
4. Review all stacked v0.32 PRs and the broad difference since v0.31.0 for breaking behavior, privacy, security and release notes. Existing source branch uses v0.31.0 metadata until this candidate.

## Decision

Keep candidate in draft and do not retag or overwrite v0.31.0. Before publication, require updated final tests, exact candidate-head GitHub CI, real IDE acceptance (or explicit documented risk acceptance where permitted), reviewed merge into main, approved release version and owner release authorization. Preserve previous assets and owner data.
