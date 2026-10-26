# Changelog

All notable changes are recorded under [Semantic Versioning](https://semver.org/).

## [Unreleased]
- Next: persistent OS process supervisor and optional secure sharing. Actual host autonomous coding and permissions remain host-owned.

## [0.24.0] — Unreleased (feature branch)
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
