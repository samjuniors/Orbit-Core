# Orbit Core — cross-agent continuity and handoff

**Status:** maintained handoff contract plus a dated engineering snapshot, **not** authorization to merge, install, or release.
**Last reviewed:** 2026-11-25 (Asia/Kolkata).
**Project:** [samjuniors/Orbit-Core](https://github.com/samjuniors/Orbit-Core). The historic Orbit-Core-MCP URL redirects to this repository.
**Applies to:** ChatGPT, Claude Code, Codex, Antigravity and other authorized coding hosts. **Not** the separate Orbit Commander project (paused by owner).

## 2026-11-25 ? v0.34 Windows verification and security containment

- Correct repository checkout: `E:\SOFTWARE\Plugin\Orbit-Core` is the owner's primary checkout. The active v0.34 worktree is `E:\SOFTWARE\Plugin\wt-v034-context-aware`, branch `feat/v034-context-aware-intelligence-20261123`. The primary checkout and active RAD security worktree remain untouched.
- Feature branch source base was `2fdf4f329774b9644e75ac0df4d89738a7cd625f`. Prior source/candidate containment commit: [`fde77820b004be8f172de723f8ffc37bf773367e`](https://github.com/samjuniors/Orbit-Core/commit/fde77820b004be8f172de723f8ffc37bf773367e). Latest structural/readiness guard and acceptance record commit: [`50efb36d6987cd351859a6091c924a71c48767b3`](https://github.com/samjuniors/Orbit-Core/commit/50efb36d6987cd351859a6091c924a71c48767b3).
- Two deterministic Windows junction-race tests proved the previous candidate writer could write outside the project and the metadata-only structural scan could expose an outside-project filename. Windows candidate writes, source-content scans and structural scans now fail closed. Blocked structural scans do not open directory entries, do not fabricate an empty snapshot, and preserve the last complete readiness snapshot/counts.
- Windows Python 3.12 full suite: **835 PASS / 43 SKIPPED / 0 FAIL**. Focused readiness: **16/16 PASS**; project audit: **1 PASS / 4 SKIPPED**; source audit: **2 PASS / 4 SKIPPED**; agent factory: **14 PASS / 2 SKIPPED**; Claude plugin parity: **4/4 PASS**. Skips and security holds are detailed in `docs/CONTEXT-AWARE-INTELLIGENCE-PLAN.md`.
- Disposable validation passed: Python compileall, Windows GUI compile, release readiness, strict bundle parity, fresh ZIP package build and extracted ZIP/MCP stdio smoke (**58 tools**). The generated artifacts were confined to a disposable copy; VERSION remains 0.33.1 and NEXT_VERSION 0.34.0. This is not a v0.34 release.
- A synthetic Claude SessionStart hook payload smoke passed against a temporary SQLite DB and stored no raw session ID/prompt/tool payload. This does not verify actual Claude Code hook delivery. No plugin update, hook activation or host configuration change was performed; installed plugin remains 0.33.1.
- Prior GitHub Actions run [#45543537489](https://github.com/samjuniors/Orbit-Core/actions/runs/45543537489) passed **5/5** on `ac25cab7e23354d74790f0c46816ee1fdd94c898`. It predates the latest structural/readiness guard. Exact-head CI is pending the feature-branch push.
- Model routing remains advisory; no active-session model switching or authoritative quota telemetry is implemented. Non-Windows path traversal and candidate persistence still require independent adversarial security review.
- The version-specific development gate is recorded in [RELEASE-ACCEPTANCE-v0.34.0.md](RELEASE-ACCEPTANCE-v0.34.0.md). No PR, merge, tag, release, plugin install or hook activation has been performed. Independent human security review and native Claude lifecycle acceptance remain required.

## 2026-11-22 — documentation merge and release disposition

- [PR #148](https://github.com/samjuniors/Orbit-Core/pull/148) is **MERGED** to `main` at [`2a11fd37b171fa2701e5c4d926b941f6b4f65332`](https://github.com/samjuniors/Orbit-Core/commit/2a11fd37b171fa2701e5c4d926b941f6b4f65332). Six documentation paths from this handoff are now on main. Exact PR-head CI #44903594241 completed success; separate push CI on the merge commit was not confirmed.
- Main `VERSION` remains `0.32.0`. **No new release was created.** v0.33.0 remains a separate unmerged candidate stacked on #133; its existing acceptance record continues to report owner-profile native delivery NOT VERIFIED, host-enforced timed permission expiry/active revocation BLOCKED, and independent review/owner release gates outstanding. Do not publish based on the documentation PR's CI.
- **Release trigger policy is branch-specific (verified 2026-11-22):** current `main` supports manual `workflow_dispatch` from `main` (default `prerelease`; `stable` only by explicit manual selection) and matching version-tag pushes (prerelease only, pointing to a commit already contained in `main`). The v0.33 candidate branch intentionally hardens this to **owner-only manual `workflow_dispatch` from `main`**; the no-write authorization job checks both original and triggering actors against `github.repository_owner`, and the publish job grants `contents: write` only after that gate. Its `.github/workflows/release.yml` and `docs/RELEASE-PROCESS.md` agree, and a tag push alone is not a publication path. Do not transfer main's tag-trigger behavior into the candidate. After v0.33 is merged, revalidate the new main workflow and update this note. All publication remains subject to release readiness and separate explicit owner approval.
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
