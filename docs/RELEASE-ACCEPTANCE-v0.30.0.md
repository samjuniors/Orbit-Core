# Orbit Core v0.30.0 ` Release-candidate acceptance record

**Status:** CONDITIONAL SOURCE RELEASE CANDIDATE / REAL-HOST QA HOLD / NOT PUBLISHED.
**Date:** 2026-11-05. **Project:** Orbit Core (not Helm, Aro or ORBIT planner).

This is a version-specific evidence record, not another publication policy.
Follow [RELEASE-PROCESS.md](RELEASE-PROCESS.md) and the
[Orbit Core Notion decisions](https://app.notion.com/p/4074f681d48881a7a407c3bdc2054409).
GitHub proves code, CI and releases; real hosts prove actual IDE behavior.

## Exact candidate provenance

- Reviewed development source: `dev/v0.30.0-native-coordination` at
  `2cbfac0725b6adf1b8670c7f0a754a8b713264e9`;
  [PR #71](https://github.com/samjuniors/Orbit-Core/pull/71).
- Host-observation guard: [PR #73](https://github.com/samjuniors/Orbit-Core/pull/73).
  Verified old-Windows-user migration: [PR #83](https://github.com/samjuniors/Orbit-Core/pull/83).
- Candidate branch: `release/v0.30.0-candidate`, distinct from main and the
  still-open v0.30 development PR.
- Metadata: `VERSION=0.30.0`, `NEXT_VERSION=0.31.0`; installer, stdio
  runtime, desktop bundle and distribution package names must all match.
- Public latest GitHub Release at preparation: `v0.28.0` prerelease.
  Source v0.29.0 is merged to main, but its public release is missing.

## Acceptance gates

| Gate | Status | Evidence or next action |
| --- | --- | --- |
| v0.30 coordinator and host-observation repair | SOURCE IMPLEMENTED | 48-tool read-only coordination; fail-closed unstarted-task release |
| Prior development exact-head CI | PASS | v0.30 merged dev HEAD `2cbfac0`, Windows and Ubuntu matrix |
| Prior development Windows regression | PASS | 516 tests, 26 skipped, zero failures (2026-11-05); not current candidate |
| Actual v0.25.1 machine migration dry-run | PASS ` PREVIEW ONLY | Antigravity + Codex: 24 CREATE, 11 UPGRADE, 1 APPEND, 1 MERGE, 22 SKIP; zero user writes |
| Candidate Python regression, strict bundle parity | PASS | Windows Python 3.12: 516 tests, 26 skipped, 0 failures; compilation, candidate MCPB preparation, release readiness and strict bundle version/source parity PASS |
| Candidate ZIP/disposable install and prior-version upgrades | PASS for automated fixtures; host security QA NOT VERIFIED | Universal/Antigravity/Suite package checksums and ZIP builder PASS; 48-tool stdio smoke PASS; isolated v0.28.0 and v0.25.1 upgrades PASS, preserving owner docs, SQLite bytes, previous runtime |
| Exact candidate GitHub CI | NOT RUN | All Ubuntu Python 3.10`3.13 and Windows Python 3.12 jobs |
| Genuine Codex native host-invocation acceptance | NOT VERIFIED | Isolated profile; actual session, permissions, independent review |
| Genuine Antigravity GUI host acceptance | NOT VERIFIED | A missing permission prompt is NOT a host denial |
| Real installed-user GUI update/restart/rollback | PREVIEW ONLY PASS, APPLY NOT RUN | Actual machine candidate update preview: 24 CREATE, 11 UPGRADE, 1 APPEND, 1 MERGE, 22 SKIP; installed v0.25.1 preserved |
| Main merge, immutable tag, public release | NOT RUN | Separate owner approval and v0.29 release-sequence resolution |

## Safety and rollback rules

Do not overwrite the owner's current shared
`~/.orbit-universal/0.25.1` runtime or any IDE registration during candidate
testing. Run synthetic host acceptance with a temporary dedicated profile and
disposable project. Keep prior versioned runtime directories, user-guidance
files, SQLite databases, WAL and `.orbit` checkpoints, and create verified
backups before an explicitly approved on-machine installation.

Source/unit smoke and reported host session IDs are not independently attested
native-worker execution, GUI permission prompts, security review or public
release. Preserve prior Git tags, released downloads and project histories.

## 2026-11-05 ` Windows candidate source test evidence

- Source workspace: disposable checkout from `2cbfac0725b6adf1b8670c7f0a754a8b713264e9`
  on new branch `release/v0.30.0-candidate`; not the real installed runtime.
- `py -3.12 -m unittest discover -s tests -q`: **516 tests, 26 skipped, zero failures; exit 0**.
- `py -3.12 -m compileall -q source installer.py orbit_setup.py scripts tests`:
  **PASS**. `scripts/prepare_release_candidate.py`, `check_release_readiness.py`
  and `check_version.py --strict-bundle`: **PASS**.
- `scripts/build_release.py --verify`: **PASS**; three versioned
  ZIPs and SHA-256 sidecars generated in the disposable source checkout.
  `scripts/smoke_release_zip.py`: **DISPOSABLE_INSTALL_AND_STDIO_SMOKE_PASS**
  (48 discovered MCP tools; no host GUI tested).
- `scripts/smoke_upgrade_previous.py --previous-root <v0.28.0 tag>`:
  **DISPOSABLE_STOCK_UPGRADE_PASS**, `0.28.0` to `0.30.0`.
  The same rehearsal with the immutable `v0.25.1` tag: **PASS**.
  Both retained customized owner guidance, checkpoint and database bytes,
  and the previous versioned runtime.
- Actual machine `orbit_setup.py update --scope machine --hosts antigravity codex`
  without apply: **PASS/PREVIEW ONLY**. All original installed v0.25.1
  files, MCP registrations, user configs, checkpoint and SQLite untouched.
- Owner-directed Codex/Antigravity native IDE permission and restart acceptance:
  **NOT VERIFIED**. Automated acceptance is not a GUI permission observation.

The upgrade rehearsal script's explicit reviewed candidate set now includes
`0.30.0`; this is not an authorization to release, merge to main or overwrite
any installed files. Re-run complete exact-head CI and local tests after
any further source changes.
