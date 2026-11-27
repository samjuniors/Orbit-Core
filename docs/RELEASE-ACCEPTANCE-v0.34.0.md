# v0.34.0 — Development acceptance record

**Status:** DEVELOPMENT HOLD — not a release candidate
**Repository:** samjuniors/Orbit-Core
**Branch:** fix/v034-filesystem-security-20261127
**Version metadata:** VERSION=0.33.1, NEXT_VERSION=0.34.0
**Decision authority:** Owner approval is required for PR/merge, release version bump, installation, host configuration and publication.

This record separates implementation evidence from security certification, native-host acceptance and publication. It does not authorize those actions.

## Capability acceptance

| Capability | Current result | Evidence / limitation |
|---|---|---|
| Project structure discovery | IMPLEMENTED / Windows adapter tested | Win32 directory handles are pinned without delete sharing; child reparse points are rejected. A raced/unsafe path makes the scan INCOMPLETE. |
| Source-content audit | IMPLEMENTED / Windows adapter tested | Bounded reads use pinned ancestors and no-delete-share leaf handles. Reparse points and multiply-linked files are rejected; raw source is not returned or persisted. |
| Findings ledger and reconciliation | IMPLEMENTED / TESTED | Stable finding identity, scope separation, review/disposition and revision-guarded task linking; no automatic task creation from unreviewed findings. |
| Audit-to-plan preview | IMPLEMENTED / TESTED | Read-only planning and dependency previews; consequential task creation requires review/confirmation. |
| Specialist candidate | IMPLEMENTED / Windows tested; POSIX adapter added | Windows uses pinned Win32 handles; POSIX uses dir_fd/O_NOFOLLOW and O_EXCL. POSIX tests are present but require Linux CI; no host agent is registered, installed or activated. |
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
| Full Windows test suite | PASS | Python 3.12: 855 tests, 44 skipped, zero failures; runtime 127.839 seconds after POSIX structural inventory integration and canonical/plugin mirror synchronization. Ten POSIX-only tests are skipped on Windows; remaining skips are platform-specific or require symlink privileges. |
| Exact-head GitHub CI | PENDING | Prior run #45557560695 predates this implementation. Fresh CI required after commit/push. |
| Release packaging / ZIP smoke | PASS | Disposable copy built the 0.33.1 candidate MCPB, passed readiness and strict bundle parity, generated all three ZIP packages/checksums, and passed extracted ZIP/MCP stdio smoke with 58 tools. No tracked/published artifact was modified; this is not a v0.34 release. |
| Independent security review | REQUIRED | Review Win32 API semantics, POSIX path traversal/writes, network shares, unusual filesystems and concurrent mutation. |
| Claude lifecycle native integration | NOT VERIFIED | Only synthetic adapter payload tested; no hook activation or active plugin update. |
| Active model switching | NOT IMPLEMENTED | Current router recommends models; it does not switch active host models. |
| Public release / native host certification | NOT APPROVED / NOT VERIFIED | No PR, merge, version bump, tag, release, plugin install, hook activation or live host certification. |

## Security implementation notes

The Windows adapter pins each traversed directory using a Win32 handle opened without FILE_SHARE_DELETE. Leaf opens use FILE_FLAG_OPEN_REPARSE_POINT; reparse points and files with multiple hard links are rejected. Candidate writes use CREATE_NEW beneath the pinned, resolved parent chain. POSIX candidate writes use an opened root descriptor, dir_fd-relative directory creation, O_NOFOLLOW, and exclusive O_CREAT|O_EXCL leaf creation. POSIX structural inventory now uses the existing descriptor-relative walker; source-content scan remains path-based. Linux CI acceptance is still pending.

This is a tested containment design, not a formal proof or independent security certification. Network shares and filesystems with different handle/share semantics have not been certified; keep those environments out of the supported claim until reviewed.

## Remaining exit criteria

1. Convert POSIX source-content audit traversal to descriptor-relative reads, run the POSIX filesystem and audit tests on Linux, and obtain independent review of both platform adapters.
2. Push the verified feature-branch source and obtain exact-head GitHub Actions across Ubuntu and Windows.
3. Validate Claude Code lifecycle hooks in a disposable plugin installation without changing the owner's active plugin.
4. Keep model routing advisory unless a supported host API for observing and switching the active model is verified and separately authorized.
5. Only after those gates, prepare a reviewed release branch: update VERSION/NEXT_VERSION, installer/runtime version declarations, CHANGELOG, README/quickstart and this acceptance record together.

**Current verdict:** Windows structural scanning, source scanning and specialist-candidate creation have been re-enabled through a handle-pinning adapter. The 855-test Windows suite and disposable package/MCP smoke pass. Exact-head CI, independent security review and native Claude acceptance remain outstanding. Keep v0.34 on DEVELOPMENT HOLD.
