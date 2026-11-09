# Orbit research-first workflow — v0.32 development

This reference supplements PROJECT-INTAKE, COMPONENT-REUSE, DOCS-AND-CONTEXT, the build ledger and decision/approval process. It is not a second planner, search agent, or autonomous web crawler.

## Route every substantive project request

1. **Understand before browsing:** identify the exact project, canonical docs, accepted decisions, product type (site/app/API/SDK/OS/plugin/etc.), maturity, goal and decision. In an existing project inspect relevant source, Git, checkpoint and old research first. One essential audience/platform scoping question may precede research when the topic is otherwise undefined.
2. **Research before choosing a stack or roadmap:** compare credible direct/adjacent competitors, applicable open-source repositories, native or existing project components, and official documentation. Evaluate fit, actual user value, license and obligations, activity, security, integration cost and maintainer compatibility. Separate observed facts, vendor claims, inference and unknowns. Research only enough to change the decision.
3. **Recommend a route:** consider REUSE, ADAPT, INTEGRATE, BUILD_NEW and NO_BUILD when relevant. State the best alternative, differentiation, tradeoffs, confidence and reversal condition. Do not claim better than a competitor without a measurable outcome and supporting evidence.
4. **Ask only missing decisions:** show a short source-linked Research Snapshot before architecture/planning. Prefer one grounded, consequential option-led question with a recommended choice, custom path and delegated defaults where allowed. Never re-ask approved decisions or treat agent preference as approval.
5. **Gate before building:** research PASS/PROVISIONAL/BLOCKED must be truthful. Only after a sufficient research synthesis choose the right-sized canonical docs, architecture and single Milestones → Gates → Steps roadmap, then execute approved tasks and verification. Existing owner-maintained docs win; GitHub owns code; project-specific SQLite/checkpoints own live execution state.
6. **Stop and preserve context:** record bounded source links and accepted decisions through the existing authorized project store. Do not bulk-copy external websites, clone competitor assets, create duplicate PRDs or run unapproved dependencies.

## Scale with the task

- **New product/architecture:** compare actual competitor experiences, adjacent substitutes, relevant maintained OSS, licensing and feasibility. If no comparable option exists, document where checked and why.
- **Existing feature/redesign:** inspect actual code, prior decisions, relevant UX patterns, maintained libraries and constraints before creating or changing the plan. No new-project interview or unnecessary competitor catalog.
- **Bug/test/security fix:** reproduce and research code history, upstream SDK docs, known issues and risks. No unrelated market survey. Small fixes can proceed with a focused investigation and targeted tests.
- **Trivial/non-project request:** skip irrelevant research. If no host browser/network is accessible, mark external claims NOT VERIFIED and do not invent sources.

## Versioned MCP research gate

New full builds from the v0.32 development source have the policy marker __orbit_research_policy = comparison-v1. Their RESEARCH → PLAN PASS requires a JSON string (maximum 4500 characters) passed to orbit_build_advance.evidence, containing the original five fields plus a dated competitor/OSS comparison and route choice. Legacy persisted builds without this marker retain the original five-field schema. Scoped fixes retain their targeted investigation path.

Example with intentionally synthetic URLs (not actual research):

~~~json
{
  "task": "Select approach for an offline personal todo app",
  "candidates": ["Native web APIs", "Reviewed open-source task list"],
  "decision": "Integrate a reviewed local component and keep data local",
  "sources": ["https://example.org/tasks", "https://github.com/example/task-list"],
  "risks": ["Confirm backup recovery and actual upstream license"],
  "competitors": [{"name": "Example Tasks", "source": "https://example.org/tasks", "finding": "Alternative supports basic list onboarding"}],
  "open_source": [{"name": "Example List", "source": "https://github.com/example/task-list", "license": "MIT", "finding": "Potential checklist primitive"}],
  "exceptions": {},
  "routes_considered": ["REUSE", "INTEGRATE", "BUILD_NEW", "NO_BUILD"],
  "selected_route": "INTEGRATE",
  "unknowns": ["Real compatibility checks still required"],
  "checked_on": "2026-11-09"
}
~~~

Each comparison category allows up to six bounded entries with the exact fields shown. If no relevant competitor or OSS exists, that list may be empty only with a corresponding concrete exception reason (at least 16 characters) keyed by competitors or open_source, and the sources list must still provide investigated references. Routes must include BUILD_NEW and one alternative; the selected route must be considered. Unknowns can be empty only if none are material.

**Important:** The MCP can validate structured host-reported evidence; it does not browse websites, validate GitHub repositories or licenses, independently confirm freshness, authenticate user permissions, or run tests. The host must actually inspect sources before reporting PASS. When the evidence is inadequate, RESEARCH remains on HOLD before PLAN. For provisional experiments, explicitly bound the validation objective without misrepresenting production readiness.

## Acceptance scenarios

- Build an AI reviewer: discover existing reviewers and OSS alternatives before stack selection and justify differentiation.
- Build a todo app: concise real alternatives and a small decision, not a speculative enterprise-scale document pack.
- Continue a half-built product: inspect source, saved decisions and checkpoint; do not restart as a fresh build.
- Fix an existing microphone bug: compare old working code with current SDK behavior, not a market analysis.
- Resume an old persisted RESEARCH build: accept its legacy evidence schema without retroactive migration.
