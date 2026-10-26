# Orbit improvement roadmap

Source review: `feat/local-preview-manager-v024` at `84ac7dd`, 2026-10-26.
This supersedes the old proposal that called preview and browser QA unimplemented.
The user goal is a capable local agent experience inside an IDE, with guided
setup that becomes less intrusive as a project matures.

## Product decision

Recommended: stabilize Orbit as the local orchestration core for existing coding
hosts first. Then add a thin IDE interface and explicit host adapter contract.
A standalone model runner is a later, separately scoped mode. MCP connects tools;
it does not itself provide inference or a coding-agent execution loop.

Keep local state, project ownership and transparent evidence as differentiators.
Do not claim superiority to another product without comparable task evaluations.
An integrated app builder also needs reliable execution, repair, preview,
backend/database workflows and deployment; more role files alone do not supply these.

## Findings and priorities

| Priority | Evidence in current source | Improvement |
| --- | --- | --- |
| P0 | `orbit_mcp.handle` dereferenced non-object initialize params; validator omitted object/item/maxItems checks; stdin iterated unbounded lines | Focused patch: explicit protocol checks, schema-subset validation, bounded frame reads and regression tests |
| P1 | `orbit_build.advance` consumes browser PASS by build ID; `save_browser` stores no source/spec identity | Bind results to source fingerprint, dirty worktree state, preview generation and acceptance case; invalidate after edits |
| P1 | `orbit_tasks.reserve` accepts only PLANNED; review can produce REWORK with no retry transition | Add explicit attempt history, replan/retry, cancellation and reservation expiry/reconciliation |
| P1 | Preview handles exist only in `SESSIONS`; Windows stop terminates the immediate process | Own process trees, verify termination and ports, reconcile restart without killing unrelated PIDs |
| P1 | Memory primary key is `(project,key)` while build/intake/tasks include roots | Add stable project identity and an explicit mapping/migration; reject ambiguous bindings |
| P1 | `orbit_intake.propose` checks revision before an upsert; approval/autonomy updates do not check rowcount | Transactional compare-and-swap and two-connection conflict tests |
| P1 | Checkpoint is a direct file write after a prior hash read | Atomic replace plus coordination lock and interruption/concurrency tests |
| P1 | CI runs Ubuntu only; Playwright tests skip when dependencies are absent | Windows/macOS smoke jobs and a dedicated required browser job with installed dependencies |
| P1 | Same candidate version has many stock hashes; installer recognizes specific historical bytes | Immutable versioned candidates, per-install manifests, reviewed upgrade diffs, rollback and customization preservation |
| P1 | Release policy marks every 0.x release prerelease; updater `latest()` ignores all prereleases | Define explicit stable/candidate channels and test upgrade discovery for the actual published release policy |
| P2 | Intake choices do not update the profile's original stack/constraints; approved profiles cannot be revised | Versioned user-approved amendments and reconciliation of answers into the operative brief |
| P2 | Resume returns checkpoint/memory/intake but no active task/build overview | Return a bounded unified status with blockers, evidence freshness and next executable action |
| P2 | Fixed build stages always require preview/browser QA | Product-specific gate profiles for CLI, library, API, desktop and web work; explicit not-applicable evidence |
| P2 | Capability selection is keyword-based; VS Code installation exists but discovery omits its configs | Typed host capabilities, connection probes and complete supported-host discovery |

## Milestone 1 — trustworthy local foundation

Owner: Orbit maintainer. Dependencies: current candidate branch and disposable test projects.

1. Land protocol regression fixes and regenerate the desktop bundle; verify source/archive parity.
2. Bind evidence to code/spec/preview identity; demonstrate that editing after QA prevents a stale PASS.
3. Implement task retry attempts and recoverable leases; test failure → repair → independent review.
4. Fix transactional intake and checkpoint concurrency; test competing writers and interrupted writes.
5. Exercise installation, upgrade, preview stop and restart on Windows plus one Unix host.

Gate: **REWORK** until evidence freshness, recovery and desktop acceptance pass.
Deliverables: focused reviewed patches, regression cases and recorded host acceptance.
Fallback: keep existing candidate available and preserve user state/customizations;
never force overwrite an unknown installation. Owner approval governs merge/release.

## Milestone 2 — dependable build, test and repair

Owner: host-adapter/runtime implementer, to be assigned. Depends on Milestone 1.

Define a host execution contract with real run IDs, progress events, cancellation,
timeouts and result artifacts. Have the host execute a bounded repair loop using
specific acceptance tests and a retry/time budget. Persist attempts and stop
reasons. Add worktree isolation when concurrent edits are actually needed.

Gate: **HOLD** pending Milestone 1. A deliberately broken sample must be repaired,
retested, and resumed after interruption without duplicate edits or false success.
Fallback: sequential host execution with an actionable recovery checkpoint.

## Milestone 3 — clear IDE experience

Owner: IDE adapter/UI implementer, to be assigned. Depends on Milestone 2.

Start with one host and a thin panel for goal, plan, current step, preview,
changes, approvals and evidence. Preserve the host's actual permissions. Guided,
assisted and trusted modes should change routine interaction frequency within
explicit scopes, not silently expand access. Add backend/API and database
verification alongside browser tests, then opt-in deployment recipes with rollback.

Gate: **HOLD**. A fresh user can complete and resume representative tasks, see why
work stopped, and inspect proof without memorizing MCP calls. Fallback: CLI/host
chat using the same orchestration core; no IDE fork required.

## Milestone 4 — measured differentiation and optional standalone runner

Owner: product/evaluation owner, to be assigned. Depends on measured host-mode outcomes.

Evaluate identical briefs: Todo persistence, authenticated CRUD, API-only service,
existing-repository bug repair, interrupted-session recovery and upgrade with
customized files. Record functional acceptance, regressions, elapsed time,
model/tool cost where available, number of user interventions and recovery success.
Include blind UI review where relevant. Record models, versions and environment.

Gate: **HOLD**. Claims such as better reliability or lower cost require reproducible
comparative results. Only then decide whether an independent model/provider loop,
credential handling, streaming, quotas and local execution sandbox justify a
separate standalone mode. Fallback: retain host-native execution.

## Validation scope

The original audited checkout ran 40 tests: 37 passed and 3 skipped. Two skipped
cases require live Playwright/Chromium; another needs a prior-version source
fixture. This is not evidence of real Antigravity/Codex/Claude desktop operation.
The focused protocol patch adds separate regression and desktop parity checks;
its PR records the updated test totals. Full browser/OS isolation, a security audit,
and performance comparisons remain unverified.
