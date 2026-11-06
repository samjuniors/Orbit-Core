# Orbit Core

[![CI](https://github.com/samjuniors/Orbit-Core/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/samjuniors/Orbit-Core/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/samjuniors/Orbit-Core?include_prereleases&label=published%20release)](https://github.com/samjuniors/Orbit-Core/releases)
[![Python](https://img.shields.io/badge/Python-3.10%E2%80%933.13-3776AB)](https://github.com/samjuniors/Orbit-Core/actions)

**A local-first project orchestrator for AI-assisted software development.**

Orbit connects to the coding environment you already use. It helps turn requirements into an approved plan, coordinate specialist work, track progress, retain concise project context, and resume from the last checkpoint—without replacing your IDE or choosing an external model for you.

**[Get started](#quick-start) · [How it works](#how-it-works) · [Documentation](#documentation) · [Roadmap](docs/NEXT-VERSION.md) · [Releases](https://github.com/samjuniors/Orbit-Core/releases)**

> [!IMPORTANT]
> **Publication and safety:** See the [GitHub Releases page](https://github.com/samjuniors/Orbit-Core/releases) for the current published version and verified downloads. The latest published `v0.29.0` and `v0.30.0` packages use the **stable GitHub release channel**, but a stable-channel label is **not** a production certification. Check the individual release notes and [current Swarm acceptance record](docs/SWARM-ENGINEERING-ACCEPTANCE.md) for genuine IDE permissions, installation/rollback, security and cross-device limitations. Orbit does not infer live-host acceptance from green CI.

## Why Orbit Core?

AI coding agents can implement work quickly, but long-running projects still need approved decisions, recoverable context and evidence before a task is considered complete.

| The problem | What Orbit Core does |
| --- | --- |
| Plans and progress get lost between sessions | Maintains project-scoped task records and checkpoints in local SQLite and supports resume |
| "Done" may be reported without verification | Records stage-specific evidence and preserves unverified or failed checks as blockers |
| Large requests need specialists | Coordinates bounded handoffs to native subagents supplied and authorized by the coding host |
| Installers can accidentally overwrite user work | Provides preview-first changes, explicit approval and backup-aware setup |

### Who it is for

- **New to AI-assisted development:** follow [Quick start](#quick-start), use a reviewed release ZIP and confirm the proposed installation changes.
- **Power users and contributors:** follow the source setup, study the [architecture](docs/ARCHITECTURE.md), and review the [acceptance records](docs/GOLDEN-PATH-ACCEPTANCE.md) before relying on a host-specific capability.

## What is Orbit?

Orbit is an **MCP (Model Context Protocol) tool server and host-adapted workflow** for organizing software work across a project's lifetime: new applications, existing codebases, incremental features, debugging, redesign and maintenance.

- **Plan with context.** Gather only consequential decisions, support custom requirements, and use approved milestone gates rather than a fixed interview for every task.
- **Coordinate specialists.** Prepare bounded tasks, file ownership and evidence requirements. Real subagents run **only through native tools provided by the connected host**.
- **Remember useful progress.** Keep project checkpoints, task records and approved reference pointers in local SQLite; retrieve compact context instead of rereading every document.
- **Work with your codebase.** Inspect existing architecture and documentation before proposing changes; preserve owner documents and explicit decisions.
- **Verify before advancing.** Use real source diffs, tests and host permissions. Unverified evidence, failed checks and missing capabilities must remain visible as blockers.

Orbit does **not** provide its own LLM, silently install AI providers, launch background agent processes, or independently attest that a host actually granted permission or ran tests.

## Quick start

### One Universal Setup for your coding hosts

**Recommended for most users:** Download the latest **published** `ORBIT-Universal-Setup-vX.Y.Z.zip` and its `.sha256` file from **[GitHub Releases](https://github.com/samjuniors/Orbit-Core/releases)**. Verify the ZIP checksum, extract it and open **`Orbit Setup.cmd`** (Windows) or **`python3 orbit_setup.py`** (macOS/Linux). Select one or more supported hosts, choose **This computer** or **One project**, review the exact file changes, then approve. Restart your IDE and verify that the Orbit MCP actually connects.

This one package can configure **Antigravity, Codex, Claude Code and VS Code** together. It does not install those coding applications or their models. **Claude Desktop** uses its separately published `.mcpb` extension and is not silently installed by the Universal Setup.

**Requirements:** Python 3.10?3.13 (Windows: 3.12 recommended); no administrator permissions or `pip install` required for Orbit's core local MCP server. The Windows graphical setup additionally needs Tkinter. Installation applies to your **current OS account**, not all computer accounts.

### Windows PowerShell or CLI ? works with published v0.30.0

From the extracted Universal Setup folder, preview first, then explicitly apply:

```powershell
py -3.12 orbit_setup.py install --scope machine --hosts antigravity codex
py -3.12 orbit_setup.py install --scope machine --hosts antigravity codex --apply
```

Select only the hosts you use. Choose `--scope project --project "C:\full\path\to\project"` for a single project. These commands use the **version of the downloaded and verified ZIP**, not the latest `main` source. They do not modify saved SQLite memory or unrelated MCP entries.

After one successful installation, the persistent launcher can check and install newer **published stable** releases without repeatedly downloading ZIPs manually:

```powershell
& "$HOME\.orbit-universal\bin\orbit.cmd" doctor
& "$HOME\.orbit-universal\bin\orbit.cmd" update --channel stable --check
& "$HOME\.orbit-universal\bin\orbit.cmd" update --channel stable
& "$HOME\.orbit-universal\bin\orbit.cmd" update --channel stable --apply
```

If PowerShell's local-script policy blocks the future `Orbit.ps1`, use `py -3.12 orbit_cli.py` with the same arguments from the verified ZIP; do not weaken global execution policy.

The `--check` action reads metadata only; without `--apply`, an update downloads and validates its ZIP but **does not execute downloaded code**. `--apply` is an explicit authorization to execute the verified release installer and change selected host files. Backups protect recognized originals; unknown customizations require review. Restart the IDE afterward.

For **v0.30.0 scoped uninstall**, return to its extracted, checksum-verified ZIP:

```powershell
py -3.12 orbit_setup.py uninstall --scope machine --hosts antigravity codex
py -3.12 orbit_setup.py uninstall --scope machine --hosts antigravity codex --apply
```

Uninstall removes selected Orbit host integrations, retaining shared runtime, project files, SQLite memory, checkpoints and unrelated MCP services. It is **not** the destructive `clean` command.

### Upcoming release-aware single CLI (development; not in v0.30.0)

The next version is being developed to make **install, update, and uninstall** work through one permanent `orbit` launcher. It defaults to published **stable** releases; `--version X.Y.Z` pins an exact published release, and `--channel candidate` is an explicit prerelease opt-in. It will also ship **`Orbit.ps1`** inside the Universal ZIP for PowerShell. These commands **are not shipped in the immutable v0.30.0 release**:

```powershell
# From the verified newer Universal ZIP:
.\Orbit.ps1 install --hosts antigravity codex
.\Orbit.ps1 install --hosts antigravity codex --apply

# After installing the newer version, from any PowerShell directory:
& "$HOME\.orbit-universal\bin\orbit.cmd" update --check
& "$HOME\.orbit-universal\bin\orbit.cmd" update --version X.Y.Z --hosts antigravity codex
& "$HOME\.orbit-universal\bin\orbit.cmd" uninstall --version X.Y.Z --hosts codex
```

Each action remains **preview-first** and requires `--apply` to change files. A pinned version must exist on the selected published channel; no floating `main` source, hidden downgrades, automatic model installation or silent project-data erasure.

For contributors testing unreleased source, clone `main` separately. `orbit_setup.py update` in a source checkout means **reapply local checkout files**, **not** fetch a GitHub Release. Details: [Release quick start](docs/RELEASE-QUICKSTART.md) and [update experience](docs/UPDATE-EXPERIENCE.md).

**Confirm live connectivity:** In your IDE, ask Orbit to call `orbit_project_scan` and report its running version and tool inventory. A config file alone is not proof that the MCP process reconnected.

## Everyday usage

Speak to Orbit in your connected coding host, for example:

```text
Orbit, review this existing project and suggest the next milestone.
Orbit, add a filter to the Todo app without changing unrelated files.
Orbit, explain the current blockers and resume the approved work.
Orbit, plan a new Android app; ask only the important questions.
```

Orbit's workflow is **situational**. New products can start with adaptive intake and plan approval. Existing projects use a baseline; small fixes should not trigger a fresh-project interview. Web projects can use preview and browser QA gates; native apps and libraries use their relevant validation flow.

## Managing a current installation

For the latest available **published** version, use the [Release quick start](docs/RELEASE-QUICKSTART.md) rather than cloning `main`. One Universal Setup manages multiple selected local hosts while protecting other MCP registrations and owner-written project files.

- **Install:** preview one or more host integrations; apply only after reviewing changes.
- **Update:** choose a verified **published release** in the Update Manager or the persistent `orbit.cmd update --channel stable` command. Source checkout updates are a separate maintainer path.
- **Uninstall:** run the installed version's verified `orbit_setup.py uninstall` from its official Universal ZIP; after the release-aware CLI ships, use `orbit uninstall`. This removes **selected integrations only**, not memory or shared runtimes.
- **Clean/reset:** an intentionally separate, destructive and typed-confirmation action. The `clean` command may affect multiple hosts and optionally saved memory. Read its preview and recovery rules in [installation options](docs/MCP-INSTALLATION-OPTIONS.md) before using it.

For significant changes keep a separate backup of SQLite database/WAL/SHM, host settings and customized files. The installer preserves recoverable backups. An older release is not an automatic compatible data rollback. Refresh your IDE after installation and verify the live tool connection.

## Orbit with other plugins

**Orbit-first for software-project coordination; specialist plugins remain available.**
When you select Orbit as the lead, it manages project plans, task handoffs,
evidence and checkpoints. It does **not** disable GitHub, browser, QA,
other MCPs or installed specialist agents. The host/user still chooses which
skills and tools activate; no cross-IDE mechanism can guarantee Orbit runs first.

For the proposed next version, `python3 orbit_priority.py` provides a read-only,
name-only warning of overlapping Orbit registrations, similar MCP names and
duplicate skill scopes. Nothing is removed, run or reconfigured. For full limits,
host differences and acceptance criteria, read
[coordinator preference and overlap detection](docs/COORDINATOR-PRIORITY.md).

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
python3 scripts/prepare_release_candidate.py
python3 scripts/check_release_readiness.py
python3 -m compileall -q source installer.py orbit_setup.py scripts tests
python3 -m unittest discover -s tests -v
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
| [Release and QA checklist](docs/RELEASE-PROCESS.md) | Repeatable checks and automatic publication workflow for every version |
| [Release acceptance](docs/RELEASE-ACCEPTANCE-v0.30.0.md) | v0.30.0 release evidence and remaining independent host gates |
| [Changelog](CHANGELOG.md) | Recorded source and release changes |

## Security and project status

Orbit uses preview-first operations, revision checks and bounded task scopes, but it is **not a security sandbox**. Some approval and test-evidence fields are caller-reported, and a host with command access can run project code. Install only in trusted workspaces, review proposed changes, and keep the host's own permission controls enabled.

Open items—including publisher authenticity, real-host acceptance and independently verifiable QA—are tracked in [security issue #9](https://github.com/samjuniors/Orbit-Core/issues/9) and the [roadmap](docs/NEXT-VERSION.md). Do not interpret a recorded `PASS` or a merged candidate as a production certification.

## Community and contributing

For contribution workflow and project compatibility expectations, read [CONTRIBUTING.md](CONTRIBUTING.md). Orbit Core is open source under the [MIT License](LICENSE); preserve the copyright and permission notice when redistributing.

Bugs, feature proposals and implementation discussions belong in [GitHub Issues](https://github.com/samjuniors/Orbit-Core/issues). For proposed changes, open an issue first, keep the patch scoped, include tests and explain how behavior was verified. Consult [the release process](docs/RELEASE-PROCESS.md) before changing release or packaging files.

## License

Orbit Core is available under the [MIT License](LICENSE). Third-party packages and references retain their own licenses.
