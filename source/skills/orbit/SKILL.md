---
name: orbit
description: Run Orbit, the project lead orchestrator, with Antigravity-native frontend/backend and other specialist subagents, local MCP project memory, bounded plans, and verified checkpoints. Use for planning, building, debugging, reviewing, and resuming software projects.
---
# Orbit orchestration in Antigravity desktop

Apply the `orbit` lead agent in `.agents/agents/orbit.md` and the specialist definitions under `.agents/agents/`. **The active Antigravity model is the reasoning engine.** Do not start Gemini CLI, Claude Code, or Codex CLI for Orbit.

- On start/resume, read current project instructions and canonical docs, check Git state, and use `orbit_project_resume` from `orbit-core-native` MCP when connected.
- Plan milestone → gate → executable steps, including frontend, backend, data, security, tests, CI/CD and deployment when applicable. Detail the nearest milestone and avoid overengineering.
- Delegate with host-native `invoke_subagent` only if genuinely available and authorized. Before dispatch, preview/register a stable scoped task (`orbit_task_plan`) and reserve a slot (`orbit_task_reserve`) using the real user/host approval; after successful native invocation record its real session reference (`orbit_task_started`). Release failed reservations. This MCP never launches an agent or runs a model. The orchestrator owns task selection, dependencies, file boundaries, review, and next steps; child agents never self-authorize more spawning.
- Prefer isolated branches/worktrees for simultaneous code changes if the host supports them. Otherwise do tasks serially. Never edit overlapping files concurrently.
- Agents return verifiable diffs, tests, status and blockers; Orbit checks the actual diff and tests, then records task outcome (`orbit_task_report`) and separately reviewed acceptance (`orbit_task_review`) before dependent tasks. Neither reported evidence nor task review is independently attested by MCP.
- Save checkpoint to `.orbit/STATE.md` through `orbit_project_checkpoint` with fresh revision and explicit approved `confirm_write`. Preserve existing user documents/ADRs and do not duplicate source of truth.
- Memory is SQLite local only when MCP connected. No remote API, paid model, automatic agent process, cloud sync, or user data export is implied by skill installation.

Read `references/TASK-LIFECYCLE.md` for the native agent ledger workflow and `references/HANDOFF.md` for a bounded handoff. Apply only when delegation is actually needed.

## Local application preview (v0.24 feature candidate)

For a new app, after approved implementation, inspect the actual package scripts, plan tests, and prefer the existing IDE browser. To preview the running app, call `orbit_preview_start` with `confirm_run: false` to show the **exact** shell-free argv and loopback URL. Re-run with `confirm_run: true` only after actual user/host permission to execute that project's code; use `orbit_preview_status` and inspect readiness and logs. Open the returned `http://127.0.0.1:<port>/` using an available host browser. Run real user interaction tests through the host browser or Playwright only when installed and permitted. Do not equate HTTP 200 with UI test success. Use `orbit_preview_stop` with `confirm_stop: true` to shut down the locally managed process when finished.

No cloud deployment, public tunnel, remote sharing, third-party auto-install, or background AI agent execution is included in these MCP tools. The preview's process tracking lives only in the active MCP process; after a host/MCP restart it cannot safely adopt or stop previously spawned processes.
