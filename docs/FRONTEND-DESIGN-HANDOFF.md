# Orbit Core frontend design handoff — v0.32 development contract

**Status: PROPOSED, NOT APPROVED / NOT HOST-ACCEPTED.** This technical note describes how the **existing** Creative Director, UX, Frontend and QA specialist profiles should cooperate. It creates no agent, MCP tool, model, design editor, editable artifact, process or approval. Product/design decisions stay in the Orbit Core Notion hub; this document is source-adjacent specialist guidance.

## When to use

Only for genuine visual work on web, mobile, desktop or game products; do not force UI design onto APIs, CLIs, SDKs or small nonvisual bug fixes. `orbit_specialists.plan` returns an optional **read-only** `design_handoff` outline for visual build/add-feature/redesign/maintain/resume operations. The outline is untrusted review metadata, **not** signed owner approval, a granted tool or proof that a design file exists. A permission denial returns no design handoff.

## Handoff sequence

1. **Orbit main agent** identifies the exact project/branch/source revision, user-approved scope, existing UI and host capabilities. Do not create an additional design agent roster or change the host's model. Authorize only task-specific specialists and bounded file scopes.
2. **Creative Director** inspects current design files and code, then proposes or references accepted tokens, typography, spacing, hierarchy, colors, components, motion and platform conventions. Preserve owner design files. Mark new direction `PROPOSED` until accepted; link the actual approval/decision source instead of inventing authority.
3. **UX** translates accepted direction into affected journeys/screens, navigation/interaction states, accessibility and platform breakpoints. Include loading, empty, error and partial states and a source/design revision. If acceptance or document identity is missing, return `HOLD`; do not send unverified instructions to workers.
4. **Frontend** implements against the project's actual framework and approved design contract. Reuse existing components and tokens; don't silently replace the design system, import new libraries, enable a remote model or write beyond assigned paths. Report actual source diff, tested commands/exit status, unresolved decisions and what the QA reviewer must reproduce.
5. **QA** independently checks the *running application* against accepted design and source revision, including viewport/breakpoint, keyboard/focus, contrast, reduced-motion and major UI states. Report exact browser/session, loopback origin, screenshots or actual observations, and source fingerprint. No canvas mockup, lint report, unobserved host invocation or model self-assessment constitutes a UI QA PASS. Follow the current `orbit_build_advance` and QA integration gates; PR #104's alternate host-native browser evidence remains a **separate unmerged** change.

## Minimal inspectable handoff record

Use existing project documents and the existing Orbit task ledger/events. Do **not** introduce a competing SQLite table or mandatory `DESIGN.md` file. A normal specialist report should identify:

- Project identity, current branch, exact source and design-artifact revisions.
- Approved design reference versus proposed/unresolved decisions, linked to the appropriate authority.
- Screen list, reusable components, design tokens, responsive layout and keyboard/motion requirements.
- Clear permitted write paths and target technology; report whether optional tools were actually connected and approved.
- Changed source files, test/preview commands and exit results.
- Independent QA observations, evidence freshness, source match, residual risks and `PASS`/`FAIL`/`BLOCKED`/`NOT RUN` state.

## External design-tool policy

[OpenDesign](https://github.com/nexu-io/open-design) (Apache-2.0) is an external design-system/scratch-workspace research reference; don't install its daemon or copy skill catalogs into Orbit. [Pencil/pen.dev](https://www.pen.dev/) is a **proprietary** optional user-selected visual canvas; follow its terms, genuine tool permissions and document identity. [OpenPencil](https://github.com/open-pencil/open-pencil) (MIT, beta) is a separate optional local design inspection/CLI/MCP reference; don't turn on code evaluation, imports or writes automatically.

For any external provider, discover actual native tools and signed-in document context first; a configured MCP name is not proof of liveness. Prefer existing app assets and host-native screenshot/browser tools. Use disposable project-local copies and exact path scopes for experiments. Never install dependencies, upload proprietary designs, send credentials, spawn provider agents or route traffic outside the authorized origin without the owner's explicit consent.

## Completion criteria

A disposable real UI project passes an accepted design→source implementation→independent rendered-app QA sequence, with exact-source evidence, no unrelated file changes and no hidden external provider action. Windows/Linux CI proves only source regressions; Codex/Antigravity real-host behavior and installer packaging require separate authorized acceptance. Merging and publishing remain owner-controlled.
