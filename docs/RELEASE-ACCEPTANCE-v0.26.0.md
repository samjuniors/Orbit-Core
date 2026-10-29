# v0.26.0 — release readiness and acceptance record

**Assessment:** 2026-10-29 · **Status:** **HOLD / NOT YET PUBLISHED**

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
| Exact reviewed M3/M4 heads | **5/5 PASS each** | [M3 #40893382550](https://github.com/samjuniors/Orbit-Core-MCP/actions/runs/40893382550), [M4 #40894592371](https://github.com/samjuniors/Orbit-Core-MCP/actions/runs/40894592371): Ubuntu Python 3.10–3.13, Windows 3.12; final main CI checked separately |
| Candidate package and installer test | **PASS in CI** | [Actions #40869882650](https://github.com/samjuniors/Orbit-Core-MCP/actions/runs/40869882650): source/MCPB parity, ZIP integrity, disposable fresh setup |
| Upgrade compatibility | **PASS in disposable CI** | v0.24.1 and v0.25.1 → v0.26.0, Windows/Linux; customized stock guidance safely blocks overwrite |
| Downloadable candidate | **CI ARTIFACT ONLY** | `orbit-v0.26.0-host-acceptance` in [Actions #40869882650](https://github.com/samjuniors/Orbit-Core-MCP/actions/runs/40869882650); not a signed publication |
| Current latest published release | **v0.25.1 prerelease** | [GitHub Releases](https://github.com/samjuniors/Orbit-Core-MCP/releases) |
| `v0.26.0` published tag / GitHub Release | **NOT DONE** | No matching published release found on 2026-10-29 |

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

### 4. Security and release verification — **NOT VERIFIED**
- [ ] Independently review authentic host user consent, workspace-root authorization, handling of caller-reported approvals/sessions, prompt injection and data privacy.
- [ ] Review release provenance: SHA256 sidecars are **integrity checks**, not proof of publisher identity or binary signing.
- [ ] Review installer compatibility, file backups, release manifest and rollback plan. Preserve existing `v0.25.1` assets.
- [ ] Owner explicitly approves final publication **after** reviewing remaining HOLD findings.

## Publication procedure (only after gates are satisfied)

Use [docs/RELEASE-PROCESS.md](RELEASE-PROCESS.md) and the GitHub `Publish versioned release` manual workflow on `main`, passing exact `version=0.26.0`. That workflow retests and builds a versioned ZIP, MCPB and SHA256 sidecars, and creates the immutable `v0.26.0` tag and prerelease. Afterwards verify the tag commit, release notes, asset names/downloads/checksums and updater behavior. **Do not trigger this workflow merely because CI and source merge passed.**

## Known blockers at this assessment

No connected computer was available through the authorized remote-device connector to perform the necessary live IDE/browser tests, and no fresh real-host v0.26.0 acceptance reports were provided. Previous M1/M2 host acceptance for v0.25.1 does not establish M3/M4 acceptance for v0.26.0. The [M3 engineering checklist](M3-ENGINEERING-ACCEPTANCE.md) contains detailed host-level cases; this document summarizes the **release-specific** go/no-go decision.

**Current decision: HOLD.** The v0.26.0 source is verified with automated checks; the full mission is not finished and its downloadable GitHub Release remains unpublished.
