# Orbit Core — roadmap and current engineering status

## 2026-11-27 — Current roadmap and acceptance gates

**Live source:** [samjuniors/Orbit-Core](https://github.com/samjuniors/Orbit-Core), revalidated 2026-11-27 22:46 Asia/Kolkata. Main remains `2fdf4f329774b9644e75ac0df4d89738a7cd625f`; `VERSION=0.33.1`; `NEXT_VERSION=0.34.0`. Latest published prerelease is v0.33.0; latest stable is v0.30.0. v0.33.1 and v0.34.0 are unpublished.

### Approved product order and current slices
1. Safe Team Builder foundation (reuse the existing project task ledger and preview; do not create a second registry).
2. Task-specific skills and tools.
3. Orbit-mediated agent/bot coordination.

Focused drafts #179–#182 remain unreviewed. Their prior exact-head CI was 5/5, but model recommendations are advisory, skill PR is test-only, specialist PR adds regression coverage, and the cybersecurity planner is bounded pattern review rather than SAST/penetration testing.

### P0 security and reliability
- **#183 filesystem containment:** draft [PR #186](https://github.com/samjuniors/Orbit-Core/pull/186), head `f81eb1f`, CI #45993595975 PASS 5/5, but stacked on the unapproved context-aware branch. Independent review must settle Windows reparse/handle identity and POSIX descriptor-relative semantics. Microsoft notes ReFS file IDs are 128-bit and the legacy 64-bit index is not guaranteed unique; use FileIdInfo or fail closed on unsupported/ambiguous filesystems.
- **#184 digest privacy:** do not ship source-line-derived `evidence_sha256`; replace with a locator-only reference and accurate field name, add regression tests, rebuild the desktop MCP bundle from exact source, verify parity and rerun exact-head CI.
- **#189 mission lock directory:** PR #187's leaf `O_NOFOLLOW` does not pin the parent directory. Use a per-user private directory pinned by handle and directory-relative leaf creation; Windows reparse-aware validation or fail closed. Until then the lock is best-effort local serialization, not a security boundary.
- **#188 intermittent MCP child crash:** two observed Linux native failures in the shared-DB subprocess test (Python 3.10 exit -6; Python 3.13 exit -11); reruns passed and Windows passed, but root cause is unknown. The updater daemon thread is only a hypothesis. Run 20+ fresh-cache iterations with update check enabled/disabled on both Linux versions, preserve child stderr/exit code/faulthandler, and add deterministic blocked-fetch shutdown lifecycle coverage. Do not mask by permanently disabling updates or relying on reruns.

### P1 bounded autonomy
- [#185 / PR #187](https://github.com/samjuniors/Orbit-Core/pull/187) adds a bounded, sequential foreground Codex CLI mission supervisor with a provider-neutral adapter contract. No native Claude Code/Antigravity dispatch, parallel execution, background service, remote execution, PC-off continuation, authenticated reviewer identity or autonomous merge/release is implemented.
- PR #187 exact-head CI #46037740696 passed 5/5 at previous code head; a documentation correction now qualifies its lock as best-effort and requires new exact-head CI. New issue #189 tracks the code fix.
- Do not merge PR #186 or #187 separately into main while each is stacked on the unapproved 100-commit base `feat/v034-context-aware-intelligence-20261123` (`8620e4a`). Reconcile/split accepted base work first.

### Release posture
v0.33.1 remains unpublished and acceptance-incomplete. Require #183/#184/#189 remediation or independent documented disposition, #188 root-cause evidence, exact-head CI, package parity, owner-profile Claude/Codex/Antigravity acceptance, host permission expiry/revocation evidence, independent human security review, compatibility/release notes and owner go/no-go. No green-CI-only release.

### Current environment
161 branches, 45 open PRs, 11 open issues. Rulesets list is empty; main branch protection API returned 403, so enforcement is unverified. Remote Arc DESKTOP-AND1FUJ and Desktop Commander are offline/unavailable; no local test, bundle rebuild, owner-profile acceptance or `.orbit`/SQLite inspection was performed. Orbit ChatGPT plugin connector is not exposed; GitHub and Notion were used. Orbit Commander remains paused; RAD P2 #138 remains separate.

## 2026-11-24 — Current main and roadmap disposition

**Canonical repository:** https://github.com/samjuniors/Orbit-Core. GitHub is implementation truth; the Notion decisions hub owns product decisions. Revalidate live state before every resume.

- Main HEAD: [2fdf4f329774b9644e75ac0df4d89738a7cd625f](https://github.com/samjuniors/Orbit-Core/commit/2fdf4f329774b9644e75ac0df4d89738a7cd625f); VERSION=0.33.1; NEXT_VERSION=0.34.0.
- Published baseline: [v0.33.0 prerelease](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.33.0), published 2026-11-23. v0.30.0 remains latest stable-channel release. v0.33.1 is source-only and unpublished.
- Main exact-head CI [run #45167794202](https://github.com/samjuniors/Orbit-Core/actions/runs/45167794202) passed 5/5. This is hosted CI evidence, not owner-profile acceptance or production certification.
- [v0.33.1 release acceptance](RELEASE-ACCEPTANCE-v0.33.1.md) remains SOURCE MERGED / RELEASE NOT PUBLISHED / ACCEPTANCE INCOMPLETE. Owner-profile Claude/Codex/Antigravity acceptance, timed native permission expiry/revocation and independent human security review remain outstanding.
- Approved product order remains: **safe Team Builder foundation → task-specific skills/tools → Orbit-mediated agent/bot coordination**. Continue mapping increments to [#90](https://github.com/samjuniors/Orbit-Core/issues/90), [#91](https://github.com/samjuniors/Orbit-Core/issues/91) and [#92](https://github.com/samjuniors/Orbit-Core/issues/92). Do not expand scope merely because a branch exists.
- Documentation-only [draft PR #178](https://github.com/samjuniors/Orbit-Core/pull/178) had two exact-head workflow runs (#45304020786 and #45304012954) pass 5/5, including Windows Python 3.12, at pre-update head 47de86f742679d61725381637ff56de7a770ef5e. It has no human review. This current handoff/roadmap refresh changes the branch again; rerun exact-head CI and keep the PR draft pending review.
- Experimental branch [feat/v034-context-aware-intelligence-20261123](https://github.com/samjuniors/Orbit-Core/tree/feat/v034-context-aware-intelligence-20261123) is 94 commits ahead / 0 behind main at [f08448ff75c9d87f280ad66ff022a5466a7f4eb4](https://github.com/samjuniors/Orbit-Core/commit/f08448ff75c9d87f280ad66ff022a5466a7f4eb4). Exact-head CI [run #45371214722](https://github.com/samjuniors/Orbit-Core/actions/runs/45371214722) passed 5/5, including Windows Python 3.12. The branch has no PR or independent review and is not approved for merge/release. Its plan now acknowledges an in-progress audit-first implementation; the earlier 57-tool smoke failure was fixed on later commits, but green CI does not close scope or security review.
- The v0.34 branch contains bounded structural inventory, consented static source review, revision-aware findings/readiness state and optional Claude lifecycle telemetry. It remains a broad multi-module change that has not been reconciled to #90/#91/#92. Do not merge it as a unit.
- **Security review lead, not a confirmed vulnerability:** the source-audit path enumeration/open sequence does not yet demonstrate Windows handle-level reparse-point identity continuity. Existing tests do not demonstrate child reparse-point replacement, hard-link behavior or Windows TOCTOU resistance. Require adversarial Windows tests and a fail-closed design before approving that slice.
- Keep RAD P2 [issue #138](https://github.com/samjuniors/Orbit-Core/issues/138) and draft PRs #136–#147 separate from product feature work; OS-isolation acceptance remains blocked.
- Current provider-neutral handoff is maintained in [docs/AGENT-HANDOFF.md](AGENT-HANDOFF.md) and the Notion [Cross-Agent Handoff & Current State](https://app.notion.com/p/4224f681d488816c9e9efbdc8be38488). Remote Arc DESKTOP-AND1FUJ remains offline; no local checkout, owner-profile host acceptance or .orbit/SQLite inspection was available. The Orbit ChatGPT plugin connector was not exposed; GitHub and Notion integrations were used. Main branch protection remains NOT VERIFIED because the GitHub API returned 403.

**Next safe engineering step:** finish review of the documentation handoff; then reconcile the v0.34 experiment to the approved #90/#91/#92 order and split accepted work into focused PRs. First close the Windows source-audit reparse-point/TOCTOU review gap with adversarial tests. Do not merge, install or publish from the experimental branch. Do not publish v0.33.1 until all owner-profile, security, packaging and release acceptance gates are verified.

**Historical material below:** The following v0.33 integration notes are retained as dated evidence from 2026-11-18 through 2026-11-22. They are not the current repository or release snapshot; revalidate GitHub and Notion before acting.

---

## Historical v0.33 integration checkpoint (2026-11-18)


**Continuity note (2026-11-22):** Cross-agent resumption rules are maintained in [AGENT-HANDOFF.md](AGENT-HANDOFF.md). This v0.33 candidate intentionally uses the manual-main-only release workflow documented in [RELEASE-PROCESS.md](RELEASE-PROCESS.md); do not copy the current mainline tag-push prerelease trigger into this candidate. Revalidate host/SQLite state and exact branch heads before resuming. This note does not authorize publication.


**Published source authority:** [v0.32.0](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.32.0) is the latest public **prerelease** (2026-11-17); [v0.30.0](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.30.0) remains the latest stable-channel release. The source `main` and the separately installed Windows release remain v0.32.0. This development branch retains `VERSION=0.32.0` / `NEXT_VERSION=0.33.0` until a separately approved release cut. It is not a published v0.33 installer.

**Current single integration entry point:** [draft PR #133](https://github.com/samjuniors/Orbit-Core/pull/133), incorporating the two still-open independently reviewed draft lines: [visual policy PR #131](https://github.com/samjuniors/Orbit-Core/pull/131) and [Autopilot/security/handoff PR #132](https://github.com/samjuniors/Orbit-Core/pull/132). The shared skill-instruction conflict was reconciled without removing either domain. No second model runner, required LLM/API key, external Agents SDK, new SQLite event store, or new permanent specialist.

**Implemented but unreleased source:** bounded visual component/source inventory, explicit design token contract and source-only UI coverage hints; project-scoped approved style preferences; preview+confirmed replay-resistant local Autopilot resume with caller-reported approval limitations; typed specialist return-to-lead/host handoff contracts; project-root/mission-scoped redacted local trace integrity hints. The original MCP inventory stays at 57. Real host authority, independent UI review and authenticated consent are not established by source heuristics or SHA digests.

**Installer regression fixed in development (Issue #130):** two previously omitted SHA-256 hashes of official immutable v0.31.0 Antigravity `orbit.md` and `orbit-creative-director.md` were verified directly against the published tag, then added only to the next-source installer allowlist with frozen fixture regression tests. Unknown/owner-edited content remains protected. No published v0.32 asset or immutable tag was changed.

**Windows device acceptance checkpoint:** the public v0.32.0 Universal Setup ZIP was downloaded from the official release, validated against its `.sha256`, and installed/updated in the current Windows user profile for Antigravity and Codex after exact 75-target inspection. The published installer hit Issue #130 and was applied with an in-memory allowlist of **only those two hash-verified official stock bytes**, preserving existing backups, runtime, SQLite and unrelated hosts. Re-preview was all SKIP; the permanent launcher reported `0.32.0`, and a real signed-in Codex MCP `orbit_update_status` returned `installed_version=0.32.0` and `UP_TO_DATE`. Antigravity **configuration** points to v0.32; its refreshed live IDE connection is not verified by config alone.

**Integration tests and evidence:** disposable Windows Python 3.12 focused visual 36 run (1 skipped), Autopilot 31/31, team events 33/33, new official-v0.31 installer regression 3/3, previous stock-agent regression 2/2: all passed. Full integration [GitHub CI run #1395](https://github.com/samjuniors/Orbit-Core/actions/runs/44288442720) was in progress when this checkpoint was drafted; the final exact-head CI after documentation updates must be checked separately. Previous isolated draft CI for PRs #131/#132 passed 5/5 each. Keep verification statuses exact.

**Blocking gates before main merge, release, or installation of v0.33:** combined exact-head Windows/Linux CI, release packaging/version metadata/rollback; independently attributable native Codex/Antigravity handoff+receipt/host denial+resume; real host visual screen/state QA and owner visual acceptance. Codex CLI source inspection under the host's filesystem policy remained BLOCKED, not bypassed; a reported child specialist result without trusted session receipt is not independently authenticated. Founder approval is required for merge, publication and user-machine installation of any future v0.33 release.

**Continuity:** prior sections below are historical development decisions; this section supersedes their "current version" claims without discarding their implementation and testing history.

---

# Orbit Core — v0.32 draft development checkpoint (2026-11-08; NOT RELEASED)

**Product direction:** Founder-delegated, roadmap-scoped autonomy, but **no unbounded unattended agent**. The [proposed Autopilot Phase 1](AUTOPILOT-PHASE1.md) is implemented only on `feat/v032-autopilot-charter-phase1-20261107`; there is no published update and no installed host execution. `VERSION=0.31.0` remains the previous publication metadata; `NEXT_VERSION=0.32.0` is an unapproved prospective release cutline.

**Phase 1 source scope:** new project-isolated SQLite Mission Charter with exact existing task specs, allowed write paths, feature branch, accepted decision types, 30-day-maximum expiry, bounded concurrency and attempt budget; charter-preview SHA-256, explicit caller-reported owner approval, revisioned pause/resume/stop and event log; read-only DAG next-task and founder-only decision gates. Reuses existing task ledger/swarm preflight and never invokes a native worker or grants host permissions. Caller approval/session/tool evidence is unverified until independently observed in the actual IDE. Normal `orbit_task_reserve` remains a distinct host-authorized workflow; the Phase 1 charter is advisory, not an executor security sandbox.

**Before considering merge:** finish unit regression and exact-head CI, inspect portable installer module inventory and stock upgrade behavior; test charter preview, activation, stop, expiry, stale source/symlink, native host tool unavailable, cross-project isolation and full test pack on Windows and Linux. Host-native Browser/Computer Use changes from the separate [PR #104](https://github.com/samjuniors/Orbit-Core/pull/104) have now been conflict-checked and ported into [stacked draft PR #123](https://github.com/samjuniors/Orbit-Core/pull/123). This is unmerged development; independently verified Codex/Antigravity UI/browser sessions and permission denial remain outstanding. No tag, automatic scheduler, cross-PC sync, user-profile changes, protected branch merge, deployment or published release is authorized by this feature branch.

**Phase 2 status (SOURCE PROTOTYPE, NOT FINISHED OR HOST-ACCEPTED):** The stacked draft [Autopilot Phase 2 PR #108](https://github.com/samjuniors/Orbit-Core/pull/108) provides an opt-in, local single-task Codex CLI runner that uses a temporary, remote-free Git clone, 600-second cap, reviewed source path checks and an explicit terminal operator confirmation. Subsequent reviewed developer changes in [PR #117](https://github.com/samjuniors/Orbit-Core/pull/117) and [PR #120](https://github.com/samjuniors/Orbit-Core/pull/120) enforce commit/remote/unsafe-link/ignored-file output guards; [PR #119](https://github.com/samjuniors/Orbit-Core/pull/119) adds a separate UTC-day local-start-count budget. This is **not** an unattended roadmap loop: real Codex/Antigravity host permission acceptance, actual native team actions, independent QA, OS orphan-worker cleanup, resilient supervisor and meaningful token/cost limits remain **NOT IMPLEMENTED or NOT VERIFIED** as applicable. See [the Phase 2 developer contract](AUTOPILOT-PHASE2.md). **Phase 3 (UNIMPLEMENTED):** founder-away notifications and opt-in remote execution, which need separate explicit privacy/cost authorization. Owner retains final authority.

---

# Orbit Core — current release and next acceptance gates (2026-11-06)

**Published release authority:** [v0.31.0 prerelease](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.31.0), tagged from the verified main commit `524b5aace4889494ee8b852bb4d1aab18b72d0cc`. The release workflow and Linux/Windows CI passed, and all four archive/checksum pairs were verified. The released 52-tool MCP runtime was installed on the authorized Windows PC for Antigravity and Codex; both host configurations point at v0.31.0. This proves packaging and installation, **not signed-in IDE worker execution or production-readiness**.

**Implemented in v0.31.0:** adaptive new/existing-project workflows, task ledger and checkpoint recovery, release-aware CLI, owner-selected coordinator preference, read-only plugin collision warnings, project-quality baseline, resource-first specialist recommendations, project-local reviewed practices and safeguarded improvement/agent candidate drafts. These use the coding host's models, native tools and user-granted permissions.

**Remaining acceptance, in priority order:**

1. Real **Codex and Antigravity** native MCP discovery after host restart, project scan and actual tool result (not a configuration readback); real specialist session IDs, handoff, cancellation and resume in disposable projects.
2. A genuinely denied **host permission prompt before session creation** and a separate positive/negative check of the already implemented invocation-state guard from [Issue #72](https://github.com/samjuniors/Orbit-Core/issues/72).
3. Real host GUI/installer keyboard and DPI smoke and **disposable-profile** upgrade/uninstall/rollback; the source-level transactional clean/recovery logic for [Issue #85](https://github.com/samjuniors/Orbit-Core/issues/85) has regression coverage but must not destructively test the owner's installed profile.
4. Representative independent QA/security/learning demonstrations across relevant project types. Open design/implementation issues [#90](https://github.com/samjuniors/Orbit-Core/issues/90), [#91](https://github.com/samjuniors/Orbit-Core/issues/91) and [#92](https://github.com/samjuniors/Orbit-Core/issues/92) should be reconciled against implemented v0.31 source; do not infer live native or independent security acceptance from the 52-tool inventory.

**Latest direct host probe:** a read-only Codex CLI run in a disposable TEMP project reached an stdin-waiting state without yielding an MCP response. The connected PC stopped returning terminal results; host acceptance from this probe is **BLOCKED / NOT VERIFIED**, not a test PASS/FAIL for the Orbit MCP. Restore remote session observability before retrying.

The dated historical snapshots that follow record previous releases and planning cutlines. They are **superseded by this current section** where they refer to v0.27/v0.28 as current.

---

# Orbit Core — current published release and development queue (2026-11-03)

**Latest verified published prerelease:** [v0.28.0](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.28.0), published **2026-11-03**, from reviewed merge commit `07067f10cb5a345be0959f1a2f9a2410eb3b0f48`. Its immutable annotated tag, successful [official publication workflow #41581180695](https://github.com/samjuniors/Orbit-Core/actions/runs/41581180695), eight public release assets and all four package/sidecar SHA-256 pairs were independently verified. [Main CI #41580966442](https://github.com/samjuniors/Orbit-Core/actions/runs/41580966442) passed all five Linux/Windows jobs. Prior [v0.27.1](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.27.1) and earlier releases remain unchanged.

**v0.28 delivered:** The read-only `orbit_software_delivery_preview` adds adaptive, project-aware specialist planning to the existing local-first Orbit runtime (**47 MCP tools**). The connected coding host—not Orbit itself—still invokes approved native subagents. Real second-PC Antigravity TODO acceptance included native backend/frontend task reviews, 37/37 backend security/HTTP tests, 9/9 source-bound Playwright Edge browser actions, strict local origin controls, and reliable MCP restart/checkpoint recovery. The integration guard returned `READY_FOR_INDEPENDENT_REVIEW` before owner-authorized prerelease publication. See [final engineering acceptance](RELEASE-ACCEPTANCE-v0.28.0.md) and [completed Issue #74](https://github.com/samjuniors/Orbit-Core/issues/74).

**Published versus production-ready:** v0.28 is a **0.x prerelease**, not production certification. Real host permission-denial checks, complete Codex end-to-end delivery, installed-user migration/rollback and publisher signing remain limited or unverified, as documented in public release notes. Official release checksums prove file integrity rather than publisher identity. Always consult [GitHub Releases](https://github.com/samjuniors/Orbit-Core/releases) for the current publication authority.

**Next release queue (not yet approved/published):** v0.29 installed-skill discovery research/development on [draft PR #70](https://github.com/samjuniors/Orbit-Core/pull/70), then v0.30 native coordination [draft PR #71](https://github.com/samjuniors/Orbit-Core/pull/71) and the corrective [draft PR #73](https://github.com/samjuniors/Orbit-Core/pull/73) for [Issue #72](https://github.com/samjuniors/Orbit-Core/issues/72). Their inherited version metadata, source upgrades, independent tests and release authorization must be reconciled **separately and in order**. Real-host testing this cycle prioritizes Antigravity and Codex; do not claim Claude Code host acceptance without execution evidence.

Older historical progress snapshots below are retained and superseded
by this current summary where they contradict a verified release/branch.

---

# Orbit Core — current release and roadmap status

**Current public prerelease:** [v0.27.0](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.27.0)
(2026-10-31); `main` is source authority. The `v0.27.1` patch is a
**separate unpublished candidate**, scoped to repository rename URLs and
update/download continuity. `NEXT_VERSION=0.28.0` remains future
development planning and does not authorize a release.

**Open release-quality issues:** native permission-dialog denial,
live-worker cancellation/restart, independent publisher provenance,
tested user migration/rollback and second-host acceptance. See the
[Swarm acceptance evidence](SWARM-ENGINEERING-ACCEPTANCE.md).

The older v0.27.0 development-lane notes below are **historical**
and were superseded by the published release. Do not restart
those completed milestones.

---

# Orbit Core roadmap — M1/M2 owner-accepted; M3 engineering in progress (2026-10-29)

The focus is **a trustworthy local orchestrator inside existing coding IDEs**, not duplicating an entire cloud app-building platform. This is a prioritized engineering backlog, not an automated promise of completed features.

## v0.27.0 — isolated next-feature development lane (PROVISIONAL)

**Branch:** `dev/v0.27.0`, forked from `main` at `7344a12c2056b586974e654733e1b3a78685827d` on 2026-10-30. This is a **development integration branch**, not a release candidate and not a published version. `NEXT_VERSION=0.27.0` on **this branch only** is a planning label because the planned work adds capabilities; `VERSION` remains `0.26.0` until an explicitly reviewed release cutline. The public release remains `v0.25.1`.

**Project Pulse (MERGED to dev, release acceptance pending):** [PR #49](https://github.com/samjuniors/Orbit-Core/pull/49) now provides optional `orbit_project_resume(compact=true,pulse=true)` and bounded local task counts with unverified next-action hints. No model/agent execution, external data sync or host liveness attestation. Real host UX and model-context benchmarks still required. Integrated along with Swarm in `dev/v0.27.0`; not in `main` or a published release.

**Agent Swarm Phase 3 — native-host batch handoff review SOURCE IMPLEMENTED, real hosts pending:** `orbit_swarm_host_preflight` checks one or two existing reserved task revisions as an all-or-nothing group before native delegation. It reuses `orbit_task_handoff`, checks exact host and permission preconditions, and returns zero invocation packets if any task is stale, scope-conflicting, already running, denied, or blocked by unrelated active work. Recovery uses existing revision-guarded `orbit_task_release` for unstarted denied/failed tasks and `orbit_task_report` only after a genuinely observed terminal host session. No actual host agent is invoked or terminated by the MCP. See [swarm engineering acceptance](SWARM-ENGINEERING-ACCEPTANCE.md). Real Antigravity/Codex/Claude permission/denial tests, real native-session recovery and independently executed integration QA remain open; the source-level freshness and readiness guards are implemented in v0.27 development.

**Agent Swarm Phase 2 — draft DAG preflight MERGED to dev, live acceptance OPEN:** `orbit_swarm_draft_preview` accepts a user/host-proposed task graph and validates all identities, roles, goal text, dependencies, path scopes, cycle/size limits and existing ledger conflicts before exposing deterministic review waves. Max 12 task drafts and 2 safe tasks per wave. It does **not** interpret natural language autonomously, register tasks, approve work, invoke native subagents or attest tests. See [Swarm engineering acceptance](SWARM-ENGINEERING-ACCEPTANCE.md). Host-reviewed registrations and read-only QA readiness are in development source; actual native delegation, cancellation, test execution and host acceptance remain open. The reviewed phase sources #50–53 are now integrated in dependency order to this development lane; do not merge the entire version lane to main before the v0.26 release decision.

**Agent Swarm mission — Phase 1 SOURCE MERGED to dev, host acceptance OPEN:** [Engineering checklist](SWARM-ENGINEERING-ACCEPTANCE.md). The new read-only `orbit_swarm_preview` tool (43rd candidate MCP tool) groups existing registered tasks by dependency readiness and non-overlapping write scopes. It checks missing dependencies, cycles, protected paths, existing reservations and a fixed maximum of two candidates. A candidate is **not** a launched agent or an approved task. `orbit_task_reserve` and host-native handoff still require actual permission and fresh revisions. The implementation is an original Orbit coordinator; the [Claude Swarm external reference](https://github.com/affaan-m/claude-swarm) is research only, without imported source or Claude SDK. **Future work:** real-host parallel execution, denial/cancellation/rollback, independent integration QA, context benchmarks and observable swarm progress. Draft validation and host preflight are already implemented in the integrated development source. No main merge or v0.27 release is authorized. The integrated development commit `7130eb381ccdbc3d1792b55b2889e139385c9dbf` includes [PR #57](https://github.com/samjuniors/Orbit-Core/pull/57) Windows alias/independent OS-process SQLite checks and [PR #58](https://github.com/samjuniors/Orbit-Core/pull/58) symlink containment and post-reservation handoff safety. Exact PR-head matrices passed [#57 CI](https://github.com/samjuniors/Orbit-Core/actions/runs/41079246959) and [#58 CI](https://github.com/samjuniors/Orbit-Core/actions/runs/41082050055), each 5/5 Ubuntu/Windows; the matching integrated development [post-merge CI](https://github.com/samjuniors/Orbit-Core/actions/runs/41082365287) passed 5/5 on Ubuntu Python 3.10–3.13 and Windows Python 3.12. Actual host agent sessions, host approvals, cancellation, independently executed integration QA and cross-PC recovery remain NOT VERIFIED.

**2026-10-30 source-development cutline (NOT A RELEASE):** [PR #60](https://github.com/samjuniors/Orbit-Core/pull/60) added transitive failed/rework dependency decisions and manual serial host-review fallback. [PR #61](https://github.com/samjuniors/Orbit-Core/pull/61) added read-only, source-fingerprint-bound task/QA integration readiness, with the installer, packaged MCP and host handoff guidance updated together. Both were merged into `dev/v0.27.0`; latest source merge `0d231b3508cf7c69bef85412a8efb2f02c714382`. [Exact #61 PR-head CI 5/5 PASS](https://github.com/samjuniors/Orbit-Core/actions/runs/41085894528); final [post-merge dev CI](https://github.com/samjuniors/Orbit-Core/actions/runs/41086243865) is a separate gate. The development source exposes **46 MCP tools**. This establishes implementation of the planned code-level readiness guards, **not** authenticated host sessions, genuine independent QA execution, installed-user migration, performance gains, security certification or permission to merge to `main`. Remaining live acceptance and release hold are tracked in the existing [Swarm engineering checklist](SWARM-ENGINEERING-ACCEPTANCE.md) and [Notion version tracker](https://app.notion.com/p/4074f681d48881a7a407c3bdc2054409). No new orchestrator backend, LLM runner or automatic worker was introduced.

**Working rules:** New independent v0.27 features use `feat/v027-<scope>` branches based on `dev/v0.27.0`, undergo review and CI, and merge into **this version development branch** after explicit approval. Do not merge the entire lane to `main` while v0.26.0 is frozen or unapproved. Once the feature scope is agreed and prior-version release rules are reconciled, create `release/v0.27.0-candidate` from an exact reviewed commit and perform release-specific tests. No feature or metadata change in this lane authorizes v0.26.0 publication, bypasses its approval gates, or retags an existing release.


## Orbit-native research and intelligence roadmap — approved direction (2026-10-27)

**Product principle:** build an original, lightweight Orbit experience, not an ECC fork or clone. Research links, annotations and retrieval records belong in **authorized local project-scoped SQLite outside the Git repository**. Owner documentation remains authoritative. External references are untrusted inputs, never auto-executed skills or agent instructions. This roadmap preserves Issue #13 product-experience commitments and Issue #9 release/security gates.

### M1 — P0: Orbit Evidence Lens (core scope OWNER-REPORTED PASS; source and CI verified)
- Save an individual reviewed research **source pointer** (URL, topic tags, short annotation, original status) with an explicit write preview and revision-guarded update. Use project folder + stable project key as namespace. Never seed global memory by default or push research links to Git.
- Recover only sources relevant to an objective within a predictable character budget; return provenance, limits, unverified-source warning and explicit live verification guidance. No network request or third-party code execution from source content.
- Support project- and folder-level isolation, duplicate identity updates, malicious URLs and stale-revision tests; retain existing local SQLite and legacy memories. A trusted local IDE user manually imports the previously prepared 9-link research packet after connecting, not a Git checkout or ChatGPT cloud session.
- **Gate / acceptance update (2026-10-29):** PR #16 merged and the source/bundle regression matrix passed. The owner reported Antigravity research-pointer save/readback and checkpoint recovery as PASS. Treat M1's core functionality as **OWNER-ACCEPTED**, not independently attested host consent or proof of automatically synchronized Notion references. Evidence: [v0.25.1 release host reports](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.25.1) and [Evidence Lens tests](../tests/test_evidence_lens.py).

### M2 — P0: Reliable real-host delegation and handoff (core scope OWNER-REPORTED PASS; extended checks open)
- Add a read-only `orbit_task_handoff` adapter contract: checked task/reservation/dependencies, exact supported native host tool names (caller-reported), limited file ownership, optional minimal Evidence Lens links, safe HOLD/serial fallback. The host **must** actually invoke its native tool; a packet is not an agent run. Real host session references and changed-file/test inspection remain prerequisites; the MCP never spawns an agent.
- **Gate / acceptance update (2026-10-29):** [PR #17](https://github.com/samjuniors/Orbit-Core/pull/17) merged with passing automated host-handoff tests. The owner's actual-host reports record **Antigravity PASS** (native delegation, Todo checks, restart/resume) and **Codex PASS** (native delegation, 14 regression checks, `todo-filter-codex` REVIEW_ACCEPTED revision 5, checkpoint/files restored after restart). Those reports are documented in the [v0.25.1 release](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.25.1); the MCP cannot independently attest host session/consent. Mark **M2 core two-host acceptance OWNER-ACCEPTED**, without claiming every new-project/existing-project or denial/fallback scenario was independently verified. Any untested scenario remains a targeted M3 follow-up, not an assumed PASS.

### M3 — P1: Independent QA, permissions and scoped recovery (IMPLEMENTATION PARTLY MERGED; LIVE ACCEPTANCE DEFERRED)
- **Objective:** Make verification evidence independently checkable where host capabilities permit, ensure permission/denial behavior is accurately represented, and recover from interrupted or cross-host work without fabricating PASS.
- **M3.1 — QA freshness:** Attach QA/test records to source revision, acceptance case, execution environment and preview generation; invalidate stale PASS after code changes. Include regression tests for stale evidence.
- **M3.2 — Host permissions:** Verify real host consent/denial paths; do not treat `confirm_write`, reported tool names or supplied session IDs as authenticated consent. Retain HOLD/serial fallback when native delegation cannot be attested.
- **M3.3 — Scoped recovery:** Exercise interrupted, cancelled, failed and rework task paths with revision checks, safe file ownership, and rollback/backup review on Windows and Linux. Do not alter older accepted task history.
- **M3.4 — Portability limitations:** [PR #22](https://github.com/samjuniors/Orbit-Core/pull/22) merged portable task/research export/import and checkpoint-only detection; **live cross-PC transfer remains NOT VERIFIED**. Test on two actual hosts/PCs only with approved, disposable project data; imported approvals and sessions remain untrusted historical records. Build/intake and legacy memory are not included.
- **Acceptance gate:** real revised-code QA (including stale-PASS rejection), host denied-permission evidence, interrupted/rework recovery, independently inspected Git diffs/tests, and an explicitly recorded cross-PC test result (PASS/FAIL/DEFERRED). Separate optional platform/GUI, provenance/signing and Issue #9 security gates are not silently closed.
- **Engineering progress:** [PR #25](https://github.com/samjuniors/Orbit-Core/pull/25) source/preview-bound QA, [PR #26](https://github.com/samjuniors/Orbit-Core/pull/26) host-first browser selection, [PR #27](https://github.com/samjuniors/Orbit-Core/pull/27) denial bookkeeping, [PR #29](https://github.com/samjuniors/Orbit-Core/pull/29) native-agent session reconciliation and [PR #32](https://github.com/samjuniors/Orbit-Core/pull/32) persistent retry budgets have merged to development `main`. Browser QA origin isolation was integrated and merged through [PR #33](https://github.com/samjuniors/Orbit-Core/pull/33), superseding the conflicting standalone #30. See [M3 engineering acceptance checklist](M3-ENGINEERING-ACCEPTANCE.md) for case/evidence requirements. Do not confuse merging with live IDE acceptance, verified permissions, two-PC continuity or production security; these remain deferred or open.

### M4 — P1: Adaptive capability surfaces and reusable context
- Reuse native host features, owned code, on-demand skills or a small MCP surface according to task—not a universal dependency pile. Extend the M1 compact pack to accepted decisions and checkpoint context only after verifying project-root binding and provenance.
- **Gate:** compare tool-turns, context bytes, recovery accuracy and install friction on Orbit's real product benchmarks.
- **M4.2 v0.26.0 source follow-up:** Existing `orbit_capability_select` now recommends focused compact resume, multi-stage full review, or high-risk permission/review gates based on the objective and caller-reported host tool names. No subagent executes from a selector, no model is switched, and actual host permissions remain external. Synthetic JSON-byte savings tests are useful but do not establish real model-token/credit savings; benchmark signed-in IDE use later.

### M5 — P2: Evidence-backed learning (opt-in)
- Suggest reusable project-scoped practices only after repeated reviewer-accepted outcomes and human review; never silently create/modify global skills, run continuous watchers, store full chats, or promote untrusted research prose to trusted instructions.
- **Owner-approved development integration (v0.26.0 source still unpublished):** two optional MCP tools expose repeated-task-pattern suggestions and explicitly reviewed SQLite practice decisions, with revisioned approve/reject/archive/supersede history. Evidence is caller-reported and must be independently inspected in the host. No background learning, automatic skill generation, cross-project knowledge transfer, model execution or token-savings claim.
- **Gate:** [M5 engineering acceptance](M5-ENGINEERING-ACCEPTANCE.md) — deterministic isolation/preview/revision/freshness tests and exact-head Linux/Windows CI have passed; real-host UX, independent permission/privacy acceptance, upgrade/rollback and separate owner release approval remain pending. M5 source merge is not permission to publish v0.26.0.

**Research inspiration:** prior user-shared sources ECC, Emergent, Lovable, Scram, Neura, etc. stay **outside Git as source pointers**. Compare behaviors and adapt ideas independently with license/security review; no copying source code or installing external components. The M1 implementation is specific to Orbit's existing SQLite and host-neutral execution model.

## v0.26.0 — Plugin-first distribution and Antigravity native-agent contract (owner-directed, 2026-10-30)

**Status: APPROVED PRODUCT DIRECTION; PACKAGING/INSTALLATION/REAL-HOST ACCEPTANCE NOT IMPLEMENTED/VERIFIED.** This mission is part of the *unpublished* 0.26.0 development target, not another project or authorization to release. Research and rationale are recorded in the existing [Orbit Core Notion research hub](https://app.notion.com/p/4074f681d488816e9fe7f4504982c948), especially the 2026-10-30 Antigravity custom-subagents supplement. Host authority: [Antigravity custom subagents](https://antigravity.google/docs/subagents?tab=cli) and [Antigravity plugins](https://antigravity.google/docs/plugins?tab=cli).

**Goal:** Install Orbit once as the host-supported combination of a selectable lead agent, reusable skill, host-native specialist profiles and locally launched stdio MCP — *no external Orbit cloud server*. Codex and Claude use their respective plugin/agent/skill formats, not Antigravity's YAML verbatim. In agent/skill-only fallback, never invent persistent SQLite checkpoints, practices or 42 MCP tool calls.

**Antigravity binding contract:**
- Existing `source/agents/orbit.md`: exactly one selectable primary `mainAgent: true`, `subagent: false`, `model: inherit`. Twelve specialist `orbit-*.md`: `mainAgent: false`, `subagent: true`. Both flags default to true in this host, so neither may be implicit. Current source profile inspection found 13 expected files with explicit role flags; this is source inspection, not live plugin-origin agent acceptance.
- Delegate *only* through actually available host `invoke_subagent`, using `inherit`, `branch` (isolated Git worktree) or `share` according to scoped file ownership and user permissions. Pass a bounded handoff: child starts with a new conversation context, not the parent's entire context. Orbit MCP itself never spawns agents.
- Treat host child session states `Running`, `Idle` (can be re-awoken) and `Killed` (terminal) distinctly. Obtain host session IDs and actual end state before changing task ledger, reviewing, retrying, or claiming cancellation. Do not exceed a practical concurrency/nesting budget; the host states a maximum nesting depth of 10 but that is not Orbit's recommended operating depth.
- Subagents inherit parent file/terminal/sandbox restrictions; tool requests needing extra consent bubble to the actual host UI. Report denied/unknown consent as HOLD, never bypass with another tool/provider. Use `model: inherit` by default; allow `flash`/`pro` recommendations only when the user's installed host makes them available and the work merits them.
- Host built-in `research` and `self` are special native roles. Built-in `browser` is invoked **only by `/browser`**, not a generic `invoke_subagent` call. Host `/boost` and `/teamwork` are plan-gated native capabilities, not mandatory Orbit dependencies or permissions to execute automatically. Host `/agents`, `/tasks`, `Alt+J` and `Ctrl+K` remain host UI controls, not Orbit MCP tools.
- Exact `tools` allowlists must be validated against the actual installed Antigravity build. Official docs warn an unknown tool string can **hang a subagent**. Review all specialist profiles including `orbit-writer.md` (`write_to_file`) before dispatch; do not assume that spelling is supported everywhere.

**Distribution and migration contract:**
- Antigravity plugin: `plugin.json`, `mcp_config.json` (NOT `mcp.json` in this manifest dialect), `skills/orbit/SKILL.md` and on-demand references, `agents/orbit.md` plus twelve specialist profiles, versioned local runtime. Prefer host-supported `${PLUGIN_ROOT}` for the code and `${PLUGIN_DATA}` for newly provisioned state, with backup-first preservation/mapping of an existing `ORBIT_LOCAL_DB`. No automatic hooks, downloads or cloud setup.
- A disposable plugin prototype validated on installed `agy 1.4.11` with `agy plugin validate --strict`: **1 skill, 13 agents, 1 MCP server; PASS** after removing UTF-8 BOM, using `mcp_config.json`, and shortening the initial skill below the host's observed 24 KB direct-load limit with full content moved into `references/`. **Prototype NOT installed**; no claim of actual plugin-origin connection or migration acceptance.
- Preserve the existing standalone v0.25.1 Orbit registrations, agent/skill customizations and user SQLite data during trial; prevent duplicate MCP tool identities if legacy and plugin distributions coexist. Provide detect/preview, upgrade/repair, disable, uninstall and rollback without deleting owner files. Use one canonical Orbit runtime and host-specific thin packages for Codex, Claude Code and Claude Desktop.
- Package version/source parity, platform interpreter resolution, offline startup, skills load limits, path-variable expansion, permission failures, unchanged user files, stale/revision evidence, stop/resume and no-MCP graceful fallback must have regression and **live-host** acceptance before publishing.

**v0.26.0 acceptance gate:** [ ] strict plugin manifest/skills/agent/allowlist tests; [ ] disposable real App installation and Orbit lead selectable in chat; [ ] authorized `invoke_subagent` with observed session ID, `branch` worktree, correct permission bubbling/deny/cancel/idle/restart; [ ] browser `/browser` routing and no fake BROWSER_QA PASS; [ ] 42 actual local MCP tools + SQLite readback without duplicate old/new registration; [ ] clean upgrade/rollback from v0.25.1 with existing database and customizations; [ ] distinct Codex and Claude plugin QA; [ ] independent security/provenance review and owner publication decision. **Do not equate validator success with real-host or release PASS.**

## P0: release and host acceptance

- Validate Windows Antigravity/Codex/Claude Code setup from **downloaded, signed-in, authorized machines**, including preview/backup of customized files, restart, actual tool discovery and user decision flow.
- Run real Windows Edge/Chrome browser QA and native Android/iOS flows where applicable; optional Playwright tests may be skipped in CI and **must not** be described as live acceptance.
- **v0.25.1 was published as a prerelease on 2026-10-29** with four ZIP/MCPB/checksum assets after passing CI. This is not production security, GUI or independent native-host acceptance. Preserve v0.24.1 assets and verify real device/installer/backup/rollback separately. See [published release](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.25.1) and [release acceptance](RELEASE-ACCEPTANCE-v0.25.1.md).

## P1: reliability and evidence authenticity

- Bind QA results to source revision, acceptance case and preview generation; invalidate stale PASS after edits.
- Persist and supervise preview process trees across MCP restarts; Windows stop must not kill unrelated processes.
- Retry, cancel and reconcile task reservations after failure, with per-attempt history and bounded time/quota budgets.
- Add transactional SQLite compare-and-swap tests for concurrent intake edits; atomically checkpoint files.
- Strengthen stable project identity to avoid cross-folder slug collision in memory keys.
- Configure branch protection, required CI statuses, independent code review and real production-threat model.

## P2: productivity and product experience

- Thin IDE plan/task/progress panel with explicit plan approval, blocked-reason status and native model availability.
- Keep model routing host-supported and cost-aware with real measurements; do not infer credits or force cheaper models for difficult tasks.
- Build a small **tested/versioned** reusable component catalog only after repeated practical demand and license review. Astryx, shadcn, Jetpack Compose, SwiftUI, Context7 and agent-browser are candidates for *different* tasks, not universal defaults.
- Selective retrieval from compact accepted briefs, checkpoints and targeted files; avoid dumping all docs every turn.
- Improve human milestone acceptance and accessibility/performance tests for chosen project types.

## Acceptance and rollback policy

Merges to `main` may contain reviewed release candidates, but must not imply production certification. Release tags are immutable; repair with new SemVer patch, preserve user data and historical runtime folders, and require explicit authorization for installs/deployments. If an installer reports a manual-review conflict, protect the file and provide an actionable diff/backup path, never silently overwrite unknown content.


## Product experience first (current development priority)

Deliver a reliable one-glance resume/decision view and correctly frozen stage progression before investing in deployment infrastructure, service supervision, distributed locks or managed hosting. Evaluate a host-native editable plan/task panel only after the lightweight MCP UX contract has been tested in Antigravity and another coding host. No premature live-production claim based solely on CI.

## Cross-PC continuity correction (2026-10-29)

A moved checkpoint does not imply the other PC's SQLite database moved. Resume
now reports the server-selected database path and exact task/research counts.
A checkpoint with no local records returns `CHECKPOINT_ONLY_LOCAL_CONTEXT_MISSING`:
continue inspecting existing code without onboarding or inventing missing history.
This is a portability limitation, not evidence of same-PC persistence failure.

Use `orbit_project_transfer` with `action: export` on the original PC. It returns a
bounded JSON bundle (100 tasks + 100 research pointers, 90 KB maximum), without
writing files. Review notes/URLs for sensitive content and manually transfer it
outside Git. No other projects, host settings, credentials or legacy global
memories are collected; notes may still contain owner-entered sensitive text.

On the destination, use the same project key, the new absolute project root,
`action: import`, and the bundle string. Review the preview, then explicitly
confirm with its `expected_revision` digest and `confirm_write: true`. Imports
are transactional, refuse existing keys, remap scope, preserve historical task
revisions, and clear approvals/reservations. Active/reported-but-unreviewed work
becomes BLOCKED. Sessions and accepted results remain unverified historical
claims, never proof of execution on this host. Existing checkpoint files are not
overwritten; transfer the project folder including `.orbit/STATE.md` separately.
Build/intake state and legacy memories are not transferred in this bounded version.
Without the original PC/export, only the available checkpoint can be recovered.

The published v0.25.1 and current development tool inventory are **40** tools.
The older 39-tool acceptance prompt predates the portable-transfer feature.
The owner reported Antigravity and Codex same-PC native delegation/restart PASS;
**live cross-PC transfer and native delegation on the destination are NOT VERIFIED**.
Neither published prerelease nor these host reports constitute production certification.


## v0.26.0 source candidate (2026-10-29)

The M3 engineering improvements and M4.1 optional compact project resume are merged into development source. `release/v0.26.0-candidate` is preparing a compatible **minor** candidate because the accumulated work adds user-facing capabilities, not just fixes. Its `VERSION=0.26.0` and `NEXT_VERSION=0.26.1` are **source metadata** until a separately authorized release. CI builds unpublished test ZIP/MCPB artifacts and checks bundle parity, SQLite upgrade behavior and Linux/Windows regressions. Do not mark the live native-host, installer, browser or Issue #9 security gates PASS based on this work; publication is separately approval-gated.


## 2026-11-25 22:44 IST — v0.34 live disposition

- Main remains 2fdf4f329774b9644e75ac0df4d89738a7cd625f, VERSION 0.33.1 / NEXT_VERSION 0.34.0; main CI #45167794202 PASS 5/5. v0.33.0 remains the latest published prerelease; v0.30.0 remains latest stable. Do not publish v0.33.1 or v0.34.0 yet.
- Open work: 43 PRs (40 drafts, 3 non-drafts) and 8 issues. The four new v0.34 draft PRs are #179 (advisory Team Builder model recommendations), #180 (skill lifecycle tests only), #181 (resource-first specialist/role-factory tests only), and #182 (product-aware security review planner plus bounded local pattern checks). #178 remains a docs-only draft; exact-head CI is green, but no human review is recorded.
- PR #182 is currently 45 commits / 25 files and remains draft. The stale 57-tool assertion is corrected to 58. The tracked Claude desktop bundle is restored to the 58-tool artifact required by strict source/package parity. Latest exact-head runs #45664882357 and #45664888434 were pending at this checkpoint. Earlier failures were inspected; do not treat them as resolved until the new exact-head runs finish.
- The first implementation of evidence_sha256 hashes matched source text. A locator-only alternative was reverted because the tracked bundle could not be regenerated in the available environment; issue #184 tracks the privacy-safe fix and exact bundle rebuild. No raw source values are returned, but the digest design remains a release blocker.
- The broad context-aware branch is 100 commits ahead / 0 behind main, has no PR, and exact-head CI #45561811215 passed 5/5 (Windows: 835 tests, 13 skips). It records a reproduced Windows junction-replacement boundary defect in the previous implementation; current branch containment disables candidate writes and source/structural scans on Windows. Do not re-enable those paths until handle-relative implementation and adversarial acceptance.
- Static review found an additional POSIX parent-directory race lead in path-based source/structural traversal and candidate creation; not yet reproduced. Issue #183 tracks handle-relative traversal/writes on all platforms. Existing orbit_specialists._visual_walk and _open_visual_source are reusable read-side primitives; candidate creation needs held-directory-relative operations.
- Security-planner scope remains narrow: product-aware checklist plus bounded regex source hints, not full SAST, scanner discovery, pentest, or certification. Permission is caller-reported; host permission is not independently verified. Do not claim a security pass from zero pattern hits.
- Research: pin OWASP ASVS stable v5.0.0; treat bleeding-edge ASVS as preview. Map mobile work to risk-selected MASVS profiles. Use NIST SP 800-218 v1.1 as final baseline and track SP 800-218 Rev.1 v1.2 as draft. Evaluate installed Semgrep CE, Trivy, OSV-Scanner offline mode and OpenSSF Scorecard as optional resource-first tools; no automatic installation/network scan.
- Environment: Remote Arc Windows device offline, Desktop Commander unconnected, container GitHub clone failed DNS. No local tests, .orbit/SQLite inspection or owner-profile host acceptance. Orbit ChatGPT plugin integration not exposed. Branch protection remains NOT VERIFIED (403).
- Release gate: no merge or release until exact-head CI is green, package source parity is rebuilt from exact source, #183/#184 security issues are resolved or explicitly accepted after independent review, host acceptance is evidenced, and release notes/compatibility are verified.


## Final live checkpoint — 2026-11-25

- PR #178 prior docs head c613bb7f9266c4c957cb567cf8724e05817b33f4 passed exact-head push #45665192614 and pull_request #45665200445, both 5/5. No human review; keep draft. This additional documentation checkpoint triggers another CI run.
- PR #182 code head 54a78b863c10baea305f0adf9f1c96c7fa39c58c passed exact-head push #45664882357 and pull_request #45664888434, both 5/5 including Windows upgrade rehearsals. Keep draft due #184 evidence-digest privacy issue, caller-reported permission and missing independent review.
- PRs #179–#181 remain draft and CI-verified, but their limits remain: advisory model recommendations only; tests do not implement skill activation or native worker execution.
- Context-aware branch: 100 commits ahead / 0 behind, no PR, CI #45561811215 PASS 5/5. Windows paths are fail-closed containment after the prior junction-replacement escape; handle-relative Windows implementation is still missing. POSIX parent-directory race lead is tracked in #183.
- Mobile: MASWE v1.0.0 (2026-08-17) defines 78 stable weakness IDs; 36/78 currently have no MASTG test. Use MAS-L1 only when its assumptions fit, and leave untested weaknesses REVIEW_REQUIRED. Source: https://mas.owasp.org/news/2026/08/17/maswe-v100-release/ ; https://mas.owasp.org/Profiles/MAS-L1/
- No release: v0.33.0 remains latest published prerelease, v0.30.0 latest stable; v0.33.1/v0.34 unpublished. No local/host acceptance or branch-protection verification occurred.


## 2026-11-26 — Current roadmap and release disposition

Main remains `2fdf4f329774b9644e75ac0df4d89738a7cd625f` (`VERSION=0.33.1`, `NEXT_VERSION=0.34.0`, 57-tool baseline). v0.33.0 is the latest published prerelease; v0.30.0 remains stable. v0.33.1 is source-only and unpublished.

Approved order remains:
1. Safe Team Builder foundation.
2. Task-specific skills and tools.
3. Orbit-mediated agent/bot coordination.

Current focused v0.34 drafts:
- #179 model recommendations (advisory only; CI 5/5).
- #180 skill lifecycle acceptance tests (test-only; CI 5/5).
- #181 resource-first specialist/role-factory regression tests (test-only; CI 5/5).
- #182 product-aware cybersecurity planner (58-tool branch; CI 5/5; not SAST or certification; caller-reported permission only; no human review).

All #178–#182 remain open drafts with no human review submissions or inline review threads. PR #178's pre-update head `1dd728cc5f0a76b6eb6f6a3df2b219bfd31b58e7` passed push #45666137573 and pull_request #45666147503, both 5/5. The current handoff append triggers new exact-head CI.

P0 security blockers:
- #183: reproduced Windows junction-replacement escape in the prior implementation; current experimental Windows behavior fails closed. POSIX parent-directory replacement is a static-review lead, not reproduced. Require handle-relative no-follow traversal/writes and adversarial cross-platform tests.
- #184: source-line-derived `evidence_sha256` in #182 can enable offline guessing. Replace with locator-only reference, rebuild desktop bundle from exact source, prove source/package parity and rerun full CI.

Broad v0.34 context branch `feat/v034-context-aware-intelligence-20261123` at `f08448ff75c9d87f280ad66ff022a5466a7f4eb4`, 100 ahead / 0 behind main, no PR, CI #45561811215 PASS 5/5 (Windows 835 tests, 13 skips). HOLD; reconcile to #90/#91/#92 and split into focused reviewable PRs.

No v0.33.1 or v0.34 release until exact-head CI, package parity, #183/#184 disposition, owner-profile host acceptance, independent human security review, compatibility/release notes and explicit owner go/no-go are evidenced. Keep RAD P2 #138 separate/on hold. No automatic scanner installation or network scanning.


## 2026-11-26 — Nightly run 4 roadmap checkpoint (22:20 Asia/Kolkata)

### Live state
- Main remains 2fdf4f329774b9644e75ac0df4d89738a7cd625f, VERSION=0.33.1, NEXT_VERSION=0.34.0, 57-tool baseline. Main CI #45167794202 PASS 5/5.
- Latest published prerelease is v0.33.0 (2026-11-23); latest stable is v0.30.0. No v0.33.1/v0.34 release.
- 159 branches, 43 open PRs, 9 open issues. Main reports protected=false; no repository rulesets were returned. Required-check/review enforcement is not established.
- PR #178 current pre-update head e63b86c passed exact push/PR CI 5/5, but remains draft with zero submitted reviews. This documentation append triggers new CI.
- PRs #179–#182 remain draft. Exact-head CI: #179 run 45545884593 PASS; #180 45549132274 PASS; #181 45548741789 PASS; #182 45664882357 and 45664888434 PASS 5/5. Their capability limits and #184 privacy gate remain unchanged.

### Approved order and new mission-supervisor work
The approved sequence remains:
1. Safe Team Builder foundation.
2. Task-specific skills and tools.
3. Orbit-mediated agent/bot coordination.

New issue [#185](https://github.com/samjuniors/Orbit-Core/issues/185) defines a bounded multi-task mission supervisor. It is a new, scoped autonomy workstream, not evidence that autonomous missions already run. The current experimental branch contains a Mission Charter/DAG review and a local Codex runner that executes only one task per invocation, requires fresh interactive confirmation, and stops for independent review. Those modules are not on main.

### Implementation contract for #185
- Extend existing orbit_autopilot.py, orbit_autopilot_runner.py, orbit_tasks.py and existing append-only journals. Do not create another task database, agent framework or process launcher.
- Obtain one explicit approval for a digest-bound, immutable charter (task set, dependency DAG, branch, write paths, parallelism, retry limits, daily launch budget and expiry). Caller-supplied approval references remain caller-reported; they are not identity proof or host permission.
- Reuse the current isolated-clone Codex adapter. A provider-neutral adapter contract may describe start/observe/cancel/reconcile capabilities, but Claude Code and Antigravity dispatch must remain unavailable until a real signed-in host adapter and permission semantics are verified.
- Run only DAG-ready tasks. Dependencies become runnable only after independent diff/path/security/test review and current REVIEW_ACCEPTED evidence.
- Persist mission revision, task fingerprint, source HEAD, workspace identity, attempt lease, heartbeat and append-only lifecycle events. Bound time, output and launches. Verify process identity and supervisor-owned process-tree termination; never kill a PID recovered from SQLite without fresh OS identity evidence.
- On restart, reconcile worker liveness with the host before resume; detect orphaned workers and fail closed. Replan only within the original charter. Pause/stop/expiry invalidate the active revision and stop only supervisor-owned processes.
- Keep merge, release, deploy, credentials, dependency installation, data deletion, permission changes, new spend and scope expansion founder-only.
- Do not add a background service, remote execution, cloud worker, or PC-off continuation in this issue.

### Acceptance evidence required
A disposable 3–5 task DAG must complete under one mission charter without repeated operator confirmation, while each task still receives independent review. Tests must cover dependency gating, no duplicate attempts, bounded recovery/replanning, pause/stop/expiry, restart/orphan handling, source/branch/task drift, path escapes, symlinks/hardlinks, ignored files, secrets and worker output limits. Run exact-head Linux and Windows CI and verify packaged runtime parity. Real host acceptance is separate from unit tests. Green CI alone does not authorize merge or release.

### Security sequencing
- [#183](https://github.com/samjuniors/Orbit-Core/issues/183) remains P0: Windows junction escape is contained by fail-closed behavior; POSIX parent-directory race is a static-review lead. Complete handle-relative no-follow reads/writes and adversarial Linux/Windows tests before enabling scans or candidate writes.
- [#184](https://github.com/samjuniors/Orbit-Core/issues/184) remains P0: replace source-derived finding hash with a locator-only reference, rename the field to reflect its semantics, rebuild the desktop bundle from exact source and prove parity.
- Broad branch feat/v034-context-aware-intelligence-20261123 is 100 commits ahead / 0 behind main at 8620e4a, CI #45561811215 PASS 5/5, but has no PR/review. Split only after scope/security reconciliation; never merge as a unit.
- Do not publish v0.33.1/v0.34 until #183/#184, independent review, owner-profile host acceptance, package parity, compatibility, release notes and owner go/no-go are complete.

### Environment blocker
Remote Arc DESKTOP-AND1FUJ is offline; no Desktop Commander device is connected. Local source edits, Windows adversarial tests, bundle rebuild and .orbit/SQLite inspection are unavailable. Continue documentation/research through GitHub and Notion, but do not simulate local verification.


## 2026-11-27 — v0.34 execution order and acceptance update

**Main baseline:** `2fdf4f329774b9644e75ac0df4d89738a7cd625f` / VERSION 0.33.1 / NEXT_VERSION 0.34.0. No new release is published. Keep main and published packages unchanged.

### Priority order

1. **P0 filesystem containment (#183 / PR #186):** review the Windows handle-pinning and POSIX dir_fd/O_NOFOLLOW implementation independently. Define supported filesystem semantics. Current Windows identity uses a 64-bit file index; Microsoft documents that ReFS file IDs are 128-bit and the 64-bit value is not guaranteed unique, while network filesystem metadata may be partial. Use FileIdInfo or fail closed outside explicitly tested filesystems. Keep Windows adversarial junction/hard-link tests and POSIX parent-swap tests mandatory.
2. **P0 finding privacy (#184 / PR #182):** remove source-line-derived hashes, use a locator-only reference, rename the output field to match semantics, rebuild the desktop MCP package from exact source and prove strict source/runtime/package parity.
3. **P1 mission supervisor (#185 / PR #187):** continue the bounded, sequential Codex CLI increment only. Pause/resume must be authorized by recorded charter PAUSE+RESUME events; the 2026-11-27 patch adds tampered-checkpoint and live-resume tests. Finish exact-head Windows CI. Fix the shared temp lock-directory parent-symlink/reparse risk before treating the lock as a safety boundary. Do not claim native Claude/Antigravity worker dispatch, parallelism, automatic replanning, background execution or PC-off continuation.
4. **P1 subprocess reliability (#188):** investigate the intermittent native crash in `test_mcp_process_and_shared_db`. Repeated reruns passing are not a root-cause fix; run repeated isolated iterations and inspect child shutdown, MCP stdio, SQLite/WAL lifetimes and native imports.
5. **Governance and acceptance:** obtain human review, reconcile stacked branches with main, complete owner-profile host acceptance and independent security review.

### Current branch/PR posture

- #178 documentation-only draft, exact-head PR CI rerun PASS 5/5; no human review.
- #179–#182 focused drafts; recorded CI PASS 5/5; no human reviews. Their claims remain bounded (advisory model recommendations, lifecycle/safety tests, static security planning).
- #186 filesystem security draft, exact-head push CI PASS 5/5, stacked on the 100-commit context-aware branch; no independent review.
- #187 mission supervisor draft, current head `03b1770214023b4eb3cd3c5a0725d415b5941ef1`; Ubuntu matrix PASS, Windows Python 3.12 in progress at the last check. Also stacked on the context-aware branch.
- The broad `feat/v034-context-aware-intelligence-20261123` branch is 100 commits ahead of main and has no PR; do not merge as a unit.

### Release gate

No v0.33.1/v0.34 publication until #183/#184, #188 reliability disposition, exact-head Linux/Windows CI, package parity, compatibility, release notes, independent security review, signed-in host acceptance and owner go/no-go are recorded. CI alone is insufficient.


### 2026-11-27 17:05 UTC — exact-head CI results

- PR #178 documentation head `7bd44acb0358f4aabf104bb744f371e8356ff143`: [#46038299281](https://github.com/samjuniors/Orbit-Core/actions/runs/46038299281) PASS 5/5, including Windows Python 3.12. Still draft; human review outstanding.
- PR #187 mission-supervisor head `03b1770214023b4eb3cd3c5a0725d415b5941ef1`: [#46037740696](https://github.com/samjuniors/Orbit-Core/actions/runs/46037740696) PASS 5/5, including Windows Python 3.12 (850 tests, 13 skips). The lock-directory parent symlink/reparse review lead remains open.
- #188 now records the daemon update-check thread as one hypothesis for the intermittent shared-DB child crash; this is not a confirmed root cause. Test enabled/disabled update-check behavior on fresh cache and add explicit bounded thread shutdown before changing the release gate.


## 2026-11-28 — v0.34 priorities and release gate revalidation

**Main baseline:** `2fdf4f329774b9644e75ac0df4d89738a7cd625f`; VERSION 0.33.1 / NEXT_VERSION 0.34.0. v0.33.0 remains the latest published prerelease; v0.30.0 remains stable. No v0.33.1/v0.34 release.

### Priority order
1. **P0 #183 / PR #186 — filesystem containment:** exact-head CI 5/5, but PR remains stacked on the unapproved 100-commit v0.34 branch. Windows identity currently relies on legacy 64-bit file index; ReFS uses 128-bit IDs and SMB/network identity semantics need an explicit tested support policy. Use FileIdInfo or fail closed; independent review required.
2. **P0 #184 / PR #182 — finding privacy:** locator-only `evidence_ref_sha256`, privacy tests and committed desktop bundle are now present on draft PR #182. Exact CI #45980372422 passed 5/5 and strict source parity passed. Issue remains open until reviewed and merged to main.
3. **P0 #189 / PR #187 — mission lock:** parent lock directory is not pinned; POSIX symlink parent was confirmed in a disposable review check. Keep lock best-effort only; implement private per-user handle-pinned directory and relative lock creation with Windows reparse handling and adversarial tests.
4. **P1 #188 — subprocess reliability:** original Linux Python 3.10 double-free and Python 3.13 SIGSEGV observed; reruns passing are not root-cause evidence. Run 20+ fresh-cache enabled/disabled tests on both versions, plus deterministic blocked-fetch shutdown test. Updater daemon-thread causation remains a hypothesis.
5. **P1 #185 / PR #187 — mission supervisor:** foreground, sequential Codex CLI only. Continue only after lock and review gates; no native Claude/Antigravity dispatch or background autonomy claim.
6. **Governance:** main branch currently reports `protected=false` and required status-check enforcement off. Owner decision needed to configure required CI/review controls.

### Branch/release posture
- PR #178 docs-only current head `167ea834228b1edf1795a5d805a23d79ea80d60c`; push #46041736579 and PR #46041743870 both PASS 5/5. Still draft; human review pending.
- PR #182 privacy fix current head `a4fcaf563ff61db678344cf82ed4eab34a76a5b1`, base main, CI 5/5; human review pending.
- PR #186 head `f81eb1f051cc6afee00ac10ed1e8619ae3b10633`, CI 5/5, stacked on v0.34 experiment.
- PR #187 head `79a6b9b740e7953273d1c424779781fb6c6e367c`, CI 5/5, stacked on v0.34 experiment.
- Broad v0.34 branch `8620e4a3063852d2c99f6a157fc9ee688c989b6a`, 100 ahead / 0 behind, no PR. Do not merge as a unit.

No v0.33.1/v0.34 publication until #183/#184/#189, #188 reliability disposition, exact-head CI, source/package parity, independent security review, owner-profile host acceptance, compatibility/release notes and explicit owner go/no-go are recorded.
