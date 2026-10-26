# v0.24.0 milestone proposal — Emergent-like local preview

**Status: PLANNED, not implemented**. This stays separate from the v0.23.0 Git baseline until the source is published and reviewed.

- Local Preview Manager: start/stop/restart a project-approved development server, strict command allowlists, project-scoped paths, logs, readiness checks, random port assignment and localhost-only binding by default.
- Browser Verification: prefer host browser tools; if unavailable, propose Playwright test install after security review. Capture screenshots, console errors and acceptance results.
- Build → preview → test → repair → retest loop with bounded retries and cost limits.
- Return a **verified** localhost link; never invent a URL. Optional temporary public tunnel only with explicit approval and separate security/auth review.
- Add structured supervisor state/checkpoints for safe crash recovery; SQLite task records alone do not keep servers alive.
- Avoid deployment, external URLs, cloud data sync and speculative multi-agent spawning.

**Acceptance test**: a fresh Todo app built in Antigravity and resumed in Claude Code or Codex; app functions, actual browser tests, and local link must be verified. No production-ready claim until live execution proves it.
