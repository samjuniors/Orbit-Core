# Orbit Core — preferred coordinator alongside other installed plugins

**Status:** Proposed v0.31 development behavior. Not shipped in published v0.30.0.

## Product decision

Orbit should be the **preferred coordinator for the software-project lifecycle** when the user selects Orbit: plan, implement, debug, add features, review, checkpoint, pause and resume. Existing specialist tools should remain available. For example, Orbit tracks tasks and evidence while an approved GitHub, browser, search, testing or deployment MCP performs its own specialty.

This is *not* global prompt dominance, an exclusive agent shell, or an automatic rule to invoke Orbit for unrelated questions. A user's explicit selection of another agent/tool, host instructions and permission controls are higher priority than Orbit's preference. Orbit does not replace the host's model or native subagents.

## Why global "always first" is not technically guaranteed

Skills are selected dynamically based on their descriptions and task context. MCP tools compete for model selection where the host exposes them. Host-specific instructions may be combined at different scopes, and a third-party plugin cannot universally set its own precedence across Antigravity, Codex, Claude Code and VS Code. Only the host/user can select the active custom agent or change tool availability. Do not claim that a config file proves an active MCP session.

Host documentation:
- [Google Antigravity skill activation](https://codelabs.developers.google.com/getting-started-google-antigravity)
- [Codex AGENTS.md](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide)
- [VS Code instruction precedence](https://code.visualstudio.com/docs/agents/reference/custom-instructions-reference)
- [VS Code tool selection and controls](https://code.visualstudio.com/docs/agents/concepts/tools)

## Proposed v0.31 behavior

1. The Orbit skill and host guidance describe Orbit as the preferred project coordinator for the owner's selected workflow. Keep instructions concise; let hosts load them normally.
2. A **read-only conflict inventory** checks only recognized MCP server names in known user/project host configs and checks duplicate Orbit skill locations. It never scans plugin code, imports a plugin, reads arbitrary skill instructions, or contacts any third-party service.
3. Report explicit Orbit configuration at user/project scope, duplicate names, possible Orbit aliases and possible orchestration-role names. Name-only similarity is *not* proof of duplicate behavior or host activation.
4. In installer preview, warn about potential overlaps. Preserve all other integrations and custom files; don't install hooks that intercept every tool call or silently disable competing plugins.
5. For a confirmed Orbit project workflow, start with Orbit's project resume/intake/ledger and use task-appropriate specialist capabilities under their actual permissions. When Orbit is unavailable, disclose that and continue only within authorized host capabilities.
6. If both an unrelated orchestration plugin and Orbit are present, the explicit user choice decides which leads; an absent choice is not blanket permission to supersede the other plugin.

## Read-only diagnostic (future version)

From a future published Universal Setup ZIP:

```powershell
py -3.12 orbit_priority.py --hosts antigravity codex
py -3.12 orbit_priority.py --project "C:\\your\\project" --hosts antigravity codex
```

The diagnostic returns `priority_enforced: false`, `host_connection_verified: false` and `configuration_modified: false` by design. `NO_OBVIOUS_NAME_COLLISION` means only that the known names do not suggest a collision. The tool cannot prove that an arbitrary installed plugin is functionally similar.

Manual activation is explicit: select Orbit's lead agent/skill in a host that supports it, or ask the host to use its connected `orbit-core-native` MCP tools for an Orbit project. Do not create or overwrite an existing `AGENTS.md`, `CLAUDE.md` or global host policy just to elevate Orbit.

## Acceptance criteria

- Exact selected host/project scope only; duplicate user/project Orbit registrations and skill shadows are labeled as possible conflicts.
- Existing MCP and plugin configurations, credentials and owner instructions remain byte-identical during an audit.
- Malformed/oversized/symlink config is not trusted; show an incomplete-review warning.
- No uninstall, mutation, auto-activation, extra agent spawn or model/provider switching occurs.
- Actual host skill selection and MCP tool invocation must be separately verified after installation; CI alone is insufficient.
- Rollback uses previously published versions and preserved backups; no silent data downgrade.
