# M3 engineering acceptance checklist — Orbit Core MCP

**Status:** IN PROGRESS · **Last engineering audit:** 2026-10-29 · **Source of truth:** GitHub code, commits, CI and real-host execution evidence.
This is a **test/review checklist**, not a release policy, replacement roadmap, or automatic approval.
Owner product intent and historical decisions live in the [Orbit Core Notion hub](https://app.notion.com/p/4074f681d48881a7a407c3bdc2054409).

## Change map and integration order

| Work | PR | Engineering state |
| --- | --- | --- |
| M3.1 source/preview-bound Playwright QA | [#25](https://github.com/samjuniors/Orbit-Core-MCP/pull/25) | MERGED to main; automated CI recorded |
| Host-first browser/computer-use selection | [#26](https://github.com/samjuniors/Orbit-Core-MCP/pull/26) | MERGED to main; provider execution remains host-owned |
| M3.2 pre-invocation permission denial | [#27](https://github.com/samjuniors/Orbit-Core-MCP/pull/27) | Draft review; not merged |
| M3.3 running-agent reconciliation | [#29](https://github.com/samjuniors/Orbit-Core-MCP/pull/29) | Draft, stacked on #27; not merged |
| M3 integrated attempts/denial/recovery | [#32](https://github.com/samjuniors/Orbit-Core-MCP/pull/32) | Draft, stacked on #29; not merged |
| Standalone attempt ledger | [#31](https://github.com/samjuniors/Orbit-Core-MCP/pull/31) | **Reference only** if #32 is accepted; do not merge duplicate implementation |
| Exact-preview-origin browser isolation | [#30](https://github.com/samjuniors/Orbit-Core-MCP/pull/30) | Independent draft; not merged |
| Historical roadmap reconciliation | [#24](https://github.com/samjuniors/Orbit-Core-MCP/pull/24) | Independent documentation PR; do not confuse with runtime acceptance |

**Proposed review order:** #27 → #29 → #32. After each owner-approved merge, check the next PR's actual merge base, conflicts, changed files and **new exact-head CI**, rather than relying on earlier green checks. Handle #30 and #24 separately. Never merge #31 as well as #32 without explicit reconciliation.

## A. Deterministic automated tests (repository)

**A1. Schema and preservation — NOT VERIFIED on a real user database.**
- [ ] Additive `orbit_task_attempts` table initializes on old database **without** replacing `orbit_agent_tasks`, memory, research, builds or checkpoints.
- [ ] Migration/readback in a disposable copy of pre-M3 SQLite: stable task keys, revisions, owner notes, accepted reviews, project-root isolation.
- [ ] Confirm legacy attempts use `LEGACY_UNVERIFIED`; never claim exact reconstructed historical counts.
- [ ] Portable imported records have **unknown historical attempt dates**. Their history may count conservatively toward step limits but must **not** be falsely charged as a fresh destination-host attempt for today's daily quota.

**A2. Host report/permission state — automated tests included; independent live-host confirmation NOT RUN.**
- [ ] Denied, unavailable and failed **pre-invocation** native calls mark an unstarted task `BLOCKED`, not user `CANCELLED`; prior rejected approval reference cannot be reused.
- [ ] A normal user-initiated cancellation of an **unstarted** task remains `CANCELLED`.
- [ ] Unknown, RUNNING, mismatched or missing host session/terminal status yields `HOLD_HOST_RECONCILIATION` and retains the task revision, host session and write-scope lock.
- [ ] A matching *host-reported* terminal session records a terminal task/attempt result, retaining notes, old session and checkpoint; do not claim independent session authentication.
- [ ] Repeated retries of one task consume distinct step/day attempts; maximum two simultaneous active slots; concurrent stale revisions cannot acquire reservations.
- [ ] A released, genuinely **unstarted** slot refunds the attempt budget without deleting its history. A started attempt is never refunded simply because the task later FAILED, BLOCKED or was cancelled.
- [ ] SQLite fault injection verifies failed reserve/start/report writes leave attempt and task records transactionally consistent. SQLite restart does not reset attempts.
- [ ] No new host execution, hidden CLI, broad filesystem permissions or extra MCP tools.

**A3. CI evidence — check at the integration PR's CURRENT head SHA.**
- [ ] `python -m compileall -q source installer.py orbit_setup.py scripts tests`
- [ ] `python -m unittest discover -s tests -v`
- [ ] `python scripts/check_version.py` and `python scripts/check_version.py --strict-bundle`
- [ ] Release-candidate ZIP parity, disposable install and previous v0.24.1 upgrade smoke tests (as configured in [CI workflow](../.github/workflows/ci.yml)).
- [ ] GitHub Actions matrix PASS: Ubuntu Python 3.10, 3.11, 3.12, 3.13; Windows Python 3.12.
- [ ] Inspect failures and exact source/head SHA. Green CI is **not** live IDE acceptance, independently authenticated user consent, release authorization or production readiness.

## B. Later real-host acceptance (OWNER DEFERRED; NOT RUN for M3)

**B1. Antigravity and Codex separately; Claude Code only with an actually exposed native agent API.**
- [ ] Confirm the actual native subagent invocation tool, its schema and scope from the host; do not assume an agent exists from config files or MCP-reported tool names.
- [ ] Approve a harmless disposable scoped task in the genuine host UI. Verify its exact returned session reference before `orbit_task_started`.
- [ ] Deny a separate harmless invocation. Verify denial causes `BLOCKED`, preserves history, does not start a worker, and **does not** silently retry through a different provider.
- [ ] With permission, start a disposable native worker, inspect the real host session, force an interruption, restart Orbit's MCP, then confirm `RUNNING` remains unresolved until the host reports a terminal observation.
- [ ] Cancel via native host controls, verify the exact worker stopped, report the matching terminal state, inspect the actual Git diff/test evidence and preserve original checkpoint/owner files.
- [ ] Verify approved retry uses fresh genuine host/user approval, a new session, the same task identity and correct attempt budget.
- [ ] Record product/host versions, project key, local machine, session IDs **only where safe**, Git SHA, sanitized logs, observed results and owner verdict. Do not persist secrets, private tabs or unreviewed full transcripts.

**B2. Browser QA and computer-use boundary (NOT RUN live).**
- [ ] Test one disposable Orbit-managed preview with approved local Chrome/Edge/Chromium + Playwright.
- [ ] Verify QA rejects a code edit after PASS and a replaced preview generation.
- [ ] For [#30](https://github.com/samjuniors/Orbit-Core-MCP/pull/30), verify exact authorized preview-port HTTP/WS and blocked different local ports/remote origins; no banned network attempts may certify QA PASS.
- [ ] Host browser, computer-use, Browser Use and Vercel agent-browser tools are **supplemental evidence only** until a separately reviewed, source-bound native evidence adapter exists. Confirm real tool/user permission. Never inspect personal Chrome profiles, credentials or unrelated desktop apps without separate explicit consent.
- [ ] A multi-server app needing a different local origin must request a reviewed scoped policy, not silently broaden the allowlist.

**B3. Portability and rollback (NOT RUN across two computers).**
- [ ] On disposable PC A, export project-scoped tasks/research; inspect the bundle, transfer outside Git, import with preview/revision guard on PC B into an authorized project root.
- [ ] Ensure imported sessions/approvals are historical/untrusted, active work is BLOCKED, checkpoint and unrelated data remain untouched, and no phantom successful native-agent execution is inferred.
- [ ] Attempt-budget history is **not** included in portable format v1; do not claim cross-PC quota continuity. Fresh destination budget must not falsely date historical attempts as current local work.
- [ ] Back up a disposable prior-version database before the new additive schema, validate upgrade/readback and a safe recovery approach. Do not overwrite or downgrade real owner data to run acceptance tests.

## C. Security and release gates

- [ ] Resolve or explicitly retain [Issue #9](https://github.com/samjuniors/Orbit-Core-MCP/issues/9): authentic host permissions, untrusted approval/session/evidence values, provenance/signing, customized installers and rollback.
- [ ] Confirm privacy/data boundaries for research pointers, SQLite records and any browser/cloud providers.
- [ ] Independent code review; compare stacked branch diffs with `main`, inspect CI for final merge candidates and agree on compatibility/rollback.
- [ ] **Owner approval is required** before each merge, installation, deployment or new release. Publishing prerelease v0.25.1 did not certify M3.

## Evidence record template

For each gate record: **case**, **host/platform**, **branch/SHA**, **environment**, **steps actually executed**, **observed output (sanitized)**, **PASS / FAIL / BLOCKED / NOT RUN / NOT VERIFIED**, **reviewer**, and a specific GitHub Actions/PR/Notion reference. A test that merely reports a host action cannot be marked independently verified.

**Current top-level decision:** Engineering work can continue with CI/regression tests. **Real-host acceptance, cross-PC verification, merging and release remain deferred unless the owner authorizes those actions separately.**
