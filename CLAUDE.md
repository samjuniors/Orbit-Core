# Claude Code — Orbit Core MCP

This is **Orbit Core** (`samjuniors/Orbit-Core`), not Orbit Commander, Helm, Aro, Nerve Core, or SamjuniorsOS. Orbit Commander is **paused by owner**; do not resume it.

1. Read [AGENTS.md](AGENTS.md) for the repository-wide engineering, release, security, and approval rules. They apply here without exception.
2. Read [docs/AGENT-HANDOFF.md](docs/AGENT-HANDOFF.md) for the canonical **ChatGPT ↔ Claude Code ↔ Codex ↔ Antigravity** continuity contract, dated GitHub snapshot, state-transfer template and one safe next action.
3. Verify live `main`, your actual branch and full HEAD SHA, open PRs/issues and exact-head CI **before acting**. A dated handoff can be stale. Preserve local uncommitted work; never assume a previous agent's commands succeeded.
4. Read the relevant [Orbit Core Notion decisions hub](https://app.notion.com/p/4074f681d48881a7a407c3bdc2054409) for product intent. GitHub establishes what exists; project-local ignored `.orbit` and SQLite hold operational state. Neither automatically syncs to Claude Code or ChatGPT. Do not publish private state or credentials.
5. For a version/release task, use the existing [release procedure](docs/RELEASE-PROCESS.md) and version-specific acceptance document. The v0.33 candidate and RAD experimental security drafts must stay separate, on HOLD until evidence and explicit owner approval. Never merge, tag, release, install or alter host security settings merely to complete a handoff.
6. At a milestone or before yielding to ChatGPT, update the **same workstream handoff** with exact branch/commit, changes, verified checks, blockers, current local checkpoint reference where accessible, and next safe action. Link to GitHub PR and existing Notion decisions rather than making duplicate roadmap/release files.

**Start-of-session prompt:** “Reconcile AGENTS.md, docs/AGENT-HANDOFF.md, the current PR and exact-head GitHub state, plus existing Orbit Notion decisions. Identify what is implemented, verified, blocked and safe to do next; resume only authorized work.”

**End-of-session contract:** Provide a redacted, portable handoff in the format in `docs/AGENT-HANDOFF.md`; explicitly mark anything NOT RUN or NOT VERIFIED. Stop writes after transferring control.
