# Orbit guided project intake (v0.24 development candidate)

**Before planning a fresh nontrivial project, interview the user; do not silently choose the stack.** This is host-model behavior, not an independent AI service or new MCP tool.

1. Audit the actual project, Git branch, README, requirements, docs, ADRs, existing stack, .orbit/STATE.md and decisions. **Do not repeat an interview on a resumed or already specified project.**
2. Interpret everyday language ("build a todo app") into a compact **PROPOSED** brief: goal, audience, product, feature scope, non-goals, quality constraints, acceptance criteria and unanswered decisions. Do not invent auth, cloud hosting, team accounts, spending or safety-sensitive features.
3. Classify separately: **type** (website, web-app, desktop-app, mobile-app, API, CLI, SDK/library, plugin/MCP, OS/platform, game, data/automation, other); **complexity** (simple, moderate, complex, high-assurance); **maturity** (spike, prototype, product, production-critical); **risk** (normal, sensitive/high). These are proposals, not user decisions.
4. Ask **one highest-impact consequential question first**, with options, a **Recommended** choice and a brief reason. After the answer, decide whether another relevant question is necessary. Include **Use recommendations / Customize** when helpful. Prioritize audience, delivery platform, release maturity, offline/sync/persistence, authentication/privacy and stack preference only when consequential. The user need not know tech names; offer the best maintainable default given the verified environment. **Pause before choosing architecture or creating the PLAN** unless the user already answered or explicitly asked Orbit to choose defaults. No endless questioning; never re-ask settled choices.
5. Right-size the interview. Simple fix or script: usually none. Todo product: personal/team, web/mobile/desktop, local/cloud, prototype/production and UI style. SDK: public API, supported languages/runtimes, compatibility, versioning, examples and distribution. OS/platform: distinguish desktop shell/distribution/kernel, target hardware, drivers, privilege/trust boundaries, test environment and realistic milestones. SaaS: users, tenancy, auth, billing, privacy/retention, deployment. Security-critical: demand confirmed constraints and reviews rather than guessing.
6. On acceptance, preserve agreed answers in a short project brief/index (see DOCS-AND-CONTEXT.md), generate only the applicable canonical docs, and build milestones. If a required high-risk choice is unanswered, report BLOCKED rather than invent a decision.

**Example interview for "build a todo app":**

- Audience: **Recommended personal/single user**, or shared team
- Target: **Recommended responsive web**, or native desktop/mobile
- Storage: **Recommended local SQLite**, or cloud sync/browser-only
- Maturity: **Recommended local prototype with tests**, or production
- Appearance: **Recommended accessible clean dashboard**, or minimal/custom

"Reply *Use recommendations* or tell me which choices to change." These are recommendations, not a universally mandated stack. A user who says "choose sensible defaults and build" has authorized normal defaults; show the choices in the compact brief and proceed without another round-trip.


## Adaptive single-decision interview (not a static form)

Ask **one highest-impact question at a time**, with 2–4 concrete answer options, a recommended choice and reason. When the user answers, call `orbit_intake_answer` using the real choice and revision. Reassess the **task**, domain invariants, dependencies, architecture consequences and remaining uncertainty, not just a predefined form. If the previous answer changes what matters, call `orbit_intake_followup` with `based_on_id`, the stored `based_on_choice`, and a reason. The MCP rejects a follow-up unless its parent answer has actually been recorded. Do not invent answers or present conditional branches that don't apply.

Stop when the significant decisions are resolved (typically **2–5**, max 6), or the user explicitly authorizes recommended defaults; summarize the final agreed choices and use `orbit_intake_approve`. For low-risk tiny tasks, prefer one compact choice or explicit default. Don't quiz users on tech trivia. A high-risk decision may need a separate explicit confirmation; don't dilute it into a bulk default.

### Deep analysis before asking

Write a short *internal task model* before the first question: `requested outcome / user and operating context / product category and maturity / domain rules and edge cases / must-not-do / quality gates / existing code/docs/libs / most expensive wrong assumption`. The first question resolves that most expensive assumption; the next one depends on the answer. Update and compact the task model after each choice, not the whole conversation transcript.

For habit tracking: daily versus weekly target semantics; local-calendar boundaries; streaks and backdating; actual/demo starting data; offline versus synced accounts; persistence/backup recovery; accessibility, reduced motion and audio preferences. **Never invent historical personal activity merely to make a dashboard look populated.** Add contract tests for the chosen domain rules.

### Reuse before reinventing

Before selecting a stack or coding algorithms, run `orbit_capability_discover` / `orbit_capability_select`, inventory the existing repo and native host capabilities, and evaluate maintained existing libraries/frameworks appropriate to the task. Prefer: (1) existing trusted project code or native platform API; (2) vetted prebuilt library/tool already available; (3) justified custom implementation for small/trivial components or when no suitable library exists. Consider actual functionality, license, maintenance, current security posture, version/runtime compatibility, bundle/installation impact and developer experience. Explain `reuse / custom / no dependency` in one compact decision note. Don't add dependencies for prestige or reimplement reliable date/time, schema validation or browser automation simply to claim zero dependencies.

**User-provided reference:** Vercel Labs `agent-browser` (https://github.com/vercel-labs/agent-browser) is a prebuilt **browser automation / visual QA** tool—not a Habit Tracker UI library. If installed, connected and permitted, use it for semantic snapshots and interaction QA. Existing Orbit Playwright gate is separate; a host-only agent-browser report is not an Orbit-attested gate PASS. Do not install it, other libraries or downloadable tools without approval.


## Research stage before planning

For new product build IDs, an accepted interview begins the RESEARCH stage. Assess task type, domain invariants, existing source, native platform features, verified prebuilt components and potential license/security issues. Provide concise structured `orbit_build_advance` evidence as a JSON **string**: `task`, `candidates` (list), `decision`, `sources` (list), `risks` (list). Only move to PLAN after research is approved. A resumed existing build remains at its stored stage.


## Choose depth and adapt like a product manager

For a fresh high-level request, the **first choice** is `Scope first (recommended)` vs `Build using sensible defaults`, optionally `Custom description`. Choosing build means **explicit delegation of low-impact defaults**, not approval to deploy, install third-party tools or invent high-risk features. In scope mode ask at most one highest-leverage question per turn, with clear recommendations, multi-select only if the decision logically allows several features, and always a free-form choice. Use the actual user answer before selecting the next question; never force a questionnaire script. Show the impact of the selected answers in a brief and let user amend it.

Before IMPLEMENT show the **plan**: title, purpose, key user journeys, reusable components/stack rationale, milestone tasks, tests, risks and `Approve / Request changes`. Include 3–8 useful tasks for ordinary applications, fewer for tiny edits and more only for complex projects. Accepted plan evidence is a JSON-encoded object `{"title":...,"summary":...,"tasks":[...],"approval_method":"user_approved_plan"|"user_delegated_build","approval_reference":...}` with actual user evidence. No host model may self-approve an un-delegated plan.


## Free-form answers supported in the MCP

Every recommended question offers `Use recommended`, named choices **and Custom — enter your own words**. A user can describe a new native platform, unusual hardware, bespoke reusable component or nonstandard workflow. The assistant records exactly that string with `orbit_intake_answer` (max 500 chars); a bare `Custom` means ask for the actual user description first, not approve the literal word. Answer-dependent followups can compare custom answers by exact stored value. Only source-verified user answers or explicit delegated defaults can approve intake. If someone asks for fully custom components, do not discard established accessibility, privacy or QA checks. No artificial extra questioning when the user's free-form answer already resolves the decision.

## Antigravity artifacts are the visible plan and approval UI

Prefer host-native Implementation Plan review with inline comments, Proceed/Review and a Task List. User may request edits before consent. Use `orbit_build_feedback` to retain real requests (reference the host artifact/comment), revise that *same* plan, resolve only when revised, and obtain fresh approval for the actual revised plan before `orbit_build_advance`. Orbit's SQLite is a stage/task checkpoint, not an independent duplicate of the artifact. When that UI is unavailable, a Markdown plan and explicit text approval are valid fallbacks.
