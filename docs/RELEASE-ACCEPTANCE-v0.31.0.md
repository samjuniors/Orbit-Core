# Orbit Core v0.31.0 — candidate engineering and release acceptance

**Status: SOURCE INTEGRATION PREPARED / RELEASE CANDIDATE REVIEW / HOST ACCEPTANCE OPEN / NO PUBLICATION AUTHORIZED.** Recorded 2026-11-05. Product: Orbit Core only, not other Samjuniors products. This record deliberately separates development-source tests, GitHub CI, packaged installer checks and real signed-in host work.

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
