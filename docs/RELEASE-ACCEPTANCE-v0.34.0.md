# v0.34.0 — Release candidate acceptance record

**Status:** REVIEW HOLD — draft PR #191; not merged or published
**Repository:** samjuniors/Orbit-Core
**Branch:** claude/funny-bell-sxccz9
**Reviewed source HEAD:** `16ec829f215171505f1a7f75b95802dafbcf776a`
**Version metadata:** VERSION=0.34.0, NEXT_VERSION=0.35.0
**Decision authority:** Owner approval is required for PR/merge, release version bump, installation, host configuration and publication.

This record separates implementation evidence from security certification, native-host acceptance and publication. It does not authorize those actions.

## Current gate summary — 2026-11-28

- Exact-head GitHub Actions run [#46126664765](https://github.com/samjuniors/Orbit-Core/actions/runs/46126664765): **PASS**.
- Local Windows Python 3.13 full suite on this exact checkout: **910 tests passed, 55 skipped, 0 failures** in 205.652 seconds. Skips include POSIX-only checks and tests requiring Windows symlink-creation privileges.
- Focused security/reliability subset within that run: **199 tests passed, 26 skipped, 0 failures** across filesystem adapters, audits, findings/readiness, mission supervisor/runner, updater notifications and MCP shared-database behavior.
- `prepare_release_candidate.py`: **PASS**, `generated=false`; committed v0.34.0 desktop bundle is already source-parity clean.
- `check_release_readiness.py`: **PASS**.
- `check_version.py --strict-bundle`: **PASS**.
- `build_release.py --verify`: **PASS** for the Universal Setup, Antigravity plugin and Plugin Suite ZIPs.
- `smoke_release_zip.py`: **PASS**, 59 tools; explicitly not a real IDE, desktop UI or browser test.
- CodeRabbit's review of prior head `6538313` reported 22 Major findings. The owner recorded fixes for three Codex findings and selected CodeRabbit findings in `16ec829`; 19 Major findings and remaining lower-severity comments were still untriaged in that review. A new incremental CodeRabbit review and a Codex review of `16ec829` have been requested; both are pending at this record update.
- Open privacy follow-up: `orbit_source_audit.inventory_snapshot_sha256` remains an unkeyed content-derived digest persisted in the readiness ledger. It needs a locally persisted key or a redesigned non-content-derived identifier; the per-process HMAC in the security-review planner does **not** fix this separate field.
- Independent human security review: **NOT DONE**. Signed-in native-host acceptance (Codex, Claude Code, Antigravity): **NOT VERIFIED**.
- Publication and merge: **NOT APPROVED**. Do not publish while security/review gates remain open.

The full-suite result supersedes the earlier focused-only validation snapshot; the focused subset is listed separately for traceability.

## Capability acceptance

| Capability | Current result | Evidence / limitation |
|---|---|---|
| Project structure discovery | IMPLEMENTED / Windows adapter tested | Win32 directory handles are pinned without delete sharing; child reparse points are rejected. A raced/unsafe path makes the scan INCOMPLETE. |
| Source-content audit | IMPLEMENTED / Windows adapter tested; POSIX adapter added | Windows reads use pinned ancestors and no-delete-share leaf handles. POSIX reads use a pinned root descriptor, descriptor-relative directory traversal and O_NOFOLLOW leaf opens. Both reject multiply-linked files; raw source is not returned or persisted. POSIX regression tests passed in exact-head Linux CI. |
| Findings ledger and reconciliation | IMPLEMENTED / TESTED | Stable finding identity, scope separation, review/disposition and revision-guarded task linking; no automatic task creation from unreviewed findings. |
| Audit-to-plan preview | IMPLEMENTED / TESTED | Read-only planning and dependency previews; consequential task creation requires review/confirmation. |
| Specialist candidate | IMPLEMENTED / Windows tested; POSIX adapter added | Windows uses pinned Win32 handles; POSIX uses dir_fd/O_NOFOLLOW and O_EXCL. POSIX regression tests passed in exact-head Linux CI; no host agent is registered, installed or activated. |
| Claude Code lifecycle adapter | Adapter IMPLEMENTED / synthetic smoke PASS | Optional hooks are not auto-loaded. Actual native Claude Code event delivery remains NOT VERIFIED. |
| Model selection | ADVISORY ONLY | Host-reported model names inform recommendations. Orbit does not switch the active model, provider or account. |
| Quota/capacity | ADVISORY / UNKNOWN without host evidence | Caller-reported context/rate/worker signals are not authoritative subscription quota or billing telemetry. |
| Checkpoint/recovery context | IMPLEMENTED / TESTED | Readiness, finding and resume state are revision/scope-aware. |

## Verification matrix

| Gate | Result | Evidence |
|---|---|---|
| Windows filesystem adapter | PASS | Nine Windows-specific tests cover junction swaps, hard-link insertion, directory rename denial, safe scanning and exclusive candidate creation. |
| Focused Windows integration | PASS | 56 tests across filesystem adapter, project/source audit, readiness, installer and protocol validation; four skips are OS symlink-creation restrictions. |
| Installer runtime inventory | PASS | Installer includes orbit_windows_fs.py and orbit_posix_fs.py; disposable install planning verifies both are shipped. |
| Python / GUI compilation | PASS | Focused py_compile completed without errors. |
| Full Windows test suite | PASS | Python 3.12: 858 tests, 46 skipped, zero failures after the plugin README and canonical package-inventory changes. POSIX-only tests are skipped on Windows; remaining skips are platform-specific or require symlink privileges. |
| Exact-head GitHub CI | PASS | Review head `92d9eb961f24725ef090bd3b3c89e786b0e4a790`; run [#45992428500](https://github.com/samjuniors/Orbit-Core/actions/runs/45992428500) passed 5/5: Ubuntu Python 3.10/3.11/3.12/3.13 and Windows Python 3.12. |
| Claude Code plugin directory validation | PASS WITH WARNING | Plugin manifest and marketplace validate; plugin-specific README and marketplace install command are included from canonical source. The validator reports only the non-blocking missing listing-icon warning. |
| Independent review packet | PREPARED / REVIEW NOT DONE | [SECURITY-REVIEW-PACKET-v0.34.md](SECURITY-REVIEW-PACKET-v0.34.md) defines the threat model, adversarial checklist and required report. A qualified independent reviewer has not yet returned findings. |
| Release packaging / ZIP smoke | PASS | Disposable copy built the 0.33.1 candidate MCPB, passed readiness and strict bundle parity, generated all three ZIP packages/checksums, and passed extracted ZIP/MCP stdio smoke with 58 tools. No tracked/published artifact was modified; this is not a v0.34 release. |
| Independent security review | REQUIRED | Review Win32 API semantics, POSIX path traversal/writes, network shares, unusual filesystems and concurrent mutation. |
| Claude lifecycle native integration | NOT VERIFIED | Synthetic adapter payload tests pass and the plugin directory validates. A session-only native host smoke did not complete under the current Claude CLI provider configuration; no active plugin or user settings were changed. Hook event delivery remains unverified. |
| Active model switching | NOT IMPLEMENTED | Current router recommends models; it does not switch active host models. |
| Public release / native host certification | NOT APPROVED / NOT VERIFIED | Draft PRs #182, #186 and #187 are open; no merge, version bump, tag, release, plugin install, hook activation or live host certification. |

## Security implementation notes

The Windows adapter pins each traversed directory using a Win32 handle opened without FILE_SHARE_DELETE. Leaf opens use FILE_FLAG_OPEN_REPARSE_POINT; reparse points and files with multiple hard links are rejected. Candidate writes use CREATE_NEW beneath the pinned, resolved parent chain. POSIX candidate writes use an opened root descriptor, dir_fd-relative directory creation, O_NOFOLLOW, and exclusive O_CREAT|O_EXCL leaf creation. POSIX structural inventory and source-content audit now use descriptor-relative traversal. The source audit pins the root, reopens each directory component with O_NOFOLLOW, opens source leaves relative to held directory descriptors, rejects non-regular/multiply-linked files, and enforces a total entry bound. POSIX regression tests passed in exact-head Linux CI; independent security review remains pending.

This is a tested containment design, not a formal proof or independent security certification. Network shares and filesystems with different handle/share semantics have not been certified; keep those environments out of the supported claim until reviewed.

## Remaining exit criteria

1. Obtain independent security review of both platform adapters, including concurrent mutation, reparse-point semantics, hard links, supported filesystem boundaries and failure behavior.
2. Preserve the exact-head Linux/Windows CI evidence; rerun after any source or test change.
3. Validate Claude Code lifecycle hooks in a disposable plugin installation without changing the owner's active plugin.
4. Keep model routing advisory unless a supported host API for observing and switching the active model is verified and separately authorized.
5. Only after those gates, prepare a reviewed release branch: update VERSION/NEXT_VERSION, installer/runtime version declarations, CHANGELOG, README/quickstart and this acceptance record together.

**Historical verdict for the earlier development-hold checkpoint:** Windows structural/source scanning and specialist-candidate creation were enabled through handle-pinning adapters; POSIX structural/source traversal had descriptor-relative implementations. The earlier 858-test Windows suite (46 skipped), 5/5 CI, disposable package/MCP smoke and Claude plugin directory validation passed. The current status is superseded by the dated integrated-candidate and current gate summaries above; do not treat this historical hold as the latest status.

## 2026-11-28 — Integrated v0.34.0 release candidate

Branch `claude/funny-bell-sxccz9`, based on main `fae73b3`. Merges context-aware intelligence, filesystem security (PR #186), mission supervisor with the #189 lock fix (PR #187), security review planner (PR #182), resource-first specialists (PR #181), skill lifecycle (PR #180) and Team Builder model routing (PR #179). Conflicts were additive (installer runtime list, tool inventory, tests); no test was dropped. Adds the 128-bit FileIdInfo root identity for #183 and bumps VERSION to 0.34.0 / NEXT_VERSION to 0.35.0.

Linux cloud container, disposable worktrees:

| Check | Result |
|---|---|
| `check_release_readiness`, `check_version --strict-bundle`, `prepare_release_candidate` (`generated=false` after regeneration) | PASS |
| Full unit suite | PASS (886 passed, 19 skipped; Windows-only tests skipped here) |
| `build_release --verify` (3 ZIPs), `smoke_release_zip` | PASS, 59 tools |
| Upgrade rehearsal from v0.32.0 and v0.33.0 (codex + antigravity) | PASS |
| Exact-head Linux/Windows CI on `841d784` ([run #46105837103](https://github.com/samjuniors/Orbit-Core/actions/runs/46105837103)) | PASS 5/5 |
| Windows FileIdInfo and mission-mutex tests on a real Windows PC (owner's DESKTOP-4MRHICM, Python 3.13, disposable clone of `841d784` in %TEMP%, deleted after) | PASS: `tests.test_windows_fs` 12/12 including both 128-bit file-ID tests; `tests.test_autopilot_mission` 22 run, 0 failed, 7 POSIX-only skipped, including `test_second_supervisor_is_held_by_exclusive_process_lock` on the named-mutex path |
| Independent human security review | NOT DONE |
| Signed-in host acceptance (Codex, Claude Code, Antigravity) | NOT VERIFIED |

Historical checkpoint note: this entry predates publication of v0.33.1 and the current `16ec829` head. The v0.33.1 publication prerequisite and disposable upgrade rehearsal are now satisfied; the current review/security hold and owner decision remain as stated in the summary above.

## 2026-11-28 — v0.33.1 to v0.34.0 upgrade rehearsal

The immutable v0.33.1 tag is now available, so scripts/smoke_upgrade_previous.py recognizes 0.33.1 as a supported prior source version.

Windows disposable rehearsal on DESKTOP-4MRHICM (Python 3.13.17), using a fresh clone of PR head ece56ff and a detached worktree at tag v0.33.1:

| Check | Result |
|---|---|
| prepare_release_candidate.py | PASS (generated=false; candidate bundle already exact) |
| check_release_readiness.py | PASS |
| build_release.py --verify | PASS (220-file Universal Setup ZIP; Antigravity plugin and plugin suite verified) |
| smoke_upgrade_previous.py --previous-root <v0.33.1> --hosts codex antigravity | PASS: DISPOSABLE_STOCK_UPGRADE_PASS |

The disposable rehearsal verified both Codex and Antigravity installer targets. A customized installed Orbit-managed file correctly blocked the upgrade without being overwritten; the subsequent stock upgrade preserved custom AGENTS.md, .orbit/STATE.md, the existing database bytes, and the v0.33.1 runtime. Preview mode made no changes, and the v0.34.0 runtime matched the candidate package. The Antigravity agent backup/preservation check also passed. The CI matrix now checks out immutable tag v0.33.1 and repeats this rehearsal on Python 3.12 under both Linux and Windows.

All fixtures and the checkout were under the Windows user's temporary directory, not the F: working copy. This is disposable installer/migration evidence only; it does not certify a signed-in IDE session or real user profile.