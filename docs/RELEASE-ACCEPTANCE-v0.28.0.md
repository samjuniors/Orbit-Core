# Orbit Core v0.28.0 — Engineering and real-host prerelease acceptance

**Status: PUBLISHED PRERELEASE — 2026-11-03.** The historical release-candidate HOLD observations below were accurate before publication; the final approved release evidence and limits are recorded at the end of this document. **Publication is not production certification.**
This record is the version-specific technical acceptance report required by
[RELEASE-PROCESS.md](RELEASE-PROCESS.md). Research/product decisions and
release sequencing are tracked in the existing
[Orbit Core Notion hub](https://app.notion.com/p/4074f681d48881a7a407c3bdc2054409).
GitHub is authoritative for implementation, CI, tags and publication.

## Exact scope

- Product: **Orbit Core**; do not confuse it with Helm, Aro, SamjuniorsOS or the
  unrelated ORBIT personal-planning plugin.
- Published starting point: [v0.27.1 prerelease](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.27.1).
- Reviewed development: [draft PR #68](https://github.com/samjuniors/Orbit-Core/pull/68),
  exact head `f9c4423effe2314b6548cf2b48dc12eeca39dbb0`.
- Release review branch: `release/v0.28.0-candidate` was approved and merged as [PR #75](https://github.com/samjuniors/Orbit-Core/pull/75). GitHub's [v0.28.0 prerelease](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.28.0) is published from the immutable tag; it was never a separate automatic installation.
- Implemented user-visible feature: read-only
  `orbit_software_delivery_preview`; 47-tool candidate runtime. Reuses
  native specialists/task ledger; does not autonomously execute a model.

## Windows acceptance evidence

**Owner-provided Antigravity host report:** disposable project
`agy-v028-todo-release-acceptance`, project-local MCP `orbit_v028_qa`.
The report documents 12 proposed tasks in 11 dependency waves, and
genuine native sessions for backend `9301fbac-5b77-4159-8f13-049c4c7c962e`
and frontend `026aae3d-8a66-4e98-922b-a165f739df58`, plus separate
read-only reviewer sessions and accepted task revisions 5/5. It reports
10/10 Python backend tests, 9/9 Chrome 156/Playwright interactions,
JS syntax, a source fingerprint, and a saved checkpoint. These are
**owner/host-reported observations**, not cryptographic host attestations.

**Independent read-only host audit by release reviewer:** on authorized
Windows PC, the exact fixture was inspected and the existing SQLite
was queried via `mode=ro` with `PRAGMA query_only=ON`.
- Backend `python -B backend/test_server.py -v` exit 0:
  **10/10 PASS**.
- `node --check frontend/app.js` exit 0: **PASS**.
- Checkpoint SHA-256: `2e12a21fd7ccd71d9591299c3b2827d8bab0f1b0966735e8707384060f0f7371`.
- Both task rows were `REVIEW_ACCEPTED` revision 5, with reported native
  session IDs and disjoint `backend/` and `frontend/` scopes.
- **No matching `build_runs` or `browser_results` in the candidate
  v0.28 SQLite.** Accordingly `orbit_swarm_integration_review` returned
  `HOLD_INDEPENDENT_QA`; this is a correct HOLD, not a release GO.
- The representative TODO backend uses `Access-Control-Allow-Origin: *`
  and permissive `OPTIONS` for an otherwise loopback-only API; explicit
  origin boundary and refreshed browser/security regression evidence
  are required for its stated **secure localhost API** objective.
  This is a **test fixture concern, not proven Orbit runtime vulnerability**.
- The external Chrome 9/9 test suite reported by Antigravity is not
  identical to a source-bound, recorded Orbit browser QA result. Static
  claims of WCAG AAA do not amount to independently certified conformance.

See [Issue #74](https://github.com/samjuniors/Orbit-Core/issues/74)
for the exact non-destructive remediation and acceptance steps.

## 2026-11-03 — Second-PC source-linked browser QA (verified)

**Separate real-host fixture:** On Windows `DESKTOP-AND1FUJ`, the
project-local v0.28 MCP `orbit_v028_secondpc` used a new isolated
`Orbit-v028-HostQA-20261103/todo-lab` project and SQLite. Antigravity
reported native backend and frontend sessions, each with separately
recorded read-only reviewers and `REVIEW_ACCEPTED` task revisions 5.
This **does not retroactively change the first-PC HOLD record above**.

**Independent execution and verification on second PC:**
- Python 3.12 backend `backend/test_app.py`: **37/37 PASS**, including
  trusted/untrusted Origin, path and other security negative regressions;
  `node --check frontend/app.js`: exit 0.
- Owner approved installation of `playwright==1.64.1` only inside the
  disposable workspace's Python 3.12 `.venv`; the project-local
  `.agents/mcp_config.json` was backed up before repointing its interpreter.
  No browser downloads, global Python/IDE changes or source edits.
- The **actual** v0.28 MCP JSON-RPC `orbit_preview_start` tool started
  a 127.0.0.1:8085 TODO server; `orbit_browser_qa` launched installed
  Edge, executed **9/9 approved mobile browser actions PASS** (input error,
  add and render, active filtering) with no console errors, failed steps
  or blocked remote-origin requests, and captured a private screenshot.
- Source fingerprint:
  `d6e8736e91f39ac2914dccb756d094118fe474f0a318f9952b6d667f12da060d`.
  Independent `mode=ro` SQLite verification confirmed exactly one
  source-linked `browser_results` PASS row on build QA revision 6,
  nine passing actions, the real screenshot file, and both unchanged
  `REVIEW_ACCEPTED` task rows.
- `orbit_swarm_integration_review` returned
  **`READY_FOR_INDEPENDENT_REVIEW`**, with source and stored QA matching.
  `orbit_build_advance` moved the build into **REVIEW revision 7**.
  Clean preview stop and fresh MCP restart recovered this state without
  lost tasks or running-worker reconciliation.
- The managed checkpoint was revision-guarded and updated to
  `INDEPENDENT_RELEASE_REVIEW_PENDING`, checkpoint SHA-256
  `e0f68d83f75e154496b2b66194e47592355c229431fa52a29d9d786168f2e1fe`.
  SQLite was backed up in the disposable fixture before QA.
- The sample origin-policy issue from the first PC was addressed in the
  **new second-PC fixture**, with test coverage; it was not merged into
  Orbit's own MCP source or used to rewrite historical evidence.

See [Issue #74](https://github.com/samjuniors/Orbit-Core/issues/74)
for the detailed real-tool evidence. The source-bound QA gate is cleared,
but `READY_FOR_INDEPENDENT_REVIEW` is **not** an owner release approval
or proof that security and host permissions were independently certified.

## Preliminary code and CI

The reviewed v0.28 development head [CI #41286619941](https://github.com/samjuniors/Orbit-Core/actions/runs/41286619941)
PASS remains historical. On the connected **second Windows PC**, the
v0.28 release candidate passed **420 Python tests (23 skipped)**, release
readiness, strict source/desktop bundle parity, deterministic three-package
ZIP builds and the extracted 47-tool MCP stdio smoke. The actual
**v0.27.1 → v0.28.0** disposable upgrade initially exposed a missing
previous-version allowlist entry; that was corrected, and the full
upgrade rehearsal passed while preserving custom guidance, prior runtime,
checkpoint and database bytes. Exact then-current source head
`85523f67be20b408b553cf3862ceb81a26b0825d` passed
[five-job Windows/Linux CI #41573407348](https://github.com/samjuniors/Orbit-Core/actions/runs/41573407348).
Documentation updates after that exact commit must receive their own
exact-head CI before release; no passing head is inferred in advance.

## Release gate ledger

| Gate | Result | Evidence / next action |
| --- | --- | --- |
| Read-only adaptive delivery blueprint | PASS | `BLUEPRINT_READY`, `DRAFT_VALIDATED`, zero write scopes |
| Native Antigravity backend/frontend workers | OWNER-REPORTED PASS | Real session IDs and saved ledger; host consent independently unverified |
| Backend regression | PASS | Original PC 10/10 and separate second PC 37/37 including origin negatives |
| JavaScript syntax | PASS | Independent Node syntax check |
| External Chrome functional browser test | OWNER-REPORTED PASS | Separate CDP browser acceptance reported on both PCs; source-linked Edge result below is independently verified |
| Source-pinned Orbit integration/browser QA | PASS — readiness only | Actual second-PC Playwright Edge 9/9, source-bound SQLite PASS row; `READY_FOR_INDEPENDENT_REVIEW` |
| Acceptance fixture cross-origin security review | PASS on new fixture | Strict loopback-origin policy and 37 HTTP regressions; old first-PC issue remains historical |
| Maturity/operations preview | PASS | New, existing API and stalled debug read-only previews |
| Checkpoint and task readback | PASS | Cold MCP resume at REVIEW rev 7; both reviewed tasks rev 5 and checkpoint updated under revision guard |
| Real hostile host permission denial | NOT VERIFIED | Antigravity did not offer denial prompt in prior test |
| Source/package version and release CI | PASS at verified source head; newest docs pending | 420 tests, candidate builds/smoke, v0.27.1 upgrade, 5/5 exact-head CI at `85523f6`; rerun CI after documentation updates |
| Owner merge/publication and public assets | **PUBLISHED, public checksums VERIFIED** | Main merge `07067f10`, release workflow #41581180695 PASS, public 8 assets; 4/4 package checksum pairs independently PASS |

## Historical prepublication required next actions (completed for v0.28 prerelease)

The source-linked browser-QA and second-PC fixture security subgates
in [Issue #74](https://github.com/samjuniors/Orbit-Core/issues/74)
are now completed with real evidence. **Next:** independently inspect
the actual release candidate diff, documented test/security boundaries,
Codex-versus-Antigravity coverage and outstanding release limitations.
Require latest exact-head Linux/Windows CI after these documentation
revisions, an explicit owner release decision, a reviewed merge to
`main`, new main CI, and the normal immutable version tag workflow.
After publication, download and verify all assets/checksums. Do not
replace the older acceptance or published release evidence.

**v0.29 and v0.30 remain separate unreleased development tracks; v0.28 publication does not automatically authorize those releases.**

## Final publication verification — 2026-11-03

- **Owner publication approval:** explicitly requested `v0.28.0` release after documented Antigravity second-PC acceptance and source-linked browser QA. This permits a truthful **0.x prerelease** with known limitations; it does not certify production hosts or authorise publishing the next versions.
- **Reviewed merge:** [PR #75](https://github.com/samjuniors/Orbit-Core/pull/75) merged into `main`, commit `07067f10cb5a345be0959f1a2f9a2410eb3b0f48`; `VERSION=0.28.0` and `NEXT_VERSION=0.29.0`.
- **Exact tested merge:** [main CI #41580966442](https://github.com/samjuniors/Orbit-Core/actions/runs/41580966442) **PASS, 5/5 jobs**, Ubuntu Python 3.10–3.13 and Windows Python 3.12, including previous official upgrade checks. Independent Windows 3.12 release-bundle parity/ZIP build/extracted 47-tool MCP smoke also PASS from the merge commit.
- **Immutable tag:** annotated `v0.28.0` object `b5a43a3e179d50889ca9cb3e2996d408e6335eb2` peels to that exact merge commit; no prior tag was moved or replaced.
- **Official workflow:** [Publish versioned release #41581180695](https://github.com/samjuniors/Orbit-Core/actions/runs/41581180695) **PASS**, including independent build checks, source parity and automatic changelog release notes.
- **Public artifact verification:** [v0.28.0 GitHub prerelease](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.28.0) published **2026-11-03 04:59:10 UTC**, `draft=false`, `prerelease=true`. Eight public assets (four packages and four SHA-256 sidecars) downloaded to a fresh authorized disposable Windows TEMP folder; **all four public package/sidecar SHA-256 comparisons PASS**.

| Public package | SHA-256 independently verified |
| --- | --- |
| `ORBIT-Universal-Setup-v0.28.0.zip` | `37f5d98337355c52409eac774d757d93098898f3ffb305278871541487bf05e8` |
| `Orbit-Antigravity-Plugin-v0.28.0.zip` | `3437f68edc470ba71998a0c9c227fb9eba5791215e067f6c850aeb7104974e45` |
| `Orbit-Core-Plugin-Suite-v0.28.0.zip` | `9855bc933b8a6e083d3aa6419852d05ee836994707b5e8bafa5ff55491fbcc1d` |
| `ORBIT-Claude-Desktop-v0.28.0.mcpb` | `bdb6ace7aa8d86f5758f8249c46af801f78e0df1250bb647990a1fe87e7bf59a` |

**Remaining limitations:** the new read-only software-delivery preview does not independently execute coding models or grant host permissions. Real permission-denial behavior, full Codex software delivery, installed-user migration/rollback and independent publisher signing/security certification are not fully verified. Public checksum integrity does **not** prove publisher identity. No real installed user Orbit or project data was modified by the publication verification. The previous tagged release v0.27.1 and other historical assets remain intact.
