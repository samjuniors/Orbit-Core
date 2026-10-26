# ORBIT Core MCP — universal local agent orchestration

**Development candidate: v0.24.0 (full testable local workflow)** · Python 3.10+ · local-first · no deployment required

This is the **standalone local MCP + cross-host installer** for the independent Orbit Workspace Orchestrator plugin. It contains the Python stdio MCP runtime, SQLite memory and task ledger, capability discovery, and host-specific agent/skill adapters for Antigravity, Codex, and Claude Code. The host AI/IDE—not this MCP—performs native model inference, subagent spawning, and code editing.

This repository is intentionally **not** the separate `samjuniors/orbit` coding-agent CLI product and must not be merged into that source without a deliberate cross-product migration.

## Install

For Windows, download a tagged release ZIP, extract to a permanent folder, and double-click `install_orbit_gui.pyw` (requires Python 3.10+ with Tkinter and `.pyw` association). Select **This computer** or **One specific project**; review the actual paths before confirming. No third-party skills, remote servers, cloud keys, or arbitrary code are installed automatically.

On macOS/Linux, run the installer preview and then an approved installation:

```bash
python3 installer.py --scope machine
python3 installer.py --scope machine --install
```

For a project-specific installation see [original installation guide](docs/INSTALLATION-ORIGINAL.md). Claude Desktop standard chat requires the separately packaged `.mcpb` desktop extension; it does not provide native coding-agent delegation.

## Repository layout

- `source/runtime/orbit_mcp.py`: JSON-RPC stdio MCP server, 24 tools at v0.24.0.
- `source/runtime/orbit_tasks.py`: SQLite project task ledger and policies.
- `source/runtime/orbit_capabilities.py`: read-only skills/MCP discovery and selection.
- `source/agents/`, `source/skills/`: host-adapted Orbit lead/specialist instructions.
- `installer.py`, `install_orbit_gui.pyw`: preview-first global/project installation.
- `tests/`: local unit and protocol tests.
- `docs/`: architecture, release, security and installation guidance.
- `.github/workflows/ci.yml`: automated GitHub tests and release-package verification.

## Development

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_version.py
python3 scripts/build_release.py
```

Run tests on a disposable checkout first. The test suite uses temporary directories. Never store SQLite memory databases, user-specific MCP configuration, credentials or transcripts in Git.

## Versioning and release policy

SemVer `MAJOR.MINOR.PATCH`, with `VERSION`, `installer.py`, `source/runtime/orbit_mcp.py` and release manifest aligned. The existing downloadable v0.23.0 ZIP is a preserved historical artifact, not a guarantee of production readiness. Each new change starts on a feature branch, is reviewed through a PR, must pass CI, and is tagged only after verification.

See [GitHub publication guide](docs/GITHUB-SETUP.md), [release policy](docs/RELEASE-PROCESS.md), [architecture](docs/ARCHITECTURE.md), and [changelog](CHANGELOG.md).

## Current limits

`orbit_capability_select` does **not** download or install new skills; native delegation requires actual host support and user-approved execution; the SQLite ledger alone does not enforce filesystem permissions. Host-specific integration and cloud-free shared public preview URLs are not yet end-to-end verified. The v0.24 preview manager runs only localhost dev servers with explicit permission and checks their HTTP readiness; native browser QA, persistent cross-session stop/control and remote sharing are still planned, not shipped.

Private source by default; no OSS license granted or implied.

## Local app preview (feature-branch v0.24.0)

Use `orbit_preview_start` with a project root, preview ID, shell-free `command` array, localhost `port` and optional health path. Omitting `confirm_run` previews the proposed execution without running anything. The host must show the command and obtain approval before sending `confirm_run: true`. Use `orbit_preview_status` for HTTP readiness/logs, and `orbit_preview_stop` with `confirm_stop: true` to stop a process **within the same active MCP session**. For Vite, a sample approved command is `npm run dev -- --host 127.0.0.1 --port 5173`. No public URL, browser visual tests or deployment are claimed. See `docs/LOCAL-PREVIEW.md`.

## Test local app-building workflow
See [end-to-end acceptance run](docs/EMERGENT-LOCAL-WORKFLOW.md). The installed Playwright library + Chromium can perform bounded mobile/desktop browser checks and store private evidence; an IDE host must execute actual code-writing agents. SQLite build-stage state resumes after host restart; local preview processes themselves do not auto-reconnect. No cloud deployment or public sharing is provided.

### Browser QA on Windows without downloading Chromium

The optional Python Playwright library must be installed in the **same Python
interpreter** used by the Orbit MCP server. The browser tool now supports
`browser: "auto"` (prefers installed Microsoft Edge/Chrome), `"msedge"`,
`"chrome"`, and `"chromium"`. Existing Edge/Chrome can be controlled without
installing a separate Chromium browser binary. See
[`docs/EMERGENT-LOCAL-WORKFLOW.md`](docs/EMERGENT-LOCAL-WORKFLOW.md) for the
explicit installation smoke test and the Antigravity-specific driver 404 warning.

## Optional Vercel Labs agent-browser MCP

Orbit can discover a separately configured `agent-browser` MCP provider and recommend
it for screenshot-driven, accessibility-tree browser testing through the host. It
is **not bundled or auto-installed**. This provider does not replace the
Orbit-owned Playwright QA gate in v0.24.0; host reports remain supplemental
until an independently verified adapter is implemented. See
[`docs/AGENT-BROWSER-OPTIONAL.md`](docs/AGENT-BROWSER-OPTIONAL.md).

## Guided intake, right-sized documentation and compact context (development candidate)

For new products, Orbit now guides the host to classify project type/complexity/maturity, interview the user with recommended options **before** stack selection, and map existing canonical docs before making a plan. It instructs an actual writer/architect host agent—or the lead sequentially—to create necessary product-appropriate vision, architecture, roadmap and design documentation. Installed host skills now carry the reference policies; source-only reference files were previously omitted by the installer. The host model compacts the agreed intent into a small brief and sends targeted context, not repeated transcripts. **This is host instruction guidance, not a new enforced MCP intake stage**. See [project discovery](docs/PROJECT-DISCOVERY.md).

## Persistent guided intake (development branch)

New Orbit MCP projects must obtain an approved product classification and user answers before `orbit_build_begin` creates a build; a fresh build otherwise returns HOLD. Five additional tools expose intake status, proposals, approved choices, autonomy review and repeatable documentation gap audits (29 total). Existing builds such as a prior Todo test are not retroactively blocked. Host-owned architect/writer agents create substantive missing docs only after reviewing owner canonical sources. No automated autonomy escalation or approval bypass is offered.
