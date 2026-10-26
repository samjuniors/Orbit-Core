# ORBIT Core MCP — universal local agent orchestration

**Baseline: v0.23.0** · Python 3.10+ · local-first · no deployment required

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

- `source/runtime/orbit_mcp.py`: JSON-RPC stdio MCP server, 17 tools at v0.23.0.
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

`orbit_capability_select` does **not** download or install new skills; native delegation requires actual host support and user-approved execution; the SQLite ledger alone does not enforce filesystem permissions. Host-specific integration and cloud-free shared public preview URLs are not yet end-to-end verified. The proposed preview manager and browser QA belong to the **v0.24.0 development plan**, not this baseline.

Private source by default; no OSS license granted or implied.
