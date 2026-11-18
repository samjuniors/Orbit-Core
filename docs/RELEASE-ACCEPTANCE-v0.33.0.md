# Orbit Core v0.33.0 — release acceptance and outstanding gates

**Status:** DRAFT / DEVELOPMENT SOURCE; **NOT MERGED, TAGGED, INSTALLED OR PUBLISHED AS v0.33.0**. This document records evidence and blockers; it is not a publication authorization or a production certificate.

**Date:** 2026-11-18. **Engineering branch:** `integration/v033-visual-coordination-20261118`, [draft PR #133](https://github.com/samjuniors/Orbit-Core/pull/133). Combined sources: [visual policy PR #131](https://github.com/samjuniors/Orbit-Core/pull/131) and [approval, specialist-return and tracing PR #132](https://github.com/samjuniors/Orbit-Core/pull/132). The latest evidence-bearing integrated commit before this record was `5eedd154dea0f203a23303236e4ee51d4cdf9088`. Evidence MUST be rechecked on the final candidate/tag commit if changed.

**Published installation baseline:** [v0.32.0](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.32.0) is the newest published **prerelease**, installed in the owner's Windows user scope. The stable channel's newest release is v0.30.0 as of this review. The installed Orbit CLI reports `0.32.0`; the release-aware candidate update check reports installed=published=`0.32.0` and **no newer candidate**. Actual Codex and Antigravity configured `orbit-core-native` MCP launchers use Windows Python 3.12 and the versioned installed `.orbit-universal/0.32.0/orbit_mcp.py`. The general doctor auto-detects Python 3.15 elsewhere on the machine; this does not change the verified host-specific Python 3.12 commands. Never silently replace a published release with a development checkout.

## Intended v0.33 content (implemented in review source)

- Source-aware visual inventory, project-scoped design guidance and token/literal drift **hints**, conservative route/state coverage proposals and stale source-fingerprint holds. These do not independently render an app or certify actual visual quality.
- Replay-resistant Autopilot resume with a two-step revision/source/scope-bound review digest and locally unique approval-reference fingerprints. Caller references/digests do **not** authenticate a person, authorize filesystem access or terminate native workers.
- Typed specialist return-to-lead contracts, separate host send/receipt observations and independently required lead review. Orbit does not run its own LLM or override the connected host.
- Bounded, redacted, local-only mission/team event timeline with payload-integrity warnings; not exported cloud telemetry and not independently authenticated host execution.
- Exact immutable official v0.31 stock-agent digest recognition in a future safe installer for [issue #130](https://github.com/samjuniors/Orbit-Core/issues/130); unknown and edited owner files remain protected. No modification to the already published v0.32 ZIP/tag.

## Acceptance matrix

| Gate | Evidence | Result |
| --- | --- | --- |
| Integrated scope/branch review | [draft PR #133](https://github.com/samjuniors/Orbit-Core/pull/133) integrates #131/#132 plus exact-stock installer fix without adding MCP tools; **57** remain | **SOURCE REVIEWED**, integration still draft |
| Exact-head GitHub CI | [run #1401](https://github.com/samjuniors/Orbit-Core/actions/runs/44289816258), Ubuntu Python 3.10–3.13 and Windows Python 3.12: 5/5 | **PASS** on `5eedd154` |
| Focused Windows tests | PR #133 evidence: 36 visual tests with 1 skipped; 31 Autopilot charter; 33 team-event; three installer regression; two old stock agent tests | **PASS** on documented revision; source-level, not host QA |
| Stock v0.31 → next-source upgrade | Frozen v0.31 source-agent SHA fixtures, backup-first upgrade, refuse customized/unknown bytes | **PASS** on disposable fixtures |
| Current release installation | Windows `orbit.cmd status`: v0.32.0; `orbit.cmd update --channel candidate --check`: no newer candidate; host MCP paths use Python 3.12 | **PASS for installed v0.32 only** |
| Codex real connected draft MCP | [PR #132 host checkpoint](https://github.com/samjuniors/Orbit-Core/pull/132#issuecomment-6975280844): actual `orbit_team_event`, `orbit_autopilot_charter`, typed preview/denial; synthetic handoff | **PARTIAL PASS**; not an authenticated native result receipt |
| Native specialist result, return and lead acceptance | Codex reports an inline native specialist result, but trusted child-session identity/delivery/independent lead acceptance not yet established | **NOT VERIFIED** end-to-end |
| Genuine host permission and denial | Caller-reported `HOLD_PERMISSION_DENIED` exercised; native Windows command reads blocked by host policy | **PARTIAL / BLOCKED**; never bypass policy |
| Antigravity real connection after installed v0.32 | Config present; headless probe found cached tool schema but timed out without actual tool-call result | **NOT VERIFIED** |
| Real product visual QA | Browser synthetic two-route fixture and source checks only; no signed-in IDE screenshot/state review for an actual product | **NOT VERIFIED** |
| Full independent Windows integration suite | Additional disposable Windows Python 3.12 source run initiated 2026-11-18; **not yet complete at initial record** | **IN PROGRESS / NOT VERIFIED** |
| v0.33 versioned candidate artifact | Source still says `VERSION=0.32.0`, `NEXT_VERSION=0.33.0`; no reviewed v0.33 ZIP/MCPB/checksum, versioned changelog entry or release tag | **NOT PREPARED** |
| Fresh-install, migration, uninstallation, rollback on final versioned ZIP | Current stock compatibility tests are not substitutes for final candidate artifact/rollback inspection | **NOT RUN** |
| Owner design/security review and release approval | Pending genuine host acceptance and reviewed published package | **PENDING** |

## Required release work, in order

1. Finish the real host gates: use approved and traceable Codex/Antigravity native file access, obtain actual child-session/permission outcome, audited specialist delivery, reported receipt and independent lead review. A host policy denial is not permission to retry with an unrestricted executor.
2. Run actual routed UI/screens/states/breakpoints in a suitable authorized IDE/browser; compare screenshots and keyboard/accessibility/reduced-motion behavior. A synthetic HTML fixture alone cannot certify real app visual quality.
3. Perform independent security/integrity review of review-digest replay, local SQLite migration/rollback, privacy/redaction and installer custom-file refusal. Verify exact-source Windows/Linux tests and permission-denial limits.
4. Only after those gates, prepare `release/v0.33.0-candidate` from the reviewed integrated source; update `VERSION`, `NEXT_VERSION`, `installer.py`, `source/runtime/orbit_mcp.py`, public `CHANGELOG.md` and package manifests together. Preserve previous releases.
5. Build unpublished versioned assets in isolation, verify four SHA-256 pairs, `scripts/check_release_readiness.py`, `check_version.py --strict-bundle`, `build_release.py --verify`, package smoke, disposable v0.31/v0.32 upgrade and rollback; require exact-head release-candidate Windows/Linux CI.
6. Present source diff, remaining limitations, release note and actual artifacts to the owner. Merge, tag, publish and install the **newly published** v0.33 release only upon explicit approval of that specific reviewed candidate. Do not interpret a generic request to finish development or install the already published release as approval to publish an unverified version.

## Evidence and continuity

- GitHub engineering truth: [PR #133](https://github.com/samjuniors/Orbit-Core/pull/133), [CI #1401](https://github.com/samjuniors/Orbit-Core/actions/runs/44289816258), [issue #130](https://github.com/samjuniors/Orbit-Core/issues/130).
- Long-term product decisions: [Orbit Core — Project Decisions & Releases](https://app.notion.com/p/4074f681d48881a7a407c3bdc2054409), [Research & References](https://app.notion.com/p/4074f681d488816e9fe7f4504982c948).
- Operational/host acceptance retained only under disposable `E:\Projects\Test\orbit-v033-*` local paths; do not upload private logs, agent tokens, SQLite files or user paths into public releases.
- Follow [the existing release policy](RELEASE-PROCESS.md). This is a **version-specific acceptance record**, not a competing release policy.
