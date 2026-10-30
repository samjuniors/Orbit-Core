# v0.26.0 — release readiness and acceptance record

**Assessment:** 2026-10-30 · **Status:** **HOLD / NOT YET PUBLISHED**

This is a **version-specific acceptance record**, not a second roadmap or authority to publish. Product decisions remain in the [Orbit Core Notion hub](https://app.notion.com/p/4074f681d48881a7a407c3bdc2054409). Source code, CI, tags and releases are verified in GitHub. Preserve every previously published tag and asset.

## Completed with evidence

| Requirement | Result | Evidence |
| --- | --- | --- |
| Source version `0.26.0` merged into `main` | **PASS** | [PR #35](https://github.com/samjuniors/Orbit-Core-MCP/pull/35), merge SHA `b8696665e596c7034b92f677e3fe569b248f3acf` |
| Native task denial, session reconciliation, retry ledger | **MERGED; automated PASS only** | [PRs #27, #29, #32](https://github.com/samjuniors/Orbit-Core-MCP/pull/32) |
| Playwright preview-origin restrictions | **MERGED; automated PASS only** | [PR #33](https://github.com/samjuniors/Orbit-Core-MCP/pull/33) |
| M4 compact resume | **MERGED; automated PASS only** | [PR #34](https://github.com/samjuniors/Orbit-Core-MCP/pull/34) |
| M3 permission-denial fallback hardening | **MERGED; automated PASS only** | [PR #37](https://github.com/samjuniors/Orbit-Core-MCP/pull/37): denied consent cannot silently switch browser/computer-use providers |
| M4.2 adaptive workflow/context routing | **MERGED; automated PASS only** | [PR #38](https://github.com/samjuniors/Orbit-Core-MCP/pull/38): focused compact vs full context, high-risk review and unverified host-native/serial recommendations; real context/token benchmarks pending |
| M5 opt-in project practice review | **MERGED; automated PASS; Antigravity real-agent read-only PASS only** | [PR #40](https://github.com/samjuniors/Orbit-Core-MCP/pull/40), reviewed [M5 acceptance](M5-ENGINEERING-ACCEPTANCE.md): 42-tool expanded source, isolated SQLite decisions, read-only preview and revision history; confirmed-write, permissions and restart acceptance NOT VERIFIED |
| Exact reviewed M3/M4 heads | **5/5 PASS each** | [M3 #40893382550](https://github.com/samjuniors/Orbit-Core-MCP/actions/runs/40893382550), [M4 #40894592371](https://github.com/samjuniors/Orbit-Core-MCP/actions/runs/40894592371): Ubuntu Python 3.10–3.13, Windows 3.12; final main CI checked separately |
| Candidate package and installer test | **PASS in CI** | [Actions #40869882650](https://github.com/samjuniors/Orbit-Core-MCP/actions/runs/40869882650): source/MCPB parity, ZIP integrity, disposable fresh setup |
| Upgrade compatibility | **PASS in disposable CI** | v0.24.1 and v0.25.1 → v0.26.0, Windows/Linux; customized stock guidance safely blocks overwrite |
| Downloadable candidate | **CI ARTIFACT ONLY** | `orbit-v0.26.0-host-acceptance` in [Actions #40869882650](https://github.com/samjuniors/Orbit-Core-MCP/actions/runs/40869882650); not a signed publication |
| Current latest published release | **v0.25.1 prerelease** | [GitHub Releases](https://github.com/samjuniors/Orbit-Core-MCP/releases) |
| `v0.26.0` published tag / GitHub Release | **NOT DONE** | No matching published release found on 2026-10-29 |

## Scope correction (2026-10-30)

The owner approved M5 engineering integration after the original M3/M4 v0.26.0 source candidate. The **development** source now includes two additional opt-in practice review tools and additive SQLite tables. This supersedes the earlier 40-tool source inventory, not the publication HOLD. Reconfirm the complete 42-tool package manifest, migration/rollback, revised user-visible changelog, and all host/security gates before deciding whether v0.26.0 is the eventual published version. No tag or release is authorized.

## 2026-10-30 — Connected Windows acceptance execution (partial real-host PASS)

**Evidence boundary:** Connected authorized device `DESKTOP-5MBQ8IF` (Windows build 10.0.26300, Python 3.15.2). Inspected its active user-space Orbit v0.25.1 but **did not install or replace it**, modify personal IDE configuration or use owner projects. Reproduced reviewed `main` commit `0a25356ae53543bf17d59ec33cb8912403d23090` in a unique temporary checkout.

| Test | Verified outcome |
| --- | --- |
| Windows M5 focused suite | **PASS — 12/12** including preview without writes, isolation, SQLite persistence, revision conflict and transactional rollback |
| Full physical Windows Python 3.15.2 regression | **PASS — 262 tests, 10 skips** from direct logged rerun; an earlier piped display run exited 1 without a captured failure, so only the independent completed logged run is accepted |
| Development tool inventory | **PASS — 42** tools including `orbit_practice_suggest` and `orbit_practice_review`; the installed v0.25.1 does **not** yet have M5 |
| Strict desktop runtime/MCPB parity | **PASS** for disposable v0.26.0 bundle at reviewed merged commit |
| Built universal ZIP and installed MCP stdio smoke | **PASS — DISPOSABLE_INSTALL_AND_STDIO_SMOKE_PASS**, 42 tools; ZIP SHA256 `9f07a2a6775ea682d269f03a2728230972dc5aac31a026e5dbc19862f8a20950` |
| Disposable v0.25.1 → v0.26.0 stock upgrade | **PASS — DISPOSABLE_STOCK_UPGRADE_PASS**; stock/custom `AGENTS.md`, checkpoint, prior DB bytes and old runtime retained |
| Actual headless Windows browser QA | **PASS**, Playwright using locally installed Microsoft Edge, disposable Orbit-owned 127.0.0.1 preview, approved `expect_text` UI check |
| Browser denied-origin negative case | **PASS of safety expectation**: injected `fetch('https://example.com/blocked-by-orbit')` was blocked, recorded `blocked_remote_hosts=['example.com']`, and correctly returned browser QA **FAIL** for the attempted prohibited network access; preview stopped afterward |
| Actual Antigravity / Codex native approval, cancellation and restart | **NOT RUN** — Antigravity process was observed, Codex CLI 0.160.0 is present and configured, but no signed-in IDE permission UI was exercised |
| Installed-user SQLite migration/rollback, second computer, independent security/provenance | **NOT RUN**; a disposable stock upgrade is not proof of an installed user upgrade |

Local probe logs/test fixtures are in a distinct OS TEMP checkout; screenshots and preview logs use TEMP-only locations. The test launches isolated headless Edge, not the user's personal Chrome/Edge profile. The browser-origin test does **not** establish OS-level network sandboxing, authentic host approval or every multi-origin application case. A GitHub release and published version remain **HOLD**.

## Required before final release acceptance

Run on **disposable projects and explicitly authorized hosts only**. A host claim from an MCP payload is not independent permission or execution evidence.

### 1. Native host interaction — **NOT RUN / NOT VERIFIED for v0.26.0**
- [ ] Antigravity: connect Orbit and enumerate real tools; approve and deny disposable native-agent invocations using genuine permission UI. Verify correct task/status transitions, no unapproved fallback and actual session identity.
- [ ] Codex: repeat real host discovery, task start/deny/interruption and approved retry; compare session observations with task ledger and scope lock.
- [ ] Claude Code / Claude Desktop: test only exposed tools; verify MCP connect and capability HOLD when native delegation is unavailable.
- [ ] On each available host: stop a disposable worker using actual host controls, restart MCP, reconcile interrupted task without assuming it stopped; verify checkpoint/review history is preserved.

### 2. Browser safety — **NOT RUN / NOT VERIFIED**
- [ ] With approved Chrome/Edge/Chromium and compatible Playwright, verify a local app preview on its exact authorized port.
- [ ] Confirm cross-port and external HTTP/WebSocket requests are blocked and cannot certify BROWSER_QA PASS; confirm stale source and preview generations invalidate prior PASS.
- [ ] Test unsupported/old Playwright, tool denial, and optional native browser/computer-use fallback: no personal tabs, profile, credentials, cloud browser or external installer without separate authorization.
- [ ] Record limitation: browser routing is **not** an OS process/network sandbox.

### 3. Host installer, data continuity, rollback — **AUTOMATED PARTIAL PASS; LIVE NOT RUN**
- [ ] On a disposable Windows profile, test graphical installer preview/update/completion/clean uninstall, protecting custom owner files and configurations.
- [ ] Confirm real IDE reload and native MCP discovery; inspect an existing and a fresh project.
- [ ] Back up a disposable older SQLite database including WAL, verify additive attempts migration, checkpoint/memory integrity and safe recovery after interruption.
- [ ] Complete two-authorized-computer project transfer; imported approvals and sessions must be historical/untrusted, and no cross-PC attempt quota continuity may be assumed.
- [ ] Run real approved Linux/macOS host acceptance when suitable devices are available (Ubuntu CI does **not** substitute for it).

### 4. M5 practice review in a real host — **ANTIGRAVITY READ-ONLY + OWNER-REPORTED IDE RESTART READBACK PASS; DISPOSABLE WRITE / MCP RESTART PASS; HOST-UI CONSENT NOT VERIFIED**
- [x] **Antigravity real-agent discovery and read-only M5:** owner-provided actual agent-tool responses exposed `orbit_practice_suggest` and `orbit_practice_review`; suggest returned `REVIEW_CANDIDATES` with 1 synthetic candidate, `auto_promoted=false`; preview-only approval (`confirm_write=false`) returned `PREVIEW_ONLY`, `execution_permissions_granted=false`. Local registry inspection confirmed both M5 schema files; read-only DB query confirmed 2 synthetic fixture task records, **0 practices, 0 practice history**. This test used separate `orbit-m5-test` registry with reviewed v0.26.0 source and isolated SQLite; installed v0.25.1 preserved. **No permission dialog occurred and none was expected for non-writing operations.**
- [x] **Exactly one owner-authorized disposable `APPROVED` SQLite decision and fresh MCP restart readback:** after asserting original `orbit-m5-test` source and isolated DB, confirming no existing practice/history rows and preview status `PREVIEW_ONLY`, one `orbit_practice_review(action=approve,confirm_write=true)` call returned `APPROVED`, revision 1. Read-only SQLite found one practice and one `approve` history row; a **fresh MCP stdio subprocess** retrieved the same approved practice and `evidence_current=true`. Authorization came from owner in ChatGPT, not from the Antigravity IDE permission UI. Original installed v0.25.1, other projects and host settings unchanged.
- [x] **Antigravity real-agent readback following owner-reported IDE restart:** `orbit_practice_suggest` returned `NO_NEW_CANDIDATES`, empty candidates, one `APPROVED` `practice-6461df594a3e41da` revision 1 with `evidence_current=true` and both synthetic task references unchanged at revision 5; `auto_promoted=false`. An independent local read-only SQLite query confirmed **one** approved practice, **one** approval-history event, **two** original accepted fixture tasks and no extra writes. This corroborates recovery but does not independently attest restart timing or host UI permissions.
- [ ] Test **genuine Antigravity IDE approval/denial UI**, agent-mediated confirmed-write/rejection, stale-evidence behavior and prohibition on executing saved notes. Already-approved fixture should **not** be approved twice. Codex/Claude real-agent M5 remains unverified.
- [ ] Confirm additive practice/history tables preserve prior SQLite data and rollback/backup can recover from interrupted migrations. Ensure notes stay local, do not cross projects and do not become executable instructions.

### 5. Security and release verification — **NOT VERIFIED**
- [ ] Independently review authentic host user consent, workspace-root authorization, handling of caller-reported approvals/sessions, prompt injection and data privacy.
- [ ] Review release provenance: SHA256 sidecars are **integrity checks**, not proof of publisher identity or binary signing.
- [ ] Review installer compatibility, file backups, release manifest and rollback plan. Preserve existing `v0.25.1` assets.
- [ ] Owner explicitly approves final publication **after** reviewing remaining HOLD findings.

## Publication procedure (only after gates are satisfied)

Use [docs/RELEASE-PROCESS.md](RELEASE-PROCESS.md) and the GitHub `Publish versioned release` manual workflow on `main`, passing exact `version=0.26.0`. That workflow retests and builds a versioned ZIP, MCPB and SHA256 sidecars, and creates the immutable `v0.26.0` tag and prerelease. Afterwards verify the tag commit, release notes, asset names/downloads/checksums and updater behavior. **Do not trigger this workflow merely because CI and source merge passed.**

## Known blockers at this assessment

An authorized Windows device was connected and the disposable Edge browser test and Antigravity M5 read-only real-agent test were completed. Permission dialogs, agent cancellation/recovery, installed-profile migration/rollback, other host integrations, independent security and cross-device checks remain outstanding. Previous M1/M2 host acceptance for v0.25.1 does not establish M3/M4/M5 acceptance for the expanded v0.26.0 source. The [M3 engineering checklist](M3-ENGINEERING-ACCEPTANCE.md) contains detailed host-level cases; this document summarizes the **release-specific** go/no-go decision.

**Current decision: HOLD.** The v0.26.0 source is verified with automated checks; the full mission is not finished and its downloadable GitHub Release remains unpublished.
