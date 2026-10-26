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


## Scoped build approval and minimal reading (Scram/Emergent/Lovable comparison)

User screenshots of Scram show **Scope first / Just start building**, a progressive question interface (audience, selected features, aesthetic), an explicit plan preview and approval, visible tasks in a persistent plan pane and in-progress step updates. Official Emergent guides document selectable Plan/Build, live preview and checkpoints; Lovable distinguishes Chat/Plan/Build with editable plan approval. Orbit adopts these as host-facing behavior **without claiming to provide its own cloud builder UI**.

To stop a vague `PLAN PASS` from silently triggering implementation, newly created build rows carry `__orbit_policy: approval-v1`. Only those rows require structured PLAN evidence with title, summary, tasks, approval_method and a real user consent/delegation reference before the stage can pass. Old builds remain resumable without retroactive interruption; all consent is **host-reported, not cryptographically authenticated by MCP**. `orbit_build_status` includes a task ledger progress summary; no fabricated completion percentage when no tasks are registered.

For token/quota efficiency, don't load all skill instructions or every project document. Use only current references, compact accepted project brief, checkpoint and affected sources. Research is proportional: quick existing-code search for tiny fixes; dependency/license and domain-reasoning research for architectural or risky new products. This is **selective retrieval, not avoidance of necessary thinking**.


## Platform and model decision extension

New separate read-only `orbit_decision_route` and `orbit_model_route` tools distinguish web/native/mobile/SDK/MCP/OS needs, keep custom component options, and recommend model tiers using only the names reported by the active host. Host model changes, installed libraries and iOS/Android device verification remain external and require actual supported tool invocation plus approvals. [Source-reviewed architecture and library matrix](ADAPTIVE-DECISION-ENGINE.md).
