# Orbit one-prompt local app testing — v0.24 candidate

## What is implemented
- Project/task scoped SQLite memory, capability discovery, delegation bookkeeping, review and checkpoints.
- Local preview start/status/stop, no deployment or public tunnel.
- Actual Playwright browser QA using an installed Edge/Chrome or Chromium browser (optional Python dependency) against active Orbit-owned loopback preview, with bounded click/fill/press/expect actions, desktop/mobile screenshots, errors and remote-network blocking.
- Durable SQLite build-stage ledger. The **host** (Antigravity, Codex or Claude Code) must execute model decisions, coding, browser/terminal work and repairs. Orbit MCP does **not** spawn the model or run autonomously after the host closes.

## Installation
Run `python installer.py --scope machine` to preview a cross-host setup, followed by `python installer.py --scope machine --install` only after reviewing paths. On Windows use `install_orbit_gui.pyw`. For a single project use `--scope project --project ABSOLUTE_PATH`. Existing unrelated configs are preserved; owner customization conflicts halt.

Browser QA needs separate approved installation if not already present: Python `playwright` inside **the same interpreter used to launch Orbit**. On Windows Orbit now automatically detects installed Microsoft Edge or Chrome, so a second Chromium download is unnecessary. No dependency is installed automatically. The host may alternatively use its own browser, but Orbit's SQLite BROWSER_QA gate cannot claim PASS from a host-only screenshot.

## Todo acceptance run
1. Create an empty `orbit-todo-lab` folder and open it in a single host. Prompt: “Orbit, build a local full-stack Todo app with create/edit/complete/delete/filter, persistent data, accessible and responsive UI, API checks, test commands, and a verified local preview. No cloud deployment. Use approved native subagents when available, otherwise implement sequentially. Track steps and get permission before running project code or browser interactions.”
2. Verify 24 Orbit MCP tools, including `orbit_build_begin/status/advance` and `orbit_browser_qa`. Record real project root and same stable project slug across hosts.
3. Check planning includes API contract, frontend/backend file ownership, acceptance criteria, scope and no unwanted network dependency.
4. Confirm actual native subagent sessions in host UI before describing parallel execution; task ledger reservation alone does not spawn anyone.
5. Require functional tests with commands and exit codes. Compare diffs and review specialist results.
6. Preview startup should first be PREVIEW_ONLY; approve separately, then require actual READY and a localhost link. For a React/Vite app e.g. `http://127.0.0.1:5173/`, but verify the actual port; this is not a public link.
7. `orbit_browser_qa` initially previews intended DOM actions; after approval it opens an installed Edge/Chrome or Chromium browser, clicks/adds Todos and checks DOM text/count, captures private mobile/desktop screenshots and console errors; errors must be repaired and retested. If the browser cannot be launched, report DEPENDENCY_MISSING or FAIL/HOLD, not a PASS.
8. Save an Orbit-managed checkpoint (`orbit_project_checkpoint`) after fresh revision approval, advance build ledger only after the checkpoint exists. Close host, reopen the exact same project and use `orbit_build_status` and `orbit_project_resume` to verify durable stage/memory. Running preview process itself is NOT safely adopted across MCP restarts; close it before host restart.
9. In a second supported host, connect same Orbit DB and project path, retrieve the same build and memory. Confirm no automatic deployments, remote URLs, or Git pushes.

## Approval and stop rules
- `confirm_run` / `confirm_interactions` / `confirm_write` are caller flags, **not** independently authenticated approvals. A host/user permission system must enforce approval.
- Executing project commands can execute arbitrary project code even with shell=False; don't use untrusted repos or elevated OS privileges.
- Browser QA may mutate *local app data* and screenshots may contain private content; it stores private files outside Git and blocks non-loopback browser requests.
- Built-in host agent controls, not Orbit SQLite, own process/model permissions. Preview processes are in-memory MCP-session-managed; SQLite build checkpoints survive MCP restarts.

## Windows browser QA recovery (Antigravity 1.57.0 driver 404)
The Antigravity built-in `browser_subagent` and Orbit's `orbit_browser_qa` are independent.
A host browser driver CDN 404 does not mean the local preview has failed. Orbit's
v0.24 candidate supports `browser: "auto"` (installed Microsoft Edge then Chrome,
then existing Chromium) or an explicit `"msedge"`, `"chrome"`, or `"chromium"`.

Install trusted Python Playwright only after approval, **with the interpreter
from your `orbit-core-native` MCP configuration**. On this test machine it is:

```powershell
$py = 'C:\Users\User_S\AppData\Local\Python\pythoncore-3.15-64\python.exe'
& $py -m pip install --user playwright
& $py -c "from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(channel='msedge',headless=True); print(b.version); b.close(); p.stop()"
```

Do not run `playwright install chromium` when Edge is present and the explicit
Edge smoke test passes. Do not populate Antigravity's internal driver cache from
unverified third-party scripts. Restart the host after updating Orbit; start an
approved Orbit-owned preview in the new MCP session, then re-run `orbit_browser_qa`
with `browser:"msedge"`. The SQLite build gate stays BLOCKED until a real PASS.

## Optional agent-browser MCP provider

If the host has connected the official Vercel Labs `agent-browser` MCP, Orbit's
`orbit_capability_select` can recognize the configured provider and any
host-reported `agent_browser_*` tool names. Verify the actual tool executes
before treating it as operational. Native browser snapshots and screenshots
are useful for UI review, but the current Orbit BROWSER_QA stage is not a
self-attested status: only a recorded PASS from `orbit_browser_qa` advances
it. Do not mark `build-001` complete using an external tool's unverified report.
Full safety and opt-in configuration: [`AGENT-BROWSER-OPTIONAL.md`](AGENT-BROWSER-OPTIONAL.md).

## Fresh project intake and documentation acceptance

Before a **new** build, the host must follow `references/PROJECT-INTAKE.md` and `references/DOCS-AND-CONTEXT.md`: audit existing sources, classify product type and maturity, present meaningful recommended choices, obtain user-selected or expressly delegated defaults, then establish an agreed brief and only the missing useful canonical vision/architecture/roadmap/design docs. Do not silently choose a stack and jump to coding. On an **existing build** such as `build-001`, resume accepted decisions and checkpoints instead of imposing a new interview. This remains a host instruction policy rather than a new SQLite build gate. See `docs/PROJECT-DISCOVERY.md`.
