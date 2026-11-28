# Orbit Core v0.33.1 — release acceptance and outstanding gates

**Status:** SOURCE MERGED / RELEASE NOT PUBLISHED / ACCEPTANCE INCOMPLETE. Do not treat the main version value as a published package.

**Version:** 0.33.1  
**Current main:** [2fdf4f329774b9644e75ac0df4d89738a7cd625f](https://github.com/samjuniors/Orbit-Core/commit/2fdf4f329774b9644e75ac0df4d89738a7cd625f)  
**NEXT_VERSION:** 0.34.0 (proposal only)  
**Published baseline:** [v0.33.0 prerelease](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.33.0), 2026-11-23. Latest stable-channel release remains v0.30.0.

## Scope

Patch release for the Claude Code Windows MCP startup issue. Generated plugin configuration uses ${ORBIT_PYTHON:-python}; the default remains python, and a Windows user whose python command resolves to the Microsoft Store alias can set ORBIT_PYTHON to a full Python 3.10–3.13 executable path. No MCP tool, database schema or workflow change is intended; the changelog reports the existing 57-tool interface.

## Evidence recorded

- [PR #175](https://github.com/samjuniors/Orbit-Core/pull/175) merged to main at a90f1b398a2be9a3807277f560360598ef247e36. It updates the Claude Code plugin command, VERSION, CHANGELOG, README and marketplace description.
- PR #175 reports Windows 11 / Claude Code 2.1.307 isolated-profile checks: plugin validate PASS; marketplace update 0.33.0 → 0.33.1 PASS; claude mcp list reports Connected when ORBIT_PYTHON is set. Without the override, the Store-alias failure remains unchanged. This is isolated-profile evidence, not proof that the owner's normal profile has been migrated.
- PR #175 reports local Windows CPython 3.12: 769 tests passed, 33 skipped; check_release_readiness, check_version --strict-bundle, build_release --verify and smoke_release_zip passed. These results are reported in the PR; they were not re-executed in this automation run.
- Current main exact-head [CI run #45167794202](https://github.com/samjuniors/Orbit-Core/actions/runs/45167794202) passed 5/5 on 2fdf4f after subsequent main changes.
- CHANGELOG.md contains a 0.33.1 prerelease entry; the committed Claude Code plugin manifest reports 0.33.1. The current main README and release quickstart distinguish published v0.33.0 from unpublished source v0.33.1.

## Compatibility and known limitations

- The patch is intended to preserve the existing MCP tool inventory, database format and workflow behavior. Universal Setup, Codex, Antigravity and Claude Desktop packages carry the version change; the release workflow must rebuild and verify all four packages and their SHA-256 sidecars.
- All v0.33.0 limitations still apply: host-enforced timed native permission expiry and active revocation remain BLOCKED; owner-profile Codex/Antigravity specialist delivery and migration/rollback remain NOT VERIFIED; full real-product visual/browser QA remains NOT VERIFIED; no independent human security review has been performed.
- The patch does not include RAD P2 OS isolation [issue #138](https://github.com/samjuniors/Orbit-Core/issues/138).

## Outstanding publication gates

| Gate | Current status | Evidence / next step |
| --- | --- | --- |
| Main source and package version | PASS | VERSION=0.33.1; plugin manifest and CHANGELOG agree. |
| Main exact-head CI | PASS | Run #45167794202, 5/5 on 2fdf4f. |
| PR #175 local package and test gates | PASS — PR-reported | 769 tests, 33 skipped; readiness, strict bundle, build verify and ZIP smoke. Re-run through the publication workflow on the exact main head. |
| Owner's normal Claude Code profile with ORBIT_PYTHON | NOT VERIFIED | The evidence is from an isolated profile. Validate in an owner-authorized session without overwriting custom configuration. |
| Owner-profile Codex/Antigravity migration and specialist delivery | NOT VERIFIED | Keep separate from the Claude Code patch; do not infer from package tests. |
| Timed permission expiry and active revocation | BLOCKED | No host-native evidence; issue #138 remains open. |
| Independent human security review | NOT DONE | Obtain review of the exact release candidate and record residual risk. |
| Main branch protection / required checks | NOT VERIFIED | GitHub API returned 403 to this integration; inspect with owner access. |
| Owner-only release workflow | NOT RUN for v0.33.1 | The manual workflow requires an owner-triggered dispatch from main and re-runs the full release gates. No v0.33.1 tag or public release exists. |

## Disposition

**Do not publish v0.33.1 from this checkpoint.** Source and hosted CI are green, but owner-profile acceptance and independent human security review are not complete, and the release workflow has not run for this version. The user-authorized release condition requires these gates and the documented residual risks to be accepted first. When ready, use only the owner-only manual workflow from the reviewed main head; never create or move the tag manually.
