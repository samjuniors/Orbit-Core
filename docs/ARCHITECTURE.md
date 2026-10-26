# Architecture / source authority

```text
Coding hosts: Antigravity / Codex / Claude Code
   ├─ host-specific instructions and agent definitions (source/agents, source/skills)
   ├─ native host tools perform actual code editing / specialist sessions
   └─ MCP stdio process (source/runtime/orbit_mcp.py)
        ├─ local SQLite MemoryStore (project keys)
        ├─ task ledger, reservations, dependencies and review records
        ├─ read-only capability discovery / selection
        └─ project checkpoints and conservative permission gates
```

This MCP does not launch external coding CLIs in the universal/native mode. It does not persist model runs after IDE termination or stream an application preview. The host must verify that delegated agents actually ran, and must not mark a task done solely from reservation entries.

**Canonical source**: This repository tracks the v0.23.0 local runtime, agent/skill templates, and installer. The separate ChatGPT private plugin has its own release record and packaging. GitHub changes do **not** automatically update that plugin; publishing is a distinct explicit release step. The separate public `samjuniors/orbit` coding-agent CLI source is not part of this repo.

**State**: User machine SQLite outside the repository, per host OS app-data directory. Sensitive/local state must not be synchronized to GitHub. Project specs and ADRs stay in their original project repositories. Orbit's project checkpoint only indexes current work and references those sources.

## v0.24.0 — preview manager (candidate)

`source/runtime/orbit_preview.py` is a bounded, opt-in localhost process runner for developer servers. It lives alongside the stdio MCP, not inside the AI model. The host must choose and approve the exact project command. The manager uses subprocess argument vectors (`shell=False`), validates the project path via `orbit_mcp.project_root`, rejects foreign occupied loopback ports and probes only `127.0.0.1`; it holds process handles in memory, with logs stored outside the project by default. It never creates tunnels, deploys apps or launches AI agents. A successful HTTP readiness check is not visual QA evidence. Cross-MCP-session supervision, automated Playwright QA, visual feedback, and shareable public links are separately gated future work.
