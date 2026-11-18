# Orbit Core v0.33 — visual decisions, reuse and UI coverage (development)

**Status: PROPOSED SOURCE / REVIEW ONLY.** Product policy is decided in the Orbit Core Notion hub; this is a technical implementation and acceptance contract. It builds on the existing v0.32 `orbit_decision_route`, `orbit_specialists.plan`, Creative Director/UX/Frontend/QA roles, project intake, and QA stages. It adds no permanent worker, external model, dependency install, database, global user preference, or release.

## New project: the correct starting point

1. Inspect the selected root and existing project decisions. A new empty project begins with its objective, users, target platform, important constraints and success criteria, **not automatic creation of DESIGN.md**.
2. Ask at most the next material intake question; reuse previously approved answers. Use owner-delegated defaults where supported, but do not manufacture consent or force a fixed interview.
3. Research current official sources and relevant competitor/product patterns for nontrivial choices. Prefer the smallest shortlist compatible with the actual product type, framework, license and quality needs. Do not force frontend research onto a CLI/API/SDK.
4. Present a brief and, for substantial visual products, compare distinct visual directions. Record the actual decision before coding a new visual identity.
5. Inspect existing design docs. **Create or update** `DESIGN.md`, `UI.md` or project-native tokens *only when useful and approved*. It is neither the first task nor a mandatory new artifact. Avoid shadow documentation.
6. Plan screens, shared shell, states, components and responsibilities. Implement against the approved design. Test the running app and report missing work.

Current implementation: `orbit_decisions.components` includes additive `reuse_policy`, `new_project_design_order` and source-review guidance. `orbit_specialists.visual_decision` supplies a bounded, read-only decision for build, redesign, fix and feature work. **These functions do not write or approve design artifacts.**

## Component source precedence

| Tier | Meaning | Policy |
| --- | --- | --- |
| 1 | Existing tested project components, styles, icons and tokens | Reuse and check exact public contracts first |
| 2 | Already approved project dependencies and component registries | Prefer consistent variants without silent migrations |
| 3 | External vetted libraries, official registries or references | Verify framework, source/version, license, maintenance, security, accessibility, dependencies and quality before recommending |
| 4 | Custom component or icon | Honor explicit user requests; justify deviation and test keyboard, focus, states and motion |

The source catalog in `orbit_decisions.py` gives **unverified, static reference pointers**, not dynamic trust scores or permission to import code. Existing source candidates include [shadcn/ui](https://ui.shadcn.com), [Radix](https://www.radix-ui.com), [React Aria](https://react-aria.adobe.com), [Lucide](https://lucide.dev), [Motion](https://motion.dev), and beta [Vercel Labs UI SDK](https://github.com/vercel-labs/ui). UI SDK supplies interaction behaviors, not a theme or complete design. Further examples, such as [Uiverse](https://uiverse.io), are research references only. Third-party skills such as AAS Core, Impeccable and design editors are **different from installable UI components**. Scram, Emergent and Lovable are workflow inspiration, not Orbit runtime dependencies.

**Do not auto-install, import, bulk-clone, open external links with credentials or create a new agent** merely because a reference is listed. Review updates on demand for substantive decisions. Existing project components may be unsuitable or inaccessible; report those facts rather than treating tier 1 as an unconditional veto.

## Orbit Guide (no new permanent agent)

`orbit_specialists.guide_decision` provides read-only advice: **HOLD** on denied permissions, **REQUIRE_OWNER_DECISION** for consequential decisions, **ASK_ONE_MATERIAL_QUESTION** when scope is unclear, **APPLY_SCOPED_EXISTING_STYLE** for a well-scoped correction under an accepted system, **OFFER_SCOPED_ALTERNATIVES** otherwise.

Preference precedence: explicit current request > approved project decisions > explicitly approved, applicable user preferences > reversible justified defaults. A one-off "I dislike this home icon" is **not a global ban on an icon pack**. Record any durable correction only through existing project-scoped improvement practices, with actual permission. Cross-project preference promotion requires the existing privacy and owner review. Do not create an Orbit Coach worker until a measured task-specific gap justifies one.

Example: "replace my home icon" → inspect actual icon set and usage, propose or apply one accessible replacement within approved scope, re-check other occurrences and hover/focus states; do not redesign navigation or install a new icon library. "Make everything premium" → inspect source and current visual references; ask which impactful direction the owner prefers before broad changes.

## Refactor coverage and independent visual QA

Before broad refactors, the host/frontend worker must inventory the affected **routes/screens, global shell, shared components and dependencies** plus state/breakpoint matrix: default, loading, empty, error, partial, keyboard/focus, reduced motion, responsive widths and zoom where relevant. A scoped icon replacement needs only its actual dependencies and uses. A backend-only request does not invoke the UI gate.

`orbit_specialists.review_visual_coverage(expected, observations, source_revision)` is a **Python-level read-only report check**, not a new MCP tool. It fails closed for missing/failed/stale screen-state evidence. An observation must name the screen, state, exact revision, result and evidence reference. Even complete caller-reported evidence yields `READY_FOR_INDEPENDENT_VISUAL_REVIEW` **not PASS**: neither the MCP nor the caller report independently proves a browser ran, a screenshot was captured, or permission was granted. Existing Orbit browser/native QA remains the independent host gate. Never mark a partial screen inventory "100% complete"; add newly discovered reachable screens to the acceptance scope.

## v0.33 next slice: source inventory, evidence review and style context

The existing `orbit_decision_route` MCP tool now supports optional read-only inputs, without changing the 57-tool inventory:

- `include_ui_inventory=true`: inspect a bounded number of local source files and infer possible routes, components, local-import consumers, declared icon families, CSS custom properties and package manifest dependencies. No project code runs, hidden dependency trees are skipped, project symlinks are not followed, no files are written, and a SHA-256 reflects the **inspected source snapshot only**, not the Git revision.
- `source_snapshot={source_id,url,version_or_commit,license,compatibility,source_evidence}`: review a host-collected, explicitly pinned component-source claim against Orbit's known official source URLs. No network fetch occurs in Orbit. Even a complete claim returns `REVIEW_SOURCE_CLAIMS` with provenance/license unverified; no install, code import or automatic trust.
- `include_project_style_context=true`: retrieve the existing project/root-scoped improvement ledger's explicitly recorded style-preference claims. Values are human/host-reported, not authenticated instructions and not auto-applied.

Use `orbit_improvement_record(action="record",kind="project-style-preference")` for durable *project-only* preferences; it requires `approval_reference` matching `evidence_ref`, as well as explicit `confirm_write=true`. Before writing, the host must verify the user's actual request and show the proposed preference. The existing archive action reverses a preference by key and revision. Normal icon-feedback observations remain just observations, not approved preferences. This reuses the existing local SQLite ledger rather than introducing a competing memory store.

**Scope limitation:** Static scan hints do not discover every route or state; React Router dynamic config, API-provided UI, Electron native shells, protected routes, tabs, modal states, aliased imports and runtime navigation may be missed. The inventory **always** reports `HEURISTIC_UI_INVENTORY_PARTIAL`, never a claim of complete coverage. The actual running app still needs a source-bound browser/native session, manual route-state review, and owner design acceptance. No online registry connector, automatic design generator, SDK install or project-to-project user preference sharing was added.

## v0.33 visual consistency and route-state review (source-level only)

To help prevent partial refactors where some screens retain old typography, icons, spacing or motion, the existing `orbit_decision_route` provides **optional**, bounded read-only design checks:

1. `include_visual_review=true` scans the same safe local source set used for `include_ui_inventory` and returns `ui_quality_review`. Without an explicitly claimed design contract, it returns `NEEDS_PROJECT_DESIGN_CONTRACT` rather than inventing default tokens.
2. `visual_contract={icon_family,spacing_policy,typography_policy,motion_policy,shape_policy}` compares heuristic icon-library imports and CSS/utility literals with the supplied **project design policy**. Policy values for the four token rules are `token-first` or `allow-literals`. A token-first policy can flag hardcoded `gap`, `padding`, `font-size`, `transition-duration`, Tailwind-style arbitrary values and similar patterns for **manual review**. Mixed icon-family imports and token names not defined in the inspected files are reported as possible drift, never automatically rewritten. CSS variables may be defined elsewhere; browser CSS cascade and approved exceptions must be checked.
3. `qa_plan_scope="full-product"` creates a provisional route checklist from discovered source routes. `qa_plan_scope="changed-slice"` requires `qa_target_routes` to specify affected screens. The plan includes candidate default/loading/empty/error/partial/focus/reduced-motion states and responsive/accessibility review areas. **Static discovery cannot prove all real or protected routes are known.**
4. `ui_coverage_packet={source_revision,scope,runtime_routes_reviewed,expected,observations}` invokes the pre-existing `review_visual_coverage` helper through the current MCP tool. `expected` maps screen/route identifiers to required state names; observations contain the exact caller-reported revision, status and evidence reference. Full-product scope **holds** when the reported expected set excludes a source-discovered route. Missing, stale, failed or unrun states remain HOLD. `runtime_routes_reviewed` is a **caller claim**, not authenticated proof; if omitted/false the report holds. Even complete reports return at most `READY_FOR_INDEPENDENT_VISUAL_REVIEW`, never a visual PASS.

These checks do not claim to generate or improve visual appearance. They do not install Vercel UI SDK, a CSS framework, design plugins or third-party skills; do not execute or modify the target app; do not capture screenshots, authenticate user approvals or learn style automatically. They are inputs to the **existing** Creative Director, Frontend and QA workflow. A tiny icon change should use only the affected routes and consumers; a large redesign needs the complete runtime screen/state inventory, approved design baseline and independent host-rendered verification.

## Engineering verification

- Focused tests: `python -m unittest discover -s tests -p 'test_visual_policy.py'`
- Existing regression: `python -m unittest discover -s tests -p 'test_specialist_assembly.py'`, and relevant `test_intake.py` coverage
- Before acceptance: Linux/Windows CI plus packaged runtime smoke checks
- Real host (later): in a disposable project, invoke actual Codex and Antigravity MCP and browser tools, compare screenshot baselines against approved direction and test targeted icon changes and large layout refactors. Record actual tool sessions, permissions, revisions, screenshots, failures, and owner feedback.

**Remaining limitations:** The UI inventory, consistency checks and coverage review are bounded static/caller-report helpers exposed through the existing MCP decision tool, not a complete framework-specific route manifest, authenticated acceptance system or real screenshot engine. Orbit does not yet independently verify style approval, provide a UI SDK adapter, or generate visual mockups. Those require subsequent implementation and independently observed acceptance. Do not merge, tag, install or publish this branch without owner approval and verification.
