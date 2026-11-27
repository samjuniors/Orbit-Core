# ORBIT v0.34 Filesystem Security Review Packet

**Purpose:** Prepare an independent reviewer to assess the filesystem-security changes in draft PR #186. This document is a review brief, not a security approval or certification.

**PR:** https://github.com/samjuniors/Orbit-Core/pull/186  
**Issue:** https://github.com/samjuniors/Orbit-Core/issues/183  
**Review head:** 5205549a309eaf9b13232b578e1093d21eda0df0  
**Implementation/test commit:** a8910328208fec8a3af12dc7e33e336878edca4e

## Scope under review

1. Windows project filesystem adapter and its pinned directory/file handle operations.
2. POSIX descriptor-relative filesystem adapter, including candidate creation and project inventory.
3. POSIX source-content audit traversal and its no-follow file reads.
4. Structural inventory and source-audit integration, including incomplete-scan behavior.
5. Canonical runtime-to-Claude-plugin synchronization and installer inventory.
6. Adversarial regression tests for reparse points, symlinks, hard links, directory replacement and leaf replacement.

The separate source-derived finding-reference change in PR #182 is not included in this packet and should be reviewed against its own issue and diff.

## Threat model

Treat the scanned project tree as untrusted. It may contain or be changed concurrently to contain:

- Windows reparse points, junctions or symbolic links.
- POSIX symbolic links and hard links.
- Directory and leaf replacements between enumeration, validation and open.
- Special files, unreadable entries, oversized files and unrepresentable names.
- A tree that changes while a scan or candidate write is in progress.

The security objective is fail-closed containment: do not follow an untrusted redirect, do not read outside the selected project root, do not overwrite an existing target, and do not mark a partial scan as complete/current.

## Implementation areas to inspect

### Windows

Inspect the handle-pinning implementation in source/runtime/orbit_windows_fs.py and all callers.

Verify:

- Directory ancestors are pinned before descendant operations.
- Sharing flags prevent a pinned directory from being renamed/deleted during the operation.
- Leaf opens do not follow reparse points.
- Reparse-point and multiple-hard-link leaves are rejected.
- File identity is checked against the pinned parent/expected entry.
- Handles are closed on every success and failure path.
- Unsupported or ambiguous filesystem behavior fails closed rather than falling back to ordinary path-based access.

### POSIX

Inspect source/runtime/orbit_posix_fs.py and the descriptor-relative callers.

Verify:

- The selected root is opened and pinned once.
- Descendant traversal and file opens remain relative to pinned directory descriptors.
- O_NOFOLLOW and appropriate directory/file flags are used at every relevant boundary.
- Hard-linked files are rejected where the policy requires a single link.
- Candidate creation is exclusive and cannot follow a leaf symlink.
- No fallback silently reverts to path-based traversal when a platform lacks required dir_fd or no-follow semantics.

### Source and structural audits

Inspect source/runtime/orbit_source_audit.py and source/runtime/orbit_specialists.py.

Verify:

- Source bytes are used only transiently for bounded analysis and are not returned or persisted as raw source.
- Persisted snapshots contain only the intended metadata/digests.
- Oversized, unreadable, redirected or truncated scans report incomplete status.
- Incomplete scans do not replace the last complete snapshot or resolve stale findings.
- Structural inventory and source-content audit have consistent root and link policies.

### Candidate writes

Inspect the candidate-write path and verify:

- Parent directories are anchored to the approved root.
- Leaf creation is exclusive; an existing target is not overwritten.
- Symlink/reparse-point substitution is rejected.
- A failure after partial directory creation cannot escape the approved root or leave an apparently successful candidate.

## Adversarial review checklist

For every item, record PASS, FAIL or NOT TESTED and cite the exact file and line range.

1. Can an attacker replace an ancestor directory after validation but before open?
2. Can an attacker replace a leaf with a symlink, junction or hard link between enumeration and open?
3. Can an attacker rename or delete a pinned directory while an operation is active?
4. Can a file handle refer to a different volume/file identity than the entry validated by the scanner?
5. Are all POSIX opens and traversals descriptor-relative, including error and fallback paths?
6. Can a special file block the scanner or cause unbounded reads?
7. Does any incomplete or truncated scan accidentally become a complete/current snapshot?
8. Can raw source content, credentials or unbounded path data enter the database, event journal or tool response?
9. Can candidate creation overwrite an existing file or escape through a replaced parent?
10. Are unsupported filesystem types and network-share semantics explicitly held rather than implicitly trusted?
11. Do the tests reproduce the races they claim to reproduce, and assert that no outside file was opened or changed?
12. Do the installed/packaged Claude runtime copies exactly match canonical source files?

## Verification evidence already available

- Exact-head GitHub Actions run #45982332996 passed 5/5 on review head 5205549a309eaf9b13232b578e1093d21eda0df0: Ubuntu Python 3.10, 3.11, 3.12, 3.13 and Windows Python 3.12.
- The implementation/test commit a8910328208fec8a3af12dc7e33e336878edca4e also passed 5/5 in run #45981481552.
- The Windows worktree full suite previously reported 857 passed, 46 skipped, 0 failures. Skips include POSIX-only tests on Windows and host-permission-dependent symlink tests.
- Exact CI runs execute the POSIX-only regression tests on Ubuntu and the Windows reparse/junction/hard-link regression tests on Windows.
- Plugin parity, Python compilation and git diff --check were verified on the implementation branch.

CI success proves that the checked-in tests passed on the listed runners. It does not prove the absence of untested races or replace source-level review.

## Supported-boundary questions

Do not assume coverage for macOS, network shares, removable media, cloud-synchronized folders, unusual filesystems, or Windows filesystems with semantics not exercised by the tests. The reviewer must identify which local filesystem/platform combinations are actually supported and whether unsupported combinations fail closed.

## Required independent review report

Return:

- Overall decision: APPROVE, REQUEST CHANGES or INSUFFICIENT EVIDENCE.
- Findings ordered by severity.
- For each finding: exact file/line, preconditions, impact, reproducible test or exploit sketch, and required remediation.
- Explicit list of platform/filesystem combinations reviewed and not reviewed.
- Residual risks and tests that remain unverified.

Do not issue a blanket security certification. Do not close issue #183 solely because CI is green.

