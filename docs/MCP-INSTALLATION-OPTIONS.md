# MCP and agent installation options (published local releases)

Orbit is a **local stdio MCP server plus optional host-specific skills and agent instructions**. It is not a cloud MCP service, self-running model, or an automatic marketplace listing. The coding host owns execution and native agent support.

## What mainstream hosts do

| Host | Native supported connection | Orbit option |
| --- | --- | --- |
| Google Antigravity IDE/CLI | MCP Store or global `~/.gemini/config/mcp_config.json` / project `.agents/mcp_config.json` | Installer merges `orbit-core-native`; refresh host and call a read-only tool |
| OpenAI Codex CLI/Desktop | `codex mcp add` or `~/.codex/config.toml` / project `.codex/config.toml` | Installer writes scoped native TOML, an Orbit skill and host guidance |
| Anthropic Claude Code | `claude mcp add` or scoped MCP configuration, plus `.claude/skills` and agents | Installer preserves existing entries and installs local Orbit skill/agent definitions |
| Visual Studio Code Copilot | MCP: Add Server / manifest, or `.vscode/mcp.json` with `servers` | Optional VS Code target, separate format and preservation of unrelated servers |
| Claude Desktop (regular chat) | Desktop extension packaging | Separate versioned `ORBIT-Claude-Desktop-vX.Y.Z.mcpb`, not native coding subagents |

Official references: https://antigravity.google/docs/mcp ; https://code.visualstudio.com/docs/agents/reference/mcp-configuration ; https://developers.openai.com/resources/docs-mcp ; https://support.claude.com/en/articles/14554922-claude-code-user-faq

## Orbit installer and detection

For a first install, use the **published Universal Setup ZIP** and double-click `Orbit Setup.cmd` on Windows (or invoke `python3 orbit_setup.py install --scope machine --hosts antigravity codex` from the extracted ZIP). Preview exact changes before adding `--apply`. The GUI checks host executables and configuration files **without launching a coding host**; its suggested host selection can be overridden. For one existing project choose `--scope project --project ABSOLUTE_PATH`. `installer.py` is a lower-level maintainer entry point, not the recommended new-user setup. A configuration file does **not** prove MCP connection; restart the selected host and execute a real read-only `orbit_project_scan` call. The installer does not grant host permissions.

Avoid installing additional marketplaces, agent CLIs, downloadable MCP servers or browser dependencies without purpose, provenance/security review and user approval. Existing OAuth credentials, account settings and unrelated MCP definitions are never migrated into Orbit.

## Persistent, published-release-aware update command

On Windows, the new installer writes `%USERPROFILE%\.orbit-universal\bin\orbit.cmd` plus a Python administration script. It does not modify user PATH automatically. Run from PowerShell:

```powershell
& "$HOME\.orbit-universal\bin\orbit.cmd" detect
& "$HOME\.orbit-universal\bin\orbit.cmd" status
& "$HOME\.orbit-universal\bin\orbit.cmd" update --channel stable --check
& "$HOME\.orbit-universal\bin\orbit.cmd" update --channel stable --hosts antigravity codex
& "$HOME\.orbit-universal\bin\orbit.cmd" update --channel stable --hosts antigravity codex --apply

# Opt in to published prereleases instead:
& "$HOME\.orbit-universal\bin\orbit.cmd" update --channel candidate --check
& "$HOME\.orbit-universal\bin\orbit.cmd" update --channel candidate --hosts antigravity codex --apply
```

`update` defaults to **official published stable releases**; `--channel candidate` opts into **published prereleases**, not branch snapshots. It validates the release ZIP SHA256 against its release sidecar and refuses unsafe archive paths and symlinks. A normal no-`--apply` update is a verified package preview, **not** the full per-file plan; to inspect that exact plan without writes, extract the verified ZIP and run `orbit_setup.py update` without `--apply`. An approved `--apply` runs the verified published installer, uses backup/customization guards and preserves other MCP entries. An offline local `--from-zip` requires a separately trusted `--sha256`; no floating source checkout is an authorized published update.

`orbit` alone works only if the bin directory is separately added to the user's PATH, which Orbit deliberately does not do without permission.

## Agent packaging distinction

MCP **tools** are registered through the host's MCP mechanism. Specialist **agents/skills** are separate files and must follow each host's supported conventions. Orbit installs only its own bundled, reviewed skill and agent templates. Tool visibility is not proof a specialist session started. Native subagent delegation must be actually available and separately verified inside the host.

## Project lifecycle

For a *new* project, the MCP's intake gate requires a proposed interview, user-accepted options (or explicitly delegated defaults), then a build plan. Reassess documentation using `orbit_docs_audit` after new features, APIs, data, security, releases, or architecture growth; this tool only identifies likely gaps and never overwrites owner documents. Approval of `guided`, `assisted`, or `trusted` mode is always explicit. No level waives high-risk host approvals.

**Status:** Core installation options ship in the [published Orbit 0.x prereleases](https://github.com/samjuniors/Orbit-Core/releases); native host permissions and plugin activation still require real-host checks. These packages are not stable-production certifications.


## Fastest verified user path

Download a published Universal Setup ZIP with its matching SHA256 **once**, preview/install selected host integrations, and thereafter use the Windows **Orbit Update Manager** from `%USERPROFILE%\.orbit-universal\bin\Orbit Update Manager.cmd` or the per-user `orbit.cmd` launcher. The CLI **defaults to stable**, while `--channel candidate` opts into published prereleases. A newer installed candidate is not silently downgraded to an older stable version. A first-time v0.31.0 prerelease install can be pinned with `--channel candidate --version 0.31.0` (see [release quick start](RELEASE-QUICKSTART.md)); do not claim it is installed merely because the setup wrote config files. No repeated ZIP download is needed for normal later updates; customized files require review. Development-branch ZIPs are **not** published release assets or independently signed distributions.
