# Orbit Core — cross-agent continuity and handoff

**Last reviewed:** 2026-11-23 22:31 Asia/Kolkata.
**Canonical repository:** https://github.com/samjuniors/Orbit-Core. Revalidate live state before every resume.
**Scope:** provider-neutral Orbit Core only. Orbit Commander remains separately paused and out of scope.
**Current baseline:** main VERSION=0.33.1 / NEXT_VERSION=0.34.0; v0.33.0 prerelease published; v0.33.1 and v0.34.0 are not published.

## 2026-11-23 — Evening live revalidation

### Main, release and CI
- Canonical main HEAD: [2fdf4f329774b9644e75ac0df4d89738a7cd625f](https://github.com/samjuniors/Orbit-Core/commit/2fdf4f329774b9644e75ac0df4d89738a7cd625f). Main reports VERSION=0.33.1 and NEXT_VERSION=0.34.0.
- Latest published release is [v0.33.0 prerelease](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.33.0), published 2026-11-23 08:20:55 UTC by owner-triggered workflow_dispatch [run #45137788352](https://github.com/samjuniors/Orbit-Core/actions/runs/45137788352). Its annotated tag points to commit [0100e6d1d3e33c907f726c03004d209f7876837d](https://github.com/samjuniors/Orbit-Core/commit/0100e6d1d3e33c907f726c03004d209f7876837d). The tag object is unsigned; SHA-256 sidecars provide integrity checks, not publisher signatures. Eight assets are present: four packages and four checksum sidecars. Latest stable-channel release remains v0.30.0.
- Exact main-head CI [run #45167794202](https://github.com/samjuniors/Orbit-Core/actions/runs/45167794202) completed PASS 5/5 on 2fdf4f. This is hosted CI evidence; no local test suite ran in this session.
- [PR #175](https://github.com/samjuniors/Orbit-Core/pull/175) merged to main at a90f1b398a2be9a3807277f560360598ef247e36 (Claude Code Windows ORBIT_PYTHON override, source VERSION 0.33.1). [PR #176](https://github.com/samjuniors/Orbit-Core/pull/176) merged at 5416230722b1009df1216023c475738f662f6c0a (Claude Code publisher attribution). [PR #173](https://github.com/samjuniors/Orbit-Core/pull/173) merged into the v0.33 integration branch at 51591e6370314e7567946ed3ca60f91aa6a189b4.
- [Issue #130](https://github.com/samjuniors/Orbit-Core/issues/130) was closed as completed after its exact v0.31 stock-agent hash fix shipped in v0.33.0. This does not certify an owner's live migration.
- v0.33.1 is source on main only; no v0.33.1 release/tag exists. No v0.34 release exists.

### Open work and release/security gates
- [Issue #138](https://github.com/samjuniors/Orbit-Core/issues/138) remains OPEN. RAD P2 OS-isolated preview is still a separate prototype/security workstream; loopback/Python preview acceptance is blocked. Draft PRs #136, #137, #139–#147 remain separate and are not release-ready.
- [PR #141](https://github.com/samjuniors/Orbit-Core/pull/141) remains an adaptive-routing proposal. Do not treat a recommendation preview as model switching or native host execution.
- v0.33 limitations remain: host-enforced timed permission expiry and active revocation BLOCKED; owner-profile native specialist delivery and migration/rollback NOT VERIFIED; independent human security review NOT DONE; full real-product visual/browser QA NOT VERIFIED. v0.33.0 is a prerelease, not a production certification.
- Main branch protection/ruleset status could not be re-read: GitHub returned 403 Resource not accessible by integration. Do not assume required checks or branch protection are enabled.

### v0.34 experimental branch — NOT APPROVED
- Branch feat/v034-context-aware-intelligence-20261123 is 38 commits ahead of main and 0 behind at head 56969232e107c56eb53f89d600793f95383ce2e6. No PR is open for this branch.
- Its plan [docs/CONTEXT-AWARE-INTELLIGENCE-PLAN.md](https://github.com/samjuniors/Orbit-Core/blob/feat/v034-context-aware-intelligence-20261123/docs/CONTEXT-AWARE-INTELLIGENCE-PLAN.md) labels the work PROPOSAL / AUDIT-FIRST / NO RUNTIME IMPLEMENTATION, but the branch actually adds runtime modules and the MCP tool orbit_project_findings. This plan/code mismatch must be resolved before review.
- Exact branch CI [run #45217966745](https://github.com/samjuniors/Orbit-Core/actions/runs/45217966745) failed all five matrix jobs at the same scripts/smoke_release_zip.py line 101 error: “Packaged MCP tool inventory mismatch”. The inspected Ubuntu Python 3.13 job ran 778 tests (6 skipped, 0 failures) before smoke failed. Ubuntu Python 3.10, 3.11, 3.12, 3.13 and Windows Python 3.12 logs all report the same inventory error; the expected inventory remains hard-coded at 57 and omits orbit_project_findings.
- Do not merge, release, or describe this branch as approved. After scope is reconciled, update the package inventory and regression coverage, then rerun all five jobs on the exact head.

### Host, connector and local state
- The Orbit ChatGPT plugin connector was not exposed in the available tool registry, so it was not used. Authorized GitHub and Notion integrations were used instead.
- Remote Arc device DESKTOP-AND1FUJ is OFFLINE; last seen 2026-11-23T11:47:38Z. An isolated checkout attempt for the exact main SHA failed because no online Fleet device satisfied the required tools and permissions.
- No local checkout, local test run, owner-profile IDE acceptance, .orbit directory or SQLite checkpoint was accessed. Mark these NOT VERIFIED / NOT RUN; do not infer local state from GitHub.
- Notion sources: [Project Decisions & Releases](https://app.notion.com/p/4074f681d48881a7a407c3bdc2054409), [Research & References](https://app.notion.com/p/4074f681d488816e9fe7f4504982c948), and [Continuous Learning / Resource-First Specialist Architecture](https://app.notion.com/p/40f4f681d48881cea5afc2df9a35084c). Current documentation-only refresh is in draft [PR #178](https://github.com/samjuniors/Orbit-Core/pull/178); stale [PR #158](https://github.com/samjuniors/Orbit-Core/pull/158) was closed as superseded because its base was 184 commits behind. No separate current Notion handoff page was found; this repository file remains the cross-agent handoff.

### Fresh research delta (2026-11-23)
- [Claude Code hooks](https://code.claude.com/docs/en/hooks): PreModelSwitch exposes context/cache metadata and can allow, deny or ask; hooks run in parallel. Treat this as a Claude-specific, version-gated adapter, not a shared provider contract.
- [Codex sandbox](https://openai.com/index/inside-the-codex-sandbox/): permission profiles constrain filesystem/network access; Windows is transitioning to MXC on compatible devices; stdio MCP server launches are not sandboxed by default. Keep sandbox capability host-specific and evidence-backed.
- [Antigravity skills migration](https://antigravity.google/docs/migration/workflows-to-skills/): workflows are deprecated; skills support progressive context loading and bundled references/scripts. Generate skills, not new legacy workflows.
- [OpenHands SDK](https://github.com/OpenHands/software-agent-sdk): current SDK/Agent Server separates conversations, workspaces, tools and events from automation lifecycle; useful architecture reference, not an automatic dependency.
- [RealSWE](https://arxiv.org/abs/2608.27831) finds realistic requests are sparse (88% problem-only/limited context vs 7% in SWE-bench) and Desired Behavior/Motivation materially improve outcomes. Ask for desired behavior on bug fixes and motivation on feature requests.
- [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) is a preliminary preprint: 39/49 skills show zero pass-rate gain, average +1.2%, and some version-mismatched skills reduce performance. Prefer targeted, version-compatible skills with deterministic paired tests; avoid blanket injection.
- [OpenAI Agents SDK tracing](https://openai.github.io/openai-agents-python/tracing/) warns generation/function spans may contain sensitive data; default to local, redacted metadata and do not require an OpenAI tracing key for provider-neutral Orbit.
- [SWE-agent](https://github.com/SWE-agent/SWE-agent) now points users to [mini-SWE-agent](https://github.com/SWE-agent/mini-swe-agent). Treat benchmark claims in the latter's README as maintainer-reported, not independent Orbit evidence.

### Approved direction and next safe action
- The existing Notion product direction orders safe Team Builder first, then task-specific skills/tools, then Orbit-mediated agent/bot coordination. Issues #90 (project-scoped learning), #91 (resource-first specialist factory) and #92 (cybersecurity specialist) remain open and must be reconciled with that order and their acceptance criteria.
- No Notion approval was found for the current v0.34 branch's expanded context-monitoring/model-routing scope. Treat it as experimental until its plan, code and acceptance criteria agree and the owner-approved scope is clear.
- Next safe action: reconcile the v0.34 branch with the approved #90/#91/#92 roadmap, keep RAD #138 separate, and only then prepare a focused implementation PR with exact-head regression evidence. Do not silently promote the experimental branch.
- No merge, release, tag, installation, host permission change, credential change or deployment was performed in this checkpoint.

---

## 2026-11-23 — Morning live revalidation (06:26 Asia/Kolkata) — historical snapshot superseded by evening revalidation

**Live snapshot:** canonical repository `samjuniors/Orbit-Core`; default `main` is signed commit [`914290b4a5ac69c0d753961affc916ba2e69b909`](https://github.com/samjuniors/Orbit-Core/commit/914290b4a5ac69c0d753961affc916ba2e69b909). Main still has `VERSION=0.32.0`, `NEXT_VERSION=0.33.0`; the latest published release is [v0.32.0 prerelease](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.32.0) (2026-11-17). Latest stable release remains v0.30.0. No v0.33 tag or public release exists. GitHub reports `main` is not protected and required status checks are off.

### Current v0.33 branches and PRs

- [Integration PR #133](https://github.com/samjuniors/Orbit-Core/pull/133): open/unmerged, head `5c1a3552cd41607d68afc91c58936561e5399254`, base `main` at `914290b4a5ac69c0d753961affc916ba2e69b909`. Exact-head CI [#45049655426](https://github.com/samjuniors/Orbit-Core/actions/runs/45049655426) completed **PASS 5/5** (Ubuntu Python 3.10–3.13; Windows Python 3.12).
- [Candidate PR #135](https://github.com/samjuniors/Orbit-Core/pull/135): open/unmerged, branch `release/v0.33.0-candidate-20261118`, head `098cdf2cfb267d8dd569ab6da5ede6cb728f3dba`, `VERSION=0.33.0`, `NEXT_VERSION=0.34.0`. Exact-head CI [#45048926337](https://github.com/samjuniors/Orbit-Core/actions/runs/45048926337) completed **PASS 5/5**. A fresh live compare now shows the candidate is **54 ahead / 12 behind** integration (`5c1a355`); it is diverged and must be synchronized and revalidated before it can be considered final. The previous sync attempts [#163](https://github.com/samjuniors/Orbit-Core/pull/163) and [#164](https://github.com/samjuniors/Orbit-Core/pull/164) closed **unmerged**; [#165](https://github.com/samjuniors/Orbit-Core/pull/165) was validation-only and closed unmerged. Do not treat its proposed merge commit as applied.
- [PR #159](https://github.com/samjuniors/Orbit-Core/pull/159) merged into the candidate at `098cdf2`, adding owner-only release dispatch/rerun authorization and owner-guidance hash-precedence protection. [PR #156](https://github.com/samjuniors/Orbit-Core/pull/156) merged into integration at `1e04dd1df7ac7fc74cf37d906b25c01bf9aa67d1`; [PR #161](https://github.com/samjuniors/Orbit-Core/pull/161) merged into integration at `5c1a3552cd41607d68afc91c58936561e5399254`. These integration fixes are not yet carried into the current candidate head.
- [PR #166](https://github.com/samjuniors/Orbit-Core/pull/166): open against integration, branch `fix/v033-pin-visual-scan-root-20261122`, head `2f69daa8365e7fd17f7e6991d3141b59c8d340fa`. It closes a parent-directory symlink race by using descriptor-relative no-follow traversal on POSIX and opened-handle containment on Windows, then reading from the validated handle. Exact-head CI [#45051094349](https://github.com/samjuniors/Orbit-Core/actions/runs/45051094349) completed **PASS 5/5**. Earlier run [#45050974010](https://github.com/samjuniors/Orbit-Core/actions/runs/45050974010) failed on the previous head because the race-test monkeypatch did not preserve `os.supports_dir_fd`; the test harness was corrected. A Codex review receipt exists for `2f69daa`, but a separate independent security sign-off is not established.
- [PR #168](https://github.com/samjuniors/Orbit-Core/pull/168) is a temporary CI-validation PR for #166 and explicitly says **DO NOT MERGE**. Older validation PR #167 is closed unmerged. [PR #134](https://github.com/samjuniors/Orbit-Core/pull/134) remains an older alternative candidate draft; keep #135 canonical and do not combine the two.

### Release, host and security gates

**v0.33 remains HOLD / NOT MERGED TO MAIN / NOT TAGGED / NOT RELEASED / NOT INSTALLED.** Outstanding host gates include inherited-profile child-result delivery and Codex child identity/receipt (**NOT VERIFIED**), host-enforced timed permission expiry/active revocation (**BLOCKED**), actual target-project browser/visual QA (**NOT VERIFIED**), historical owner-settings delta (**NOT VERIFIED**), and owner-profile v0.33 install/rollback (**NOT RUN**). RAD P2 [issue #138](https://github.com/samjuniors/Orbit-Core/issues/138) remains open; drafts #136–#147 are separate from v0.33. LPAC Python HTTP preview and descendant launch remain blocked; do not describe the prototype as a production OS sandbox.

The candidate release workflow is owner-only manual dispatch from `main`; main's currently published workflow separately supports manual dispatch and tag-push prereleases. Reconcile this branch-specific difference after any approved merge.

### Environment and research

Remote Arc device `DESKTOP-AND1FUJ` is still **offline** (last seen 2026-11-21 11:56 UTC). No local checkout, local tests, owner-profile operation, or `.orbit`/SQLite checkpoint was accessed in this report. The Orbit-specific ChatGPT plugin connector was not exposed in the available tool registry; GitHub and Notion were used. The latest research record remains 2026-11-22 and is based on primary vendor documentation (Google Antigravity, Anthropic Claude Code, OpenAI Codex/Agents SDK); findings are host-specific design references, not implementation evidence or an approved dependency. No new external research or owner decision was added in this run.

### Next safe sequence

1. Complete review of #166; merge only the actual fix into integration after review and exact-head CI remain green. Never merge #168.
2. Rebuild/synchronize the candidate from the current integration head, preserving candidate-only release controls; then run exact-head candidate CI and fresh review. Do not rely on the closed #163/#164/#165 sync attempts.
3. Reconnect the authorized Windows host and run bounded disposable native acceptance; update the existing v0.33 acceptance matrix with evidence.
4. Obtain the owner's explicit risk/release decision only after the host, security, package, and rollback gates are reviewed. Do not merge to main, tag, publish, install, or deploy before that decision.

## 2026-11-22 — Live continuation checkpoint: P2 stop-session retry + provider adapter research

**Verified source snapshot:** canonical repo `samjuniors/Orbit-Core`; default `main` at `914290b4a5ac69c0d753961affc916ba2e69b909` (signed commit). Published latest release remains prerelease `v0.32.0`; no v0.33 release is published. The historic Orbit-Core-MCP URL redirects to this repository.

### Active work and evidence

- [PR #133](https://github.com/samjuniors/Orbit-Core/pull/133) remains open/unmerged as the v0.33 integration base. [PR #135](https://github.com/samjuniors/Orbit-Core/pull/135) remains the versioned v0.33.0 candidate stacked on #133. [PR #155](https://github.com/samjuniors/Orbit-Core/pull/155) is CI-validation-only; never merge it.
- Codex's review on #133 found a P2 defect: an earlier native worker session's stop request could block a retry in a new session. [PR #156](https://github.com/samjuniors/Orbit-Core/pull/156) implements task-revision/native-session-scoped duplicate detection, exact attempt stop-plan lookup, retirement correlation, and a regression test preserving the old request as audit evidence.
- Initial #156 CI run [#45047149105](https://github.com/samjuniors/Orbit-Core/actions/runs/45047149105) failed on all four Ubuntu Python versions at an assertion expecting the prior stop request to disappear from the inbox. That expectation conflicts with the intended audit contract: historical requests remain pending evidence. The branch was updated; current PR head observed as `dd835332cd1279ded38de51eeb5fc5b835cd183a`. Latest matrix run [#45047242899](https://github.com/samjuniors/Orbit-Core/actions/runs/45047242899) was **IN PROGRESS** at snapshot time. Recheck exact head and all five jobs before calling it PASS.
- [PR #157](https://github.com/samjuniors/Orbit-Core/pull/157) is explicitly a temporary CI-validation PR for #156; its body says **DO NOT MERGE**. Close only after its validation purpose is fulfilled and evidence is recorded.
- [RAD P2 issue #138](https://github.com/samjuniors/Orbit-Core/issues/138) remains open. RAD P0/P1/P2 drafts #136–#147 are separate, security-sensitive, and not automatically included in #135.

### Release disposition

**v0.33 remains HOLD / NOT MERGED / NOT TAGGED / NOT RELEASED / NOT INSTALLED.** Outstanding gates include real supported-host acceptance (including native child receipts/permission and cancellation reconciliation), host-enforced timed permission expiry/revocation, actual target-project browser/visual QA, independent security review, and owner release decision. Do not treat CI or a synthetic fixture as host/production certification. Follow the canonical [release process](RELEASE-PROCESS.md) and existing [v0.33 acceptance matrix](RELEASE-ACCEPTANCE-v0.33.0.md). Preserve v0.32 assets.

### Cross-host primary-source research delta

Research recorded in the existing Notion [Orbit Core Research & References](https://app.notion.com/p/4074f681d488816e9fe7f4504982c948) page (2026-11-22):
- Antigravity's current rules support cumulative workspace/global `AGENTS.md`, `GEMINI.md`, and `.agents/rules/*.md`; Google says legacy Workflows are deprecated in favor of skills. Enforce documented file/token budgets; don't emit deprecated workflow manifests as the preferred integration.
- Claude Code exposes lifecycle hooks (SessionStart, PreToolUse, PostToolUse, PermissionRequest, Stop, PostCompact); hooks execute commands with host-user privileges, so treat them as privileged code requiring review and narrow allowlists.
- Codex distinguishes read-only/workspace-write sandboxes and approval policies; bypass flags remove protection. Preserve native approvals and never route around host denials.
- OpenAI Agents SDK documents manager-owned agents-as-tools versus control-transferring handoffs, plus traces for tool calls/handoffs/guardrails. Use as design reference only, not an Orbit runtime dependency.
- Recommendation: canonical provider-neutral task/evidence state + thin versioned adapters; model host capabilities as observed, not assumed; represent proposed → host-approved → host-invoked → independently observed → reconciled; measure task quality, regression, policy compliance, interventions, latency and cost only where real metadata exists.

### Blockers and next safe action

- Remote Arc Windows was previously reported offline; recheck before any local/IDE acceptance. No local `.orbit`/SQLite checkpoint was accessed in this run.
- Orbit-specific ChatGPT plugin was not exposed in the available integration registry; GitHub and Notion integrations were used. Do not claim plugin execution.
- **Next:** revalidate #156 latest head and #45047242899; inspect failure logs if any, then obtain focused independent review. Keep #157 non-mergeable/validation-only. Resume #133/#135 acceptance only after the P2 finding is resolved and all separate host/security/release gates are evidenced.

**Notion records updated:** [Project Decisions & Releases](https://app.notion.com/p/4074f681d48881a7a407c3bdc2054409) and [Research & References](https://app.notion.com/p/4074f681d488816e9fe7f4504982c948). GitHub and Notion are linked sources, not auto-synchronized. This is a redacted shared handoff; no credentials, local paths, raw SQLite/WAL or host tokens included.

---

## Source of truth and handoff contract

**Status:** maintained handoff contract plus a dated engineering snapshot, **not** authorization to merge, install, or release.
**Last reviewed:** 2026-11-23 (Asia/Kolkata).
**Project:** [samjuniors/Orbit-Core](https://github.com/samjuniors/Orbit-Core). The historic Orbit-Core-MCP URL redirects to this repository.
**Applies to:** ChatGPT, Claude Code, Codex, Antigravity and other authorized coding hosts. **Not** the separate Orbit Commander project (paused by owner).

## 2026-11-22 — documentation merge and release disposition

- [PR #148](https://github.com/samjuniors/Orbit-Core/pull/148) is **MERGED** to `main` at [`2a11fd37b171fa2701e5c4d926b941f6b4f65332`](https://github.com/samjuniors/Orbit-Core/commit/2a11fd37b171fa2701e5c4d926b941f6b4f65332). Six documentation paths from this handoff are now on main. Exact PR-head CI #44903594241 completed success; separate push CI on the merge commit was not confirmed.
- Main `VERSION` remains `0.32.0`. **No new release was created.** v0.33.0 remains a separate unmerged candidate stacked on #133; its existing acceptance record continues to report owner-profile native delivery NOT VERIFIED, host-enforced timed permission expiry/active revocation BLOCKED, and independent review/owner release gates outstanding. Do not publish based on the documentation PR's CI.
- **Release trigger policy verified on 2026-11-22:** `.github/workflows/release.yml` intentionally supports (1) manual `workflow_dispatch` from `main`, with `prerelease` as the default and `stable` available only through that explicit manual path, and (2) a matching `v[0-9]*` tag push, which is forced to `prerelease` and must point to a commit already contained in `main`. `docs/RELEASE-PROCESS.md` documents both paths. The earlier handoff statement calling this a contradiction/manual-only policy was incorrect. No workflow code change is required for this finding; release readiness and explicit owner approval remain separate mandatory gates.
- Notion project hub updated with the merge SHA, release HOLD, and this workflow discrepancy. Local PC `.orbit`/SQLite remains unverified; Remote Arc was offline at the last check.

## 1. Source of truth and handoff limits

| Source | Owns | Never assume |
| --- | --- | --- |
| GitHub | Exact implementation, branch/commit, open PRs/issues, CI, acceptance evidence, release tags/assets | An unmerged PR is installed; green CI means host/release approval |
| [Orbit Core Notion decisions hub](https://app.notion.com/p/4074f681d48881a7a407c3bdc2054409) | Product intent, decisions, rationale, research, approved priorities | A Notion proposal is implemented or released |
| Local project SQLite and ignored .orbit directory | Project-specific tasks, checkpoints, revisions, recovery and host-operational state | The database or local files automatically follow a Git clone, another computer, or another AI session |

Provider switching transfers **explicit records and source evidence**, not hidden conversations, model context, credentials, host permissions, in-memory processes or uncommitted work. A new agent **must verify actual state**, not silently replay actions. Private/local databases stay local; use the existing Orbit project scan/resume/task/checkpoint MCP tools when the authorized host exposes them. Never upload SQLite/WAL, approval tokens, private host settings, log secrets or unrelated project memory to Git/Notion.

**Agent reading order:** [AGENTS.md](../AGENTS.md) → this document → relevant task branch and PR → relevant code/tests → [Notion decisions hub](https://app.notion.com/p/4074f681d48881a7a407c3bdc2054409). For releases, [RELEASE-PROCESS.md](RELEASE-PROCESS.md) and the exact version acceptance document are mandatory. For Claude Code, [CLAUDE.md](../CLAUDE.md) is a short entry point, **not** another source of truth.

## 2. Dated active engineering snapshot — 2026-11-21

This is a **historical checkpoint**. Before work resumes, inspect the current head, base, status and reviews of each named PR, the latest GitHub Releases page, exact-head CI and the most recent Notion decision. Do not promote this snapshot into evidence of present-day test success.

| Track | State and action |
| --- | --- |
| Published release | [v0.32.0 prerelease](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.32.0) is the published installation baseline, with 57 reported MCP tools in prior acceptance. Main's VERSION was 0.32.0 when read for this checkpoint. Recheck releases before version operations. |
| Candidate v0.33 | [Integration draft #133](https://github.com/samjuniors/Orbit-Core/pull/133) → stacked [candidate draft #135](https://github.com/samjuniors/Orbit-Core/pull/135), branch `release/v0.33.0-candidate-20261118`. Its own [release acceptance matrix](https://github.com/samjuniors/Orbit-Core/blob/release/v0.33.0-candidate-20261118/docs/RELEASE-ACCEPTANCE-v0.33.0.md) is authoritative for exact tests, hosts and evidence. **UNMERGED / UNPUBLISHED / RELEASE HOLD.** |
| Candidate last observed | PR #135 reports checkpoint [4e20b04c](https://github.com/samjuniors/Orbit-Core/commit/4e20b04c034a26069d9e6f7236d7973c2e9a0bcd) with [CI run #44901076599](https://github.com/samjuniors/Orbit-Core/actions/runs/44901076599) PASS 5/5 after a rerun of Ubuntu 3.10; the prior signal-11 MCP subprocess failure has **unverified cause**. The PR describes disposable host child delivery/lead review as scoped PASS, but owner-profile inherited delivery and historical settings change as NOT VERIFIED, and timed permission expiry/active revocation as BLOCKED. This is **not** a claim that the current PR head equals that SHA. |
| RAD layered defense | [Issue #138](https://github.com/samjuniors/Orbit-Core/issues/138) OPEN; security drafts [#136](https://github.com/samjuniors/Orbit-Core/pull/136), [#137](https://github.com/samjuniors/Orbit-Core/pull/137), [#139](https://github.com/samjuniors/Orbit-Core/pull/139), [#140](https://github.com/samjuniors/Orbit-Core/pull/140), [#143](https://github.com/samjuniors/Orbit-Core/pull/143)–[#147](https://github.com/samjuniors/Orbit-Core/pull/147) are **separate and draft**. #146 is synthetic, bounded static HTTP snapshot research; #147 proposes package exclusion of experimental prototypes. Neither is proof of production OS isolation or live application browser security. Do **not** automatically fold these into #135. |
| Other independent work | [Adaptive-routing draft #141](https://github.com/samjuniors/Orbit-Core/pull/141) and other older draft PRs remain independent. Inspect each before claiming it is superseded or complete. |
| Owner constraints | **No merge, tag, publication, installation, credential changes, OS security profile changes or release approval** granted by this handoff request. Orbit Commander remains paused; do not resume it under Orbit Core. |

**Next recommended bounded task:** read #135's actual current head and [acceptance matrix](https://github.com/samjuniors/Orbit-Core/blob/release/v0.33.0-candidate-20261118/docs/RELEASE-ACCEPTANCE-v0.33.0.md); reconcile its open gates with #133, Notion and the current host capabilities. Prioritize reproducible intermittent CI diagnostics and remaining host/release blockers **without weakening fail-closed policy**. Advance only work approved in the current task; do not silently cross from documentation/analysis to release operations.

## 3. Switching protocol (ChatGPT → Claude Code → ChatGPT)

### Before yielding control — outgoing agent

1. Read actual repository/branch/PR state and working tree. Record **branch, full HEAD SHA, base PR and dirty/untracked file counts**. Never hide pending local edits or overwrite another agent's work.
2. Capture objective and scope, approved decisions, changes made, paths touched, tests actually run (commands, environment, exact commit, results), evidence links, blockers, release/host gates, pending processes and the **single next safe action**.
3. If Orbit MCP is connected and authorized, read/resume the correct project and record its existing revisioned checkpoint/task/ledger state **using its real APIs**. Do not fabricate a checkpoint or treat tool discovery as a successful write. Leave local SQLite/WAL intact.
4. Save **private operational detail** in project-local ignored `.orbit/` using existing project checkpoint conventions. Publish only a **redacted summary** via the current GitHub draft branch/PR and append durable **product decisions** to the existing Orbit Notion hub. Do not copy an entire session transcript, raw credentials, local filesystem paths, host approval tokens or private evidence into a public commit.
5. Confirm any issued write completed. Report **NOT VERIFIED** for any attempted but unconfirmed action. Stop issuing writes after handing over ownership; never allow two agents to mutate the same files/checkpoint concurrently.

### On taking control — incoming agent

1. Read this file, AGENTS.md, the task's PR/evidence and the Notion hub. Requery live GitHub status and verify source HEAD, actual working tree, existing local Orbit state and host/permission availability.
2. Compare the prior handoff's exact SHA/branch/revision to what is truly present. On mismatch, **pause writes, reconcile and preserve both versions**; do not replay uncertain installs, approvals, merges or irreversible actions.
3. Restore only **the relevant project's** state. If local `.orbit` or SQLite isn't accessible, work from sanitized shared records and mark local revision/host checks **BLOCKED or NOT VERIFIED** rather than pretending to have loaded them.
4. Continue one bounded authorized action on an appropriate branch. Re-run impacted tests and record evidence. Do not inherit permission grants from an earlier model/host.

### Minimal read-only terminal checks

```bash
git status --short
git branch --show-current
git rev-parse HEAD
git log -1 --format='%H %s'
```

Use the connected host's approved read-only GitHub/Notion tools when no terminal is available. Commands above do not prove that ignored SQLite or other local state has been recovered.

## 4. Handoff record template (fill at every meaningful milestone)

Keep one **current handoff per workstream**, linked from the active draft PR or its comment. Update/supersede the prior handoff instead of spawning competing files. This template is intentionally plain text and works in GitHub, Notion, Claude Code and ChatGPT.

```text
ORBIT CORE HANDOFF — YYYY-MM-DD HH:MM timezone
From agent/host:                 To agent/host:
Project: samjuniors/Orbit-Core (never another product)
Objective and scope:
Branch / base / full HEAD SHA:
Open PR(s) / issue(s):
Working tree: clean | dirty (counts only); unpushed work:
Version / published baseline (verified with URL and date):
Completed changes (IMPLEMENTED vs VERIFIED):
Checks: command + platform + source SHA + PASS/FAIL/BLOCKED/NOT RUN:
Native IDE / permission / browser acceptance:
Local Orbit project key + checkpoint/task revision (no secrets):
Local-only/private evidence location (reference, not contents):
Notion decision page / approved vs proposed:
Outstanding bugs, risks, blockers and owner decisions:
Pending processes / unresolved side effects / cleanup:
Next single safe action + expected acceptance evidence:
Explicit limits (no merge/release/install/credential change unless approved):
Handoff saved where / receiving agent verification result:
```

**Status vocabulary:** PROPOSED, APPROVED, IMPLEMENTED, VERIFIED for decisions/implementation; **PASS, FAIL, BLOCKED, SKIPPED, NOT RUN, NOT VERIFIED** for tests/gates. A PR comment, model statement, checklist or agent-generated receipt is **not** evidence of a host action without independent confirmation.

## 5. Ready-to-use resume prompt

> You are continuing **Orbit Core** only, repository https://github.com/samjuniors/Orbit-Core. First read AGENTS.md, docs/AGENT-HANDOFF.md, the current task PR and its exact-head acceptance record, plus the Orbit Core Notion decisions hub. Compare current GitHub branch/commit/CI with the handoff snapshot, then inspect local .orbit/SQLite checkpoint **only if connected and authorized**. Report discrepancies and verified vs not-verified work. Preserve uncommitted work, credentials and host permissions; do not touch paused Orbit Commander or other repositories. Continue the smallest approved next action on a draft branch, add regression evidence and update the handoff for the next ChatGPT/Claude Code switch. Never merge, install or release without explicit owner permission.

## 6. Updating the handoff itself

At the end of each meaningful task, update **this single handoff record** only for shared engineering summary and actionable pointers; preserve dated historical evidence instead of rewriting it as current. Put detailed version/host acceptance in the **existing** `docs/RELEASE-ACCEPTANCE-vX.Y.Z.md`, product decisions in the **existing** Notion hub, and ephemeral task/checkpoint data in **local** SQLite/`.orbit`. Link rather than duplicate. If a new agent can't access one source, record that constraint explicitly and do not infer its contents.
