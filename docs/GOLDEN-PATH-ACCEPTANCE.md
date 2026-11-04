# Orbit Core v0.29 — P0 full-stack golden-path acceptance

**Status:** **PARTIAL / BLOCKED** — real native Codex MCP intake/planning verified; native implementation and all downstream verification gates **NOT RUN**.

**Test date:** 2026-11-04 (Asia/Kolkata).  
**Engineering source:** `samjuniors/Orbit-Core`, candidate `5cc6d06d23fbc666674b95d7dfeb79936602a7be`, [v0.29 review PR #77](https://github.com/samjuniors/Orbit-Core/pull/77) (open, unmerged).  
**Host:** Windows `DESKTOP-5MBQ8IF`; `codex-cli 0.166.0`; Python 3.12 available. Antigravity CLI 1.4.12 was present but was **not used for this P0 tool sequence**.  
**Scope:** disposable `%TEMP%\Orbit-P0-GoldenPath-20261104\project`, project key `orbit-p0-fieldnotes`, build `fieldnotes-p0`. MCP server name **only** `orbit_p0_test`, pointing at the candidate runtime with independent `orbit-data/orbit-p0.sqlite3` and isolated setup home. Global installed `orbit-core-native` (historically v0.25.1), `orbit-m5-test`, other products, real user projects and production deployments were not used.

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
| REVIEW / CHECKPOINT / DONE | No task completion/review acceptance or Orbit checkpoint recorded. | **NOT RUN** |

**Important permission distinction:** The MCP preflight HOLD follows the **caller-reported** `host_workspace_mode="read-only"`. This is not independent proof of the host OS/IDE's effective sandbox mode. Codex separately reported a policy block while attempting to read an Orbit skill during its first planning run. Neither condition authorizes circumventing host policy with an alternate server, Desktop Commander, direct scripts, a different host or blanket approval. No backend specialist was called. The host's claim that a native specialist tool was available is also **not proof of an actual invocation**.

## Measured real Codex MCP call frequency

Counted from completed `mcp_tool_call` events in four native Codex JSONL session logs; **23 total invocations**, all to `orbit_p0_test`. Of these, **21 returned completed tool events and 2 were rejected during argument validation**. No other native tool invocation was observed in these four logs.

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
| **Total** | **23** | **21 completed + 2 argument failures** |

This partial dataset covers **intake and planning only**, **not** the entire golden path. It does **not** support a decision to merge, remove or deprecate any of Orbit's 47 tools. No call counts for later stages were observed. Host-reported free-form summaries were checked against native JSONL event records and the disposable SQLite state.

## Failures, manual actions and reproduction

1. **Invalid intake revision.** Initial `orbit_intake_propose` with an invalid new-project `expected_revision=0` returned `Invalid arguments.expected_revision: integer range`. **Reproduce:** call the new-project intake proposal with revision zero. **Recovery observed:** omitted the optional revision for a new project; preview then confirmed fixture-only write.
2. **Incomplete profile.** Second `orbit_intake_propose` returned `Profile requires type, complexity, maturity, goal, audience, constraints, stack, risk`. **Reproduce:** omit any mandatory profile key. **Recovery observed:** supplied exactly those eight keys with a valid type, complexity and maturity; the second Codex session completed proposal/approval.
3. **Premature build.** `orbit_build_begin` before approved intake returned `HOLD`, explaining the missing interview. **Reproduce:** begin a new-project build while intake is `NOT_STARTED`. **Recovery observed:** after caller-delegated defaults were recorded, build creation returned `CREATED`. This is **expected safety behavior**, not a defect.
4. **Unreserved backend task.** `orbit_task_handoff` returned `HOLD_RESERVE_TASK_FIRST` because the backend was `PLANNED`, not reserved. **Reproduce:** hand off a planned task without a successful `orbit_task_reserve`. **No workaround attempted.**
5. **Native-host write permission/liveness gap.** Preflight returned `HOLD_HOST_PREFLIGHT` when Codex supplied workspace mode `read-only`. No independent host permission or actual native worker session was observed. **Reproduce:** in the disposable fixture, call `orbit_swarm_host_preflight` with host `codex`, the planned backend revision and caller-declared read-only workspace mode. **Recovery NOT VERIFIED.** Requires the owner to open the disposable workspace in a genuinely authorized **workspace-write** host session, review the exact project-local MCP and native worker permissions, then rerun preflight with *observed*, not guessed, host capabilities. A denial must remain a denial; do not retry it via another server or tool.
6. **Native skill read blocked.** The first Codex planning session reported a denied terminal read of an Orbit skill; it did not retry that operation through another route. **No bypass or manual override was performed.**

## Evidence and continuity

The Windows fixture stores its four raw session traces (including any stderr transport diagnostics) in:

`%TEMP%\Orbit-P0-GoldenPath-20261104\logs\`

- `codex-readonly-mcp-probe.jsonl`
- `codex-phaseA-intake-plan.jsonl`
- `codex-phaseA2-valid-intake.jsonl`
- `codex-phaseB-backend-native.jsonl`

The isolation database is `%TEMP%\Orbit-P0-GoldenPath-20261104\orbit-data\orbit-p0.sqlite3`. A separate inspection saw **one intake record and one build record**; the project source directory had **zero files**. Event logs are not committed to Git (they may contain session metadata). Historical counts and status claims here are not evidence of any unrecorded terminal, native agent, app or browser activity.

### Resume instructions / next authorized gate

Only after a real native coding host makes **scoped workspace-write and agent permissions available**: open the disposable fixture (not a user project), connect **only `orbit_p0_test`**, verify real permission and available native tools, retrieve fresh task revisions, reserve the backend task with caller-supplied owner approval reference and confirm it through MCP, invoke an actual backend specialist if available, record its returned session and app files, run independent backend tests, then proceed to frontend, integration, browser QA, security/review and an Orbit checkpoint. Keep each file change under the approved task scopes and preserve raw results.

**Owner actions required before the next implementation gate:** interactive host consent for only the disposable workspace's write operations and relevant native specialist call, plus permission to use the existing isolated P0 MCP; no global Orbit upgrade or new dependencies. If a real host denies, stop and mark BLOCKED. **Do not claim golden-path PASS or stable-release acceptance until all remaining gates are actually executed.**

**P2 tool-consolidation note:** These 23 planning-stage calls are useful **partial frequency evidence**, but a complete call-frequency proposal needs a finished golden path and actual subsequent tool uses. No MCP tool was removed or added.
