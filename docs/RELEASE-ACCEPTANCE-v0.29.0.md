# Orbit Core v0.29.0 — Development and acceptance evidence

**Status: DEVELOPMENT CANDIDATE — SOURCE/Windows QA VERIFIED; REAL-HOST ACCEPTANCE PENDING.**
**Date:** 2026-11-03. **Project:** Orbit Core (not Helm, Aro or the separate ORBIT planner).

GitHub is engineering authority; [Orbit Core Notion hub](https://app.notion.com/p/4074f681d48881a7a407c3bdc2054409) records the approved product intent. A development branch, version string or passing CI is not a public release.

## Product and supported scope

The approved v0.29 mission is original, **read-only project-aware installed-skill discovery** inspired conceptually by the separately evaluated AAS reference. Existing `orbit_capability_select` gains a bounded shortlist (max five), declared product/platform/technology/operation/IDE-host fit, explicit requests for installed names, and a SHA-pinned `orbit-skill-plan-v2` manifest with drift/revalidation.

All skill directory names, descriptions, version and license metadata are **untrusted claims**. Hash matches prove byte identity, not publisher authenticity, license rights, safe execution or owner consent. No external skill catalog, importer, installation, plugin auto-activation, content execution, subprocess runner, new model layer or new MCP tool is introduced. The existing native host handles permission-gated actions.

## Branch ancestry and version

- Latest **published prerelease**: [v0.28.0](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.28.0); original tested release tag preserved.
- Existing development work: [draft PR #70](https://github.com/samjuniors/Orbit-Core/pull/70), branch `dev/v0.29.0-skill-discovery`, original source `4308b0ff2082ed940cc46368e7515cbd7f51ad32`.
- New separate integration branch: `fix/v029-main-reconcile`, merging latest published-v0.28 `main` commit `015bf5d2cc294de237a129cc317bcf9d6f3062df` into the prior v0.29 source with **zero conflicts**. The preceding merge commit is `db42873d5bd8e94c5af91e02fd559bdfdd79ac79`.
- Candidate metadata: `VERSION=0.29.0`, `NEXT_VERSION=0.30.0`, matching installer, runtime, archive names and public changelog heading. Does not alter already-published v0.28 tags/assets or installed user settings.
- Upgrade suite now tests **immutable v0.28.0 → candidate v0.29.0** on Windows and Linux Python 3.12, in addition to the existing published prior-release checks.

## Actual independent engineering evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Existing skill shortlist targeted regressions | PASS with 3 SKIPs | Windows Python 3.12: 36 tests; 3 symlink/environment skips |
| Initial full source suite | FAIL, repaired | 458 tests; three inherited hardcoded v0.28 assertions uncovered at version promotion, not skill-planner execution defects |
| Corrected full source suite | **PASS** | Windows Python 3.12: 458 tests, 26 skipped, 0 failures; exit 0 |
| Candidate bundle preparation | **PASS** | `prepare_release_candidate.py` generated new 0.29.0 MCPB without changing previous bundles |
| Version/readiness/parity | **PASS** | `check_release_readiness.py` and `check_version.py --strict-bundle` |
| Reproducible ZIP package build | **PASS** | `build_release.py --verify`: Universal Setup 137 files, Antigravity plugin 46 files, plugin suite 173 files |
| Disposable installed stdio smoke | **PASS** | `smoke_release_zip.py`: 47 MCP tools; no user install/IDE touched |
| Latest published release upgrade | **PASS** | `smoke_upgrade_previous.py --previous-root <immutable v0.28.0 checkout>`; preserves owner-custom guidance, .orbit checkpoint, SQLite bytes and v0.28 runtime |
| New integration exact-head CI | **NOT RUN at document creation** | Require Ubuntu Python 3.10–3.13 and Windows Python 3.12 on the pushed PR head |
| Real Antigravity/Codex skill execution/consent | **NOT VERIFIED** | Needs authorized isolated host profiles and explicit real-host evidence; read-only source tests do not attest it |
| Symlink-specific runtime protection on Windows | **SKIPPED in local environment** | Review Linux CI and host filesystem permissions; do not claim Windows symlink acceptance |
| Release merge/tag/public assets | **NOT RUN** | Separate owner decision after source/host QA; do not publish now |

## Acceptance and release blockers

1. Run and inspect **exact integration-head GitHub CI**, including package parity and v0.28 immutable upgrade on Linux/Windows.
2. Independently review untrusted skill parsing, bounded tree hashing, host-specific locations, symlinks, project-scope isolation, stale v1/v2 manifest behavior, explicit permission-denial HOLD and all unverified license/provenance metadata.
3. Exercise *read-only selection and revalidation through the actual project-local MCP* on Antigravity and Codex in disposable projects. Report real host detection, permission denial, invalid/missing/changed skills and fallback; do not install third-party code or silently enable skills.
4. Review owner-specified version cutline, updated draft PR #70, v0.30 stack compatibility, installer upgrade/backups and truthful public documentation before a release candidate is promoted. Require explicit owner merge/publication approval. No Claude Code acceptance required in this cycle.

**Evidence semantics:** PASS means actually executed; documented source tests and local MCP smoke are not live IDE/agent acceptance, and a SHA-256 fingerprint is not a trust or security certificate.
