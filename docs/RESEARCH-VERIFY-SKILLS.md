# Research and verification gates; preferred skills and component reuse

This experimental branch is **not** main or v0.25. Built from v0.24.

## Lifecycle design
**Fresh** application build IDs start at `RESEARCH`, then `PLAN → IMPLEMENT → VERIFY → PREVIEW → BROWSER_QA → REVIEW → CHECKPOINT → DONE`. Existing builds stay at their previously persisted stage and revision.

At RESEARCH, `orbit_build_advance` requires `evidence` to be a **JSON-encoded string** with nonempty fields:
```json
{"task":"Habit Tracker domain and scope","candidates":["existing platform APIs","maintained date library"],"decision":"Use native DOM and review tested date utilities","sources":["docs/ARCHITECTURE.md"],"risks":["weekly targets and calendar-day gaps"]}
```
Source references must be independently reviewed by the coding host. Orbit MCP validates structure, not citation truth.

At VERIFY, `evidence` must be JSON encoded:
```json
{"commands":[{"command":"node --test tests/*.test.cjs","exit_code":0}],"edge_cases":["gapped daily streaks and weekly 3-of-7 target tested"],"security":["backup validation and escaping tested"]}
```
The host must actually execute the commands and inspect results. **MCP does not run or independently attest CLI tests.** Later PREVIEW and BROWSER_QA still require the real managed localhost server and recorded Playwright interactive pass.

## Role-specific skill preferences
`orbit_capability_select` with `objective` beginning `orbit-frontend:`, `orbit-qa:`, `orbit-security:`, etc. returns `role_skill_preferences`: hard-coded candidate names, official sources, applicability, installed status, and fallback.

- Frontend/UX: Vercel `react-best-practices`, `web-design-guidelines`; Anthropic `frontend-design`; optional `impeccable`.
- QA: Anthropic `webapp-testing`; Trail of Bits `property-based-testing`; optional Vercel Labs `agent-browser` MCP.
- Security: Trail of Bits `static-analysis`, `insecure-defaults`, `supply-chain-risk-auditor`.
- Architect/research: Trail of Bits `trailmark`; Anthropic `mcp-builder` only when building MCP software.
- Backend/data: `modern-python` only when Python applies, or `property-based-testing`.
- Writer: Vercel `writing-guidelines`; Anthropic `doc-coauthoring`.
- Reviewer/integrator: Trail of Bits `spec-to-code-compliance`, `code-improver`.
- DevOps: `open-sourcing` only when publishing OSS; supply-chain review as needed.

**These are preferred research candidates, not mandatory downloads, installed plugins or guarantees of "best."** Every agent checks for installed approved skills first and otherwise uses current host capabilities. Any new skill/MCP install needs an explicit consent and provenance/security review.

Official upstream indexes: https://github.com/vercel-labs/agent-skills, https://github.com/anthropics/skills, https://github.com/trailofbits/skills, https://github.com/vercel-labs/agent-browser.

## Scram-style reusable components
Scram says it assembles apps from pretested building blocks: https://www.scram.com. Orbit adopts the **reuse-first decision flow**: verified project components/native APIs → approved versioned templates → appropriately reviewed existing libraries/skills → narrowly scoped custom code with tests. It does **not** include or license Scram's proprietary building blocks. The policy and catalog suggestions are implemented; a separate production-grade, vetted component-block repository is **not yet built** and should not be claimed.

Acceptance is not only UI click-through: test relevant business/domain rules (calendar streaks, weekly targets, data validation, persistence failure, XSS), accessibility and actual documentation consistency. Avoid a 15-stage bureaucracy for simple scripts.
