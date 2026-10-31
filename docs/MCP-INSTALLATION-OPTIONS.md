# MCP and agent installation options (Orbit v0.24 development)

Orbit is a **local stdio MCP server plus optional host-specific skills and agent instructions**. It is not a cloud MCP service, self-running model, or an automatic marketplace listing. The coding host owns execution and native agent support.

## What mainstream hosts do

| Host | Native supported connection | Orbit option |
| --- | --- | --- |
| Google Antigravity IDE/CLI | MCP Store or global `~/.gemini/config/mcp_config.json` / project `.agents/mcp_config.json` | Installer merges `orbit-core-native`; refresh host and call a read-only tool |
| OpenAI Codex CLI/Desktop | `codex mcp add` or `~/.codex/config.toml` / project `.codex/config.toml` | Installer writes scoped native TOML, skills and AGENTS.md guidance |
| Anthropic Claude Code | `claude mcp add` or scoped MCP configuration, plus `.claude/skills` and agents | Installer preserves existing entries and installs local Orbit skill/agent definitions |
| Visual Studio Code Copilot | MCP: Add Server / manifest, or `.vscode/mcp.json` with `servers` | Optional VS Code target, separate format and preservation of unrelated servers |
| Claude Desktop (regular chat) | Desktop extension packaging | Separate versioned `ORBIT-Claude-Desktop-vX.Y.Z.mcpb`, not native coding subagents |

Official references: https://antigravity.google/docs/mcp ; https://code.visualstudio.com/docs/agents/reference/mcp-configuration ; https://developers.openai.com/resources/docs-mcp ; https://support.claude.com/en/articles/14554922-claude-code-user-faq

## Orbit installer and detection

The GUI checks existing CLI executables and host configuration files *without launching a coding host*. It selects detected hosts by default, but the user may override. `python installer.py --scope machine --hosts auto` previews detected installation targets. Add `--install` only after checking the changes. For an explicitly chosen host, pass `--hosts antigravity`, `codex`, `claude-code` or `vscode`. For a project-specific install pass `--scope project --project ABSOLUTE_PATH`. A configuration file does **not** prove MCP connection; refresh the host and execute one read-only `orbit_intake_status` or `orbit_capability_discover` call.

Avoid installing additional marketplaces, agent CLIs, downloadable MCP servers or browser dependencies without purpose, provenance/security review and user approval. Existing OAuth credentials, account settings and unrelated MCP definitions are never migrated into Orbit.

## Stable update command

On Windows, the new installer writes `%USERPROFILE%\.orbit-universal\bin\orbit.cmd` plus a Python administration script. It does not modify user PATH automatically. Run from PowerShell:

```powershell
& "$HOME\.orbit-universal\bin\orbit.cmd" detect
& "$HOME\.orbit-universal\bin\orbit.cmd" status
& "$HOME\.orbit-universal\bin\orbit.cmd" update --check
& "$HOME\.orbit-universal\bin\orbit.cmd" update
& "$HOME\.orbit-universal\bin\orbit.cmd" update --apply
```

`update` uses only **official published stable GitHub Releases**, validates the archive SHA256 against the published release sidecar, refuses zip-slip paths and symlinks, shows file changes before applying, backs up old configs and avoids overwriting owner changes. If no stable release exists, it reports that rather than installing an unsigned development branch. Candidate/local updates require an independently trusted ZIP SHA256 and explicit `--from-zip`; no automatic source-code execution from a floating branch.

`orbit` alone works only if the bin directory is separately added to the user's PATH, which Orbit deliberately does not do without permission.

## Agent packaging distinction

MCP **tools** are registered through the host's MCP mechanism. Specialist **agents/skills** are separate files and must follow each host's supported conventions. Orbit installs only its own bundled, reviewed skill and agent templates. Tool visibility is not proof a specialist session started. Native subagent delegation must be actually available and separately verified inside the host.

## Project lifecycle

For a *new* project, the MCP's intake gate requires a proposed interview, user-accepted options (or explicitly delegated defaults), then a build plan. Reassess documentation using `orbit_docs_audit` after new features, APIs, data, security, releases, or architecture growth; this tool only identifies likely gaps and never overwrites owner documents. Approval of `guided`, `assisted`, or `trusted` mode is always explicit. No level waives high-risk host approvals.

**Status:** Core installation options ship in the [published Orbit 0.x prereleases](https://github.com/samjuniors/Orbit-Core-MCP/releases); native host permissions and plugin activation still require real-host checks. These packages are not stable-production certifications.


## Fastest verified user path

Use the published GitHub Release ZIP once, preview and install selected host integrations, then use `orbit doctor` and `orbit update --check` / `orbit update --apply` from the stable per-user launcher. 0.x uses the candidate channel by default; no repeated manual ZIP download is required after this setup. The updater never silently overwrites customized files. Read `README.md` and `RELEASE-QUICKSTART.md` for exact commands. Source branch ZIPs are development snapshots, **not** signed or published release assets.
