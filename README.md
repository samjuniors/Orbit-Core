# Orbit Core MCP

[![CI](https://github.com/samjuniors/Orbit-Core-MCP/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/samjuniors/Orbit-Core-MCP/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/samjuniors/Orbit-Core-MCP?include_prereleases&label=published%20release)](https://github.com/samjuniors/Orbit-Core-MCP/releases)
[![Python](https://img.shields.io/badge/Python-3.10%E2%80%933.13-3776AB)](https://github.com/samjuniors/Orbit-Core-MCP/actions)

**A local-first project orchestrator for AI-assisted software development.**

Orbit connects to the coding environment you already use. It helps turn requirements into an approved plan, coordinate specialist work, track progress, retain concise project context, and resume from the last checkpoint—without replacing your IDE or choosing an external model for you.

**[Get started](#quick-start) · [How it works](#how-it-works) · [Documentation](#documentation) · [Roadmap](docs/NEXT-VERSION.md) · [Releases](https://github.com/samjuniors/Orbit-Core-MCP/releases)**

> [!IMPORTANT]
> **Release status:** The latest published package is **v0.24.1 (prerelease)**. The `main` branch currently contains **v0.25.1 development source**, including the unified setup manager, Evidence Lens and native-agent handoff; it is **not a published or production-certified release**. The published v0.24.1 package has **33 MCP tools**; current source has **39**. CI passing does not establish live IDE acceptance.

## What is Orbit?

Orbit is an **MCP (Model Context Protocol) tool server and host-adapted workflow** for organizing software work across a project's lifetime: new applications, existing codebases, incremental features, debugging, redesign and maintenance.

- **Plan with context.** Gather only consequential decisions, support custom requirements, and use approved milestone gates rather than a fixed interview for every task.
- **Coordinate specialists.** Prepare bounded tasks, file ownership and evidence requirements. Real subagents run **only through native tools provided by the connected host**.
- **Remember useful progress.** Keep project checkpoints, task records and approved reference pointers in local SQLite; retrieve compact context instead of rereading every document.
- **Work with your codebase.** Inspect existing architecture and documentation before proposing changes; preserve owner documents and explicit decisions.
- **Verify before advancing.** Use real source diffs, tests and host permissions. Unverified evidence, failed checks and missing capabilities must remain visible as blockers.

Orbit does **not** provide its own LLM, silently install AI providers, launch background agent processes, or independently attest that a host actually granted permission or ran tests.

## Quick start

### Requirements

- **Python 3.10–3.13** for the currently CI-tested source; Python **3.12 recommended** for Windows setup. Windows double-click setup needs Tkinter.
- A supported coding host and an existing, trusted project folder.
- No `pip install` or administrator privilege is required for the core local MCP server.

### Option A — Published package

For the last publicly published package (**v0.24.1**), get the Universal Setup ZIP and its SHA256 file from **[GitHub Releases](https://github.com/samjuniors/Orbit-Core-MCP/releases)**. Verify the downloaded checksum, extract the archive and run `install_orbit_gui.pyw` on Windows, or `installer.py` on other systems.

The published version does **not** contain the new `Orbit Setup.cmd` launcher or the 39-tool development runtime.

### Option B — Current development source

For testing the latest merged features, clone `main` or update your existing clean checkout:

```sh
git clone https://github.com/samjuniors/Orbit-Core-MCP.git
cd Orbit-Core-MCP
```

**Windows — graphical setup:** Double-click **`Orbit Setup.cmd`**. The launcher selects an available CI-tested Python with Tkinter and opens a single window for **Install**, **Update from source**, **Published updates**, and **Uninstall**.

**Windows — PowerShell menu:**

```powershell
py -3.12 orbit_setup.py
```

**macOS/Linux — terminal menu:**

```sh
python3 orbit_setup.py
```

Choose your host(s) and either **one project** (existing absolute directory) or **this computer** (current OS user, not every user account). Review the proposed file changes before confirming. Restart or refresh the host's MCP connection after applying changes.

For noninteractive setup, preview first and then explicitly apply:

```sh
python3 orbit_setup.py install --scope machine --hosts codex
python3 orbit_setup.py install --scope machine --hosts codex --apply
```

You can substitute `antigravity`, `claude-code` or `vscode` as needed, or use `--scope project --project /absolute/path/to/project` for a single workspace.

**Confirm connectivity:** Open the selected project in your IDE and ask Orbit to call `orbit_project_scan`. Check that `orbit-core-native` is actually connected and that the reported version and tool list match the installation. A configuration file alone is **not** proof of a live MCP connection.

## Everyday usage

Speak to Orbit in your connected coding host, for example:

```text
Orbit, review this existing project and suggest the next milestone.
Orbit, add a filter to the Todo app without changing unrelated files.
Orbit, explain the current blockers and resume the approved work.
Orbit, plan a new Android app; ask only the important questions.
```

Orbit's workflow is **situational**. New products can start with adaptive intake and plan approval. Existing projects use a baseline; small fixes should not trigger a fresh-project interview. Web projects can use preview and browser QA gates; native apps and libraries use their relevant validation flow.

## Install, update and uninstall

The unified setup manager operates on **the selected host integrations**. Its actions are preview-first; terminal changes require `--apply`.

| Action | Terminal command | Behavior |
| --- | --- | --- |
| Install | `python3 orbit_setup.py install` | Preview/apply bundled host files and MCP registration |
| Update from source | `python3 orbit_setup.py update` | Reapply **the current local checkout** after reviewing new source |
| Uninstall | `python3 orbit_setup.py uninstall` | Remove recognized Orbit host files and registrations, with backups |
| Diagnose | `python3 orbit_setup.py status` | Read-only local runtime and host-configuration report |

Pass `--hosts` and the required scope/project options, then `--apply` only after verifying the preview. For source updates, run `git pull --ff-only` separately **after checking your working tree**; Orbit does not automatically pull Git commits.

**Published updates** are a separate path in the setup window. The existing Update Manager works with verified, published release assets and requires confirmation. Neither update path silently overwrites unrecognized customized files.

**Uninstall is intentionally conservative:** It preserves project directories, Git checkouts, shared Orbit runtime/updater, local SQLite memory, unrelated MCP entries, owner-authored guidance, and customized files. Verified target files receive backups under `~/.orbit-uninstall-backups/`. It is **not** a cross-project data-wipe command.

See [installation options](docs/MCP-INSTALLATION-OPTIONS.md), [update behavior](docs/UPDATE-EXPERIENCE.md) and [release quick start](docs/RELEASE-QUICKSTART.md).

## Supported host integrations

| Host | Integration | Native agent execution |
| --- | --- | --- |
| **Antigravity** | Orbit agents, skills and local stdio MCP | Host-controlled, only when a native delegation tool is actually available |
| **Codex** | Orbit skill/guidance and local stdio MCP | Host-controlled, only when supported and authorized |
| **Claude Code** | Orbit skill, specialist profiles and local stdio MCP | Host-controlled, only when supported and authorized |
| **VS Code** | MCP configuration where supported by the active extension/host | No universal native delegation guarantee |
| **Claude Desktop** | Separate published `.mcpb` extension | MCP access is **not** Claude Code subagent execution |

**Real multi-host delegation is still an open acceptance gate.** The `orbit_task_handoff` tool builds a read-only packet from registered task scope, dependencies and reported host capabilities. It does **not** spawn an agent, authorize a host action or verify a session ID.

## How it works

```text
Your coding IDE / agent host
          |
          | MCP over local stdio
          v
  Orbit Core MCP (Python)
  ├─ Project intake & decisions
  ├─ Task ledger & delegation handoffs
  ├─ Checkpoints & local SQLite context
  ├─ Research pointers & capability selection
  └─ Build, preview and QA coordination
          |
          v
  Host executes code edits, native agents and approved tools
```

The MCP runtime focuses on **project state and coordination**, while the host remains responsible for model selection, native agent execution, command permissions, source inspection and actual testing. Memory is local-first; saved research pointers are project-folder scoped and treated as untrusted reference data.

## Development and verification

From a source checkout with a supported Python interpreter:

```sh
python3 -m compileall -q source installer.py orbit_setup.py scripts tests
python3 -m unittest discover -s tests -v
python3 scripts/prepare_release_candidate.py
python3 scripts/check_version.py
python3 scripts/build_release.py --verify
```

The CI matrix covers Ubuntu with Python **3.10–3.13** and Windows with Python **3.12**, plus disposable installer/MCP protocol, release packaging and previous-version upgrade checks. A green build is **not** a substitute for signed-in IDE integration, live browser/device testing or a production-security review.

## Documentation

| Resource | Purpose |
| --- | --- |
| [Architecture](docs/ARCHITECTURE.md) | System components and host/MCP boundaries |
| [Product experience](docs/PRODUCT-EXPERIENCE.md) | Intake, plan review, progress and resume behavior |
| [Adaptive decision engine](docs/ADAPTIVE-DECISION-ENGINE.md) | Context-specific decisions and reusable capabilities |
| [Installation and updates](docs/MCP-INSTALLATION-OPTIONS.md) | Host setup, scope and configuration |
| [Security](SECURITY.md) | Threat boundaries, approval caveats and known gaps |
| [Roadmap](docs/NEXT-VERSION.md) | M1–M5 implementation and outstanding acceptance gates |
| [Release acceptance](docs/RELEASE-ACCEPTANCE-v0.25.1.md) | Gates for the unpublished source candidate |
| [Changelog](CHANGELOG.md) | Recorded source and release changes |

## Security and project status

Orbit uses preview-first operations, revision checks and bounded task scopes, but it is **not a security sandbox**. Some approval and test-evidence fields are caller-reported, and a host with command access can run project code. Install only in trusted workspaces, review proposed changes, and keep the host's own permission controls enabled.

Open items—including publisher authenticity, real-host acceptance and independently verifiable QA—are tracked in [security issue #9](https://github.com/samjuniors/Orbit-Core-MCP/issues/9) and the [roadmap](docs/NEXT-VERSION.md). Do not interpret a recorded `PASS` or a merged candidate as a production certification.

## Community and contributing

Bugs, feature proposals and implementation discussions belong in [GitHub Issues](https://github.com/samjuniors/Orbit-Core-MCP/issues). For proposed changes, open an issue first, keep the patch scoped, include tests and explain how behavior was verified. Consult [the release process](docs/RELEASE-PROCESS.md) before changing release or packaging files.

**License:** This repository currently has **no general open-source license grant**. Public visibility does not itself authorize redistribution or use under an assumed open-source license. Contact the repository owner about permissions before reuse or redistribution.
