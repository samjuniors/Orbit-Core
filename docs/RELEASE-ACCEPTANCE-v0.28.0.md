# Orbit Core v0.28.0 — Engineering and real-host prerelease acceptance

**Status: RELEASE HOLD — reviewed candidate only (2026-11-02).**
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
- Release review branch: `release/v0.28.0-candidate`; changes on this
  branch are not automatically merged, tagged or published.
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

## Preliminary code and CI

The v0.28 development branch's [exact-head CI run #41286619941](https://github.com/samjuniors/Orbit-Core/actions/runs/41286619941)
reported PASS. Candidate packaging, strict runtime-bundle parity,
disposable fresh install, v0.27.1-to-v0.28.0 upgrade and new **release
branch exact-head Windows/Linux CI** are separate gates to execute before
publication. Prior CI is not evidence that later documentation/release
candidate commits were tested.

## Release gate ledger

| Gate | Result | Evidence / next action |
| --- | --- | --- |
| Read-only adaptive delivery blueprint | PASS | `BLUEPRINT_READY`, `DRAFT_VALIDATED`, zero write scopes |
| Native Antigravity backend/frontend workers | OWNER-REPORTED PASS | Real session IDs and saved ledger; host consent independently unverified |
| Backend regression | PASS | Independent Windows 3.12 run, 10/10 |
| JavaScript syntax | PASS | Independent Node syntax check |
| External Chrome functional browser test | OWNER-REPORTED PASS | 9/9 in host report; independent rerun/record pending |
| Source-pinned Orbit integration/browser QA | HOLD | Missing project-scoped `build_runs` / `browser_results` |
| Acceptance fixture cross-origin security review | HOLD | Wildcard CORS; fix/negative tests required |
| Maturity/operations preview | PASS | New, existing API and stalled debug read-only previews |
| Checkpoint and task readback | PASS for local fixture | Confirmed persisted task status and hash |
| Real hostile host permission denial | NOT VERIFIED | Antigravity did not offer denial prompt in prior test |
| Source/package version and release CI | NOT RUN on this candidate | Prepare candidate bundle, audit notes, verify exact commit |
| Owner merge/publication and public assets | NOT RUN | No main merge/tag/release until required checks |

## Required next actions

Complete [Issue #74](https://github.com/samjuniors/Orbit-Core/issues/74)
inside a new reviewed disposable fixture revision, using real host tools
and unmodified historical evidence. Record source-linked browser QA via
the supported Orbit build/QA workflow; do not insert hand-crafted SQLite
PASS rows. Then run strict package parity and current Linux/Windows
CI, inspect exact release diff, merge only after the required review
and owner authorization, and publish via the standard immutable tag
workflow. Verify all published assets and matching checksums after
actual publication.

**No permission to publish v0.29 or v0.30 ahead of this acceptance.**
