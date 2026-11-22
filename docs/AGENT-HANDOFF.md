# Orbit Core — cross-agent continuity and handoff

**Status:** maintained handoff contract plus a dated engineering snapshot, **not** authorization to merge, install, or release.
**Last reviewed:** 2026-11-21 (Asia/Kolkata).
**Project:** [samjuniors/Orbit-Core](https://github.com/samjuniors/Orbit-Core). The historic Orbit-Core-MCP URL redirects to this repository.
**Applies to:** ChatGPT, Claude Code, Codex, Antigravity and other authorized coding hosts. **Not** the separate Orbit Commander project (paused by owner).

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
