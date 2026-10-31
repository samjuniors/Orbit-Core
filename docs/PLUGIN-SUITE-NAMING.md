# Orbit Core v0.26.0 — one package, multiple native hosts

**Publication status:** v0.26.0 is a [published GitHub prerelease](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.26.0). This specification describes the shipped 42-tool package; authentic host-native plugin activation, IDE permission UI, installed-user rollback and independent security certification remain **NOT VERIFIED**. Publication does not imply production certification.

## Naming and identity contract

| Kind | Canonical packaged name | Role |
| --- | --- | --- |
| Product / package | `orbit-core` | One product and shared code |
| Lead agent | `orbit-lead-agent` | Selectable main agent on Antigravity; host-provided main session elsewhere |
| Specialist agent | `orbit-qa-agent`, `orbit-writer-agent` etc. | Twelve scoped roles |
| Skill | `orbit-workflow-skill` | On-demand workflows and reference docs |
| Local MCP | `orbit-core-mcp` | 42 local tools, project SQLite and checkpoints |

Legacy identifiers such as `orbit-core-native`, `orbit` and `orbit-qa` remain recognized by existing installations. The new package must not activate duplicate old and new registrations.

## One downloadable ZIP, separate adapters

`Orbit-Core-Plugin-Suite-v0.26.0.zip` contains:

- `antigravity/orbit-core/` — native `plugin.json`, `mcp_config.json`, lead agent, 12 specialists, skill and runtime.
- `codex/orbit-core/` — portable `plugin.json`, `mcp.json`, skill and runtime. Its top-level host session serves as lead; no claim that Antigravity-style agent frontmatter is understood.
- `claude-code/orbit-core/` — `.claude-plugin/plugin.json`, `.mcp.json`, skill, 12 host-adapted specialists and runtime. The main session still belongs to Claude Code.

The shared code, versions and skill come from the existing Orbit source, with thin host-specific manifests. Different formats mean one user download **does not mean** a single manifest is universally understood.

**DeepSeek Harness is not yet supported.** It uses Cordis plugins and `dsh.bundle` npm packages, which need an independently researched and tested adapter. Do not install the suite into DeepSeek Harness as if it were an Agent Plugins package.

No remote/cloud server is required for locally supported MCP stdio. The host starts the included Python subprocess, using the existing Orbit default SQLite path unless an approved override is preserved.

## Windows compact setup

Double-click `Orbit Setup.cmd` to open the **minimal setup view (504 × 350 pixels)**. The default screen displays Orbit Core, detected coding apps, a short installation status and **one context-aware primary button**. No separate Install/Update tabs or detailed file lists occupy the main window.

- **Install Orbit** appears for a new local integration. **Update Orbit** appears when the selected bundled source differs from a recognized existing installation. **You're up to date** is disabled when no changes are needed. **Review setup** appears for customized or conflicting files; technical error messages remain in the detailed review rather than the default view.
- The small **More options** disclosure expands the window (approximately 504 × 590 pixels) to reveal coding-host checkboxes, machine vs. one-project installation, folder selection, rediscovery and an optional **Uninstall** flow. These options collapse completely when not needed.
- **Uninstall** preserves memory and checkpoints by default. A separate **Clean reset** offers optional memory deletion and requires typing `REMOVE ORBIT`. No destructive operation is executed from a normal Install/Update click.
- The primary action opens a compact confirmation dialog with a short summary. Full file-by-file changes are behind **View file details**; nothing is written before explicit confirmation. Existing safe backup and revalidation logic stays in force.
- This is a **bundled local source** update indicator, **not** an unverified online-update claim. The compact window uses the existing preview-first host integration backend, not yet one-click native plugin marketplace activation. No Python dependency outside the standard Tkinter stack has been introduced.

The design uses a dark, high-contrast style with a vector-drawn Orbit mark and rounded keyboard-accessible primary control. Real Windows Tkinter open/expand/collapse checks are required before declaring the published prerelease production-ready.

The existing detailed setup GUI remains available as `install_orbit_gui.pyw` for compatibility while the new compact window is verified.

## Remaining release acceptance

Complete actual signed-in host plugin installation/enable, selectable main-agent and delegation tests, MCP tool discovery and path expansion, denial/cancel permissions, installed-version upgrade and rollback with custom files, two-PC portability, independent security review, and owner approval before publishing v0.26.0. The last published version stays v0.25.1.

References: [Antigravity Plugins](https://antigravity.google/docs/plugins), [Codex portable plugins](https://developers.openai.com/plugins/build/plugins), [Claude Code plugins](https://code.claude.com/docs/en/plugins-reference), [DeepSeek Harness architecture](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md).
