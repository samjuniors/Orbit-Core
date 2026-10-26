# Orbit guided project intake (v0.24 development candidate)

**Before planning a fresh nontrivial project, interview the user; do not silently choose the stack.** This is host-model behavior, not an independent AI service or new MCP tool.

1. Audit the actual project, Git branch, README, requirements, docs, ADRs, existing stack, .orbit/STATE.md and decisions. **Do not repeat an interview on a resumed or already specified project.**
2. Interpret everyday language ("build a todo app") into a compact **PROPOSED** brief: goal, audience, product, feature scope, non-goals, quality constraints, acceptance criteria and unanswered decisions. Do not invent auth, cloud hosting, team accounts, spending or safety-sensitive features.
3. Classify separately: **type** (website, web-app, desktop-app, mobile-app, API, CLI, SDK/library, plugin/MCP, OS/platform, game, data/automation, other); **complexity** (simple, moderate, complex, high-assurance); **maturity** (spike, prototype, product, production-critical); **risk** (normal, sensitive/high). These are proposals, not user decisions.
4. Ask **2–5 consequential questions in one concise group**, each with choices, a **Recommended** option and a brief reason. Include **Use all recommendations / Customize**. Prioritize audience, delivery platform, release maturity, offline/sync/persistence, authentication/privacy and stack preference only when consequential. The user need not know tech names; offer the best maintainable default given the verified environment. **Pause before choosing architecture or creating the PLAN** unless the user already answered or explicitly asked Orbit to choose defaults. No endless questioning; never re-ask settled choices.
5. Right-size the interview. Simple fix or script: usually none. Todo product: personal/team, web/mobile/desktop, local/cloud, prototype/production and UI style. SDK: public API, supported languages/runtimes, compatibility, versioning, examples and distribution. OS/platform: distinguish desktop shell/distribution/kernel, target hardware, drivers, privilege/trust boundaries, test environment and realistic milestones. SaaS: users, tenancy, auth, billing, privacy/retention, deployment. Security-critical: demand confirmed constraints and reviews rather than guessing.
6. On acceptance, preserve agreed answers in a short project brief/index (see DOCS-AND-CONTEXT.md), generate only the applicable canonical docs, and build milestones. If a required high-risk choice is unanswered, report BLOCKED rather than invent a decision.

**Example interview for "build a todo app":**

- Audience: **Recommended personal/single user**, or shared team
- Target: **Recommended responsive web**, or native desktop/mobile
- Storage: **Recommended local SQLite**, or cloud sync/browser-only
- Maturity: **Recommended local prototype with tests**, or production
- Appearance: **Recommended accessible clean dashboard**, or minimal/custom

"Reply *Use recommendations* or tell me which choices to change." These are recommendations, not a universally mandated stack. A user who says "choose sensible defaults and build" has authorized normal defaults; show the choices in the compact brief and proceed without another round-trip.
