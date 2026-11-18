# Orbit Core v0.33 — visual decisions, reuse and UI coverage (development)

**Status: PROPOSED SOURCE / REVIEW ONLY.** Product policy is decided in the Orbit Core Notion hub; this is a technical implementation and acceptance contract. It builds on the existing v0.32 \`orbit_decision_route\`, \`orbit_specialists.plan\`, Creative Director/UX/Frontend/QA roles, project intake, and QA stages. It adds no permanent worker, external model, dependency install, database, global user preference, or release.

## New project: the correct starting point

1. Inspect the selected root and existing project decisions. A new empty project begins with its objective, users, target platform, important constraints and success criteria, **not automatic creation of DESIGN.md**.
2. Ask at most the next material intake question; reuse previously approved answers. Use owner-delegated defaults where supported, but do not manufacture consent or force a fixed interview.
3. Research current official sources and relevant competitor/product patterns for nontrivial choices. Prefer the smallest shortlist compatible with the actual product type, framework, license and quality needs. Do not force frontend research onto a CLI/API/SDK.
4. Present a brief and, for substantial visual products, compare distinct visual directions. Record the actual decision before coding a new visual identity.
5. Inspect existing design docs. **Create or update** \`DESIGN.md\`, \`UI.md\` or project-native tokens *only when useful and approved*. It is neither the first task nor a mandatory new artifact. Avoid shadow documentation.
6. Plan screens, shared shell, states, components and responsibilities. Implement against the approved design. Test the running app and report missing work.

Current implementation: \`orbit_decisions.components\` includes additive \`reuse_policy\`, \`new_project_design_order\` and source-review guidance. \`orbit_specialists.visual_decision\` supplies a bounded, read-only decision for build, redesign, fix and feature work. **These functions do not write or approve design artifacts.**

## Component source precedence

| Tier | Meaning | Policy |
| --- | --- | --- |
| 1 | Existing tested project components, styles, icons and tokens | Reuse and check exact public contracts first |
| 2 | Already approved project dependencies and component registries | Prefer consistent variants without silent migrations |
| 3 | External vetted libraries, official registries or references | Verify framework, source/version, license, maintenance, security, accessibility, dependencies and quality before recommending |
| 4 | Custom component or icon | Honor explicit user requests; justify deviation and test keyboard, focus, states and motion |

The source catalog in \`orbit_decisions.py\` gives **unverified, static reference pointers**, not dynamic trust scores or permission to import code. Existing source candidates include [shadcn/ui](https://ui.shadcn.com), [Radix](https://www.radix-ui.com), [React Aria](https://react-aria.adobe.com), [Lucide](https://lucide.dev), [Motion](https://motion.dev), and beta [Vercel Labs UI SDK](https://github.com/vercel-labs/ui). UI SDK supplies interaction behaviors, not a theme or complete design. Further examples, such as [Uiverse](https://uiverse.io), are research references only. Third-party skills such as AAS Core, Impeccable and design editors are **different from installable UI components**. Scram, Emergent and Lovable are workflow inspiration, not Orbit runtime dependencies.

**Do not auto-install, import, bulk-clone, open external links with credentials or create a new agent** merely because a reference is listed. Review updates on demand for substantive decisions. Existing project components may be unsuitable or inaccessible; report those facts rather than treating tier 1 as an unconditional veto.

## Orbit Guide (no new permanent agent)

\`orbit_specialists.guide_decision\` provides read-only advice: **HOLD** on denied permissions, **REQUIRE_OWNER_DECISION** for consequential decisions, **ASK_ONE_MATERIAL_QUESTION** when scope is unclear, **APPLY_SCOPED_EXISTING_STYLE** for a well-scoped correction under an accepted system, **OFFER_SCOPED_ALTERNATIVES** otherwise.

Preference precedence: explicit current request > approved project decisions > explicitly approved, applicable user preferences > reversible justified defaults. A one-off "I dislike this home icon" is **not a global ban on an icon pack**. Record any durable correction only through existing project-scoped improvement practices, with actual permission. Cross-project preference promotion requires the existing privacy and owner review. Do not create an Orbit Coach worker until a measured task-specific gap justifies one.

Example: "replace my home icon" → inspect actual icon set and usage, propose or apply one accessible replacement within approved scope, re-check other occurrences and hover/focus states; do not redesign navigation or install a new icon library. "Make everything premium" → inspect source and current visual references; ask which impactful direction the owner prefers before broad changes.

## Refactor coverage and independent visual QA

Before broad refactors, the host/frontend worker must inventory the affected **routes/screens, global shell, shared components and dependencies** plus state/breakpoint matrix: default, loading, empty, error, partial, keyboard/focus, reduced motion, responsive widths and zoom where relevant. A scoped icon replacement needs only its actual dependencies and uses. A backend-only request does not invoke the UI gate.

\`orbit_specialists.review_visual_coverage(expected, observations, source_revision)\` is a **Python-level read-only report check**, not a new MCP tool. It fails closed for missing/failed/stale screen-state evidence. An observation must name the screen, state, exact revision, result and evidence reference. Even complete caller-reported evidence yields \`READY_FOR_INDEPENDENT_VISUAL_REVIEW\` **not PASS**: neither the MCP nor the caller report independently proves a browser ran, a screenshot was captured, or permission was granted. Existing Orbit browser/native QA remains the independent host gate. Never mark a partial screen inventory "100% complete"; add newly discovered reachable screens to the acceptance scope.

## Engineering verification

- Focused tests: \`python -m unittest discover -s tests -p 'test_visual_policy.py'\`
- Existing regression: \`python -m unittest discover -s tests -p 'test_specialist_assembly.py'\`, and relevant \`test_intake.py\` coverage
- Before acceptance: Linux/Windows CI plus packaged runtime smoke checks
- Real host (later): in a disposable project, invoke actual Codex and Antigravity MCP and browser tools, compare screenshot baselines against approved direction and test targeted icon changes and large layout refactors. Record actual tool sessions, permissions, revisions, screenshots, failures, and owner feedback.

**Honest limitations:** v0.33 source does not yet expose a native UI manifest scanner or \`review_visual_coverage\` as an MCP endpoint, authenticate user style decisions, implement a UI SDK adapter, persist a new design memory or automatically produce visual mockups. Those require subsequent implementation and independently observed acceptance. Do not merge, tag, install or publish this branch without owner approval and verification.
