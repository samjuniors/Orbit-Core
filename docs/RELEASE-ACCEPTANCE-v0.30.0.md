# Orbit Core v0.30.0 ` Release-candidate acceptance record

**Status:** OWNER-APPROVED RELEASE CANDIDATE / FINAL-HEAD CI PENDING / INDEPENDENT GUI ACCEPTANCE NOT VERIFIED / NOT PUBLISHED.
**Date:** 2026-11-05. **Project:** Orbit Core (not Helm, Aro or ORBIT planner).

## 2026-11-05 - Latest owner-approved release reconciliation

The owner explicitly reported PASS and authorized merging, publishing both
v0.29.0 and v0.30.0, and installing Orbit on the connected Windows PC.
This owner-reported acceptance is distinct from independently verified IDE
permission prompts, native host execution, restart, and rollback.

- v0.29.0 was published stable from immutable tag `8f0e3ea` with eight
  checked distribution assets, preserving all prior published releases.
- Native coordination PR #71 merged into `main`. Release workflow PR #87
  merged into `main` after 5/5 Ubuntu/Windows GitHub CI:
  https://github.com/samjuniors/Orbit-Core/actions/runs/41984147062
- Installer safety PR #86 merged into this candidate. Windows Python 3.12
  full suite ran 524 tests, 26 skipped, zero failures, and exact-head
  GitHub CI passed 5/5:
  https://github.com/samjuniors/Orbit-Core/actions/runs/41982615363
  It adds versioned clean/reset progress, rollback, explicit recovery and
  SQLite liveness preflight. The old v1 backup remains manual-review only.
- Current candidate incorporates the latest `main` via an isolated merge,
  without code conflicts. Run its exact-source CI, package verification,
  tag provenance and release checks before v0.30.0 publication.
- On connected Windows PC before installation, machine-wide Antigravity
  and Codex Orbit registrations are absent, and the old v0.25.1 runtime
  is incomplete. Preserve all 203 historical backup files, live SQLite,
  WAL, SHM, host settings and other MCP registrations. Review installer
  changes and take independent backup-first snapshots before applying.
- Actual interactive Antigravity GUI and Codex native session/permission
  acceptance on the exact final release commit remain NOT INDEPENDENTLY
  VERIFIED; installation and restart evidence must be recorded separately.

Older HOLD entries below are historical and superseded only for owner
authorization, not as evidence of independently completed host tests.



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
| Exact candidate GitHub CI | PASS on initial SHA | Candidate commit de221db: 5/5 Ubuntu/Windows jobs PASS, [run #41975838472](https://github.com/samjuniors/Orbit-Core/actions/runs/41975838472); reverify after amendment |
| Genuine Codex native host-invocation acceptance | BLOCKED | Codex 0.166.0 recognized isolated test MCP, but model usage limit prevented any MCP call or returned native session |
| Genuine Antigravity GUI host acceptance | NOT VERIFIED | Project-local config starts version 0.30.0 / 48 tools directly; real GUI invocation and permission prompt unobserved |
| Real installed-user GUI update/restart/rollback | BLOCKED - LIVE REGISTRATION DRIFT | Candidate global preview PASS, but later both global Orbit MCP entries and prior v0.25.1 runtime entrypoint were absent; root cause unverified; do not restore automatically |
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

## 2026-11-05 - Exact CI and isolated host results

- [Candidate GitHub run #41975838472](https://github.com/samjuniors/Orbit-Core/actions/runs/41975838472):
  all five Windows/Linux Python matrix jobs PASS on `de221db8243f03302e6402d0fd574f3af4d82c38`.
  This is source CI, not interactive IDE acceptance.
- A disposable project under `%TEMP%/Orbit-v030-HostAcceptance-20261105/project`
  was installed using `orbit_setup.py install --scope project --hosts antigravity codex`.
  Preview PASS (50 CREATE), test-only apply PASS, and the private
  temporary runtime and database paths were separate from the real user
  installation and all owner projects.
- Direct stdio launches using the generated Antigravity and Codex
  project-local MCP configuration files both returned
  `serverInfo.version=0.30.0` and exactly 48 tools. A synthetic
  read-only draft yielded `DRAFT_REVIEW_REQUIRED`,
  `state_written=false`, `agent_invoked=false`, and no tool error.
  These tests demonstrate project configuration and stdio behavior
  but are NOT actual interactive GUI or model tool use.
- Codex CLI 0.166.0 recognized an ephemeral `orbit_v030_qa`
  MCP definition, but its actual read-only model-run attempt terminated
  with a **usage-limit** message before any MCP call. No host permission
  prompt, native invocation or session was observed. Status: BLOCKED,
  not an Orbit feature regression.
- Antigravity interactive native `invoke_subagent` and
  GUI permission/restart remain NOT VERIFIED. The direct
  synthetic MCP launch does not replace these checks.
- At test setup, the real machine-wide v0.25.1 runtime and global
  Antigravity/Codex registration files were present. A later independent
  read found the Orbit registrations missing; see drift note below.

### Remaining host acceptance procedure

Open the disposable project in the actual Antigravity IDE. Confirm
the **project-local** MCP points to version 0.30.0 with 48 tools;
do not use global v0.25.1. In that genuine host, call
`orbit_native_coordination_preview` on a synthetic read-only task.
Record the actual returned status and permission behavior. A
preview is never native-worker execution. Before an approved
native synthetic worker, require owner/host consent and capture
the real host session; absence of a prompt is not permission denial.
Repeat Codex only after its usage limit is resolved.

### Decision

**HOLD public release and live user-machine update.**
Source, CI, ZIP parity and isolated upgrade checks passed, but real
Codex/Antigravity host acceptance, GUI update/restart/rollback,
and the separate v0.29 public-release sequencing remain open.

## 2026-11-05 - Post-fixture global registration drift (BLOCKED)

The actual Windows device had both Antigravity and Codex global
`orbit-core-native` registrations pointing at the shared
`~/.orbit-universal/0.25.1/orbit_mcp.py` at the start of this session.
A later read-only inspection found:
- Antigravity's global `.gemini/config/mcp_config.json` contains only
  an unrelated service, with no `orbit-core-native` entry.
- Codex's global `.codex/config.toml` similarly has no Orbit entry;
  unrelated MCP settings remain present.
- The previous `0.25.1/orbit_mcp.py` executable is missing, even though
  the `0.25.1` parent folder remains. The old config backup files
  still exist. The detected global config modification timestamps
  are 2026-11-05 at approximately 11:13-11:14 local Windows time.
- The disposable v0.30 installer apply log contains **50** CREATE
  actions, all within `%TEMP%/Orbit-v030-HostAcceptance-20261105`,
  and **zero** paths outside that fixture. The synthetic test
  used isolated setup-home and runtime-home environment paths.

The **origin of the changes to global registration/runtime files is
NOT ESTABLISHED**. Do not claim this was caused by the synthetic
installer, a concurrent user action, or a specific external process
without separate evidence. Do not restore or recreate a host registration
until the owner reviews the current config and chooses the intended
machine-wide state. Live acceptance/upgrade is BLOCKED; source CI and
disposable-host evidence remain valid but do not substitute for it.
