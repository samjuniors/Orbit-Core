# ORBIT Universal v0.23.0 — Machine-wide one-click setup + capability preflight

**One installer window, two scopes.** On Windows with Python 3.10+ installed and associated with `.pyw`, double-click `install_orbit_gui.pyw`. The default **This computer (all projects)** option installs Orbit agent/skills and one shared local MCP registration to Antigravity, Codex and Claude Code's user-level configuration. No project folder selection is needed. Or select **One specific project**, Browse and install only there. Click **Install Orbit (one click)**, review the confirmation showing all target paths, and approve. The installer never edits application code, executes external AI CLIs, installs third-party skills or changes MCP credentials. Refresh/restart the coding hosts afterward. Python is a prerequisite; this ZIP is **not** a native `.exe` or a zero-dependency installer.

**Global locations** (per user, not system administrator): Antigravity `~/.gemini/config/agents/orbit*.md`, `~/.gemini/config/skills/orbit/SKILL.md`, and `~/.gemini/config/mcp_config.json`; Codex `~/.agents/skills/orbit/SKILL.md` and `~/.codex/config.toml`; Claude Code `~/.claude/skills/orbit/SKILL.md`, `~/.claude/agents/orbit*.md` and `~/.claude.json`. Project-scoped files remain under `.agents`, `.codex`, `.claude`, `AGENTS.md`, `CLAUDE.md`, and `.mcp.json` only when selected. The local MCP runtime is installed into `~/.orbit-universal/0.23.0/`. The same existing default OS-user SQLite database is reused across hosts, without cloud synchronization.

**Capability intelligence (2 new MCP tools; 17 total):** `orbit_capability_discover` enumerates installed local skill metadata and configured MCP names. `orbit_capability_select` matches candidate skills to a specific task, suggests a narrow official external research lead (currently Impeccable for UI polish), and returns a recommendation for Orbit. Both tools are **read-only**: they do not actually search the internet, run installers or verify connected MCP tools. The host's own LLM may use authorized web search if the needed skill is missing, and must review publisher, source, permission scope and code before requesting approval for any external installation or connection. Installed skills are not automatically trusted. Orbit may choose existing trusted tools autonomously; it cannot silently elevate permissions.

**Upgrades:** An exact match of known stock v0.22 files can be upgraded with an `.orbit-backup` copy. Customized agent files are blocked for review. Existing `AGENTS.md`/`CLAUDE.md` instructions are preserved, and unrelated MCP entries are kept. Reinstalling an unchanged v0.23 setup is idempotent. Existing older v0.20/v0.21 custom installs may require manual reconciliation. No automatic deletes, archive, move or Git commit.

**Claude Desktop ordinary chat** uses `ORBIT-Claude-Desktop-v0.23.0.mcpb` included here, rather than the coding-host configuration; it provides memory/capability/ledger tools, not native coding subagents. **macOS/Linux:** `installer.py --scope machine --install` is available after reviewing `installer.py --scope machine`; a desktop GUI entry launcher can be set up separately. This release's tested one-click double-click workflow targets Windows with a working Python association.

## Quick verification

1. Install machine-wide and refresh your selected coding host. Verify `orbit-core-native` lists **17 tools**, including the new `orbit_capability_select`.
2. Ask Orbit to inspect your existing frontend project, classify its design needs, list installed matching skills, and list *only* reputable official candidates for missing skills. It should not auto-install Impeccable.
3. In fresh `orbit-todo-lab`, ask Orbit to plan a responsive Todo app, select frontend/backend specialists, decide whether Impeccable offers value, and request approval before adding any new dependency. Check actual hosted subagent sessions separately from Orbit's task reservations.
4. Reopen the same project in another installed coding host and verify memory/ledger from the shared SQLite database, not from chat history.

Official reference: https://antigravity.google/docs/skills ; https://antigravity.google/docs/mcp ; https://antigravity.google/docs/subagents/ ; https://learn.chatgpt.com/docs/build-skills ; https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview ; https://impeccable.style/ .

---

# ORBIT Universal Local Setup — v0.23.0

(Prior v0.22 reference below; v0.23 setup above supersedes its installer instructions.)

This package adapts the existing **Orbit v0.21.0 Antigravity runtime** to **Antigravity Desktop/IDE, Codex desktop/CLI, and Claude Code CLI or Claude Desktop Code tab**. All three local coding hosts use the **same** Python stdio MCP runtime and per-user SQLite storage. This is not an autonomous model launcher; your host's own model and native subagent tools do the coding.

**Claude Desktop regular chat:** use the separate `ORBIT-Claude-Desktop-v0.23.0.mcpb` found in this ZIP. It adds the same MCP tools to normal desktop chat; it does **not** give regular chat a local coding terminal or native subagent capability. If using Claude Desktop Code tab, follow the Claude Code project setup and its host connection behavior.

## Requirements

- Python 3.10 or later with Tkinter for the GUI installer. Python **only** starts the local MCP server; no Gemini/Claude/Codex CLI is required by this package.
- A machine-local installation of at least one supported coding host, signed in and able to access your local project folder.
- Node.js 20+ and npm only **when you build the Todo example**, if your host selects React/Vite/Express. No Node dependency is needed to install Orbit itself.
- An existing **empty project folder**, e.g. `Documents/orbit-todo-lab`. Create it with Windows File Explorer or Finder. No existing repositories need to be touched.

## Install without terminal on Windows

1. Extract this ZIP to a **permanent** folder.
2. Open the extracted `orbit-universal-0.23.0` folder and double-click `install_orbit_gui.pyw` (Windows file may appear without extension). If it does not launch, check Python 3.10+ with Tk support and `.pyw` file association.
3. Browse to your **empty** `orbit-todo-lab` folder. Leave the three host checkboxes selected for all-host setup.
4. Click **1. Preview changes**, review paths carefully, and click **2. Install in workspace**. Installation writes no app code, Git commits, or cloud credentials.
5. Open *that same folder* in your chosen coding host, refresh/restart its MCP list, and inspect the tools and Orbit skill.

On macOS/Linux, use `python3 installer.py --project /absolute/path/to/orbit-todo-lab` to preview, then repeat with `--install` when satisfied. This requires a terminal for installation on those systems; the actual coding stays inside the host app.

### What is installed

| Purpose | File/location |
|---|---|
| MCP runtime (shared) | `~/.orbit-universal/0.23.0/orbit_mcp.py` + `orbit_tasks.py` |
| Local database (shared) | Existing OS-specific Orbit Core SQLite default: `%LOCALAPPDATA%/OrbitCore/memory.sqlite3` on Windows; `~/.local/share/orbit-core/memory.sqlite3` on macOS/Linux unless `$XDG_DATA_HOME` overrides it |
| Antigravity agents | `.agents/agents/orbit.md`, 12 `orbit-*.md` specialist files |
| Shared Antigravity/Codex Orbit skill | `.agents/skills/orbit/SKILL.md` |
| Antigravity MCP | `.agents/mcp_config.json` |
| Codex MCP | `.codex/config.toml` (trusted project) |
| Codex rules | `AGENTS.md` |
| Claude Code agents | `.claude/agents/orbit-lead.md`, 12 specialist files |
| Claude Code skill | `.claude/skills/orbit/SKILL.md` |
| Claude Code MCP | `.mcp.json` |
| Claude Code rules | `CLAUDE.md` |

Preview mode is the default. Existing *different* files are never overwritten without a manual review. Existing MCP JSON is merged, and changes back up the original as `.orbit-backup`. Existing Codex TOML is appended only if the Orbit MCP table is missing; if the table is present but different, setup stops. Never commit machine-specific absolute paths from MCP config files to a public repository. The installer refuses unsafe root/home/symlink project targets and never touches app code or Git.

## Verify each host

**Antigravity Desktop:** Open the project. Select custom **orbit** agent. Settings → Customizations → Installed MCP Servers → Refresh, or for Antigravity IDE: agent panel `… → MCP Servers → Manage MCP Servers → View raw config`. Verify `orbit-core-native` with 15 tools. Custom agent files live at `.agents/agents/`. Ask Orbit to list them. Native delegation requires the host to expose `invoke_subagent` with user permission.

**Codex desktop/CLI:** Open the project as a **trusted local folder**. Codex reads `.agents/skills/orbit` and project `.codex/config.toml`. Look for `$orbit` in skill chooser (`/skills` in CLI) and `orbit-core-native` in the MCP server settings or `/mcp`. Codex's own agent delegation capabilities depend on your host/version/permissions.

**Claude Code CLI / Claude Desktop Code tab:** Open the project, approve the new project `.mcp.json` MCP server when prompted, and verify `/mcp` lists `orbit-core-native`. Read `.claude/skills/orbit/SKILL.md`; the `orbit-lead` and specialists are defined in `.claude/agents`. In Code tab, project MCP precedence and host environment may differ—verify `/mcp` rather than assuming the CLI and Code tab are identical.

**Claude Desktop regular chat:** Settings → Desktop app → Manage Extensions → Advanced settings → Install Extension, select `ORBIT-Claude-Desktop-v0.23.0.mcpb`. Ensure Python is available, then verify the local connector via the **+ → Connectors** control. This **only** provides MCP memory/task tools, not code editing or native delegation in regular chat. Do not install both the MCPB and the project `.mcp.json` as separate competing tool sources in one session unless you understand the host's duplicate handling.

## Acceptance test

Open [TODO-LAB-TEST.md](TODO-LAB-TEST.md). Build the Todo app *from the Orbit prompt*, not by copying a prebuilt project. Verify the separate planning/agent/MCP behavior; a completed UI alone does not prove Orbit or subagents worked.

## Boundaries

- This installer has been locally tested; it has **not** been tested in your live Codex, Antigravity, Claude Code, or Claude Desktop installation.
- Local MCP is shared only when all clients run on the **same computer and OS user account** and access the same database path. It is not cloud synchronization. Concurrent SQLite writes have busy-timeouts; the task reservation ledger coordinates cooperative agents, not malicious actors or filesystem access.
- The local MCP doesn't spawn agents, run tests, inspect full code diffs, or claim independent evidence. The host executes and verifies work.
- The Antigravity v0.21 installer is **not** a universal installer. Use this new v0.22 bundle for a fresh test project. Upgrades of existing customized v0.21 workspaces require a manual review; do not blindly overwrite them.
- Python interpreter paths in the generated MCP config are machine-specific; moving your project to another computer requires reconfiguration.

Official references:
- Codex MCP: https://learn.chatgpt.com/docs/extend/mcp
- Codex skills: https://learn.chatgpt.com/docs/build-skills
- Antigravity MCP: https://antigravity.google/docs/mcp
- Antigravity custom subagents: https://antigravity.google/docs/subagents/
- Claude Code MCP: https://code.claude.com/docs/en/mcp
- Claude Code subagents: https://code.claude.com/docs/en/sub-agents
- Claude Desktop MCP extensions: https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop
