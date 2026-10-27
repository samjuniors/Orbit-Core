# Orbit Core MCP

**Local-first, approval-driven orchestration for your own coding IDE.** Python 3.10+ · SQLite · **36 MCP tools on the update-notification branch (35 on current `main`; 33 in published v0.24.1 desktop bundle)** · Antigravity, Codex, Claude Code, optional VS Code and Claude Desktop.

Orbit helps an existing coding host turn plain-language requests into approved product decisions, researched architecture, reusable components, staged implementation tasks, checkpointed progress, and verifiable checks. **Orbit is not a standalone LLM, IDE, code editor or background worker**: the host performs reasoning, agent invocation, file edits and terminal commands. Model recommendations never switch providers or consume credits by themselves.

> **Release status:** v0.24.1 is **published as a prerelease candidate**. The newer lifecycle and adversarial-audit source fixes are merged to `main`, but **not included in the published v0.24.1 installer**. `VERSION=0.25.0` identifies the **merged, unpublished candidate source**; `NEXT_VERSION=0.25.1` is a tentative subsequent patch target. GitHub CI is not a substitute for live Windows/IDE acceptance. Published releases are available at [Releases](https://github.com/samjuniors/Orbit-Core-MCP/releases). This repository is separate from other Orbit-branded CLIs/plugins.

## v0.25.0 source merged — public release still gated

The merged source builds a **test artifact**, not a published GitHub Release. The last approved test artifact was produced from the tested release PR; regular `main` CI does not publish a release. GitHub Actions CI prepares `ORBIT-Claude-Desktop-v0.25.0.mcpb`, verifies byte-for-byte parity of all runtime modules, creates `ORBIT-Universal-Setup-v0.25.0.zip` and its checksum, and uploads them under a short-lived **orbit-v0.25.0-host-acceptance** artifact from Ubuntu Python 3.12. No tag, install, publisher attestation, automatic host changes or production certification occurs. The testing and approval checklist is in [v0.25.0 release acceptance](docs/RELEASE-ACCEPTANCE-v0.25.0.md). Downloads from CI should be evaluated in a disposable project and verified against the job's checksum before use.

Published v0.24.1 instructions below remain the only supported public installation instructions until v0.25.0 is separately approved and released. In particular, don't mistake an Actions artifact for a signed public release.

## Get started (install once)

**Windows / Antigravity / Codex / Claude Code / VS Code**

1. Download `ORBIT-Universal-Setup-v0.24.1.zip` **and its `.sha256` checksum** from [the release page](https://github.com/samjuniors/Orbit-Core-MCP/releases). Verify the checksum and extract the ZIP.
2. Ensure Python 3.10+ with Tkinter is installed. From the extracted `orbit-universal-0.24.1` folder double-click `install_orbit_gui.pyw`, or run `py -3 install_orbit_gui.pyw`.
3. Select **This computer** (recommended if you want Orbit in every project) or **One project**, and choose your IDEs. The wizard detects likely hosts; detection is not a live connection test. **Preview changes → Install Orbit**. The installer preserves owner docs, other MCP entries, SQLite and existing projects. Unrecognized customized files require manual review, never a forced overwrite.
4. Restart/refresh the selected IDE's MCP servers; confirm the **published v0.24.1** `orbit-core-native` exposes 33 tools (this candidate source exposes 35) and call `orbit_project_scan` in an approved project.

**macOS/Linux**: extract the verified release archive, then in its root run:

```bash
python3 installer.py --scope machine --hosts codex
python3 installer.py --scope machine --hosts codex --install
```

Replace `codex` with your selected host; `--scope project --project /absolute/path` installs to only one trusted workspace. No sudo, external model CLI or `pip install` is needed for the MCP server itself. **Python Playwright is optional** and only required for Orbit's built-in browser QA.

For normal Claude Desktop chat, install the matching `ORBIT-Claude-Desktop-v0.24.1.mcpb` extension from the verified release. It provides MCP tools, not Claude Code terminal or native subagent execution.

## Install once, then update through Orbit

**Upcoming feature branch — not in the published v0.24.1 release yet.** Orbit adds a **built-in Update Manager** and read-only update notices. After this code is released, the local Orbit MCP checks **published** candidate or stable release metadata on startup in the background, no more than once daily. If a newer version exists, `orbit_project_resume` includes `update_notice`. A supported IDE can surface an **Update / Later** prompt; other hosts display a normal text notice. Orbit never downloads or executes an installer just because an agent resumed a project.

Open the existing stable Orbit launcher using `orbit manager` (or **Manage updates** in the bundled setup GUI). The manager shows installed/latest versions, chooses machine scope versus one project, and lets you select Antigravity, Codex, Claude Code and VS Code host configurations. Click **Install update** and approve its confirmation to run the existing backup-first, SHA256-checked updater. Restart the IDE's Orbit MCP server afterward. No fresh manual ZIP download or installer wizard is needed for a normal local host update.

**Important limitations:** the first upgrade from v0.24.1 to a version containing this manager remains a one-time manual/CLI transition; the previous published installer cannot magically acquire a future UI. No standalone background service or unsolicited OS popups exist. Separate Claude Desktop `.mcpb` extensions and hosted ChatGPT connectors follow their own platform update/publishing path and are **not** silently replaced by this local manager. Updates apply only to the current OS account and selected host/project scope, not all user accounts or every registered project. `ORBIT_UPDATE_CHECK=0` disables automatic metadata checks. A GitHub ZIP checksum is not cryptographic publisher authenticity. See [Update experience and per-host limitations](docs/UPDATE-EXPERIENCE.md) and [release-security gate](https://github.com/samjuniors/Orbit-Core-MCP/issues/9).

## Update without reinstalling manually

After the first installation, use the stable local Orbit launcher. GitHub **0.x releases are labeled candidates**, so the default update channel is `candidate`. All update actions preview first, fetch official published assets, verify SHA256, check ZIP paths and back up recognized stock files.

```powershell
& "$HOME\.orbit-universal\bin\orbit.cmd" doctor
& "$HOME\.orbit-universal\bin\orbit.cmd" update --check
& "$HOME\.orbit-universal\bin\orbit.cmd" update
& "$HOME\.orbit-universal\bin\orbit.cmd" update --apply
```

Use `update --channel stable` only when a stable release exists. `orbit update` works without the full path only if you **choose** to add the launcher folder to your user PATH. Orbit never modifies PATH or installs tools automatically. Local development ZIPs may be previewed with `update --from-zip <file> --sha256 <separately-trusted-digest>`; do not blindly install an unreviewed branch. If the updater reports a manual-review conflict, keep the file and investigate—do not delete it.

## How to use Orbit

Start a new approved project folder in your IDE and ask: **"Orbit, build a mobile habit tracker."** Orbit should propose **Scope first** or explicit **Build with sensible defaults**, then ask consequential questions *based on your last answer*. You can always type **Custom** requirements. After accepted intake, it researches existing code/libraries, shows an editable task plan for approval and runs the appropriate host-driven workflow.

A new web build uses `RESEARCH → PLAN → IMPLEMENT → VERIFY → PREVIEW → BROWSER_QA → REVIEW → CHECKPOINT → DONE`. Native apps use native QA; SDK, CLI, API, MCP or platform work omits irrelevant web preview gates. Existing persisted builds retain their original stage. Architect, QA, writer and other specialist agents use host-native delegation **only when supported**. Models can be **recommended** by task from host-reported availability, not independently selected or billed by MCP.

`orbit_project_resume` recovers the saved stage, next action and task ledger. `orbit_docs_audit` helps maintain useful canonical vision, architecture, roadmap and design documents as projects evolve. Orbit favors vetted installed components and libraries over unnecessary custom implementation; no library, skill, browser driver or MCP is installed without approval.

## What is actually verified?

- Runtime: Python stdio JSON-RPC, persistent SQLite, bounded request validation, revision-gated project state, scope-aware task ledger and checkpoints.
- Installer: preview-first per-user or per-project configuration, backed-up recognized stock upgrades, host detection, read-only diagnostics.
- Tests: Python 3.10–3.13 Linux CI and Python 3.12 Windows CI, source-to-desktop-package parity, release version/ZIP checks. See [CI](https://github.com/samjuniors/Orbit-Core-MCP/actions).
- **Limitations:** Model calls, subagent execution, host permissions, genuine browser/device QA, user approval and acceptance remain host-controlled. Preview process supervision is same-session; worktree isolation, evidence-to-commit binding, robust multi-process locking and managed deployment require further work. Do not treat `DONE` as independent production certification.

## Repository

```text
source/runtime/    Python MCP tools and decision/build/task modules
source/agents/     Lead and specialist host-agent instructions
source/skills/     Orbit skill and just-in-time references
installer.py       Preview-first, scope-aware cross-host installer
install_orbit_gui.pyw   Windows setup wizard
orbit_cli.py       Installed updater, detect and doctor
scripts/           Release build, extension sync and validation
tests/             Protocol, updater, build, installation regressions
docs/              Architecture, technical decisions, onboarding and roadmap
```

From a clean checkout:

```bash
python -m compileall -q source installer.py scripts tests
python -m unittest discover -s tests -v
python scripts/check_version.py
python scripts/build_release.py --verify
```

See [architecture](docs/ARCHITECTURE.md), [release process](docs/RELEASE-PROCESS.md), [source/component decision matrix](docs/ADAPTIVE-DECISION-ENGINE.md), [installer choices](docs/MCP-INSTALLATION-OPTIONS.md), [security boundaries](SECURITY.md) and [honest roadmap](docs/NEXT-VERSION.md).

**License note:** This public repository has no general open-source license grant unless the owner adds one. Do not repackage or redistribute it under a guessed license.


## Product experience (merged into main)

The merged Product Experience v1 work adds a read-only one-glance `experience` summary to `orbit_project_resume` and `orbit_build_status` (next decision, real stage/task progress, approval and blocker hints), fixes native/SDK-specific stage progression, and adds the 34th tool, `orbit_build_feedback`: an approval-gated, revision-checked change-request history.

**Use the IDE you already have:** Antigravity's native Implementation Plan (comments and Proceed), Task List, diff review, and walkthrough are the editing/review surfaces. Orbit tracks unresolved requests in SQLite; a stage cannot be marked PASS while requested changes remain open. The MCP does not pretend to create a new IDE visual panel or automatically inspect or approve Antigravity artifacts.

These changes are **merged into main but not included in the already published v0.24.1 release**. They require a future separately versioned release and real IDE acceptance before they are available to installed users. See [product experience specification](docs/PRODUCT-EXPERIENCE.md) and [PR #5](https://github.com/samjuniors/Orbit-Core-MCP/pull/5).

## All-maturity lifecycle (Issue #7 — merged source, unreleased)

Ask Orbit to **start, stop/pause, resume, debug/fix, add a feature, redesign, refactor, test, review or continue**, in your own words. `orbit_project_resume` shows the existing compact experience/checkpoint. `orbit_project_action` accepts a plain-text `action` and returns evidence-limited project maturity signals and a proportional workflow. The host verifies Git, active branch, changed files and real tests; Orbit never runs a host model or automatically edits the product.

An empty project uses adaptive intake. An established, partial, maintained or stalled project uses a read-only baseline and existing files/documents. For an owner-authorized change to existing code, `orbit_build_begin` accepts a **new** `build_id`, `change_kind` (`adopt`, `fix`, `feature`, `redesign`, `refactor`) and either `baseline_reference` (host-inspected existing code) or `change_from` (a completed DONE build ID). A fix starts with focused implementation/testing; new features, redesigns and refactors start at plan review. Completed builds never reopen or get overwritten.

`orbit_project_action(action="pause", build_id="...", expected_revision=N)` first returns `PREVIEW_ONLY`. With owner permission, `confirm_write=true` pauses the specific Orbit build ledger; `resume` uses the new revision. Neither affects host-native agents or deployed processes. Stopping a managed *local preview* is a separate approved `orbit_preview_stop` call. Use `orbit_project_checkpoint` after meaningful work; if two unfinished builds exist, choose one explicitly. All source and history remain project-scoped; no new database schema, background worker, agent runtime or doc tree is introduced.

**Host support:** Antigravity uses native plan/task artifacts and supported subagent APIs when available; Codex/Claude Code use their actual host tools; VS Code depends on the installed MCP-compatible extension; Claude Desktop chat may offer only read-only/status and Markdown handoff. None of these claims means a local IDE acceptance test has run.

**Unreleased source policy:** the tracked `ORBIT-Claude-Desktop-v0.24.1.mcpb` is a frozen published artifact and does **not** contain Issue #7. Development tests compile both sources and bundle but permit intentional difference; `python scripts/check_version.py --strict-bundle` remains the strict package-parity gate for future tagged releases. This unreleased development source must not be advertised as an available published installer until a separately versioned package is produced and tested.

## Adversarial audit fixes (Issue #9 — pending independent host acceptance)

The October 2026 external audit identified reproducible protocol, SQLite, checkpoint, preview, task-ledger and recovery defects. The source hardening branch applies the audited patch and additional focused defenses: non-executing updater previews, explicit source adoption for existing projects, safer preview environment defaults, a strict optional host-configured workspace allowlist and clearer host-approval boundaries. See [SECURITY.md](SECURITY.md).

**Not a production certification:** the MCP does not authenticate a person behind `approval_reference` or `confirm_write`; these are agent-reported. Real consent comes from the configured host's tool approval UI. Preview commands execute project code and are not a sandbox. Optional `ORBIT_TRUSTED_ROOTS` (platform path-separated absolute paths configured by the host process) restricts workspace roots; without it, Orbit blocks common credential directories but cannot verify comprehensive owner trust. Untrusted source content must never supply instructions or approvals.

The published `v0.24.1` desktop bundle has **not** been updated by the audit patch; release signing/attestation, strict bundle parity, actual Antigravity/Codex/Claude/VS Code integration, Chromium/WebSocket security, and Windows `.cmd` behavior remain separate release gates. The audit findings can be reviewed under [Issue #9](https://github.com/samjuniors/Orbit-Core-MCP/issues/9).
