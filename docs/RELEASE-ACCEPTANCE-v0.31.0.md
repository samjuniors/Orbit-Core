# Orbit Core v0.31.0 — candidate engineering and release acceptance

**Status: COMPLETE v0.31 SOURCE CONSOLIDATED ON REVIEW BRANCH / HOST ACCEPTANCE OPEN / NOT PUBLISHED.** Updated 2026-11-06. Historic acceptance evidence below is preserved and superseded by the latest checkpoint at the end of this document. Product: Orbit Core only, not other Samjuniors products. This record deliberately separates development-source tests, GitHub CI, packaged installer checks and real signed-in host work.

## Sources of truth and provenance

- Published immutable previous stable: [v0.30.0](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.30.0); do not overwrite it.
- Reviewed source integration: [draft PR #95](https://github.com/samjuniors/Orbit-Core/pull/95), based on the source development work in [PRs #88, #89, #93 and #94](https://github.com/samjuniors/Orbit-Core/pulls).
- Candidate source branch: `release/v0.31.0-candidate`, not `main`. `VERSION=0.31.0` and `NEXT_VERSION=0.32.0` refer to candidate build metadata, **not a public release**.
- Product and safety rationale: [Notion design](https://app.notion.com/p/40f4f681d48881cea5afc2df9a35084c). Implementation work: GitHub issues [#90](https://github.com/samjuniors/Orbit-Core/issues/90), [#91](https://github.com/samjuniors/Orbit-Core/issues/91), [#92](https://github.com/samjuniors/Orbit-Core/issues/92).

## Feature implementation review

| Feature | Source status | Proof or remaining gate |
| --- | --- | --- |
| Release-aware CLI and PowerShell wrapper | Development integrated | Exact branch-head CI/ZIP smoke and real Windows install/update/uninstall acceptance required |
| Owner-selected Orbit coordinator preference and competing-plugin name audit | Development integrated | Read-only heuristic; actual host precedence against semantic duplicate plugins NOT VERIFIED |
| Context-inferred security, quality, privacy, accessibility and recovery | Development integrated | Deterministic blueprint regression; actual code-specific review not automatically attested |
| Project-scoped reviewed practice to instruction-only SKILL.md | Development integrated | Revision/fresh-evidence/no-overwrite tests; global activation and cross-project reuse intentionally not automatic |
| Resource-first specialist role recommendations | Development integrated | Selection remains read-only; external source/license and native host tool safety require separate inspection |
| Project Manager, Creative Director, Software Engineer and enhanced existing orbit-security profiles | Source profiles integrated | Host-specific real native subagent registration, selection, permissions and execution NOT VERIFIED |
| Bounded autonomous continuation inside approved milestones | Host guidance integrated | Real native execution/cancellation/verification/stop-gates NOT VERIFIED |
| Continuous lifelong background learning, model weight training, global skill activation, independent worker executor | NOT IMPLEMENTED | Not part of this release's safe scope; require separate owner consent/design |

## Verified candidate CI checkpoint — 2026-11-06

- **Exact reviewed candidate SHA:** `7d5ac1538a1703a7db938b761dcde025b9234fa4` (prior to this documentation-only checkpoint).
- **GitHub CI run:** [42077141682](https://github.com/samjuniors/Orbit-Core/actions/runs/42077141682), completed with overall conclusion **success**. All five matrix checks completed **success**: Ubuntu Python 3.10, 3.11, 3.12 and 3.13; Windows Python 3.12. CodeRabbit was skipped, not passed.
- This is evidence of the GitHub workflow as configured on that SHA; do **not** infer from its aggregate status that manual CLI commands, packaged Windows installer GUI interactions, real host worker sessions, or user-machine migration/rollback were independently executed.
- Candidate remains on a draft PR stack: [#95](https://github.com/samjuniors/Orbit-Core/pull/95) into `main`, then [#96](https://github.com/samjuniors/Orbit-Core/pull/96) into the integrated branch. The current `main` still publishes v0.30.0.
- **Next gate:** review exact CI workflow command coverage and candidate artifact manifests; test a disposable v0.30→v0.31 update/rollback, real Antigravity/Codex host invocation and permission/recovery paths. The owner must approve merge and publication separately.
- **Release status:** HOLD; this checkpoint is not a release authorization. Do not claim all cross-chat self-improvement, native dynamic agent creation, or background autonomy are implemented; their guarded draft/selection foundations are the candidate's scope.


## Unmerged learning follow-up development — 2026-11-06

The isolated branch `feat/v031-continuous-learning-agent-factory` adds four proposed MCP interfaces to the prior 48-tool candidate: explicit project improvement recording, scoped recall, privacy-reviewed cross-project abstract lesson promotion, and a project-only specialist candidate factory. **Expected inventory after integration: 52**, not the older 48. New tests cover project isolation, no-overwrite, revisions, secret/injection guards and shared lesson revocation. These features only improve procedural records and drafts; they never train model weights, automatically execute a skill, start a worker, install plugins or attest host consent. Source and package tests must run on the exact new head and this development must be reviewed and integrated into PR #96 before publication. Do not count it as published until it is merged and retested. Real Antigravity/Codex specialist invocation and signed-in host permission are separate outstanding release gates.

## Engineering and package verification

- Initial learning/specialists draft CI uncovered missing installer runtime modules and hardcoded Antigravity agent count. Fixes now add both runtime modules and validate 16 source agent profiles.
- The complete integrated PR #95 source has Ubuntu Python 3.10–3.13 checks reported PASS; final exact-head Windows + Ubuntu acceptance and all package/upgrade smoke must be independently read back before approval.
- This candidate must regenerate `ORBIT-Claude-Desktop-v0.31.0.mcpb` from previously released immutable bundle resources using `scripts/prepare_release_candidate.py`, and require all source module byte parity checks to pass.
- Run `python scripts/check_release_readiness.py`, `python -m unittest discover -s tests -v`, `python scripts/check_version.py --strict-bundle`, `python scripts/build_release.py --verify`, `python scripts/smoke_release_zip.py`, and all five Ubuntu/Windows CI jobs on the exact final candidate SHA. Record actual command outputs, artifact checksum inventory and exceptions. **Do not mark PASS on this template until results exist.**

## Live owner-host acceptance — NOT VERIFIED

- Antigravity: installed/connected MCP version and 48-tool inventory, actual developer and specialist role invocation, current permission prompt/denial, restart/resume, validated browser/native UI where appropriate.
- Codex: installed/connected MCP version and 48 tools, native worker session, approved delegation, failed worker recovery, honest source/test evidence and verified handoff.
- Windows installer: v0.30.0 to v0.31.0 transition, scope preview, owner-edited conflict handling, existing SQLite/WAL/SHM preservation, backup inventory, clean reset and recovery in a disposable home (live profile destructive actions require separate consent).
- Cross-platform: Linux real host/toolchain integration, final release ZIP extraction, previous-version migration and rollback. CI is not equivalent to signed-in host acceptance.
- User PCs were offline during preparation; no live host state was changed or independently tested.

## Release HOLD and decision

**HOLD publication and installed-user updates** until exact candidate GitHub CI and package/version parity are confirmed, source risks/security review completed, real Antigravity/Codex acceptance completed or explicitly and accurately risk-accepted, and owner explicitly authorizes merge/publication. A draft PR is not authorization to tag, deploy, publish or install.

At every meaningful milestone update this existing acceptance record with exact branch/head, test evidence, unresolved blockers, reviewed artifacts, decision date and next action. Preserve prior release downloads, tags, project memories, owner files and backups.


## 2026-11-06 — Reconciliation against merged main (newest checkpoint)

- **Source:** `main` merged [PR #98](https://github.com/samjuniors/Orbit-Core/pull/98) at `134dff7b0be6e3febb2db40dcbdebc33b4cebd02` (release CLI and coordinator warnings). The complete release candidate and learning-agent-factory draft were separately preserved, then reconciled into `integration/v031-complete-20261106` with source merge commits. Earlier drafts [#95](https://github.com/samjuniors/Orbit-Core/pull/95), [#96](https://github.com/samjuniors/Orbit-Core/pull/96), [#97](https://github.com/samjuniors/Orbit-Core/pull/97) were not rewritten or deleted.
- **Integrated scope:** v0.31.0 is the **52-tool** candidate, including the existing resource-first specialists, default product-quality review, reviewed practices, project-isolated improvement recording, bounded recall, explicit privacy-reviewed abstract lesson promotion and reviewed specialist candidate drafting. No model training, unrestricted native agent execution, automatic skill installation or automatic cross-project memory sync.
- **Local Windows read-only inventory:** Antigravity and Codex both show a user-scope Orbit MCP registration. Codex also contains `orbit-m5-test`, flagged `POSSIBLE_ORBIT_ALIAS` by name only. `priority_enforced=false`, `configuration_modified=false`, `host_connection_verified=false`. Do not remove this fixture without separate inspection.
- **Local package checks on consolidated branch:** `scripts/prepare_release_candidate.py` PASS; `scripts/check_release_readiness.py` PASS; `scripts/check_version.py --strict-bundle` PASS; `scripts/build_release.py --verify` PASS with 166 Universal ZIP files, 56 Antigravity plugin files and 211 plugin-suite files; `scripts/smoke_release_zip.py` PASS (`DISPOSABLE_INSTALL_AND_STDIO_SMOKE_PASS`, 52 tools). These are **locally generated unpublished artifacts**.
- **Focused regression:** 31 tests completed, 1 skipped, zero failures. Full regression suite and exact-head GitHub CI remain to be recorded separately after completion.
- **Live-host boundary:** Antigravity/Codex UI/native tool selection and permission/denial/restart tests are **NOT VERIFIED**; no installed runtime was changed. Publish only after reviewing the final exact-head CI and consciously accepting any remaining real-host limits; a configured MCP or smoke import does not prove live user experience.
- **Latest release authority:** public `v0.30.0` remains unchanged until an actual `v0.31.0` tag and release are published and checksum-verified.
