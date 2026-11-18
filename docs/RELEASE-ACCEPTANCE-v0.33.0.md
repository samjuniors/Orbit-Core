# Orbit Core v0.33.0 — release-candidate acceptance and verification

**Status:** DRAFT / RELEASE HOLD — candidate source and package development, not publication authorization. Date 2026-11-18. This record supersedes older v0.32 acceptance descriptions only for the **new proposed version**; published v0.32 remains immutable and installed.

**Engineering baseline:** published [v0.32.0](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.32.0), `main` commit `f6b7b4d81198142f121e5793fb9a06fbee195892`. The combined [draft PR #133](https://github.com/samjuniors/Orbit-Core/pull/133) integrates [visual PR #131](https://github.com/samjuniors/Orbit-Core/pull/131), [Autopilot/team PR #132](https://github.com/samjuniors/Orbit-Core/pull/132), and [installer issue #130](https://github.com/samjuniors/Orbit-Core/issues/130). The separate `release/v0.33.0-candidate` source branch sets `VERSION=0.33.0`, `NEXT_VERSION=0.34.0`, matching installer and stdio MCP metadata, and adds an explicitly bounded changelog section.

## Verified evidence (upstream development source; NOT candidate artifact proof)

- Integrated source GitHub [CI #1401](https://github.com/samjuniors/Orbit-Core/actions/runs/44289816258) **PASS 5/5** across Ubuntu Python 3.10–3.13 and Windows Python 3.12, at integration head `5eedd154dea0f203a23303236e4ee51d4cdf9088`. Earlier CI failed one new Windows test fixture's noncanonical path equality; corrected to compare resolved Windows paths and reran green. This test fix changed no installer runtime enforcement.
- Disposable Windows focused visual inventory/policy/quality: 36 tests run (1 skipped, 0 fails); Autopilot charter 31/31; chartered team events 33/33; verified official v0.31 stock Antigravity agent upgrade test 3/3; previous stock-upgrade regression 2/2. The full integrated CI also ran the suite.
- Original signed-in Codex-to-unreleased-branch MCP calls (on prior PR #132) observed bounded local trace, denied staffing `HOLD_PERMISSION_DENIED`, typed specialist return and disallowed transfer control. Report: [PR #132 Windows host evidence](https://github.com/samjuniors/Orbit-Core/pull/132#issuecomment-6975280844). A Codex native inline specialist returned a correct host-reported result, but an independently authenticated child ID/receipt was unavailable. Windows file-read commands were blocked by host policy, no bypass.
- Latest officially published v0.32 ZIP SHA256 `bfa8038cc80dc81d5f87643f0573ae424f9968a7791d7d78327d7d07149556c9` matched release sidecar. User-scope Windows upgrade selected Antigravity and Codex; 75-target preview, compatibility-only exact two-hash in-memory allowance for **byte-identical immutable v0.31 stock** agent files (Issue #130), backup-first official installer; post-install all 75 targets SKIP. The current Windows permanent launcher and a genuine signed-in Codex `orbit_update_status` call confirmed running **v0.32.0**, not v0.33.0. Old runtime and SQLite preserved.

## Candidate-specific release checks (pending fresh evidence)

| Gate | Status | Requirement |
| --- | --- | --- |
| Candidate VERSION/metadata source alignment | SOURCE PREPARED / NOT YET VERIFIED | VERSION, NEXT_VERSION, installer and MCP server versions, no conflict |
| Candidate desktop MCPB source parity | NOT RUN | `python scripts/prepare_release_candidate.py`; strict bundle parity |
| Candidate release notes and README readiness | NOT RUN | `python scripts/check_release_readiness.py` |
| Candidate 57-tool MCP protocol + full suite | NOT RUN | Actual isolated Windows/Linux CI and native version response |
| Candidate package ZIP/MCPB/sidecar checksums | NOT RUN | `python scripts/build_release.py --verify`, ZIP smoke and four pairs |
| Candidate published-old-version upgrade and rollback | NOT RUN | Exact v0.31 and v0.32 stock+custom migration, backed-up recovery |
| Real Codex/Antigravity native worker dispatch, receipt, rejection and resume | PARTIAL / NOT VERIFIED | Independently attributable session, real permissions and trusted acceptance |
| Actual UI/browser/native screenshots and design quality | NOT VERIFIED | Beyond synthetic HTML fixture; independent screen/state review needed |
| Antigravity installed v0.32 IDE after refresh | NOT VERIFIED | Headless CLI timed out; cached schema != MCP invocation |
| Owner final release approval | NOT GIVEN | Require explicit consent and inspect all known risks |
| Merge, tag, GitHub public release, candidate installation on owner's PC | NOT DONE | Only after all required gates and owner approval |

## Security and compatibility boundaries

- Orbit remains a local-first coordinator, **not** a separate LLM/agent runner; the connected coding host controls real tool calls, permissions, model selection and native workers.
- Approval reference SHA-256 and preview digest are not authenticated founder identity, not a cryptographic signature, and not a cross-machine authorization. New journal fingerprints are bounded to the local SQLite database and legacy references cannot be retroactively verified.
- Source-only UI route discovery and caller-reported screenshot/QA evidence never prove rendered visual acceptance; source provenance is a pin/claim, not an independent download/license review.
- v0.33 introduces an intentionally stricter resume API: old custom clients must preview and pass `expected_resume_digest`, not silently downgrade security.
- No third-party OpenAI Agents SDK, new mandatory provider key, cloud trace export, autonomous hidden host runner, silent overwrite, unauthorized third-party installation or unreviewed Git merge.

## Continuity

Current focus: finish fresh candidate packaging + CI, resolve genuine host acceptance and independent review. Keep [draft integration PR #133](https://github.com/samjuniors/Orbit-Core/pull/133) and this candidate work separately reviewable. Record exact-head CI and host evidence here, then update existing Notion project release decisions; do not create an unrelated release policy. Keep prior published v0.32 and rollback assets immutable.
