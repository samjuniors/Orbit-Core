# Orbit Core — cross-agent continuity and handoff

**Last reviewed:** 2026-11-27 22:46 Asia/Kolkata.
**Canonical repository:** https://github.com/samjuniors/Orbit-Core. Revalidate live state before every resume.
**Scope:** provider-neutral Orbit Core only. Orbit Commander remains separately paused and out of scope.
**Current baseline:** main VERSION=0.33.1 / NEXT_VERSION=0.34.0; v0.33.0 prerelease published; v0.33.1 and v0.34.0 are not published.

## 2026-11-27 — Nightly live revalidation

### Canonical GitHub and release state
- Canonical repository: [samjuniors/Orbit-Core](https://github.com/samjuniors/Orbit-Core). Main ref is `2fdf4f329774b9644e75ac0df4d89738a7cd625f`; `VERSION=0.33.1`; `NEXT_VERSION=0.34.0`. The last main CI run [#45167794202](https://github.com/samjuniors/Orbit-Core/actions/runs/45167794202) completed successfully (5/5) on 2026-11-23; no newer main-branch run was returned.
- Releases: [v0.33.0](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.33.0) remains the latest published prerelease (2026-11-23, eight package/checksum assets); v0.30.0 remains the latest stable release. v0.33.1 and v0.34.0 are unpublished.
- Live inventory: 161 branches (100 on page 1 + 61 on page 2), 45 open PRs, 11 open issues. Repository is public, writable, and not archived. Rulesets API returned an empty list; main branch-protection endpoint returned 403, so required-review/check enforcement is NOT VERIFIED.
- Main combined commit-status endpoint returned no status rows; Actions run #45167794202 is the available main CI evidence.

### Current focused development
- [PR #178](https://github.com/samjuniors/Orbit-Core/pull/178) is OPEN / DRAFT / docs-only, based on main. Previous head `58831d39d81075beec9846057b27fba05779ef3e` passed exact-head runs [#46039214019](https://github.com/samjuniors/Orbit-Core/actions/runs/46039214019) and [#46039209679](https://github.com/samjuniors/Orbit-Core/actions/runs/46039209679). Current head after the 2026-11-27 handoff/roadmap/inventory updates is `e6c4e04135be1fa9ca37576e1e2cc2e6434e1889`; exact-head push [#46041304228](https://github.com/samjuniors/Orbit-Core/actions/runs/46041304228) and pull_request [#46041300591](https://github.com/samjuniors/Orbit-Core/actions/runs/46041300591) are IN PROGRESS. Keep draft until both runs pass and human review is recorded.
- [PR #186](https://github.com/samjuniors/Orbit-Core/pull/186) is OPEN / DRAFT at `f81eb1f051cc6afee00ac10ed1e8619ae3b10633`, stacked on experimental base `8620e4a`, not main. Exact-head CI [#45993595975](https://github.com/samjuniors/Orbit-Core/actions/runs/45993595975) passed 5/5. It adds descriptor-relative POSIX operations and Windows reparse-aware project-root handling. Independent review remains required; Microsoft documents 128-bit ReFS file IDs and warns that the legacy 64-bit file index is not guaranteed unique. Use `FILE_ID_INFO`/FileIdInfo where supported, or fail closed on unsupported/ambiguous filesystems. Do not claim #183 is closed.
- [PR #187](https://github.com/samjuniors/Orbit-Core/pull/187) is OPEN / DRAFT at `79a6b9b740e7953273d1c424779781fb6c6e367c`, stacked on the same experimental base, not main. Previous exact-head run [#46037740696](https://github.com/samjuniors/Orbit-Core/actions/runs/46037740696) passed 5/5 (Windows: 850 tests / 13 skips as reported in the PR). A documentation-only follow-up now describes the mission lock as best-effort local serialization, not a security boundary; re-run CI on the new head. The code-level lock parent-directory issue is tracked by [#189](https://github.com/samjuniors/Orbit-Core/issues/189).
- PR #187 implements a foreground, sequential local Codex CLI supervisor only. It does not implement native Claude Code or Antigravity worker dispatch, parallel execution, remote/background execution, PC-off continuation, authenticated reviewer identity, auto-merge or release.
- PRs #179–#182 remain open drafts; their prior exact-head CI passed 5/5, but no human review/host acceptance is established. #179 is advisory model routing; #180 is skill lifecycle test coverage; #181 is specialist regression coverage; #182 is bounded static security planning, not SAST or penetration testing.

### Open reliability/security gates
- [#183](https://github.com/samjuniors/Orbit-Core/issues/183): project filesystem boundary. [PR #186](https://github.com/samjuniors/Orbit-Core/pull/186) is progress but remains stacked on the 100-commit experimental branch and needs independent Windows/POSIX and supported-filesystem review.
- [#184](https://github.com/samjuniors/Orbit-Core/issues/184): source-line-derived security finding digest may enable offline guessing. Still a release blocker until replaced by a locator-only reference, renamed accurately, tested, and desktop package regenerated from exact source with parity verified.
- [#185](https://github.com/samjuniors/Orbit-Core/issues/185) / [PR #187](https://github.com/samjuniors/Orbit-Core/pull/187): bounded multi-task mission supervisor; experimental, Codex-only and foreground-only.
- [#188](https://github.com/samjuniors/Orbit-Core/issues/188): intermittent native child crashes in `test_mcp_process_and_shared_db`. Observed Linux Python 3.10 (`-6`, double-free/corruption) and Linux Python 3.13 (`-11`, SIGSEGV); reruns passed and Windows passed, but root cause is unknown. The updater's startup daemon thread is a hypothesis only. Python's official threading docs say daemon threads are abruptly stopped at interpreter shutdown and resources may not be released; this makes the hypothesis plausible, not proven. Required: at least 20 fresh-cache runs on Linux 3.10 and 3.13 with update check enabled/disabled, preserve child stderr/exit code/faulthandler, block the fetch during shutdown in a deterministic test, and verify bounded thread lifecycle/cache writes. Do not permanently disable update checks or mark fixed based on reruns.
- [#189](https://github.com/samjuniors/Orbit-Core/issues/189): mission lock parent-directory symlink/reparse risk. The leaf `O_NOFOLLOW` does not pin the parent; Windows reparse handling is absent. Require a private per-user directory pinned by handle, directory-relative lock creation, adversarial POSIX/Windows tests, and independent review.
- The 100-commit branch `feat/v034-context-aware-intelligence-20261123` at `8620e4a3063852d2c99f6a157fc9ee688c989b6a` remains unapproved for bulk merge. Reconcile its accepted work to #90/#91/#92 and split into reviewable changes.
- Keep RAD P2 #138 and PRs #136–#147 separate and on hold. Orbit Commander remains paused and out of scope.

### Research delta (primary sources)
- [Python 3.12 threading documentation](https://docs.python.org/3.12/library/threading.html): daemon threads are abruptly stopped at interpreter shutdown; use explicit signalling and graceful lifecycle when cleanup matters. This supports investigation of #188 but does not prove causation.
- [Microsoft FILE_ID_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_id_info) and [BY_HANDLE_FILE_INFORMATION](https://learn.microsoft.com/en-us/windows/desktop/api/fileapi/ns-fileapi-by_handle_file_information): file identity is filesystem-specific; ReFS uses 128-bit identifiers and a 64-bit index is not guaranteed unique. Use FileIdInfo where available or fail closed when identity cannot be established.
- [GetFileInformationByHandleEx](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getfileinformationbyhandleex) is the documented handle-based retrieval API for FileIdInfo.

### Environment and next actions
- Remote Arc DESKTOP-AND1FUJ is OFFLINE (last seen 2026-11-27 11:51:32 UTC); Desktop Commander has no connected devices. No local checkout, Windows/Linux adversarial execution, desktop bundle rebuild, owner-profile Claude/Codex/Antigravity acceptance, or `.orbit`/SQLite inspection occurred.
- Orbit ChatGPT plugin connector is not exposed; authorized GitHub and Notion integrations were used. No paid API spend, install, deployment, merge or release occurred.
- Next: (1) verify exact-head CI for new PR #178 and #187 docs commits; (2) address #189 lock-directory safety; (3) finish #186 filesystem independent review and supported-filesystem policy; (4) resolve #184 digest privacy and bundle parity; (5) run the #188 discriminator experiment on Linux; (6) continue #185 only after lock/review gates; (7) keep all v0.34 work out of main until its base is reconciled and reviewed.

## 2026-11-25 — Morning live revalidation

### Main, release and merged fixes
- Canonical `main` remains [`2fdf4f329774b9644e75ac0df4d89738a7cd625f`](https://github.com/samjuniors/Orbit-Core/commit/2fdf4f329774b9644e75ac0df4d89738a7cd625f). Main metadata remains `VERSION=0.33.1` / `NEXT_VERSION=0.34.0`; exact-head [CI #45167794202](https://github.com/samjuniors/Orbit-Core/actions/runs/45167794202) passed all five jobs (Ubuntu Python 3.10–3.13 and Windows Python 3.12).
- Latest published prerelease remains [v0.33.0](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.33.0), published 2026-11-23 08:20:55 UTC; latest stable remains v0.30.0. v0.33.0 has eight assets (four packages plus four SHA-256 sidecars). The tag is annotated; its target commit is `0100e6d1d3e33c907f726c03004d209f7876837d`. v0.33.1 remains source-only and unpublished.
- [PR #175](https://github.com/samjuniors/Orbit-Core/pull/175) merged to main at `a90f1b398a2be9a3807277f560360598ef247e36` (Claude Code Windows `ORBIT_PYTHON` override). [PR #176](https://github.com/samjuniors/Orbit-Core/pull/176) merged at `5416230722b1009df1216023c475738f662f6c0a` (Samjuniors publisher metadata). The owner’s normal profile and actual Claude UI trust-warning behavior remain NOT VERIFIED; publisher metadata does not remove third-party marketplace trust classification.

### Documentation handoff PR
- [PR #178](https://github.com/samjuniors/Orbit-Core/pull/178), branch `docs/orbit-nightly-handoff-20261123`, was at `2cf36d8d240e8c92ee5b436833603e61a8b55647` before this 25 Nov documentation append. It is OPEN / DRAFT, documentation-only (7 files, 13 commits), with no submitted reviews or inline review threads.
- Exact-head [CI #45445143967](https://github.com/samjuniors/Orbit-Core/actions/runs/45445143967) passed 5/5, including Windows Python 3.12. This append creates a new docs-only commit; verify its new exact-head CI and obtain human documentation review before considering merge. Do not merge automatically.

### v0.34 context-aware experiment — still not approved
- Branch [`feat/v034-context-aware-intelligence-20261123`](https://github.com/samjuniors/Orbit-Core/tree/feat/v034-context-aware-intelligence-20261123) is 94 commits ahead / 0 behind main at `f08448ff75c9d87f280ad66ff022a5466a7f4eb4`; no PR or independent review exists.
- Its earlier packaged MCP inventory smoke failure has been corrected. Exact-head [CI #45371214722](https://github.com/samjuniors/Orbit-Core/actions/runs/45371214722) now passes 5/5, including Windows Python 3.12. Green CI does not approve the broad 94-commit branch for merge or release. Reconcile it to approved issues #90/#91/#92 and split any accepted work into bounded PRs.
- Two static review leads remain, neither a reproduced exploit: (1) `source/runtime/orbit_source_audit.py` does not yet demonstrate Windows handle-level reparse-point identity binding across enumeration/open; add adversarial child-reparse-point, hard-link and TOCTOU tests or fail closed. (2) `source/runtime/orbit_agent_factory.py` uses pathname-based parent-directory checks/writes that do not pin parent identity; add directory-handle-relative and Windows reparse-point-aware protections with adversarial tests.

### Previous nightly execution — verified record
- [Orbit Nightly Build](https://github.com/samjuniors/Orbit-Core) did execute on 2026-11-24: run `903fe8fd-19c0-8326-808d-820c8ad70e4d`, scheduled 22:00 IST, started 22:26:04 IST, completed 22:50:39 IST. Recorded status `completed`; latest result run ID matches; result was not marked as a failure, required no user action, and was not truncated. Delivery status is unknown.
- Its recorded outcome: main CI 5/5 PASS; PR #178 exact-head CI 5/5 PASS; v0.34 remains HOLD despite CI 5/5 PASS; handoff, Notion research and roadmap, and release documentation were refreshed. No runtime merge, release, install or deployment occurred.

### Host, connector and next actions
- Remote Arc `DESKTOP-AND1FUJ` remains OFFLINE (last seen 2026-11-23 11:47:38 UTC). No local checkout/tests, owner-profile Claude/Codex/Antigravity acceptance, `.orbit` or SQLite inspection occurred. Orbit ChatGPT plugin connector remains unavailable. GitHub branch-protection endpoint returned 403 `Resource not accessible by integration`; required-check enforcement remains NOT VERIFIED.
- Approved order remains safe Team Builder → task-specific skills/tools → Orbit-mediated agent/bot coordination. Main already contains a read-only Team Builder/skills preview foundation; the missing evidence is host-owned execution, delivery/stop/expiry, permission/session attestation and owner-profile acceptance. Keep preview-only.
- Next: (1) review this docs-only #178 update and verify its new exact-head CI; (2) resolve the two v0.34 static review leads with Windows adversarial tests; (3) reconcile v0.34 to #90/#91/#92; (4) complete owner-profile host acceptance and independent human security review before any v0.33.1 publication; (5) keep RAD P2 #138 separate and on hold.

## 2026-11-24 — Nightly live revalidation

### Main, releases and open work
- Canonical main HEAD remains [2fdf4f329774b9644e75ac0df4d89738a7cd625f](https://github.com/samjuniors/Orbit-Core/commit/2fdf4f329774b9644e75ac0df4d89738a7cd625f); main reports VERSION=0.33.1 / NEXT_VERSION=0.34.0.
- Main exact-head CI [run #45167794202](https://github.com/samjuniors/Orbit-Core/actions/runs/45167794202) remains PASS 5/5.
- Latest published release remains [v0.33.0 prerelease](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.33.0), published 2026-11-23 08:20:55 UTC. Latest stable-channel release remains v0.30.0. v0.33.1 is source-only and unpublished; no release was created.
- Live issue search returned six open issues: #138, #92, #91, #90, #85 and #72. Preserve the approved product order: safe Team Builder → task-specific skills/tools → Orbit-mediated agent/bot coordination. Keep RAD P2 #138 separate.
- PR #178 remains a documentation-only draft. Before this handoff update, its head was 47de86f742679d61725381637ff56de7a770ef5e; exact-head runs [#45304020786](https://github.com/samjuniors/Orbit-Core/actions/runs/45304020786) and [#45304012954](https://github.com/samjuniors/Orbit-Core/actions/runs/45304012954) each passed 5/5, including Windows Python 3.12. No human review is recorded. This documentation update will trigger new exact-head CI; recheck it before marking the PR ready.

### v0.34 context-aware intelligence experiment — NOT APPROVED FOR MERGE
- Branch [feat/v034-context-aware-intelligence-20261123](https://github.com/samjuniors/Orbit-Core/tree/feat/v034-context-aware-intelligence-20261123) is now 94 commits ahead / 0 behind main at [f08448ff75c9d87f280ad66ff022a5466a7f4eb4](https://github.com/samjuniors/Orbit-Core/commit/f08448ff75c9d87f280ad66ff022a5466a7f4eb4). No PR exists.
- Latest exact-head CI [run #45371214722](https://github.com/samjuniors/Orbit-Core/actions/runs/45371214722) passed all five jobs: Ubuntu Python 3.10, 3.11, 3.12 and 3.13, plus Windows Python 3.12. The Windows job also completed ZIP smoke and disposable upgrade rehearsals.
- The plan now labels the work **IN PROGRESS / AUDIT-FIRST IMPLEMENTATION** and explicitly withholds merge, release, installation, host configuration, permission and autonomous-execution authorization. The branch adds structural project inventory, consented bounded source static signals, readiness metadata, revision-aware findings and optional Claude Code lifecycle telemetry. It remains broad and is not yet reconciled to approved issues #90/#91/#92; green CI is not approval.
- **Static security review lead, not a confirmed vulnerability:** source-audit candidate paths are enumerated before open; `O_NOFOLLOW` is used only where the platform exposes it. The code checks file type, size and mtime on the opened handle but does not yet demonstrate Windows handle-level reparse-point identity continuity. Current tests do not demonstrate child reparse-point replacement, hard-link behavior or Windows TOCTOU resistance. Add adversarial Windows tests and prove safe handle semantics or fail closed before approving this slice.
- The optional Claude hook is fail-open telemetry only: it records allowlisted lifecycle event names and a session digest, while discarding prompts, transcripts, tool input/output and permission data. Keep it optional and event-limited; validate the exact host hook schema/version before installation.

### Host, connector and local execution
- Orbit ChatGPT plugin connector is not exposed in the available integration registry; authorized GitHub and Notion integrations were used.
- Remote Arc DESKTOP-AND1FUJ remains OFFLINE (last seen 2026-11-23T11:47:38Z). No Desktop Commander device is connected.
- No local checkout, local test run, owner-profile Claude/Codex/Antigravity acceptance, .orbit directory or SQLite checkpoint was accessed. These remain NOT VERIFIED / NOT RUN.
- Main branch-protection endpoint returned 403 Resource not accessible by integration; ruleset listing returned an empty list. Branch protection and required-check enforcement remain NOT VERIFIED.
- A dedicated Notion handoff page now exists: [Orbit Core — Cross-Agent Handoff & Current State](https://app.notion.com/p/4224f681d488816c9e9efbdc8be38488). Notion Research & References and Continuous Learning/Roadmap were updated with 2026-11-24 findings.

### Fresh research delta (2026-11-24)
- [SWE-Explore](https://arxiv.org/abs/2606.07297) separates repository exploration from patch success and evaluates line-level evidence coverage, ranking and context efficiency across 848 issues, 10 languages and 203 repositories. Add retrieval-quality metrics to Orbit's discovery evaluation; its trajectory-derived ground truth is useful but not a universal diagnosis oracle.
- [DeepSWE](https://arxiv.org/abs/2607.07946) uses 113 original long-horizon tasks and hand-written functional verifiers. Its paper reports 1.4% verifier/LLM-judge disagreement versus 32.4% for inherited SWE-Bench Pro tests in the audited sample. Add original multi-step tasks and behavior-level verifiers; this is a benchmark result, not proof that every verifier is correct.
- [OpenHands Software Agent SDK](https://github.com/OpenHands/software-agent-sdk) separates SDK/Agent Server execution from automation scheduling/dispatch. Use as an architecture reference for keeping Orbit coordination distinct from host-owned execution; no dependency is approved.
- [Claude Code hooks reference](https://code.claude.com/docs/en/hooks) documents event-specific hook type support and security considerations. Keep Orbit hooks optional, command-only and version-gated; never assume all hook types work for all events.

**Historical snapshot:** The 2026-11-23 section below is preserved as dated evidence and is superseded where it conflicts with this 2026-11-24 live revalidation.

## 2026-11-23 — Evening live revalidation

### Main, release and CI
- Canonical main HEAD: [2fdf4f329774b9644e75ac0df4d89738a7cd625f](https://github.com/samjuniors/Orbit-Core/commit/2fdf4f329774b9644e75ac0df4d89738a7cd625f). Main reports VERSION=0.33.1 and NEXT_VERSION=0.34.0.
- Latest published release is [v0.33.0 prerelease](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.33.0), published 2026-11-23 08:20:55 UTC by owner-triggered workflow_dispatch [run #45137788352](https://github.com/samjuniors/Orbit-Core/actions/runs/45137788352). Its annotated tag points to commit [0100e6d1d3e33c907f726c03004d209f7876837d](https://github.com/samjuniors/Orbit-Core/commit/0100e6d1d3e33c907f726c03004d209f7876837d). The tag object is unsigned; SHA-256 sidecars provide integrity checks, not publisher signatures. Eight assets are present: four packages and four checksum sidecars. Latest stable-channel release remains v0.30.0.
- Exact main-head CI [run #45167794202](https://github.com/samjuniors/Orbit-Core/actions/runs/45167794202) completed PASS 5/5 on 2fdf4f. This is hosted CI evidence; no local test suite ran in this session.
- [PR #175](https://github.com/samjuniors/Orbit-Core/pull/175) merged to main at a90f1b398a2be9a3807277f560360598ef247e36 (Claude Code Windows ORBIT_PYTHON override, source VERSION 0.33.1). [PR #176](https://github.com/samjuniors/Orbit-Core/pull/176) merged at 5416230722b1009df1216023c475738f662f6c0a (Claude Code publisher attribution). [PR #173](https://github.com/samjuniors/Orbit-Core/pull/173) merged into the v0.33 integration branch at 51591e6370314e7567946ed3ca60f91aa6a189b4.
- [Issue #130](https://github.com/samjuniors/Orbit-Core/issues/130) was closed as completed after its exact v0.31 stock-agent hash fix shipped in v0.33.0. This does not certify an owner's live migration.
- v0.33.1 is source on main only; no v0.33.1 release/tag exists. Its [version-specific acceptance record](RELEASE-ACCEPTANCE-v0.33.1.md) documents the merged patch, test evidence and outstanding host/security gates. No v0.34 release exists.

### Open work and release/security gates
- [Issue #138](https://github.com/samjuniors/Orbit-Core/issues/138) remains OPEN. RAD P2 OS-isolated preview is still a separate prototype/security workstream; loopback/Python preview acceptance is blocked. Draft PRs #136, #137, #139–#147 remain separate and are not release-ready.
- [PR #141](https://github.com/samjuniors/Orbit-Core/pull/141) remains an adaptive-routing proposal. Do not treat a recommendation preview as model switching or native host execution.
- v0.33 limitations remain: host-enforced timed permission expiry and active revocation BLOCKED; owner-profile native specialist delivery and migration/rollback NOT VERIFIED; independent human security review NOT DONE; full real-product visual/browser QA NOT VERIFIED. v0.33.0 is a prerelease, not a production certification.
- Main branch protection/ruleset status could not be re-read: GitHub returned 403 Resource not accessible by integration. Do not assume required checks or branch protection are enabled.

### v0.34 experimental branch — NOT APPROVED
- Branch feat/v034-context-aware-intelligence-20261123 is 38 commits ahead of main and 0 behind at head 56969232e107c56eb53f89d600793f95383ce2e6. No PR is open for this branch.
- Its plan [docs/CONTEXT-AWARE-INTELLIGENCE-PLAN.md](https://github.com/samjuniors/Orbit-Core/blob/feat/v034-context-aware-intelligence-20261123/docs/CONTEXT-AWARE-INTELLIGENCE-PLAN.md) labels the work PROPOSAL / AUDIT-FIRST / NO RUNTIME IMPLEMENTATION, but the branch actually adds runtime modules and the MCP tool orbit_project_findings. This plan/code mismatch must be resolved before review.
- Exact branch CI [run #45217966745](https://github.com/samjuniors/Orbit-Core/actions/runs/45217966745) failed all five matrix jobs at the same scripts/smoke_release_zip.py line 101 error: “Packaged MCP tool inventory mismatch”. The inspected Ubuntu Python 3.13 job ran 778 tests (6 skipped, 0 failures) before smoke failed. Ubuntu Python 3.10, 3.11, 3.12, 3.13 and Windows Python 3.12 logs all report the same inventory error; the expected inventory remains hard-coded at 57 and omits orbit_project_findings.
- Do not merge, release, or describe this branch as approved. After scope is reconciled, update the package inventory and regression coverage, then rerun all five jobs on the exact head.

### Host, connector and local state
- The Orbit ChatGPT plugin connector was not exposed in the available tool registry, so it was not used. Authorized GitHub and Notion integrations were used instead.
- Remote Arc device DESKTOP-AND1FUJ is OFFLINE; last seen 2026-11-23T11:47:38Z. An isolated checkout attempt for the exact main SHA failed because no online Fleet device satisfied the required tools and permissions.
- No local checkout, local test run, owner-profile IDE acceptance, .orbit directory or SQLite checkpoint was accessed. Mark these NOT VERIFIED / NOT RUN; do not infer local state from GitHub.
- Notion sources: [Project Decisions & Releases](https://app.notion.com/p/4074f681d48881a7a407c3bdc2054409), [Research & References](https://app.notion.com/p/4074f681d488816e9fe7f4504982c948), and [Continuous Learning / Resource-First Specialist Architecture](https://app.notion.com/p/40f4f681d48881cea5afc2df9a35084c). Current documentation-only refresh is in draft [PR #178](https://github.com/samjuniors/Orbit-Core/pull/178); stale [PR #158](https://github.com/samjuniors/Orbit-Core/pull/158) was closed as superseded because its base was 184 commits behind. No separate current Notion handoff page was found; this repository file remains the cross-agent handoff.

### Fresh research delta (2026-11-23)
- [Claude Code hooks](https://code.claude.com/docs/en/hooks): PreModelSwitch exposes context/cache metadata and can allow, deny or ask; hooks run in parallel. Treat this as a Claude-specific, version-gated adapter, not a shared provider contract.
- [Codex sandbox](https://openai.com/index/inside-the-codex-sandbox/): permission profiles constrain filesystem/network access; Windows is transitioning to MXC on compatible devices; stdio MCP server launches are not sandboxed by default. Keep sandbox capability host-specific and evidence-backed.
- [Antigravity skills migration](https://antigravity.google/docs/migration/workflows-to-skills/): workflows are deprecated; skills support progressive context loading and bundled references/scripts. Generate skills, not new legacy workflows.
- [OpenHands SDK](https://github.com/OpenHands/software-agent-sdk): current SDK/Agent Server separates conversations, workspaces, tools and events from automation lifecycle; useful architecture reference, not an automatic dependency.
- [RealSWE](https://arxiv.org/abs/2608.27831) finds realistic requests are sparse (88% problem-only/limited context vs 7% in SWE-bench) and Desired Behavior/Motivation materially improve outcomes. Ask for desired behavior on bug fixes and motivation on feature requests.
- [SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) is a preliminary preprint: 39/49 skills show zero pass-rate gain, average +1.2%, and some version-mismatched skills reduce performance. Prefer targeted, version-compatible skills with deterministic paired tests; avoid blanket injection.
- [OpenAI Agents SDK tracing](https://openai.github.io/openai-agents-python/tracing/) warns generation/function spans may contain sensitive data; default to local, redacted metadata and do not require an OpenAI tracing key for provider-neutral Orbit.
- [SWE-agent](https://github.com/SWE-agent/SWE-agent) now points users to [mini-SWE-agent](https://github.com/SWE-agent/mini-swe-agent). Treat benchmark claims in the latter's README as maintainer-reported, not independent Orbit evidence.

### Approved direction and next safe action
- The existing Notion product direction orders safe Team Builder first, then task-specific skills/tools, then Orbit-mediated agent/bot coordination. Issues #90 (project-scoped learning), #91 (resource-first specialist factory) and #92 (cybersecurity specialist) remain open and must be reconciled with that order and their acceptance criteria.
- No Notion approval was found for the current v0.34 branch's expanded context-monitoring/model-routing scope. Treat it as experimental until its plan, code and acceptance criteria agree and the owner-approved scope is clear.
- Next safe action: reconcile the v0.34 branch with the approved #90/#91/#92 roadmap, keep RAD #138 separate, and only then prepare a focused implementation PR with exact-head regression evidence. Do not silently promote the experimental branch.
- No merge, release, tag, installation, host permission change, credential change or deployment was performed in this checkpoint.

---

## 2026-11-23 — Morning live revalidation (06:26 Asia/Kolkata) — historical snapshot superseded by evening revalidation

**Live snapshot:** canonical repository `samjuniors/Orbit-Core`; default `main` is signed commit [`914290b4a5ac69c0d753961affc916ba2e69b909`](https://github.com/samjuniors/Orbit-Core/commit/914290b4a5ac69c0d753961affc916ba2e69b909). Main still has `VERSION=0.32.0`, `NEXT_VERSION=0.33.0`; the latest published release is [v0.32.0 prerelease](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.32.0) (2026-11-17). Latest stable release remains v0.30.0. No v0.33 tag or public release exists. GitHub reports `main` is not protected and required status checks are off.

### Current v0.33 branches and PRs

- [Integration PR #133](https://github.com/samjuniors/Orbit-Core/pull/133): open/unmerged, head `5c1a3552cd41607d68afc91c58936561e5399254`, base `main` at `914290b4a5ac69c0d753961affc916ba2e69b909`. Exact-head CI [#45049655426](https://github.com/samjuniors/Orbit-Core/actions/runs/45049655426) completed **PASS 5/5** (Ubuntu Python 3.10–3.13; Windows Python 3.12).
- [Candidate PR #135](https://github.com/samjuniors/Orbit-Core/pull/135): open/unmerged, branch `release/v0.33.0-candidate-20261118`, head `098cdf2cfb267d8dd569ab6da5ede6cb728f3dba`, `VERSION=0.33.0`, `NEXT_VERSION=0.34.0`. Exact-head CI [#45048926337](https://github.com/samjuniors/Orbit-Core/actions/runs/45048926337) completed **PASS 5/5**. A fresh live compare now shows the candidate is **54 ahead / 12 behind** integration (`5c1a355`); it is diverged and must be synchronized and revalidated before it can be considered final. The previous sync attempts [#163](https://github.com/samjuniors/Orbit-Core/pull/163) and [#164](https://github.com/samjuniors/Orbit-Core/pull/164) closed **unmerged**; [#165](https://github.com/samjuniors/Orbit-Core/pull/165) was validation-only and closed unmerged. Do not treat its proposed merge commit as applied.
- [PR #159](https://github.com/samjuniors/Orbit-Core/pull/159) merged into the candidate at `098cdf2`, adding owner-only release dispatch/rerun authorization and owner-guidance hash-precedence protection. [PR #156](https://github.com/samjuniors/Orbit-Core/pull/156) merged into integration at `1e04dd1df7ac7fc74cf37d906b25c01bf9aa67d1`; [PR #161](https://github.com/samjuniors/Orbit-Core/pull/161) merged into integration at `5c1a3552cd41607d68afc91c58936561e5399254`. These integration fixes are not yet carried into the current candidate head.
- [PR #166](https://github.com/samjuniors/Orbit-Core/pull/166): open against integration, branch `fix/v033-pin-visual-scan-root-20261122`, head `2f69daa8365e7fd17f7e6991d3141b59c8d340fa`. It closes a parent-directory symlink race by using descriptor-relative no-follow traversal on POSIX and opened-handle containment on Windows, then reading from the validated handle. Exact-head CI [#45051094349](https://github.com/samjuniors/Orbit-Core/actions/runs/45051094349) completed **PASS 5/5**. Earlier run [#45050974010](https://github.com/samjuniors/Orbit-Core/actions/runs/45050974010) failed on the previous head because the race-test monkeypatch did not preserve `os.supports_dir_fd`; the test harness was corrected. A Codex review receipt exists for `2f69daa`, but a separate independent security sign-off is not established.
- [PR #168](https://github.com/samjuniors/Orbit-Core/pull/168) is a temporary CI-validation PR for #166 and explicitly says **DO NOT MERGE**. Older validation PR #167 is closed unmerged. [PR #134](https://github.com/samjuniors/Orbit-Core/pull/134) remains an older alternative candidate draft; keep #135 canonical and do not combine the two.

### Release, host and security gates

**v0.33 remains HOLD / NOT MERGED TO MAIN / NOT TAGGED / NOT RELEASED / NOT INSTALLED.** Outstanding host gates include inherited-profile child-result delivery and Codex child identity/receipt (**NOT VERIFIED**), host-enforced timed permission expiry/active revocation (**BLOCKED**), actual target-project browser/visual QA (**NOT VERIFIED**), historical owner-settings delta (**NOT VERIFIED**), and owner-profile v0.33 install/rollback (**NOT RUN**). RAD P2 [issue #138](https://github.com/samjuniors/Orbit-Core/issues/138) remains open; drafts #136–#147 are separate from v0.33. LPAC Python HTTP preview and descendant launch remain blocked; do not describe the prototype as a production OS sandbox.

The candidate release workflow is owner-only manual dispatch from `main`; main's currently published workflow separately supports manual dispatch and tag-push prereleases. Reconcile this branch-specific difference after any approved merge.

### Environment and research

Remote Arc device `DESKTOP-AND1FUJ` is still **offline** (last seen 2026-11-21 11:56 UTC). No local checkout, local tests, owner-profile operation, or `.orbit`/SQLite checkpoint was accessed in this report. The Orbit-specific ChatGPT plugin connector was not exposed in the available tool registry; GitHub and Notion were used. The latest research record remains 2026-11-22 and is based on primary vendor documentation (Google Antigravity, Anthropic Claude Code, OpenAI Codex/Agents SDK); findings are host-specific design references, not implementation evidence or an approved dependency. No new external research or owner decision was added in this run.

### Next safe sequence

1. Complete review of #166; merge only the actual fix into integration after review and exact-head CI remain green. Never merge #168.
2. Rebuild/synchronize the candidate from the current integration head, preserving candidate-only release controls; then run exact-head candidate CI and fresh review. Do not rely on the closed #163/#164/#165 sync attempts.
3. Reconnect the authorized Windows host and run bounded disposable native acceptance; update the existing v0.33 acceptance matrix with evidence.
4. Obtain the owner's explicit risk/release decision only after the host, security, package, and rollback gates are reviewed. Do not merge to main, tag, publish, install, or deploy before that decision.

## 2026-11-22 — Live continuation checkpoint: P2 stop-session retry + provider adapter research

**Verified source snapshot:** canonical repo `samjuniors/Orbit-Core`; default `main` at `914290b4a5ac69c0d753961affc916ba2e69b909` (signed commit). Published latest release remains prerelease `v0.32.0`; no v0.33 release is published. The historic Orbit-Core-MCP URL redirects to this repository.

### Active work and evidence

- [PR #133](https://github.com/samjuniors/Orbit-Core/pull/133) remains open/unmerged as the v0.33 integration base. [PR #135](https://github.com/samjuniors/Orbit-Core/pull/135) remains the versioned v0.33.0 candidate stacked on #133. [PR #155](https://github.com/samjuniors/Orbit-Core/pull/155) is CI-validation-only; never merge it.
- Codex's review on #133 found a P2 defect: an earlier native worker session's stop request could block a retry in a new session. [PR #156](https://github.com/samjuniors/Orbit-Core/pull/156) implements task-revision/native-session-scoped duplicate detection, exact attempt stop-plan lookup, retirement correlation, and a regression test preserving the old request as audit evidence.
- Initial #156 CI run [#45047149105](https://github.com/samjuniors/Orbit-Core/actions/runs/45047149105) failed on all four Ubuntu Python versions at an assertion expecting the prior stop request to disappear from the inbox. That expectation conflicts with the intended audit contract: historical requests remain pending evidence. The branch was updated; current PR head observed as `dd835332cd1279ded38de51eeb5fc5b835cd183a`. Latest matrix run [#45047242899](https://github.com/samjuniors/Orbit-Core/actions/runs/45047242899) was **IN PROGRESS** at snapshot time. Recheck exact head and all five jobs before calling it PASS.
- [PR #157](https://github.com/samjuniors/Orbit-Core/pull/157) is explicitly a temporary CI-validation PR for #156; its body says **DO NOT MERGE**. Close only after its validation purpose is fulfilled and evidence is recorded.
- [RAD P2 issue #138](https://github.com/samjuniors/Orbit-Core/issues/138) remains open. RAD P0/P1/P2 drafts #136–#147 are separate, security-sensitive, and not automatically included in #135.

### Release disposition

**v0.33 remains HOLD / NOT MERGED / NOT TAGGED / NOT RELEASED / NOT INSTALLED.** Outstanding gates include real supported-host acceptance (including native child receipts/permission and cancellation reconciliation), host-enforced timed permission expiry/revocation, actual target-project browser/visual QA, independent security review, and owner release decision. Do not treat CI or a synthetic fixture as host/production certification. Follow the canonical [release process](RELEASE-PROCESS.md) and existing [v0.33 acceptance matrix](RELEASE-ACCEPTANCE-v0.33.0.md). Preserve v0.32 assets.

### Cross-host primary-source research delta

Research recorded in the existing Notion [Orbit Core Research & References](https://app.notion.com/p/4074f681d488816e9fe7f4504982c948) page (2026-11-22):
- Antigravity's current rules support cumulative workspace/global `AGENTS.md`, `GEMINI.md`, and `.agents/rules/*.md`; Google says legacy Workflows are deprecated in favor of skills. Enforce documented file/token budgets; don't emit deprecated workflow manifests as the preferred integration.
- Claude Code exposes lifecycle hooks (SessionStart, PreToolUse, PostToolUse, PermissionRequest, Stop, PostCompact); hooks execute commands with host-user privileges, so treat them as privileged code requiring review and narrow allowlists.
- Codex distinguishes read-only/workspace-write sandboxes and approval policies; bypass flags remove protection. Preserve native approvals and never route around host denials.
- OpenAI Agents SDK documents manager-owned agents-as-tools versus control-transferring handoffs, plus traces for tool calls/handoffs/guardrails. Use as design reference only, not an Orbit runtime dependency.
- Recommendation: canonical provider-neutral task/evidence state + thin versioned adapters; model host capabilities as observed, not assumed; represent proposed → host-approved → host-invoked → independently observed → reconciled; measure task quality, regression, policy compliance, interventions, latency and cost only where real metadata exists.

### Blockers and next safe action

- Remote Arc Windows was previously reported offline; recheck before any local/IDE acceptance. No local `.orbit`/SQLite checkpoint was accessed in this run.
- Orbit-specific ChatGPT plugin was not exposed in the available integration registry; GitHub and Notion integrations were used. Do not claim plugin execution.
- **Next:** revalidate #156 latest head and #45047242899; inspect failure logs if any, then obtain focused independent review. Keep #157 non-mergeable/validation-only. Resume #133/#135 acceptance only after the P2 finding is resolved and all separate host/security/release gates are evidenced.

**Notion records updated:** [Project Decisions & Releases](https://app.notion.com/p/4074f681d48881a7a407c3bdc2054409) and [Research & References](https://app.notion.com/p/4074f681d488816e9fe7f4504982c948). GitHub and Notion are linked sources, not auto-synchronized. This is a redacted shared handoff; no credentials, local paths, raw SQLite/WAL or host tokens included.

---

## Source of truth and handoff contract

**Status:** maintained handoff contract plus a dated engineering snapshot, **not** authorization to merge, install, or release.
**Last reviewed:** 2026-11-23 (Asia/Kolkata).
**Project:** [samjuniors/Orbit-Core](https://github.com/samjuniors/Orbit-Core). The historic Orbit-Core-MCP URL redirects to this repository.
**Applies to:** ChatGPT, Claude Code, Codex, Antigravity and other authorized coding hosts. **Not** the separate Orbit Commander project (paused by owner).

## 2026-11-22 — documentation merge and release disposition

- [PR #148](https://github.com/samjuniors/Orbit-Core/pull/148) is **MERGED** to `main` at [`2a11fd37b171fa2701e5c4d926b941f6b4f65332`](https://github.com/samjuniors/Orbit-Core/commit/2a11fd37b171fa2701e5c4d926b941f6b4f65332). Six documentation paths from this handoff are now on main. Exact PR-head CI #44903594241 completed success; separate push CI on the merge commit was not confirmed.
- Main `VERSION` remains `0.32.0`. **No new release was created.** v0.33.0 remains a separate unmerged candidate stacked on #133; its existing acceptance record continues to report owner-profile native delivery NOT VERIFIED, host-enforced timed permission expiry/active revocation BLOCKED, and independent review/owner release gates outstanding. Do not publish based on the documentation PR's CI.
- **Release trigger policy verified on 2026-11-22:** `.github/workflows/release.yml` intentionally supports (1) manual `workflow_dispatch` from `main`, with `prerelease` as the default and `stable` available only through that explicit manual path, and (2) a matching `v[0-9]*` tag push, which is forced to `prerelease` and must point to a commit already contained in `main`. `docs/RELEASE-PROCESS.md` documents both paths. The earlier handoff statement calling this a contradiction/manual-only policy was incorrect. No workflow code change is required for this finding; release readiness and explicit owner approval remain separate mandatory gates.
- Notion project hub updated with the merge SHA, release HOLD, and this workflow discrepancy. Local PC `.orbit`/SQLite remains unverified; Remote Arc was offline at the last check.

## 1. Source of truth and handoff limits

| Source | Owns | Never assume |
| --- | --- | --- |
| GitHub | Exact implementation, branch/commit, open PRs/issues, CI, acceptance evidence, release tags/assets | An unmerged PR is installed; green CI means host/release approval |
| [Orbit Core Notion decisions hub](https://app.notion.com/p/4074f681d48881a7a407c3bdc2054409) | Product intent, decisions, rationale, research, approved priorities | A Notion proposal is implemented or released |
| Local project SQLite and ignored .orbit directory | Project-specific tasks, checkpoints, revisions, recovery and host-operational state | The database or local files automatically follow a Git clone, another computer, or another AI session |

Provider switching transfers **explicit records and source evidence**, not hidden conversations, model context, credentials, host permissions, in-memory processes or uncommitted work. A new agent **must verify actual state**, not silently replay actions. Private/local databases stay local; use the existing Orbit project scan/resume/task/checkpoint MCP tools when the authorized host exposes them. Never upload SQLite/WAL, approval tokens, private host settings, log secrets or unrelated project memory to Git/Notion.

**Agent reading order:** [AGENTS.md](../AGENTS.md) → this document → relevant task branch and PR → relevant code/tests → [Notion decisions hub](https://app.notion.com/p/4074f681d48881a7a407c3bdc2054409). For releases, [RELEASE-PROCESS.md](RELEASE-PROCESS.md) and the exact version acceptance document are mandatory. For Claude Code, [CLAUDE.md](../CLAUDE.md) is a short entry point, **not** another source of truth.

## 2. Dated active engineering snapshot — 2026-11-21

This is a **historical checkpoint**. Before work resumes, inspect the current head, base, status and reviews of each named PR, the latest GitHub Releases page, exact-head CI and the most recent Notion decision. Do not promote this snapshot into evidence of present-day test success.

| Track | State and action |
| --- | --- |
| Published release | [v0.32.0 prerelease](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.32.0) is the published installation baseline, with 57 reported MCP tools in prior acceptance. Main's VERSION was 0.32.0 when read for this checkpoint. Recheck releases before version operations. |
| Candidate v0.33 | [Integration draft #133](https://github.com/samjuniors/Orbit-Core/pull/133) → stacked [candidate draft #135](https://github.com/samjuniors/Orbit-Core/pull/135), branch `release/v0.33.0-candidate-20261118`. Its own [release acceptance matrix](https://github.com/samjuniors/Orbit-Core/blob/release/v0.33.0-candidate-20261118/docs/RELEASE-ACCEPTANCE-v0.33.0.md) is authoritative for exact tests, hosts and evidence. **UNMERGED / UNPUBLISHED / RELEASE HOLD.** |
| Candidate last observed | PR #135 reports checkpoint [4e20b04c](https://github.com/samjuniors/Orbit-Core/commit/4e20b04c034a26069d9e6f7236d7973c2e9a0bcd) with [CI run #44901076599](https://github.com/samjuniors/Orbit-Core/actions/runs/44901076599) PASS 5/5 after a rerun of Ubuntu 3.10; the prior signal-11 MCP subprocess failure has **unverified cause**. The PR describes disposable host child delivery/lead review as scoped PASS, but owner-profile inherited delivery and historical settings change as NOT VERIFIED, and timed permission expiry/active revocation as BLOCKED. This is **not** a claim that the current PR head equals that SHA. |
| RAD layered defense | [Issue #138](https://github.com/samjuniors/Orbit-Core/issues/138) OPEN; security drafts [#136](https://github.com/samjuniors/Orbit-Core/pull/136), [#137](https://github.com/samjuniors/Orbit-Core/pull/137), [#139](https://github.com/samjuniors/Orbit-Core/pull/139), [#140](https://github.com/samjuniors/Orbit-Core/pull/140), [#143](https://github.com/samjuniors/Orbit-Core/pull/143)–[#147](https://github.com/samjuniors/Orbit-Core/pull/147) are **separate and draft**. #146 is synthetic, bounded static HTTP snapshot research; #147 proposes package exclusion of experimental prototypes. Neither is proof of production OS isolation or live application browser security. Do **not** automatically fold these into #135. |
| Other independent work | [Adaptive-routing draft #141](https://github.com/samjuniors/Orbit-Core/pull/141) and other older draft PRs remain independent. Inspect each before claiming it is superseded or complete. |
| Owner constraints | **No merge, tag, publication, installation, credential changes, OS security profile changes or release approval** granted by this handoff request. Orbit Commander remains paused; do not resume it under Orbit Core. |

**Next recommended bounded task:** read #135's actual current head and [acceptance matrix](https://github.com/samjuniors/Orbit-Core/blob/release/v0.33.0-candidate-20261118/docs/RELEASE-ACCEPTANCE-v0.33.0.md); reconcile its open gates with #133, Notion and the current host capabilities. Prioritize reproducible intermittent CI diagnostics and remaining host/release blockers **without weakening fail-closed policy**. Advance only work approved in the current task; do not silently cross from documentation/analysis to release operations.

## 3. Switching protocol (ChatGPT → Claude Code → ChatGPT)

### Before yielding control — outgoing agent

1. Read actual repository/branch/PR state and working tree. Record **branch, full HEAD SHA, base PR and dirty/untracked file counts**. Never hide pending local edits or overwrite another agent's work.
2. Capture objective and scope, approved decisions, changes made, paths touched, tests actually run (commands, environment, exact commit, results), evidence links, blockers, release/host gates, pending processes and the **single next safe action**.
3. If Orbit MCP is connected and authorized, read/resume the correct project and record its existing revisioned checkpoint/task/ledger state **using its real APIs**. Do not fabricate a checkpoint or treat tool discovery as a successful write. Leave local SQLite/WAL intact.
4. Save **private operational detail** in project-local ignored `.orbit/` using existing project checkpoint conventions. Publish only a **redacted summary** via the current GitHub draft branch/PR and append durable **product decisions** to the existing Orbit Notion hub. Do not copy an entire session transcript, raw credentials, local filesystem paths, host approval tokens or private evidence into a public commit.
5. Confirm any issued write completed. Report **NOT VERIFIED** for any attempted but unconfirmed action. Stop issuing writes after handing over ownership; never allow two agents to mutate the same files/checkpoint concurrently.

### On taking control — incoming agent

1. Read this file, AGENTS.md, the task's PR/evidence and the Notion hub. Requery live GitHub status and verify source HEAD, actual working tree, existing local Orbit state and host/permission availability.
2. Compare the prior handoff's exact SHA/branch/revision to what is truly present. On mismatch, **pause writes, reconcile and preserve both versions**; do not replay uncertain installs, approvals, merges or irreversible actions.
3. Restore only **the relevant project's** state. If local `.orbit` or SQLite isn't accessible, work from sanitized shared records and mark local revision/host checks **BLOCKED or NOT VERIFIED** rather than pretending to have loaded them.
4. Continue one bounded authorized action on an appropriate branch. Re-run impacted tests and record evidence. Do not inherit permission grants from an earlier model/host.

### Minimal read-only terminal checks

```bash
git status --short
git branch --show-current
git rev-parse HEAD
git log -1 --format='%H %s'
```

Use the connected host's approved read-only GitHub/Notion tools when no terminal is available. Commands above do not prove that ignored SQLite or other local state has been recovered.

## 4. Handoff record template (fill at every meaningful milestone)

Keep one **current handoff per workstream**, linked from the active draft PR or its comment. Update/supersede the prior handoff instead of spawning competing files. This template is intentionally plain text and works in GitHub, Notion, Claude Code and ChatGPT.

```text
ORBIT CORE HANDOFF — YYYY-MM-DD HH:MM timezone
From agent/host:                 To agent/host:
Project: samjuniors/Orbit-Core (never another product)
Objective and scope:
Branch / base / full HEAD SHA:
Open PR(s) / issue(s):
Working tree: clean | dirty (counts only); unpushed work:
Version / published baseline (verified with URL and date):
Completed changes (IMPLEMENTED vs VERIFIED):
Checks: command + platform + source SHA + PASS/FAIL/BLOCKED/NOT RUN:
Native IDE / permission / browser acceptance:
Local Orbit project key + checkpoint/task revision (no secrets):
Local-only/private evidence location (reference, not contents):
Notion decision page / approved vs proposed:
Outstanding bugs, risks, blockers and owner decisions:
Pending processes / unresolved side effects / cleanup:
Next single safe action + expected acceptance evidence:
Explicit limits (no merge/release/install/credential change unless approved):
Handoff saved where / receiving agent verification result:
```

**Status vocabulary:** PROPOSED, APPROVED, IMPLEMENTED, VERIFIED for decisions/implementation; **PASS, FAIL, BLOCKED, SKIPPED, NOT RUN, NOT VERIFIED** for tests/gates. A PR comment, model statement, checklist or agent-generated receipt is **not** evidence of a host action without independent confirmation.

## 5. Ready-to-use resume prompt

> You are continuing **Orbit Core** only, repository https://github.com/samjuniors/Orbit-Core. First read AGENTS.md, docs/AGENT-HANDOFF.md, the current task PR and its exact-head acceptance record, plus the Orbit Core Notion decisions hub. Compare current GitHub branch/commit/CI with the handoff snapshot, then inspect local .orbit/SQLite checkpoint **only if connected and authorized**. Report discrepancies and verified vs not-verified work. Preserve uncommitted work, credentials and host permissions; do not touch paused Orbit Commander or other repositories. Continue the smallest approved next action on a draft branch, add regression evidence and update the handoff for the next ChatGPT/Claude Code switch. Never merge, install or release without explicit owner permission.

## 6. Updating the handoff itself

At the end of each meaningful task, update **this single handoff record** only for shared engineering summary and actionable pointers; preserve dated historical evidence instead of rewriting it as current. Put detailed version/host acceptance in the **existing** `docs/RELEASE-ACCEPTANCE-vX.Y.Z.md`, product decisions in the **existing** Notion hub, and ephemeral task/checkpoint data in **local** SQLite/`.orbit`. Link rather than duplicate. If a new agent can't access one source, record that constraint explicitly and do not infer its contents.


## 2026-11-24 — Morning live revalidation

### Main, releases and merged work
- Canonical `main` remains [2fdf4f329774b9644e75ac0df4d89738a7cd625f](https://github.com/samjuniors/Orbit-Core/commit/2fdf4f329774b9644e75ac0df4d89738a7cd625f). `VERSION=0.33.1`; `NEXT_VERSION=0.34.0`. The latest main commit pins deterministic Git line endings in `.gitattributes` (`* text=auto eol=lf`) and exempts Windows `.bat/.cmd` files from conversion.
- Exact-main [CI #45167794202](https://github.com/samjuniors/Orbit-Core/actions/runs/45167794202) passed 5/5 (Ubuntu Python 3.10–3.13; Windows Python 3.12).
- Published [v0.33.0 prerelease](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.33.0) remains the latest prerelease, published 2026-11-23 08:20:55 UTC by owner-triggered [workflow #45137788352](https://github.com/samjuniors/Orbit-Core/actions/runs/45137788352). The annotated tag points to `0100e6d1d3e33c907f726c03004d209f7876837d`; eight assets are present (four packages plus four SHA-256 sidecars). The tag object is unsigned; sidecars are integrity checks, not publisher signatures. Latest stable release remains v0.30.0. No v0.33.1 or v0.34 tag/release exists.
- [PR #175](https://github.com/samjuniors/Orbit-Core/pull/175) merged to main at `a90f1b398a2be9a3807277f560360598ef247e36`: Claude Code Windows plugin MCP supports `${ORBIT_PYTHON:-python}`. [PR #176](https://github.com/samjuniors/Orbit-Core/pull/176) merged at `5416230722b1009df1216023c475738f662f6c0a`: explicit Samjuniors marketplace/plugin publisher metadata. The actual post-refresh Claude UI display replacing “Unknown Developer” is still NOT VERIFIED; third-party marketplace trust warnings remain expected.
- [PR #173](https://github.com/samjuniors/Orbit-Core/pull/173) merged into the v0.33 integration branch at `51591e6370314e7567946ed3ca60f91aa6a189b4` for Codex P2 review remediations. [Issue #130](https://github.com/samjuniors/Orbit-Core/issues/130) is closed as completed after the stock-agent installer fingerprint fix shipped in v0.33.0.

### Cross-agent handoff and docs PR
- [PR #178](https://github.com/samjuniors/Orbit-Core/pull/178), branch `docs/orbit-nightly-handoff-20261123`, is still OPEN / DRAFT / documentation-only. Before this 2026-11-24 handoff append, its head was `f37a2eebe17ad8b96de6280bd056b9e447423e17`, 9 commits ahead / 0 behind main. Exact-head [CI #45225953749](https://github.com/samjuniors/Orbit-Core/actions/runs/45225953749) passed 5/5, including Windows Python 3.12. No review submissions or inline review threads were returned. It changes seven documentation files only; no runtime changes.
- This append creates a new docs-only head; rerun/verify exact-head CI before merging #178. Do not merge automatically.

### v0.33.1 publication gates
- v0.33.1 is source-only on main; no tag/release and no owner-only release workflow dispatch. [PR #175](https://github.com/samjuniors/Orbit-Core/pull/175) reports isolated Claude Code 2.1.307 validation, marketplace update 0.33.0→0.33.1, and `claude mcp list` Connected with `ORBIT_PYTHON`; without the override the machine's Microsoft Store Python alias still fails. It also reports 769 Windows CPython 3.12 tests passed / 33 skipped plus readiness, strict-bundle, build-verify and ZIP-smoke PASS. These are PR-reported results, not rerun in this automation.
- Owner's normal Claude Code profile, owner-profile Codex/Antigravity migration and specialist delivery, timed host permission expiry/active revocation, complete real-project visual/browser QA, and independent human security review remain NOT VERIFIED / BLOCKED / NOT DONE. Main branch protection/required checks remain NOT VERIFIED because the GitHub integration previously returned 403. Do not publish v0.33.1 until the acceptance record is revalidated and owner release authorization is explicit.

### v0.34 experiment and approved product order
- `feat/v034-context-aware-intelligence-20261123` is 38 commits ahead / 0 behind main at `56969232e107c56eb53f89d600793f95383ce2e6`, with no PR. Exact [CI #45217966745](https://github.com/samjuniors/Orbit-Core/actions/runs/45217966745) failed 5/5: every matrix job fails at `scripts/smoke_release_zip.py:101` with “Packaged MCP tool inventory mismatch”. The inspected Ubuntu Python 3.13 job passed 778 tests (6 skipped) before the smoke failure. The branch adds `orbit_project_findings` but the packaged smoke inventory still expects 57 tools. Its plan says “no runtime implementation” while the branch contains runtime changes. No approval for this expanded scope was found. Do not merge or release it.
- The approved product order remains safe Team Builder first, task-specific skills/tools second, Orbit-mediated agent/bot coordination third. [Issues #90](https://github.com/samjuniors/Orbit-Core/issues/90), [#91](https://github.com/samjuniors/Orbit-Core/issues/91), and [#92](https://github.com/samjuniors/Orbit-Core/issues/92) remain open. Reconcile the v0.34 proposal with this order before selecting a bounded implementation.
- RAD P2 [issue #138](https://github.com/samjuniors/Orbit-Core/issues/138) remains OPEN and separate. Draft PRs #136–#147 are not release-ready; OS-isolation/preview acceptance remains on hold.

### Research and nightly execution
- The Notion Research & References page includes the 2026-11-23 update: Claude Code hooks are host-privileged and provider-specific; Codex sandbox/approval policy remains host authority; Antigravity is migrating from legacy Workflows to Skills; OpenHands SDK is an architectural comparison, not an adopted dependency; RealSWE supports asking for desired behavior/motivation; SWE-Skills-Bench is a preliminary preprint warning against blanket skill injection; mini-SWE-agent benchmark claims are maintainer-reported. No new research was added on 2026-11-24.
- [Orbit Nightly Build](https://github.com/samjuniors/Orbit-Core) actually ran: recorded run `5a3858a3-c5a8-8320-946c-6f47b2694e06`, scheduled 2026-11-23 22:00 IST, started 22:31 IST, completed 22:51 IST with status `completed`; its result matched the run ID, was not marked as a failure, and required no user action. It reported main CI 5/5 PASS, #178 CI pending at that time, and v0.34 CI 5/5 FAIL. Automation delivery status is unknown.
- Remote Arc `DESKTOP-AND1FUJ` remains OFFLINE (last seen 2026-11-23 11:47:38 UTC). No local checkout/tests, owner-profile IDE acceptance, `.orbit` or SQLite inspection occurred. The Orbit ChatGPT plugin connector was not exposed; GitHub and Notion were used.

### Next safe actions
1. Review #178 and rerun exact-head CI after this documentation append; keep it draft until reviewed.
2. Validate the owner’s normal Claude Code profile and actual marketplace publisher display; preserve existing user configuration.
3. Complete owner-profile Codex/Antigravity acceptance and obtain independent human security review; document timed permission expiry/revocation as blocked until host evidence exists.
4. Keep v0.33.1 unpublished until its exact-main release workflow, acceptance gates and owner authorization are satisfied.
5. Reconcile the v0.34 plan/runtime mismatch with the #90/#91/#92 order; do not merge the 38-commit experiment as-is.
6. Keep RAD P2 #138 isolated from product/release work.


## 2026-11-25 22:44 IST — live nightly revalidation

### Canonical repository and release state
- Canonical repository revalidated: https://github.com/samjuniors/Orbit-Core
- Main remains 2fdf4f329774b9644e75ac0df4d89738a7cd625f; VERSION=0.33.1; NEXT_VERSION=0.34.0.
- Main exact-head CI #45167794202 remains PASS 5/5.
- Latest published prerelease remains v0.33.0; latest stable-channel release remains v0.30.0. v0.33.1 and v0.34.0 are not published.
- Live inventory: 159 branches (page 1 = 100, page 2 = 59, page 3 empty); 8 open issues; 43 open PRs (40 drafts, 3 non-drafts). No bulk cleanup was performed.

### Focused v0.34 PR stack — all remain drafts
- PR #178 — docs/roadmap/handoff refresh: https://github.com/samjuniors/Orbit-Core/pull/178. Head f305f1eea2b4f51f0da6158cf9a758e6b97b2c6f; 7 files. Exact-head push and pull-request runs #45526281822 and #45526293033 both PASS. No human review.
- PR #179 — task-specific Team Builder model recommendations: https://github.com/samjuniors/Orbit-Core/pull/179. Head 1c1e949e96df3445ab64d109ab0b951204de183f; workflow run #45545884593 completed successfully. Recommendations remain advisory; no host model switch or provider execution is claimed.
- PR #180 — project-scoped skill lifecycle tests: https://github.com/samjuniors/Orbit-Core/pull/180. Head 50ab30468a036c3803950d6cb20e7576682c204e; workflow run #45549132274 completed successfully. This is test coverage, not the complete Issue #90 runtime implementation.
- PR #181 — resource-first specialist / role-factory safety tests: https://github.com/samjuniors/Orbit-Core/pull/181. Head b46fad39e5ec26a7af7cef8ef646d28342da6da4; workflow run #45548741789 completed successfully. This is test coverage, not authenticated native worker execution.
- PR #182 — product-aware cybersecurity review planning: https://github.com/samjuniors/Orbit-Core/pull/182. Current head 54a78b863c10baea305f0adf9f1c96c7fa39c58c; 45 commits / 25 files; still draft. Prior CI failures exposed (1) a stale 57-tool assertion after adding tool 58, now fixed to 58, and (2) strict source/package parity after the generated desktop bundle was temporarily restored to main's old blob. The branch now carries the 58-tool desktop bundle required by the parity check. Latest exact-head runs #45664882357 and #45664888434 were pending at this checkpoint; recheck before any readiness decision.
- PR #182's planner and bounded static pattern review are not SAST, a penetration test, scanner-discovery proof, or security certification. Tool names are caller-reported hints; host permission is not independently verified. No external scanner is installed or invoked.

### v0.34 context-aware experiment — NOT APPROVED
- Branch feat/v034-context-aware-intelligence-20261123 compares 100 commits ahead / 0 behind main and has no PR. Exact branch CI #45561811215 passed 5/5; its Windows job reports 835 tests, 13 skips.
- The branch plan records deterministic disposable Windows junction-replacement reproductions in the previous implementation: agent candidate creation wrote outside the selected project, and structural inventory included a sibling-project path. Current branch containment fails closed on Windows: agent candidate writes return HOLD_WINDOWS_SAFE_WRITE_UNAVAILABLE; source audit and structural inventory return INCOMPLETE without reading/enumerating. This is containment, not a complete Windows implementation.
- New POSIX static-review lead, not yet reproduced: orbit_source_audit.scan_source enumerates with path-based os.scandir and later opens full paths with leaf-only O_NOFOLLOW; this does not pin intermediate parent directories. orbit_project_audit.scan_project uses path-based directory traversal, and orbit_agent_factory.candidate checks/creates parents by pathname before the final O_NOFOLLOW open. A parent symlink/directory replacement may redirect reads or writes between those operations. Non-Windows traversal/writes remain enabled and need adversarial tests.
- Created issue #183: https://github.com/samjuniors/Orbit-Core/issues/183. It tracks handle-relative traversal and candidate creation across platforms. Reuse existing orbit_specialists._visual_walk / _open_visual_source for handle-relative reads where appropriate; implement held-handle-relative creation for writes. Keep the broad 100-commit branch off main until scope and security review are complete.

### Security-review finding deferred for exact package parity
- During PR #182 review, evidence_sha256 was found to hash the matched source line. For credential-like findings this can become an offline guessing oracle even though raw source text is not returned.
- A locator-only digest fix was prototyped, but strict prepare_release_candidate.py parity requires rebuilding the tracked desktop MCP bundle from the exact source. The local build environment was unavailable, so the source change was reverted rather than bypassing the parity gate.
- Created issue #184: https://github.com/samjuniors/Orbit-Core/issues/184. Until the locator-only reference is implemented and the package rebuilt, do not describe the current line-derived digest as a safe redacted proof.

### Fresh security research delta
- OWASP ASVS 5.0.0 is the stable release (published 2025-05-30); OWASP's bleeding-edge build is preview-only. Pin stable, versioned requirement IDs in release evidence rather than tracking moving master.
- OWASP MASVS is a living, risk-based mobile standard covering storage, crypto, auth, network, platform, code, resilience and privacy. It is not a substitute for secure architecture/threat modeling or backend controls.
- NIST SSDF publications list SP 800-218 v1.1 as final and SP 800-218 Rev.1 v1.2 as a draft (published 2025-12-17). Use v1.1 as the current final baseline and track v1.2 as draft only; the GenAI community profile SP 800-218A is a separate final reference.
- Semgrep Community Edition is a local SAST candidate; Trivy repository scanning covers vulnerabilities, misconfigurations, secrets and licenses; OSV-Scanner supports dependency/lockfile analysis and offline mode with a preloaded local database; OpenSSF Scorecard supplies supply-chain hygiene heuristics, not proof of application security.
- Do not install or invoke these automatically. Discover already-installed tools, pin versions/rules/data, confirm license and network behavior, require explicit project/host permission, and report scanner coverage/limitations. OSV-Scanner offline mode avoids network after the database is provisioned; online mode can query OSV.dev/deps.dev and registries. Trivy local repo mode is preferable to remote URL mode for local-first review.

### Execution environment and gates
- Remote Arc DESKTOP-AND1FUJ last seen 2026-11-25T11:40:58Z and is currently OFFLINE. Desktop Commander reports no connected devices. A container git clone attempt failed because github.com DNS resolution was unavailable. No local checkout/test execution, owner-profile Claude/Codex/Antigravity acceptance, .orbit inspection or SQLite inspection occurred in this run.
- Orbit ChatGPT plugin connector remains unavailable in the exposed integration registry; GitHub and Notion integrations were used.
- GitHub branch-protection endpoint still returns 403 Resource not accessible by integration; required-check enforcement remains NOT VERIFIED.
- No merge, release, install, deployment, paid API use or host permission change occurred.
- Next: recheck PR #182 CI; obtain a real build environment to regenerate its bundle and implement #184; prioritize adversarial POSIX path-replacement tests and handle-relative work in #183; review #178–#182 independently; keep v0.33.1 and v0.34 unpublished until host acceptance, independent security review, packaging parity and all release gates pass.


## Final live checkpoint — 2026-11-25

- PR #178 prior docs head c613bb7f9266c4c957cb567cf8724e05817b33f4 (16 commits / 7 files) passed both exact-head runs: push #45665192614 and pull_request #45665200445, each 5/5 including Windows Python 3.12. No human review is recorded; keep draft. This additional handoff checkpoint is another documentation-only commit and will trigger a fresh exact-head CI run; verify it before any merge decision.
- PR #182 current code head 54a78b863c10baea305f0adf9f1c96c7fa39c58c (45 commits / 25 files) passed push #45664882357 and pull_request #45664888434, both 5/5 including Windows Python 3.12 and previous-version upgrade rehearsals. Keep draft: issue #184's source-derived evidence digest privacy concern remains open, host permission is caller-reported, and independent human/security review is still required.
- PR #179 (advisory model recommendations), #180 (skill lifecycle tests only) and #181 (resource-first specialist tests only) remain draft; their previously checked CI runs succeeded. None proves host model switching, skill activation or native worker execution.
- The context-aware experiment is 100 commits ahead / 0 behind main, no PR; CI #45561811215 passed 5/5 (Windows 835 tests, 13 skips). The previous Windows junction-replacement escape is contained by fail-closed Windows paths, not fixed by handle-relative implementation. POSIX parent-directory replacement remains a static-review lead, tracked in #183.
- Mobile-security research update: OWASP published MASWE v1.0.0 on 2026-08-17 with 78 stable weakness IDs; OWASP reports 36/78 still have no MASTG test. Use MAS-L1 only where its assumptions fit; untested weaknesses remain REVIEW_REQUIRED. Link the MASVS control → MASWE weakness → MASTG test/demo chain when available. Sources: https://mas.owasp.org/news/2026/08/17/maswe-v100-release/ and https://mas.owasp.org/Profiles/MAS-L1/
- Notion handoff, roadmap, decisions and research pages were updated; the new MASWE/MAS-L1 research delta was added to Research & References and Roadmap.
- Environment remains blocked for local execution: Remote Arc Windows device offline, Desktop Commander unconnected, container clone failed DNS. No local checkout/tests, .orbit/SQLite inspection or owner-profile host acceptance. Orbit ChatGPT plugin connector is not exposed; GitHub and Notion integrations were used. Branch protection remains unverified (403).
- No merge, release, installation, deployment, paid API use or host permission change. v0.33.1 and v0.34 remain unpublished.


## 2026-11-26 — Live GitHub / Notion checkpoint

**Main:** `2fdf4f329774b9644e75ac0df4d89738a7cd625f`, unchanged since 2026-11-23; `VERSION=0.33.1`, `NEXT_VERSION=0.34.0`, main's MCP inventory 57 tools. Main CI evidence: [#45167794202](https://github.com/samjuniors/Orbit-Core/actions/runs/45167794202), PASS 5/5.

**Release:** v0.33.0 remains latest published prerelease (tag target `0100e6d1d3e33c907f726c03004d209f7876837d`, published 2026-11-23 08:20:55 UTC, eight assets); v0.30.0 remains latest stable. v0.33.1/v0.34.0 are unpublished. `docs/RELEASE-ACCEPTANCE-v0.33.1.md` exists on this PR #178 branch but not on main; main's docs directory currently has only the v0.33.0 acceptance record.

**PR #178:** branch `docs/orbit-nightly-handoff-20261123`, previous head `1dd728cc5f0a76b6eb6f6a3df2b219bfd31b58e7`, 18 commits / 7 files, OPEN / DRAFT / documentation-only. Exact-head push #45666137573 and pull_request #45666147503 both PASS 5/5 (Ubuntu Python 3.10–3.13; Windows Python 3.12). No review submissions or inline review threads. This checkpoint adds another docs-only commit; recheck its new exact-head CI and keep draft pending human review.

**Focused v0.34 PRs (all OPEN / DRAFT; no human reviews):**
- #179 `feat/v034-team-builder-model-routing-20261125` at `1c1e949e96df3445ab64d109ab0b951204de183f`, 7 commits / 7 files, CI 5/5. Advisory per-task model recommendations only; no host model switch or worker spawn.
- #180 `feat/v034-skill-lifecycle-20261125` at `50ab30468a036c3803950d6cb20e7576682c204e`, 4 commits / 1 file, CI 5/5. Test-only; no host skill install/activation.
- #181 `feat/v034-resource-first-specialists-20261125` at `b46fad39e5ec26a7af7cef8ef646d28342da6da4`, 1 commit / 1 file, CI 5/5. Regression coverage only; no live external resource discovery or native worker invocation.
- #182 `feat/v034-security-review-plan-20261125` at `54a78b863c10baea305f0adf9f1c96c7fa39c58c`, 45 commits / 25 files; push #45664882357 and pull_request #45664888434 both PASS 5/5. Adds read-only `orbit_security_review_plan`; branch inventory is 58 tools. The bounded local pattern scan is not SAST, penetration testing or certification; permission is caller-reported and `host_permission_verified=false`. Keep draft.

**Security blockers:**
- [Issue #183](https://github.com/samjuniors/Orbit-Core/issues/183): disposable Windows junction-replacement tests reproduced the prior agent-candidate write escaping the selected project and structural inventory including a sibling-project path. Current experimental Windows paths fail closed (candidate writes HOLD; source/structural scans return INCOMPLETE). This is containment, not a complete fix. POSIX parent-directory replacement remains a static-review lead, not reproduced. Require held-root/directory handles, handle-relative no-follow reads/writes, Windows reparse-point-aware checks, adversarial Linux/Windows tests and independent review.
- [Issue #184](https://github.com/samjuniors/Orbit-Core/issues/184): #182's `evidence_sha256` hashes the matched source line and can enable offline guessing of predictable credentials. A locator-only change was reverted because the tracked desktop MCP bundle could not be regenerated from exact source in the available build environment. Replace with a locator-only reference and accurate field name, add tests, rebuild the bundle from exact source, verify parity and rerun CI. Release blocker.

**Broad v0.34 experiment:** `feat/v034-context-aware-intelligence-20261123` at `f08448ff75c9d87f280ad66ff022a5466a7f4eb4`, 100 ahead / 0 behind main, no PR. Exact CI #45561811215 PASS 5/5; Windows 835 tests, 13 skips. Keep unapproved; split only reviewed slices mapped to #90/#91/#92. Do not merge the 100-commit branch as a unit.

**Research:** latest delta is 2026-11-25; no new sources were added 2026-11-26. It records OWASP ASVS 5.0.0/MASVS, NIST SSDF v1.1 final (v1.2 Rev.1 draft), MASWE v1.0.0 (78 weakness IDs; OWASP reports 36/78 without a MASTG test), MAS-L1 assumptions, and optional Semgrep CE, Trivy, OSV-Scanner and OpenSSF Scorecard. These are primary standards/vendor/project references, not proof of Orbit integration or scanner execution. No automatic installation/network scanning.

**Decisions:** Decision 002 is adopted (Helm retired as active product; Orbit Core focus). Decision 001 remains proposed for owner adoption. Product order remains safe Team Builder → task-specific skills/tools → Orbit-mediated agent/bot coordination. RAD P2 #138 remains separate/on hold; Orbit Commander remains paused.

**Previous nightly run:** Orbit Nightly Build run `77bdb0e4-e3a0-832c-991a-0be4a7ffe5bd` actually executed, scheduled 2026-11-25 22:00 IST, started 22:44:07 IST, completed 23:06:30 IST; recorded status `completed`, latest result ID matched, no failure flag, no user action, not truncated, delivery status unknown. It reported main CI 5/5, #182 CI 5/5, #178 CI pending then (both runs later passed 5/5), v0.34 CI 5/5, and #183/#184 follow-ups. No merge/release/install/deployment.

**Execution limits:** Remote Arc `DESKTOP-AND1FUJ` is OFFLINE (last seen 2026-11-25 11:40:58 UTC); no local checkout/tests, owner-profile host acceptance, `.orbit` or SQLite inspection. Orbit ChatGPT plugin connector is not exposed. GitHub branch-protection endpoint returns 403; rulesets query is empty; required-check enforcement remains NOT VERIFIED. No merge, release, installation, deployment, paid API use or host permission change.

**Next:** (1) resolve #184 in a build-capable environment and regenerate the exact desktop bundle; (2) implement #183 handle-relative traversal/writes and adversarial tests; (3) obtain independent human/security review for #178–#182; (4) split the 100-commit v0.34 branch; (5) reconnect Windows for owner-profile Claude/Codex/Antigravity acceptance; (6) keep v0.33.1 unpublished until all release gates and explicit owner go/no-go are recorded.


## 2026-11-26 — Nightly run 4 live revalidation (22:20 Asia/Kolkata)

**Canonical repository:** samjuniors/Orbit-Core; default branch main. This checkpoint supersedes older branch/issue counts but does not authorize merge, install, release or host changes.

### Live GitHub state
- Main HEAD: 2fdf4f329774b9644e75ac0df4d89738a7cd625f; VERSION=0.33.1; NEXT_VERSION=0.34.0.
- Branch inventory: 159 branches (100 on page 1, 59 on page 2); 43 open PRs; 9 open issues.
- Main exact-head CI [#45167794202](https://github.com/samjuniors/Orbit-Core/actions/runs/45167794202) is completed PASS 5/5. The latest run for main is still this run (2026-11-23 11:43:53 UTC).
- Latest published prerelease: [v0.33.0](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.33.0), published 2026-11-23 08:20:55 UTC, eight assets. Latest stable: v0.30.0. No v0.33.1 or v0.34.0 release exists.
- Repository governance: the branch-list API reports main.protected=false; the repository rulesets collection is empty. Required-check / review enforcement is therefore not configured through those mechanisms at this checkpoint. Do not change repository administration settings without owner direction.

### Documentation PR #178
- [PR #178](https://github.com/samjuniors/Orbit-Core/pull/178), branch docs/orbit-nightly-handoff-20261123, pre-update head e63b86c2aaa7f3ac2d201876d4336f36980dd263, OPEN / DRAFT, 20 commits / 7 files.
- Exact-head push run [#45734263882](https://github.com/samjuniors/Orbit-Core/actions/runs/45734263882) and pull_request run [#45734274128](https://github.com/samjuniors/Orbit-Core/actions/runs/45734274128) completed PASS. The latter's five matrix jobs (Ubuntu Python 3.10–3.13 and Windows Python 3.12) all report success.
- No submitted reviews or inline review threads exist. This new documentation append creates another commit and must receive fresh exact-head CI. Keep draft until CI and human review are complete.

### Focused v0.34 drafts
- [#179](https://github.com/samjuniors/Orbit-Core/pull/179), head 1c1e949e96df3445ab64d109ab0b951204de183f, exact CI [#45545884593](https://github.com/samjuniors/Orbit-Core/actions/runs/45545884593) PASS. Task-specific model recommendations remain advisory; no host model switch or worker spawn.
- [#180](https://github.com/samjuniors/Orbit-Core/pull/180), head 50ab30468a036c3803950d6cb20e7576682c204e, exact CI [#45549132274](https://github.com/samjuniors/Orbit-Core/actions/runs/45549132274) PASS. Test-only; no host skill install/activation.
- [#181](https://github.com/samjuniors/Orbit-Core/pull/181), head b46fad39e5ec26a7af7cef8ef646d28342da6da4, exact CI [#45548741789](https://github.com/samjuniors/Orbit-Core/actions/runs/45548741789) PASS. Regression coverage only; no live external resource crawler or native worker invocation.
- [#182](https://github.com/samjuniors/Orbit-Core/pull/182), head 54a78b863c10baea305f0adf9f1c96c7fa39c58c, exact CI [#45664882357](https://github.com/samjuniors/Orbit-Core/actions/runs/45664882357) and [#45664888434](https://github.com/samjuniors/Orbit-Core/actions/runs/45664888434) PASS 5/5. Adds bounded local cybersecurity review planning (58-tool branch inventory); it is not full SAST, penetration testing or certification. Caller-reported permission is not host attestation. Keep draft because #184 remains open.
- #179–#182 are still open drafts. No human review submissions or inline review threads were returned for #178 or #182; do not infer review approval from CI.

### Security and autonomy issues
- [#183](https://github.com/samjuniors/Orbit-Core/issues/183): a previous Windows junction-replacement implementation was reproduced writing an agent candidate outside the selected project and leaking a sibling path into structural inventory. The current experimental branch contains the Windows paths by failing closed (candidate write HOLD; source/structural scans INCOMPLETE without traversal). This is containment, not a complete Windows implementation. POSIX parent-directory replacement remains a static-review lead, not a reproduced exploit.
- [#184](https://github.com/samjuniors/Orbit-Core/issues/184): #182's source-derived evidence_sha256 can act as an offline guessing oracle for predictable secrets. A locator-only source change was reverted to restore strict desktop bundle parity. Fix the field semantics, add tests, rebuild the exact desktop bundle and prove parity before any release.
- New [#185](https://github.com/samjuniors/Orbit-Core/issues/185) specifies a bounded multi-task mission supervisor. It must extend the existing charter, task ledger, DAG and single-task Codex runner; no second task database or process launcher. One mission approval is limited to the immutable charter; host permissions remain separately enforced. Only DAG-ready tasks whose dependencies have independently reached REVIEW_ACCEPTED may advance. Worker output is untrusted. Pause/stop/expiry, heartbeat, output/time limits, process-tree ownership, safe orphan recovery and restart checkpoints are required. Claude Code and Antigravity remain future provider adapters until actual host execution and permission behavior are verified. This scope explicitly excludes background service, remote execution and PC-off continuation.
- Experimental branch [feat/v034-context-aware-intelligence-20261123](https://github.com/samjuniors/Orbit-Core/tree/feat/v034-context-aware-intelligence-20261123) is 100 commits ahead / 0 behind main at 8620e4a3063852d2c99f6a157fc9ee688c989b6a; exact CI [#45561811215](https://github.com/samjuniors/Orbit-Core/actions/runs/45561811215) PASS 5/5. It has no PR or independent review. Do not merge it as a unit.

### Fresh research and design implications
- OpenAI's Codex harness/app-server separates the agent loop (thread/turn events, streaming, interruption and host approval) from application-owned product context, tools and policy. Treat it as a Codex adapter reference, not Orbit's provider-neutral core. [Codex as a platform](https://developers.openai.com/blog/codex-as-a-platform).
- Claude Code and Antigravity expose host-native subagents, skills/rules, tool restrictions and lifecycle hooks. Hooks execute local commands; availability and permissions remain host-owned. Negotiate actual host capabilities and never report a planned dispatch as a spawned agent. [Claude subagents](https://code.claude.com/docs/en/sub-agents) · [Antigravity features](https://antigravity.google/docs/features).
- OpenHands separates SDK/Agent Server execution from automation scheduling/dispatch. This supports a distinct Orbit mission supervisor and provider execution adapter; it does not justify importing a second runtime. [SDK](https://github.com/OpenHands/software-agent-sdk) · [Automation](https://github.com/OpenHands/automation).
- Verification research supports independent review: a 2026 preprint reports critic-review gains on SWE-bench Verified and Terminal-Bench; LHTB 2.0 evaluates sustained progress over 3-hour runs with periodic verifier checkpoints. Treat these as evaluation evidence, not production guarantees. [Verification study](https://arxiv.org/abs/2610.34577) · [LHTB 2.0](https://arxiv.org/abs/2610.14146).

### Execution environment and exact blockers
- Remote Arc device DESKTOP-AND1FUJ is OFFLINE (last seen 2026-11-25 11:40:58 UTC); Desktop Commander has no connected devices. No local checkout, Linux/Windows adversarial test run, desktop bundle rebuild, owner-profile host acceptance or .orbit/SQLite inspection was possible.
- Orbit ChatGPT plugin connector is not exposed in the available tools. Authorized GitHub and Notion integrations were used.
- No runtime code was changed in this run. No merge, release, installation, deployment, paid model API use or host permission change occurred. Orbit Commander was not touched.

**Next safe sequence:** (1) reconnect a build-capable Windows/Linux environment; (2) resolve #183 with handle-relative no-follow traversal/writes and adversarial tests; (3) resolve #184 and regenerate the tracked desktop bundle from exact source; (4) implement #185 by extending the existing runner/ledger with a mission-level state machine and provider-neutral adapter contract; (5) obtain independent security/human review and actual host acceptance. Keep v0.33.1/v0.34 unpublished until all release gates are satisfied.


## 2026-11-27 — Morning live revalidation

Canonical repository: [samjuniors/Orbit-Core](https://github.com/samjuniors/Orbit-Core). This checkpoint records live GitHub/Notion/automation evidence; it does not authorize merge, release, installation, deployment or host permission changes.

### Main and releases
- Main remains `2fdf4f329774b9644e75ac0df4d89738a7cd625f`; the latest main commit is still the 2026-11-23 deterministic Git line-ending fix. `VERSION=0.33.1`, `NEXT_VERSION=0.34.0`, 57-tool main baseline.
- Main CI [#45167794202](https://github.com/samjuniors/Orbit-Core/actions/runs/45167794202) is completed PASS 5/5 (Ubuntu Python 3.10–3.13 and Windows Python 3.12).
- Latest published prerelease remains [v0.33.0](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.33.0), published 2026-11-23 08:20:55 UTC with four packages and four SHA-256 sidecars. Latest stable remains v0.30.0. v0.33.1 and v0.34.0 are unpublished.
- GitHub main branch metadata reports `protected=false`; the branch-protection object has enforcement off and no required checks. No repository ruleset was found in the prior authorized ruleset read. This is a governance risk; no admin settings were changed.

### Documentation handoff PR #178
- [PR #178](https://github.com/samjuniors/Orbit-Core/pull/178), branch `docs/orbit-nightly-handoff-20261123`, head `3eb8b51a2d866357bc2041ad6224b75373a45976`, 22 commits / 7 documentation files, OPEN / DRAFT / mergeable.
- New commits from the 2026-11-26 nightly: `ff4a341806beeb4ab26447c792f9fc3d786f2687` (handoff) and `3eb8b51a2d866357bc2041ad6224b75373a45976` (roadmap / mission-supervisor acceptance).
- Exact-head push CI [#45863566602](https://github.com/samjuniors/Orbit-Core/actions/runs/45863566602) and pull-request CI [#45863571895](https://github.com/samjuniors/Orbit-Core/actions/runs/45863571895) are both completed PASS 5/5, including Windows Python 3.12. No submitted reviews or inline review threads; keep draft pending human documentation review.
- This 2026-11-27 checkpoint is being appended as a documentation-only commit; its new exact-head CI must be checked separately.

### Focused v0.34 drafts
- [#179](https://github.com/samjuniors/Orbit-Core/pull/179), `feat/v034-team-builder-model-routing-20261125`, head `1c1e949e96df3445ab64d109ab0b951204de183f`, CI [#45545884593](https://github.com/samjuniors/Orbit-Core/actions/runs/45545884593) PASS 5/5. Recommendations only; no host model switch or worker spawn.
- [#180](https://github.com/samjuniors/Orbit-Core/pull/180), `feat/v034-skill-lifecycle-20261125`, head `50ab30468a036c3803950d6cb20e7576682c204e`, CI [#45549132274](https://github.com/samjuniors/Orbit-Core/actions/runs/45549132274) PASS 5/5. Test-only; no host skill install/activation.
- [#181](https://github.com/samjuniors/Orbit-Core/pull/181), `feat/v034-resource-first-specialists-20261125`, head `b46fad39e5ec26a7af7cef8ef646d28342da6da4`, CI [#45548741789](https://github.com/samjuniors/Orbit-Core/actions/runs/45548741789) PASS 5/5. Regression tests only; no live external resource crawler or native worker spawn.
- [#182](https://github.com/samjuniors/Orbit-Core/pull/182), `feat/v034-security-review-plan-20261125`, head `54a78b863c10baea305f0adf9f1c96c7fa39c58c`, 45 commits / 25 files. Push [#45664882357](https://github.com/samjuniors/Orbit-Core/actions/runs/45664882357) and PR [#45664888434](https://github.com/samjuniors/Orbit-Core/actions/runs/45664888434) CI PASS 5/5. Adds bounded `orbit_security_review_plan` (58-tool branch inventory); not full SAST/pentest/certification, and caller-reported permission is not host attestation.
- All #179–#182 remain OPEN / DRAFT. No human reviews or inline review threads were returned for #178–#182.

### Broad v0.34 branch and security issues
- `feat/v034-context-aware-intelligence-20261123` is at `8620e4a3063852d2c99f6a157fc9ee688c989b6a`, 100 commits ahead / 0 behind main, no PR. Exact-head CI [#45561811215](https://github.com/samjuniors/Orbit-Core/actions/runs/45561811215) PASS 5/5. Do not merge this branch as a unit.
- [Issue #183](https://github.com/samjuniors/Orbit-Core/issues/183) remains OPEN. Disposable Windows junction-replacement tests reproduced an earlier project-boundary escape. Current experimental Windows paths fail closed (candidate write HOLD; source/structural scans INCOMPLETE); this is containment, not a complete fix. POSIX parent-directory replacement remains a static-review lead, not a reproduced exploit.
- [Issue #184](https://github.com/samjuniors/Orbit-Core/issues/184) remains OPEN. PR #182's source-line-derived `evidence_sha256` can enable offline guessing of predictable secrets. A locator-only source change was reverted to preserve strict desktop-bundle parity; fix the field semantics, add tests, rebuild from exact source and verify parity before release.
- [Issue #185](https://github.com/samjuniors/Orbit-Core/issues/185) was opened 2026-11-26 for a bounded multi-task mission supervisor. It is a proposed implementation workstream, not implemented autonomy. Reuse the existing Mission Charter, DAG/task ledger, append-only journal and one-task Codex runner; one approval binds only an immutable bounded charter. Require independent review before dependants run; keep host permissions separate. No background service, remote execution or PC-off continuation.

### Research and decisions
- The 2026-11-26 research delta is now recorded in Notion Research & References: primary Codex/Agents API security docs, official Claude Code subagent and Google Antigravity docs, OpenHands SDK/Automation repositories, plus three arXiv evaluation preprints on independent verification, long-horizon checkpoints and trajectory summaries. Vendor docs/repositories are primary sources; arXiv findings are preprints and benchmark-specific, not production guarantees. No new external sources were added on 2026-11-27.
- Decision 002 remains ADOPTED (Helm retired; Orbit Core focus); Decision 001 release/versioning policy remains PROPOSED. Approved product order remains safe Team Builder → task-specific skills/tools → Orbit-mediated agent/bot coordination. RAD P2 #138 remains separate/on hold; Orbit Commander remains paused.

### Previous nightly execution
- Orbit Nightly Build run `e39566bf-ab3c-8332-9c4d-f8887587f4fd` actually executed: scheduled 2026-11-26 22:00 IST, started 22:20:49 IST, completed 22:31:13 IST; recorded status `completed`. Latest result run ID matches; not a failure message, no user action required, not truncated; delivery status unknown.
- Recorded work: appended handoff/roadmap docs in PR #178 (commits above), added issue #185, updated four Notion records. No runtime merge, release, install or deployment.

### Environment and limitations
- Remote Arc device `DESKTOP-AND1FUJ` remains OFFLINE; last seen 2026-11-25 11:40:58 UTC. No local checkout/tests, desktop bundle rebuild, owner-profile Claude/Codex/Antigravity acceptance, or `.orbit`/SQLite inspection occurred.
- Orbit ChatGPT plugin connector is not exposed. GitHub and Notion integrations were available and used. No local machine was operated in this checkpoint.

### Next safe actions
1. Resolve #184 in a build-capable environment and prove exact desktop bundle/source parity.
2. Resolve #183 with handle-relative no-follow traversal/writes, Windows reparse-point protections and adversarial Linux/Windows tests.
3. Obtain human review of #178–#182; keep all drafts until reviewed.
4. Reconcile/split the 100-commit v0.34 branch into focused issue-mapped PRs; implement #185 only by extending existing state/runner architecture.
5. Reconnect Windows for real owner-profile host/permission/stop/expiry acceptance.
6. Keep v0.33.1 unpublished until exact-head CI, package parity, independent security review, host acceptance and explicit owner go/no-go are recorded.


## 2026-11-27 — Nightly live revalidation and engineering checkpoint

**Canonical repository:** [samjuniors/Orbit-Core](https://github.com/samjuniors/Orbit-Core). Revalidated 2026-11-27 22:18 Asia/Kolkata.

### Repository and release truth

- `main` remains `2fdf4f329774b9644e75ac0df4d89738a7cd625f`; `VERSION=0.33.1`, `NEXT_VERSION=0.34.0`. Latest main push CI is [#45167794202](https://github.com/samjuniors/Orbit-Core/actions/runs/45167794202), PASS 5/5 (2026-11-23); no newer main push run was returned.
- Latest published prerelease: [v0.33.0](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.33.0), published 2026-11-23 with eight assets (four packages and four SHA-256 sidecars). Latest stable: v0.30.0. v0.33.1 and v0.34.0 are not published.
- Live inventory: 159 branches (100 on page 1, 59 on page 2), 45 open PRs and 10 open issues after creating #188. The 45 PRs include the current #178–#187 work plus older v0.32 and RAD P2 drafts; do not bulk-close or merge historical work.
- The rulesets endpoint returned an empty list. The branch-protection endpoint returned 403, so required-check/review enforcement is **UNVERIFIED**; do not claim main is protected or unprotected.

### Current focused PRs

- [PR #178](https://github.com/samjuniors/Orbit-Core/pull/178), documentation-only, OPEN/DRAFT, head `401ff1923ea89c90f08aba3c9f7f1bd21e30435c`, 23 commits / 7 files. Exact-head pull_request run [#45917993187](https://github.com/samjuniors/Orbit-Core/actions/runs/45917993187) completed PASS 5/5 after rerun. No human review is recorded.
- [PRs #179–#182](https://github.com/samjuniors/Orbit-Core/pulls), Team Builder model recommendation, skill lifecycle tests, specialist safety tests and cybersecurity planner. Their previously recorded exact-head CI is PASS 5/5; all remain drafts with no submitted human reviews. Recommendations/tests do not prove host model switching, native skill activation or complete SAST/penetration testing.
- [PR #186](https://github.com/samjuniors/Orbit-Core/pull/186), filesystem containment, head `f81eb1f051cc6afee00ac10ed1e8619ae3b10633`, 11 commits / 28 files, OPEN/DRAFT. Push CI [#45993595975](https://github.com/samjuniors/Orbit-Core/actions/runs/45993595975) PASS 5/5. The PR description reports a local Windows suite of 857 passed / 46 skipped; this run did not independently reproduce that local result. It is stacked on `feat/v034-context-aware-intelligence-20261123` at `8620e4a3063852d2c99f6a157fc9ee688c989b6a`, not on main. Independent review comment #7223899988 records the ReFS/SMB identity limitation: the implementation uses the 64-bit file index from BY_HANDLE_FILE_INFORMATION; Microsoft says ReFS 64-bit IDs are not guaranteed unique and network FS metadata may be partial. Use FileIdInfo (128-bit) or explicitly scope/fail closed on unsupported filesystems before accepting #183.
- [PR #187](https://github.com/samjuniors/Orbit-Core/pull/187), bounded mission supervisor, current head `03b1770214023b4eb3cd3c5a0725d415b5941ef1`, 7 commits / 7 files, OPEN/DRAFT. Exact-head run [#46037740696](https://github.com/samjuniors/Orbit-Core/actions/runs/46037740696): Ubuntu Python 3.10/3.11/3.12/3.13 PASS; Windows Python 3.12 was still in progress at the final check. The branch is also stacked on the 100-commit context-aware branch, not main.
- PR #187 received a focused pause/resume fix in commits `16c0c24f42a6a0317df1d32203d437cb72354b79` and `03b1770214023b4eb3cd3c5a0725d415b5941ef1`. The supervisor now keeps the pre-pause approved revision, requires the charter event ledger to show PAUSE then RESUME, and fails closed for a PAUSED supervisor checkpoint without matching charter events. Added tests for a tampered/inconsistent checkpoint and a live pause/resume path. Exact-head CI is still required; do not claim the patch passes until run #46037740696 finishes.

### Reliability and security findings

- [Issue #183](https://github.com/samjuniors/Orbit-Core/issues/183) remains P0. The earlier Windows junction escape was reproduced; PR #186 adds Windows handle pinning and POSIX descriptor-relative/no-follow traversal. Independent security review and supported-filesystem boundaries remain open.
- [Issue #184](https://github.com/samjuniors/Orbit-Core/issues/184) remains P0. The cybersecurity planner still has a source-line-derived `evidence_sha256`; replace with a locator-only reference, rename the field and rebuild the exact desktop MCP bundle before release.
- [Issue #185](https://github.com/samjuniors/Orbit-Core/issues/185) is in progress through PR #187. This increment is sequential Codex CLI only. It does not provide native Claude Code/Antigravity dispatch, parallel execution, automatic replan, background service or PC-off continuation.
- PR #187 review comment #7223900615 identifies a lock-directory parent risk: `Path.mkdir(exist_ok=True)` accepts a pre-existing symlink-to-directory; `O_NOFOLLOW` protects only the final lock file. Use a private directory opened/validated by handle and relative lock creation; add POSIX symlink and Windows junction tests. Until fixed, treat mission serialization as best-effort, not a security boundary.
- [Issue #188](https://github.com/samjuniors/Orbit-Core/issues/188) tracks intermittent `test_mcp_process_and_shared_db` child-process crashes. Initial attempts failed with `double free or corruption (out)` / exit -6 on Ubuntu Python 3.10 in run #45993907780 and SIGSEGV / exit -11 on Ubuntu Python 3.13 in #45917993187; reruns passed 5/5. Reruns do not establish root cause. Require repeated isolated runs and child/SQLite/WAL lifecycle diagnosis.

### Host and connector limits

- Remote Arc `DESKTOP-AND1FUJ` is OFFLINE; last seen 2026-11-27 11:51:32 UTC. No local Windows/Linux checkout, adversarial local run, desktop bundle rebuild, owner-profile Claude/Codex/Antigravity acceptance, or `.orbit`/SQLite inspection occurred.
- The Orbit ChatGPT plugin connector is not exposed in the available integration/tool set. GitHub and Notion integrations were used; do not claim Orbit's own plugin was invoked.
- No merge, release, install, deployment, host permission change, external scan or paid API spend occurred. Orbit Commander remains paused and untouched.

### Next safe actions

1. Finish exact-head Windows CI for #187 and inspect the new pause/resume tests.
2. Fix the #187 lock-directory parent symlink/reparse-point issue.
3. Investigate #188 with repeatable subprocess stress tests; do not mask with reruns alone.
4. Complete #183 filesystem review including ReFS/SMB support policy and #184 digest/package parity.
5. Obtain human review of #178–#187; keep drafts until their base/stacking strategy is reconciled.
6. Split only approved v0.34 slices from the 100-commit experimental branch onto focused branches based on main after dependencies are understood; do not merge that branch as a unit.
7. Complete signed-in owner-profile host acceptance and independent security review before release consideration.


### 2026-11-27 17:05 UTC — exact-head CI completion and #188 investigation lead

- PR #178 current head `7bd44acb0358f4aabf104bb744f371e8356ff143` completed [pull_request run #46038299281](https://github.com/samjuniors/Orbit-Core/actions/runs/46038299281) PASS 5/5, including Windows Python 3.12. This verifies the current documentation head; PR remains draft with no human review.
- PR #187 current head `03b1770214023b4eb3cd3c5a0725d415b5941ef1` completed [run #46037740696](https://github.com/samjuniors/Orbit-Core/actions/runs/46037740696) PASS 5/5. Windows Python 3.12 ran 850 tests with 13 skips. This verifies CI tests, not owner-profile host permission behavior.
- Issue #188 static investigation found a plausible but unconfirmed cause: `orbit_mcp.main` starts an untracked daemon update-check thread; `orbit_updates._fetch` uses urllib with an 8-second timeout; the short-lived shared-DB subprocess test does not set `ORBIT_UPDATE_CHECK=0`. Compare fresh-cache runs with update check enabled/disabled and add a bounded thread-lifecycle/shutdown test. Do not mark #188 fixed without root-cause evidence.
