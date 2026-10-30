# Orbit Core v0.26.0 — one package, multiple native hosts

**Implementation status:** source candidate; not a published release. The plugin suite and compact Windows setup are in development. Host-native plugin installation and full permission/rollback acceptance are not yet complete.

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

Double-click `Orbit Setup.cmd`: select this computer or one project, view detected Antigravity/Codex/Claude Code/VS Code hosts, then **Install**, **Update** or **Uninstall**. The compact UI uses the existing **preview-first direct host integration backend**; it is not yet a one-click native plugin marketplace installer.

- **Install** enables only when the selected local source integration is missing.
- **Update** enables when the bundled source would change the selected integration. This is **not** a claim that an online release exists; no update downloads are silently performed.
- **Uninstall** offers *preserve memory (recommended)* and *clean reset*, with explicit memory deletion and typed confirmation for clean reset.
- Every action previews affected files and asks for user confirmation. Modified user files, unknown host configurations and recorded memory are preserved or blocked by existing safety guards. A success dialog appears only after the installer returns successfully.

The existing detailed setup GUI remains available as `install_orbit_gui.pyw` for compatibility while the new compact window is verified.

## Remaining release acceptance

Complete actual signed-in host plugin installation/enable, selectable main-agent and delegation tests, MCP tool discovery and path expansion, denial/cancel permissions, installed-version upgrade and rollback with custom files, two-PC portability, independent security review, and owner approval before publishing v0.26.0. The last published version stays v0.25.1.

References: [Antigravity Plugins](https://antigravity.google/docs/plugins), [Codex portable plugins](https://developers.openai.com/plugins/build/plugins), [Claude Code plugins](https://code.claude.com/docs/en/plugins-reference), [DeepSeek Harness architecture](https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/architecture.md).
