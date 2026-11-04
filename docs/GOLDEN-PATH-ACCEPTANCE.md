# Orbit Core v0.29 — P0 full-stack golden-path acceptance

**Status:** **PARTIAL / BLOCKED** — real native Codex MCP intake/planning verified; native implementation and all downstream verification gates **NOT RUN**.

**Test date:** 2026-11-04 (Asia/Kolkata).  
**Engineering source:** `samjuniors/Orbit-Core`, candidate `5cc6d06d23fbc666674b95d7dfeb79936602a7be`, [v0.29 review PR #77](https://github.com/samjuniors/Orbit-Core/pull/77) (open, unmerged).  
**Host:** Windows `DESKTOP-5MBQ8IF`; `codex-cli 0.166.0`; Python 3.12 available. Antigravity CLI 1.4.12 was present but was **not used for this P0 tool sequence**.  
**Scope:** disposable `%TEMP%\Orbit-P0-GoldenPath-20261104\project`, project key `orbit-p0-fieldnotes`, build `fieldnotes-p0`. MCP server name **only** `orbit_p0_test`, pointing at the candidate runtime with independent `orbit-data/orbit-p0.sqlite3` and isolated setup home. Global installed `orbit-core-native` (historically v0.25.1), `orbit-m5-test`, other products, real user projects and production deployments were not used.

## P0 continuation — real native implementation, blocked browser gate (2026-11-04)

**Latest disposition: IMPLEMENT and VERIFY verified; managed BROWSER_QA BLOCKED by missing optional Python Playwright.** This supersedes the *earlier* no-app-source snapshot documented in the historical sections below; do not replace earlier failed/blocked observations. Native specialists and browser interaction results are host-reported with local source/evidence artifacts, whereas the 12-test execution was additionally **independently rerun** on the connected Windows fixture.

| Area | Updated evidence | Acceptance |
| --- | --- | --- |
| Backend/frontend implementation | Actual Python backend, SQLite, HTML/CSS/JS frontend and test sources now exist in the isolated `project/` fixture. Four host-native specialist references were recorded: `/root/orbit_backend`, `/root/orbit_frontend`, `/root/orbit_qa`, `/root/orbit_security`. The agent reports `collaboration.spawn_agent` calls; root test transcript is in the fixture, not committed raw. Existing backend and frontend Orbit tasks are `REVIEW_ACCEPTED` revision **5** each. | **PASS for implementation; specialist calls host-reported** |
| Verify | Agent reported 12 full Python standard-library tests PASS, final real GitHub Zen API probe `source=github`, static frontend check and independent QA/security specialist reviews. **Separately executed on the connected PC:** `python -B -m unittest discover -s tests -v` in the disposable project: **12 tests, exit 0**, covering auth/session/CSRF, user-scoped CRUD, malformed requests, migrations and mocked external behavior. No dependencies installed. | **PASS for the tested scope; live upstream result host-reported** |
| Preview | Orbit-owned local preview reached `READY` and loopback `/healthz` returned **HTTP 200**; agent reported server restart/persistence PASS. Preview processes were subsequently stopped. | **PASS (historical managed session)** |
| Browser interactions | Agent reported actual CUA in-app browser interactions on desktop/mobile: invalid and valid login, notes create/edit/delete, account isolation, visible XSS-shaped text rather than execution, keyboard/focus, responsive layout, login/logout, persistence. Screenshots `browser-desktop.jpg`, `browser-mobile.jpg` and `browser-mobile-logout.jpg` remain under the disposable fixture's `logs/`. The attempted delete-dialog confirmation specifically remains **NOT VERIFIED**. | **Supplemental host browser checks PASS, not Orbit-certified** |
| Formal Orbit `BROWSER_QA` | `orbit_browser_qa` returned **`DEPENDENCY_MISSING`** because Python `playwright` is not installed in Orbit's interpreter; third-party installation was explicitly prohibited. Independent read-only SQLite inspection confirmed `build_runs.stage=BROWSER_QA`, revision **7**, and **zero rows** in `browser_results`. Current `orbit_build_advance` requires an actual recorded interactive QA PASS bound to current source fingerprint, preview ID, preview generation and build revision. CUA reports alone cannot satisfy that trust boundary. | **BLOCKED** |
| REVIEW / CHECKPOINT | Independent implementation/security reviews are **host-reported PASS**, but formal downstream Orbit build `REVIEW` and `CHECKPOINT` stages **NOT RUN**. Orbit saved the blocked operational checkpoint, revision `6775e192b684e2dde6481ecf4f90d8a958f7a55c1bb04175af250afe883e6039`; independent read-only file inspection confirms `Gate: BLOCKED_BROWSER_DEPENDENCY` and `Last result: BLOCKED`. | **Formal review NOT RUN; blocked checkpoint PASS** |
| Restart recovery | Agent reports successful local application process restart/data persistence, **not** an actual Orbit MCP/IDE reconnect acceptance. | **MCP/host restart NOT VERIFIED** |

**Reproducible evidence:** the disposable workspace is `%TEMP%\Orbit-P0-GoldenPath-20261104`. Host-prepared `logs/resume-results.md`, `logs/resume-host-evidence.md`, `logs/resume-orbit-calls-final.json`, screenshots, source hash manifest, and independent `logs/independent-12-unittest-20261104.log` are preserved locally. The 40 resumed Orbit-call summaries were reconstructed from the actual host conversation after the first logging array proved empty; **do not treat them as independently parsed raw MCP telemetry**, unlike the earlier 28 Codex JSONL calls. No user project, global Orbit installation, published release, or production service was changed.

**Product decision needed before full P0 PASS:** Do **not** silently whitelist host-reported browser screenshots as a Playwright PASS or insert forged `browser_results`. Either obtain owner approval to use the already-tested Playwright route in a disposable interpreter (currently prohibited) **or** separately design and security-review a host-native browser evidence adapter. Any adapter must require independently validated interaction results, origin/network constraints, source fingerprint, build revision, approved preview generation, non-empty interactions, error reporting and scoped host permission; weaker evidence stays explicitly `HOST_REPORTED_NOT_ATTESTED`. No adapter is implemented or approved in this acceptance report. Final build REVIEW, CHECKPOINT and actual MCP restart recovery remain pending.

## What the golden path was meant to prove

Build a minimal but nontrivial local-only **Field Notes** web app using actual host-native specialists: secure local synthetic-account/password session authentication, CSRF protection, SQLite migrations and per-user notes CRUD, HTML/CSS/JS frontend, `/healthz`, a read-only public GitHub Zen API integration with timeout and mocked offline fallback. Zero installed third-party dependencies and no production credentials.

Required Orbit lifecycle: **intake → approved plan → implement → VERIFY → PREVIEW → BROWSER_QA → REVIEW → CHECKPOINT**. Later evidence should also include real HTTP/browser QA, CI, dependency/secret checks, database migration and rollback rehearsal, and an owner-run milestone script. **No app source was created during the run below.** These are acceptance requirements, not completed implementation.

## Actual gate results

| Gate | Observed outcome | Status |
| --- | --- | --- |
| Project scan | Real Codex call to `orbit_project_scan`: no docs, checkpoint `MISSING`. | **PASS** (fresh fixture detection) |
| Intake | Initially `NOT_STARTED`; after supplying all eight mandatory profile fields and two bounded questions, `orbit_intake_propose` returned `PROPOSED` revision 1 and `orbit_intake_approve` returned `APPROVED` revision 2 with exactly the owner-delegated synthetic defaults. | **PASS** for Orbit's records; consent remains **caller-reported**, not host-authenticated |
| Approved plan | `orbit_software_delivery_preview` returned `BLUEPRINT_READY`; `orbit_swarm_draft_preview` returned `DRAFT_VALIDATED` for four proposed work items. | **PASS** (read-only proposal, not execution) |
| Build registration | Initial `orbit_build_begin` returned `HOLD` before approval. After completed intake it returned `CREATED` at `RESEARCH` revision 1. | **PASS** for gating/state |
| Task registration | Backend `fieldnotes-backend` and frontend `fieldnotes-frontend` returned `PLANNED` revision 1; frontend depends on backend, with disjoint planned write scopes. | **PASS** for ledger planning, not assigned workers |
| Native specialist handoff | `orbit_task_handoff` returned `HOLD_RESERVE_TASK_FIRST`. `orbit_swarm_host_preflight` returned `HOLD_HOST_PREFLIGHT` with caller-reported workspace mode `read-only` and `host_workspace_writes_verified=false`. No reservation or native `spawn_agent` event was observed. | **BLOCKED** |
| IMPLEMENT | No source files created in the disposable project. No backend/frontend worker executed. | **NOT RUN / BLOCKED** |
| VERIFY | No app-specific tests, HTTP checks, security scan, or migration/CI verification ran. | **NOT RUN** |
| PREVIEW / BROWSER_QA | No application process, preview session, or browser QA ran. | **NOT RUN** |
| REVIEW / DONE | No task completion, independent review acceptance, or application DONE state recorded. | **NOT RUN** |
| CHECKPOINT (blocked outcome) | Later real Codex calls: first preview PREVIEW_ONLY, confirmed write STALE_REVISION for omitted initial revision; corrected expected_revision=MISSING returned SAVED. orbit_project_resume recovered identical checkpoint revision and gate BLOCKED_HOST_POLICY. | **PASS for recording BLOCKED, not app PASS** |

**Important permission distinction:** The MCP preflight HOLD follows the **caller-reported** `host_workspace_mode="read-only"`. This is not independent proof of the host OS/IDE's effective sandbox mode. Codex separately reported a policy block while attempting to read an Orbit skill during its first planning run. Neither condition authorizes circumventing host policy with an alternate server, Desktop Commander, direct scripts, a different host or blanket approval. No backend specialist was called. The host's claim that a native specialist tool was available is also **not proof of an actual invocation**.

## Measured real Codex MCP call frequency

Counted from completed `mcp_tool_call` events in **seven native Codex JSONL session logs: 28 total invocations**, all to `orbit_p0_test`. Of these, **26 returned completed tool events and 2 were rejected during argument validation**. The completed events include a preview and a stale-revision response; completion does not mean gate PASS. No native backend/frontend worker invocation was observed.

| Orbit tool | Calls | Evidence |
| --- | ---: | --- |
| `orbit_task_plan` | 6 | Four previews across sessions; two confirmed `PLANNED` records |
| `orbit_intake_propose` | 4 | Two invalid-input rejections, one `PREVIEW_ONLY`, one `PROPOSED` |
| `orbit_build_begin` | 3 | `HOLD`, `PREVIEW_ONLY`, `CREATED` |
| `orbit_intake_status` | 2 | `NOT_STARTED` in both early sessions |
| `orbit_intake_approve` | 2 | `PREVIEW_ONLY`, `APPROVED` |
| `orbit_project_scan` | 1 | Missing checkpoint/doc inventory |
| `orbit_software_delivery_preview` | 1 | `BLUEPRINT_READY` |
| `orbit_swarm_draft_preview` | 1 | `DRAFT_VALIDATED` |
| `orbit_task_list` | 1 | Backend `PLANNED`, revision 1 |
| `orbit_task_handoff` | 1 | `HOLD_RESERVE_TASK_FIRST` |
| `orbit_swarm_host_preflight` | 1 | `HOLD_HOST_PREFLIGHT` |
| `orbit_project_checkpoint` | 3 | `PREVIEW_ONLY`, `STALE_REVISION`, corrected `SAVED` |
| `orbit_project_resume` | 2 | Read-only resume; final readback confirms saved blocked checkpoint |
| **Total** | **28** | **26 completed tool events + 2 argument failures; 0 worker invocations** |

This partial dataset covers **intake, planning, preflight and a blocked checkpoint only**, **not** the entire golden path. It does **not** support a decision to merge, remove or deprecate any of Orbit's 47 tools. No call counts for later stages were observed. Host-reported free-form summaries were checked against native JSONL event records and the disposable SQLite state.

## Failures, manual actions and reproduction

1. **Invalid intake revision.** Initial `orbit_intake_propose` with an invalid new-project `expected_revision=0` returned `Invalid arguments.expected_revision: integer range`. **Reproduce:** call the new-project intake proposal with revision zero. **Recovery observed:** omitted the optional revision for a new project; preview then confirmed fixture-only write.
2. **Incomplete profile.** Second `orbit_intake_propose` returned `Profile requires type, complexity, maturity, goal, audience, constraints, stack, risk`. **Reproduce:** omit any mandatory profile key. **Recovery observed:** supplied exactly those eight keys with a valid type, complexity and maturity; the second Codex session completed proposal/approval.
3. **Premature build.** `orbit_build_begin` before approved intake returned `HOLD`, explaining the missing interview. **Reproduce:** begin a new-project build while intake is `NOT_STARTED`. **Recovery observed:** after caller-delegated defaults were recorded, build creation returned `CREATED`. This is **expected safety behavior**, not a defect.
4. **Unreserved backend task.** `orbit_task_handoff` returned `HOLD_RESERVE_TASK_FIRST` because the backend was `PLANNED`, not reserved. **Reproduce:** hand off a planned task without a successful `orbit_task_reserve`. **No workaround attempted.**
5. **Native-host write permission/liveness gap.** Preflight returned `HOLD_HOST_PREFLIGHT` when Codex supplied workspace mode `read-only`. No independent host permission or actual native worker session was observed. **Reproduce:** in the disposable fixture, call `orbit_swarm_host_preflight` with host `codex`, the planned backend revision and caller-declared read-only workspace mode. **Recovery NOT VERIFIED.** Requires the owner to open the disposable workspace in a genuinely authorized **workspace-write** host session, review the exact project-local MCP and native worker permissions, then rerun preflight with *observed*, not guessed, host capabilities. A denial must remain a denial; do not retry it via another server or tool.
6. **Native skill read blocked.** The first Codex planning session reported a denied terminal read of an Orbit skill; it did not retry that operation through another route. **No bypass or manual override was performed.**
7. **Corrected native host attempt blocked.** A later Codex session explicitly launched with CLI `--sandbox workspace-write` nevertheless reported that its *effective host instructions* were read-only and that a native workspace inspection was blocked by policy. That session made **zero MCP calls and zero successful native worker invocations**. The earlier preflight's caller-reported `read-only` value is not independent proof of this separate host-policy denial. No further alternate-tool attempt occurred.
8. **Checkpoint optimistic revision.** The first confirmed checkpoint omitted `expected_revision`, so Orbit returned `STALE_REVISION` with actual revision `MISSING`. A new authorized Codex call supplied the exact expected revision literal `MISSING` and received `SAVED`. Read-only resume returned checkpoint revision `3037b6c856b0874c3dd081c54a8ff9408af3ee3a8385505abf80fd821fd4c7b1`, gate `BLOCKED_HOST_POLICY`, last result `BLOCKED`. This is an operational blocked checkpoint, not completion of the golden path.

## Evidence and continuity

The Windows fixture stores its seven raw native Codex session traces (including any stderr transport diagnostics) in:

`%TEMP%\Orbit-P0-GoldenPath-20261104\logs\`

- `codex-readonly-mcp-probe.jsonl`
- `codex-phaseA-intake-plan.jsonl`
- `codex-phaseA2-valid-intake.jsonl`
- `codex-phaseB-backend-native.jsonl`
- `codex-phaseB2-backend-workspace.jsonl` (0 MCP calls; host-reported policy denial)
- `codex-p0-blocked-checkpoint.jsonl`
- `codex-p0-checkpoint-corrected.jsonl`

The isolation database is `%TEMP%\Orbit-P0-GoldenPath-20261104\orbit-data\orbit-p0.sqlite3`. A separate inspection saw the intake/build/task records; **no backend/frontend/tests application source** was present. After the corrected checkpoint call, the only new top-level project entry was `.orbit/` containing `STATE.md`. That checkpoint is scoped operational state; no app implementation files were created. Event logs are not committed to Git (they may contain session metadata). Historical counts and status claims here are not evidence of any unrecorded terminal, native agent, app or browser activity.

### Resume instructions / next authorized gate

Only after a real native coding host makes **scoped workspace-write and agent permissions available**: open the disposable fixture (not a user project), connect **only `orbit_p0_test`**, verify real permission and available native tools, retrieve fresh task revisions, reserve the backend task with caller-supplied owner approval reference and confirm it through MCP, invoke an actual backend specialist if available, record its returned session and app files, run independent backend tests, then proceed to frontend, integration, browser QA, security/review and **update the already-saved BLOCKED checkpoint** only after actual new evidence. Keep each file change under the approved task scopes and preserve raw results.

**Owner actions required before the next implementation gate:** interactive host consent for only the disposable workspace's write operations and relevant native specialist call, plus permission to use the existing isolated P0 MCP; no global Orbit upgrade or new dependencies. If a real host denies, stop and mark BLOCKED. **Do not claim golden-path PASS or stable-release acceptance until all remaining gates are actually executed.**

**P2 tool-consolidation note:** These 28 intake/planning/preflight/checkpoint calls are useful **partial frequency evidence**, but a complete call-frequency proposal needs a finished golden path and actual subsequent tool uses. No MCP tool was removed or added.

## Separate Antigravity read-only continuity probe — NOT VERIFIED

After the earlier Codex session series, a **separate, read-only Antigravity CLI** attempt was launched on the same disposable workspace. The request asked for `orbit_project_resume` and `orbit_task_list` from `orbit_p0_test` only, in plan/sandbox mode, with no write, agent spawn, global Orbit or permission bypass.

The Antigravity headless session produced **no tool response and no stdout/stderr diagnostics** while monitored. Its own test process was then terminated; it did not return a usable result. No MCP call, native specialist activity, or application file change can be attributed to this attempt. **Status: NOT VERIFIED**, not PASS, FAIL or a proven permission denial. The host's unrelated preexisting Antigravity background process was not terminated.

The empty disposable capture files are `logs/antigravity-readonly-continuity.json` and `logs/antigravity-readonly-continuity.stderr.log`; they add **zero** to the 28 verified Codex MCP call count above. Any further Antigravity real-host testing should use an owner-authorized interactive workspace and report the actual MCP response, not inferred tool availability.
