# Antigravity native plugin — v0.26.0 development candidate

**Status:** source implementation and disposable verification only. This is **NOT** a published release or production-certified installer. Existing v0.25.1 installations remain supported. [Product integration research](https://app.notion.com/p/4074f681d488816e9fe7f4504982c948) · [Release gates](RELEASE-ACCEPTANCE-v0.26.0.md)

## What the package provides

A single `orbit-core` Antigravity plugin contains:

- The selectable Orbit lead agent (`mainAgent: true`, `subagent: false`) and 12 explicitly subagent-only specialist profiles.
- A compact `orbit` skill and all original workflow references, loaded on demand rather than injecting an oversized prompt.
- The canonical local Python Orbit stdio MCP runtime (42 development tools) in `runtime/`; `mcp_config.json` registers it as `orbit-core-plugin`.
- **No cloud MCP endpoint, always-on service, downloaded Python runtime, hooks, third-party model or user data.** The host starts the Python process as needed. A supported Python installation must be available on PATH.
- The packaged main-agent references are rewritten for plugin-local skill and server names; canonical standalone agent files remain unchanged.

`python scripts/build_release.py --verify` creates `dist/Orbit-Antigravity-Plugin-v0.26.0.zip` and its SHA256 sidecar alongside the universal setup ZIP and Claude Desktop MCPB. The standalone command `python scripts/build_antigravity_plugin.py` also creates a new versioned plugin ZIP, but **refuses to overwrite an existing one**; the release builder verifies existing content rather than silently replacing it.

## Safety preflight — essential for existing Orbit users

Before installing or enabling the plugin, run:

```powershell
python scripts/preview_antigravity_plugin.py
```

This command **only reads** `~/.gemini/config/mcp_config.json` and the known global Orbit agent/skill paths. A safe new profile reports `safe_to_install_now: true`.

If `legacy_mcp`, `global_agents`, `global_orbit_skill` or `additional_orbit_mcp_servers` is present, **stop**. Direct installation would duplicate Orbit tools or selectable agents. Keep the current v0.25.1 working configuration active.

For an explicitly reviewed transition, first **remove/disable any temporary `orbit-m5-test` or other Orbit MCP test entries only with separate authorization**, and verify they are no longer needed. Do not delete databases or checkpoints. Inspect the preflight output and preserve the old config. The optional opt-in migration:

```powershell
python scripts/preview_antigravity_plugin.py --apply --confirm ARCHIVE_LEGACY_ORBIT_AND_KEEP_BACKUPS
```

archives the exact **known** legacy Orbit MCP entry, existing `orbit*.md` specialist profiles, and `skills/orbit` into a dated backup folder under `~/.gemini/config/orbit-core-migration-backups/`. It preserves unrelated MCP entries and refuses unknown Orbit configs, symlinked skill trees, unreviewed additional Orbit servers and unconfirmed calls. **It does not install or enable a plugin.** Custom owner files are kept in the backup, not thrown away. The action changes a host profile and therefore must be approved deliberately and tested in a disposable profile first.

**Rollback:** before restoring, disable/uninstall the newly installed plugin in Antigravity and close the IDE. Read the dated backup, restore the previous MCP JSON/agents/skill without overwriting newer customizations, then restart the IDE. Do not remove the local SQLite database; the bundled stdio runtime uses the *existing Orbit default database path* unless the owner separately sets `ORBIT_LOCAL_DB`. The plugin's `PLUGIN_DATA` path is intentionally not used by default because redirecting to it would silently fork existing Orbit history. Future migration UI should support an explicitly reviewed data-path choice.

## Disposable validation without touching installed integrations

```powershell
python scripts/build_antigravity_plugin.py
# Extract the versioned ZIP into a new temporary folder.
agy plugin validate --strict "PATH_TO_EXTRACTED/orbit-core"
python -m unittest discover -s tests -p test_antigravity_plugin.py -v
```

Strict validation reports the plugin's agents/skills/MCP inventory, not whether a signed-in host can invoke them. Test a disposable project with a separate host profile/workspace before giving the package access to real work. The full release acceptance requires UI selection of Orbit as primary agent, genuine authorized `invoke_subagent`, child lifecycle/permission-denial, native `/browser` routing, 42-tool discovery, reliable SQLite recovery, backups and rollback. **Do not claim these pass based only on validator or unit-test output.**

## Compatibility limits

Host-specific features vary: Antigravity main-agent selectability is not a universal Codex/Claude Code capability. Codex and Claude Code need their own plugin formats and independent acceptance; the existing universal setup and Claude Desktop `.mcpb` remain separate options.

Antigravity subagents inherit parent permissions; calling Orbit's MCP does not grant the ability to spawn native agents. The built-in browser requires `/browser`, and `/boost` and `/teamwork` are optional plan-dependent native features. Unsupported tool identifiers in specialist frontmatter can hang a child, so they require signed-in host acceptance on each supported Antigravity version.

**Releases are owner-approved only after the acceptance checklist is complete.**
