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
| Full Windows test suite | PASS | Python 3.12: 857 tests, 46 skipped, zero failures; runtime 131.512 seconds after POSIX source-audit integration and canonical/plugin mirror synchronization. POSIX-only tests are skipped on Windows; remaining skips are platform-specific or require symlink privileges. |
| Exact-head GitHub CI | PASS | Commit `a8910328208fec8a3af12dc7e33e336878edca4e`; run [#45981481552](https://github.com/samjuniors/Orbit-Core/actions/runs/45981481552) passed 5/5: Ubuntu Python 3.10/3.11/3.12/3.13 and Windows Python 3.12. |
| Release packaging / ZIP smoke | PASS | Disposable copy built the 0.33.1 candidate MCPB, passed readiness and strict bundle parity, generated all three ZIP packages/checksums, and passed extracted ZIP/MCP stdio smoke with 58 tools. No tracked/published artifact was modified; this is not a v0.34 release. |
| Independent security review | REQUIRED | Review Win32 API semantics, POSIX path traversal/writes, network shares, unusual filesystems and concurrent mutation. |
| Claude lifecycle native integration | NOT VERIFIED | Only synthetic adapter payload tested; no hook activation or active plugin update. |
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

**Current verdict:** Windows structural/source scanning and specialist-candidate creation are enabled through handle-pinning adapters; POSIX structural/source traversal now has descriptor-relative implementations. The 857-test Windows suite and disposable package/MCP smoke pass. POSIX regression tests passed in exact-head Linux CI; independent security review and native Claude lifecycle acceptance remain outstanding. Keep v0.34 on DEVELOPMENT HOLD.
