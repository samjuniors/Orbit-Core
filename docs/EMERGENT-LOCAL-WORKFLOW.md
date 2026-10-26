# Orbit one-prompt local app testing — v0.24 candidate

## What is implemented
- Project/task scoped SQLite memory, capability discovery, delegation bookkeeping, review and checkpoints.
- Local preview start/status/stop, no deployment or public tunnel.
- Actual Chromium Playwright browser QA (optional installed dependency) against active Orbit-owned loopback preview, with bounded click/fill/press/expect actions, desktop/mobile screenshots, errors and remote-network blocking.
- Durable SQLite build-stage ledger. The **host** (Antigravity, Codex or Claude Code) must execute model decisions, coding, browser/terminal work and repairs. Orbit MCP does **not** spawn the model or run autonomously after the host closes.

## Installation
Run `python installer.py --scope machine` to preview a cross-host setup, followed by `python installer.py --scope machine --install` only after reviewing paths. On Windows use `install_orbit_gui.pyw`. For a single project use `--scope project --project ABSOLUTE_PATH`. Existing unrelated configs are preserved; owner customization conflicts halt.

Browser QA needs separate approved installation if not already present: Python `playwright` plus compatible Chromium. No dependency is installed automatically. The host may alternatively use its own browser, but Orbit's SQLite BROWSER_QA gate cannot claim PASS from a host-only screenshot.

## Todo acceptance run
1. Create an empty `orbit-todo-lab` folder and open it in a single host. Prompt: “Orbit, build a local full-stack Todo app with create/edit/complete/delete/filter, persistent data, accessible and responsive UI, API checks, test commands, and a verified local preview. No cloud deployment. Use approved native subagents when available, otherwise implement sequentially. Track steps and get permission before running project code or browser interactions.”
2. Verify 24 Orbit MCP tools, including `orbit_build_begin/status/advance` and `orbit_browser_qa`. Record real project root and same stable project slug across hosts.
3. Check planning includes API contract, frontend/backend file ownership, acceptance criteria, scope and no unwanted network dependency.
4. Confirm actual native subagent sessions in host UI before describing parallel execution; task ledger reservation alone does not spawn anyone.
5. Require functional tests with commands and exit codes. Compare diffs and review specialist results.
6. Preview startup should first be PREVIEW_ONLY; approve separately, then require actual READY and a localhost link. For a React/Vite app e.g. `http://127.0.0.1:5173/`, but verify the actual port; this is not a public link.
7. `orbit_browser_qa` initially previews intended DOM actions; after approval it opens real Chromium, clicks/adds Todos and checks DOM text/count, captures private mobile/desktop screenshots and console errors; errors must be repaired and retested. If Chromium cannot be launched, report missing dependency/HOLD, not a PASS.
8. Save an Orbit-managed checkpoint (`orbit_project_checkpoint`) after fresh revision approval, advance build ledger only after the checkpoint exists. Close host, reopen the exact same project and use `orbit_build_status` and `orbit_project_resume` to verify durable stage/memory. Running preview process itself is NOT safely adopted across MCP restarts; close it before host restart.
9. In a second supported host, connect same Orbit DB and project path, retrieve the same build and memory. Confirm no automatic deployments, remote URLs, or Git pushes.

## Approval and stop rules
- `confirm_run` / `confirm_interactions` / `confirm_write` are caller flags, **not** independently authenticated approvals. A host/user permission system must enforce approval.
- Executing project commands can execute arbitrary project code even with shell=False; don't use untrusted repos or elevated OS privileges.
- Browser QA may mutate *local app data* and screenshots may contain private content; it stores private files outside Git and blocks non-loopback browser requests.
- Built-in host agent controls, not Orbit SQLite, own process/model permissions. Preview processes are in-memory MCP-session-managed; SQLite build checkpoints survive MCP restarts.
