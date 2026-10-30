# Changelog

All notable changes are recorded under [Semantic Versioning](https://semver.org/).

## [Unreleased] — beyond v0.26.0 candidate

### Next-version development (not released)
- **Opt-in project pulse:** `orbit_project_resume(compact=true,pulse=true)` adds a bounded, read-only task count and safe next-action hint sourced only from project-scoped local records. No new MCP tool, host invocation, approval, state write or promise of live agent/test verification. The default compact response remains unchanged; genuine host/test acceptance and actual token-savings measurements are still required.


The next published release/version remains undecided until the expanded v0.26.0 source scope passes its live-host and security gates. `NEXT_VERSION=0.26.1` remains a tentative planning marker, not a release authorization.

## [0.26.0] — Development release candidate (NOT PUBLISHED; NOT production-certified)

**Additional v0.26.0 development work (still not a published release)**
- **Multi-host suite and compact setup (source candidate only):** one deterministic `Orbit-Core-Plugin-Suite-v0.26.0.zip` with distinct Antigravity, Codex and Claude Code plugin manifests generated from canonical Orbit runtime/skill; new packaged suffix naming `orbit-lead-agent` / `orbit-<role>-agent` / `orbit-workflow-skill` / `orbit-core-mcp`; small Windows Install/Update/Uninstall setup UI with host detection, scope, reviewed file changes and memory-preserving default. This does **not** claim tested native-marketplace installation or DeepSeek Harness compatibility; those are release gates. See `docs/PLUGIN-SUITE-NAMING.md`.

- **Antigravity native plugin candidate (not installed/published):** deterministic `Orbit-Antigravity-Plugin-v0.26.0.zip` with SHA256, existing Orbit main-agent + 12 specialist definitions, compact skill with retained full references and all 42 canonical local MCP tools. Adds backup-first, explicit opt-in Antigravity legacy-profile migration preview to avoid duplicate MCP/agent registrations. Requires host Python; no remote server. Manifest validation, real plugin-origin delegation/permission UI, clean host migration and separate Codex/Claude plugin adapters remain release gates. See [plugin guide](docs/ANTIGRAVITY-PLUGIN.md).

- **M5 opt-in practice learning (owner-approved source integration):** `orbit_practice_suggest` identifies candidate patterns from repeated same-project reviewer-accepted task records; `orbit_practice_review` previews and records user-reviewed approve/reject/archive/supersede decisions, with revision guards, append-only SQLite history, stale-evidence visibility and cross-project isolation. This is reference data only: no automatic skill creation, model/subagent execution, Notion sync, independent host approval attestation or background learner. Two additive SQLite tables are created on startup; prior data stays intact. The previous 40-tool source inventory becomes **42**. M5 live-host/security acceptance is pending and no release is authorized.
- **M3 consent hardening:** the existing capability selector now accepts optional caller-reported `permission_state`; denied browser/computer use yields a HOLD instead of recommending another provider.
- **M4 adaptive guidance:** a small `adaptive_workflow` recommendation chooses focused compact resume or full review according to task risk/complexity, and suggests only available host-native or serial execution paths. All tool/permission/model execution remains host-controlled; no new MCP tool or automatic installation.
- Automated regression tests, including simulated context-byte comparisons, are required before integrating into the v0.26.0 source candidate. Real host/context savings remain unverified.

**What’s new**
- **Compact context on resume (M4.1):** the existing `orbit_project_resume` accepts opt-in `compact=true`, an objective and a bounded JSON-character budget. It summarizes approved local intake (approval is caller-reported), a project-matched checkpoint, a local build recovery hint and relevant research source pointers. Full resume remains the default. It does not fetch full Notion pages, reuse unscoped memories or invoke another AI model.
- **Adaptive browser selection:** prioritize genuinely available, authorized host-native browser/computer-use tools before a local installed browser and optional reviewed agent-browser integration; do not silently operate personal browser profiles.

**Reliability, permissions and recovery**
- **Host-denial clarity:** failed or refused pre-invocation delegation is recorded as BLOCKED instead of being confused with user cancellation. Fresh host approval remains required to retry.
- **Interrupted-agent reconciliation:** running tasks retain their scoped reservations until an exact, caller-reported native host session and compatible terminal state are observed. Unknown session state fails closed and never proves the worker stopped.
- **Durable attempt budgets:** local SQLite records individual native-agent reservations and their outcomes, including repeated retries; enforce existing per-step, per-day and concurrency limits. Safely refund only unused pre-invocation slots. Keep prior host sessions in attempt history, preserve old task rows and checkpoint data.
- **Portable historical accounting:** imported task history with unknown reservation dates is not incorrectly charged as new same-day destination-host work. Local attempt records are **not** synchronized across computers.
- **Partial database safety:** explicitly check for missing task/research tables on resume, without suppressing unrelated SQLite operational errors.
- **Transactional regression tests:** task state and attempt history must remain consistent after failed reserve, start or report writes, including restart recovery.

**Browser QA protection**
- Restrict Orbit-managed Playwright HTTP and WebSocket QA requests to the exact approved local preview origin. Blocked network attempts cannot produce a passing build-gate result. Playwright **1.48+** WebSocket routing is required for that bounded policy; an older installation returns a dependency HOLD rather than an unearned PASS.
- Browser routing does not form a complete operating-system network sandbox or authenticate any external provider’s permissions. Multi-origin applications require a separately reviewed policy.

**Compatibility / behavior changes**
- Clients reporting terminal native-agent outcomes for RUNNING tasks should now supply the correct `observed_host_session` and compatible `host_state` to `orbit_task_report`. Missing or uncertain observations return HOLD instead of clearing a possibly live worker. Verify host-side cancellation independently.
- The additive `orbit_task_attempts` SQLite table preserves old task records, but **backing up SQLite (including WAL files) before upgrading is recommended**; older runtimes may not understand every newer state/behavior. Never silently downgrade user databases.
- Source runtime and installer version move to **0.26.0**; `NEXT_VERSION=0.26.1` remains tentative. MCP tool inventory is **42** in the expanded development source (40 baseline + 2 optional M5 review tools); no new model runtime, implicit subagent spawning, cloud synchronization or extra installation is introduced.

**Requirements, packaging and verification**
- Python 3.10–3.13 CI targets; Windows Python 3.12 recommended. Host-native delegation is limited to tools actually supplied and authorized by Antigravity, Codex, Claude Code or other supported hosts.
- Candidate artifacts are built from the exact current runtime and packaged through GitHub Actions as **unpublished host-acceptance artifacts**; versioned ZIP/MCPB and SHA256 integrity checks are part of CI. Successful checksum verification is not publisher signing.
- Independent signed-in host permission/cancellation, physical browser/device QA, upgrade/rollback, two-computer transfer and Issue #9 security gates remain **NOT VERIFIED / OWNER-DEFERRED**. CI success and merging this source branch do **not** certify a production release.
- **Publication:** No `v0.26.0` tag or GitHub Release is authorized by this candidate alone; publication requires a separate explicit owner go-ahead and completed release gates.

## [0.25.1] — Published prerelease (2026-10-29; NOT production-certified)

**Included from the previously staged post-candidate source at the published 40-tool commit:**
- **Explicit clean reset:** add **Clear Orbit / Fresh install…** with exact path preview, typed `REMOVE ORBIT` confirmation, all-global-host/customized Orbit cleanup, shared runtime removal, optional selected-project cleanup and separately opted-in memory deletion. Back up all originals before changes; preserve unrelated MCPs/configuration and product source. Refuse symlinks, invalid shared config and stale previews. Equivalent `orbit_setup.py clean` command; Windows visual acceptance remains pending.
- **Setup repair and polish:** recognize exact official intermediate agent templates from `7e1372f` (native/Claude, LF/CRLF) for backup-first upgrades, fixing the reported `orbit-architect.md` block. Unknown edits remain protected. Use a themed three-step layout, scrollable file preview, clearer review messages and one state-aware action. Windows visual acceptance remains pending.
- **Unified setup (published prerelease):** `Orbit Setup.cmd` opens the expanded native Windows setup UI; `orbit_setup.py` offers an interactive terminal menu or explicit preview-first `install`, `update`, and reversible `uninstall` for selected IDE hosts. Uninstall preserves shared runtime, SQLite, owner docs, unrelated MCP entries and custom files, with backups; it does not auto-update Git or bypass stock-file conflicts. Included in candidate ZIP smoke and Windows/Linux CI.
- **M2 host-native delegation handoff (published prerelease; not production-certified):** a read-only `orbit_task_handoff` produces source-scoped, approval-aware packets only for reserved tasks with a matching *reported* native IDE agent tool. Native invocation, session evidence and execution still belong entirely to the connected host; safe HOLD/serial fallback when unavailable. No extra model CLI or automatic agent spawning.

- **Orbit Evidence Lens (published prerelease; not production-certified):** original folder+project-scoped SQLite research source pointers with preview-first, revision-guarded review; bounded objective-relevant context pack and untrusted-source warnings. No automatic crawler, source execution, Git research notes, global cross-project sharing or new model service. Existing local memory retained; requires real IDE/local install acceptance.
- **Research/context milestones:** approved M1–M5 roadmap for scoped research memory, native-agent handoffs, evidence authentic QA, adaptive skills/context and optional verified learning, without adopting ECC's runtime or a universal auto-learning hook system.

- No additional published changes. `NEXT_VERSION=0.25.2` is planning metadata only.


**What's new and why it matters**
- **Update Manager:** Once installed, open `orbit manager` or the per-user Update Manager launcher; select local hosts and approve an in-place upgrade without re-downloading and re-running setup each time.
- **Update notices:** MCP checks **published releases** in the background at most daily, then shows an optional update notification on resume when newer. No network dependency for normal project work and no unattended install.
- **Read what changed:** View the actual published release description in the Update Manager and its confirmation dialog before approving an update; the MCP notice can show the bounded published summary as display-only data.
- **Older versions:** Open the GitHub Releases archive through the manager or `orbit versions` to download a previous version deliberately. Older versions remain available; downgrade is manual and may be incompatible with newer saved data.
- **Safety:** Keep release version pinned to what the user approved, check ZIP SHA256 and package paths, retain recognized-stock backups and preserve customized documents/SQLite; unknown files block, rather than silently overwrite.
- **Included since v0.24.1:** Previous v0.25.0 source improvements to existing-project adoption, scoped changes to completed products, restart/checkpoints and audit hardening. v0.25.0 source was never a separately published installer.
- **Important limitations:** No claim of publisher signature from a colocated SHA256, real native toast in every IDE, automated Claude Desktop extension updating, all-workspace batch updates, OS-level notifications, or independent host-approved MCP writes. Restart the relevant IDE/MCP server after installation. Real-host acceptance and Issue #9 security gates remain open.


- Add read-only, asynchronous, cached published-release notification on Orbit MCP startup and `orbit_project_resume` (one day cadence, `ORBIT_UPDATE_CHECK=0` opt-out). Add an explicit `orbit_update_status` tool (36 total).
- Add persistent local Orbit Update Manager with a real Install button, version-pinned approved updates and a launcher available without re-downloading setup; one selected machine-user or project install scope at a time. No silent code execution, automatic upgrade or native IDE popup guarantees.
- Keep SHA256, signed-publisher limitation, customized owner file/SQLite protection and versioned-runtime backup rules; preserve distinct Claude Desktop and hosted ChatGPT plugin update channels.
- The next patch target is tracked in `NEXT_VERSION`; no subsequent release has been published.

## [0.25.0] — Candidate source merged; NOT PUBLISHED
- Main source supports lifecycle operations for fresh, partially built, existing and completed products, with host-neutral routing, safe pause/resume and scoped existing-product adoption (Issues #7 and #9).
- Merge the externally audited MCP protocol, checkpoint/SQLite, recovery, preview, agent-task and memory hardening; add adversarial regression coverage (PR #10).
- Update previews no longer execute downloaded installer code. Introduce optional host-controlled trusted workspace roots, restricted child environment defaults and clearer warnings about model-asserted approvals.
- Support safe future version preparation from the immutable prior desktop bundle and explicit NEXT_VERSION planning.
- **v0.25.0 was not published separately:** the later v0.25.1 prerelease includes updated installers while real IDE/browser acceptance, host-attested approvals, signing/provenance and threat-model fixes remain open. Older v0.24.1 assets and tags stay unchanged.

## [0.24.1] — Integration candidate
- Combine adaptive product intake and model recommendations, vetted component selection, role-specific workflows, durable checkpoints and native host delegation guidance.
- Harden JSON-RPC validation and bounded request parsing with source-to-extension parity tests.
- Enable checksum-verified candidate-channel upgrades, local read-only doctor command, and Windows CI tests.
- Preserve owner code/docs, SQLite, previous versioned runtimes and other MCP registrations. No autonomous CLI installs, model switching or deployment.
- This 0.x candidate requires live Windows host and browser acceptance before production certification.

- On isolated development branch: support unrestricted bounded custom interview answers, dependent conditional followups, source-reviewed platform component recommendations, host-reported model-tier suggestions, and new-build type-specific QA flows. Existing builds are not retroactively changed. Claude Desktop package refreshed to 33 tools.

- Integrate selected Product Kit v0.2 patterns: bounded SQLite-driven recovery briefing, milestone owner QA guidance, lean change/reuse ladder, no-progress retry stop and documented boundaries; no new runtime, unapproved CLI spawning or Git mutations.

- Isolated experimental branch: new-build RESEARCH/VERIFY stage gates with structured host evidence, legacy-build compatibility and curated role-specific skill preferences (native fallbacks; no auto install).

- Next: persistent OS process supervisor and optional secure sharing. Actual host autonomous coding and permissions remain host-owned.

## [0.24.0] — Unreleased (feature branch)
- Add incremental revision-guarded `orbit_intake_answer` and dependency-checked `orbit_intake_followup`; support conditional interviews rather than a fixed upfront question batch.
- Add deep domain-analysis and reuse-before-reinventing policy to project intake and specialist workflow; clarify that agent-browser is a separate prebuilt QA provider.
- Add stable local Orbit CLI with read-only host detection and checksum-verified release updates (preview default, explicit apply). Add opt-in native VS Code MCP configuration.
- Add five SQLite-backed intake/autonomy/doc-audit tools, enforce interview acceptance before new MCP build creation, preserve earlier build runs. Tool count 29; host UI still owns real consent and writing.
- Add guided fresh-project intake interview (recommended answer options), type/complexity/maturity classification, right-sized canonical docs policy and compact prompt/hand-off contract in installed host references. This guidance is host-executed; no new MCP stage gate is claimed.
- Ensure installer delivers Orbit skill references to Antigravity, Codex and Claude Code, with preview/backup-aware upgrades; enable writer's native file tools when supported.
- Recognize the optional Vercel Labs `agent-browser` MCP provider in capability selection; add opt-in host integration instructions and trust-status reporting. No binary bundling, automatic installs, or third-party QA gate bypass.
- Browser QA compatibility: discover installed Microsoft Edge/Chrome and support explicit browser selection; avoids mandatory Chromium download on Windows.
- Add three opt-in localhost preview MCP tools: start, status and stop.
- Prevent automatic adoption of foreign processes; enforce approved, shell-free runtime commands and loopback HTTP readiness checks.
- Bounded process logs and per-session lifecycle management; never start a public tunnel or deploy.
- Add real HTTP smoke tests and safe installer upgrades from stock v0.23.0 installations.
- Add approved local Playwright Chromium browser QA with mobile/desktop screenshots, bounded DOM assertions and external-browser-network blocking.
- Add four MCP tools for durable SQLite build-stage orchestration and browser QA; total 24 tools.
- Require real preview readiness, recorded interactive browser pass and managed checkpoint before advancing respective build stages.
- Update host instructions, installer and Claude Desktop extension; real host-native agent execution remains unverified.
- Persistent process supervisor, cloud-free remote preview sharing, and independent background model execution are **not** implemented.

## [0.23.0] — 2026-10-26
- Baseline snapshot of the previously created ORBIT Universal Setup v0.23.0 source and installation package.
- User-level and project-level installs for Antigravity, Codex and Claude Code, with preview-first conflict handling.
- Shared local SQLite memory, task ledger, checkpoints, and 17 MCP tools.
- Read-only capability discovery and selection with permission gates for third-party installations.
- Claude Desktop MCPB extension package retained.

> Note: Earlier v0.18.0–v0.22.0 versions were ChatGPT plugin/distribution iterations, not a reconstructed Git commit history. Do not fabricate historical Git commits. This is the **first Git baseline**.
