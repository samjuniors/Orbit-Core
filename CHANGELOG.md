# Changelog

All notable changes are recorded under [Semantic Versioning](https://semver.org/).

## [Unreleased] — post-v0.25.1 work
- **Orbit Evidence Lens (merged source, not published):** original folder+project-scoped SQLite research source pointers with preview-first, revision-guarded review; bounded objective-relevant context pack and untrusted-source warnings. No automatic crawler, source execution, Git research notes, global cross-project sharing or new model service. Existing local memory retained; requires real IDE/local install acceptance.
- **Research/context milestones:** approved M1–M5 roadmap for scoped research memory, native-agent handoffs, evidence authentic QA, adaptive skills/context and optional verified learning, without adopting ECC's runtime or a universal auto-learning hook system.

- No additional published changes. `NEXT_VERSION=0.25.2` is planning metadata only.

## [0.25.1] — Install-once update experience (candidate; NOT PUBLISHED)

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
- **Not yet released:** host-specific approval evidence, comprehensive threat-model fixes, real IDE/browser acceptance, cryptographic provenance and updated versioned desktop installer remain gates. `v0.24.1` artifacts and tags stay unchanged.

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
