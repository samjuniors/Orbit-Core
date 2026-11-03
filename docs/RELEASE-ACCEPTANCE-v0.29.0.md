# Orbit Core v0.29.0 — Development and acceptance evidence

**Status: DEVELOPMENT CANDIDATE — source/CI QA verified; interactive Antigravity reported PASS; native Codex five-call read-only acceptance independently log-verified PASS. Remaining host/security/release gates listed below. Not released.**
**Date:** 2026-11-03. **Project:** Orbit Core (not Helm, Aro or the separate ORBIT planner).

GitHub is engineering authority; [Orbit Core Notion hub](https://app.notion.com/p/4074f681d48881a7a407c3bdc2054409) records the approved product intent. A development branch, version string or passing CI is not a public release.

## Product and supported scope

The approved v0.29 mission is original, **read-only project-aware installed-skill discovery** inspired conceptually by the separately evaluated AAS reference. Existing `orbit_capability_select` gains a bounded shortlist (max five), declared product/platform/technology/operation/IDE-host fit, explicit requests for installed names, and a SHA-pinned `orbit-skill-plan-v2` manifest with drift/revalidation.

All skill directory names, descriptions, version and license metadata are **untrusted claims**. Hash matches prove byte identity, not publisher authenticity, license rights, safe execution or owner consent. No external skill catalog, importer, installation, plugin auto-activation, content execution, subprocess runner, new model layer or new MCP tool is introduced. The existing native host handles permission-gated actions.

## Branch ancestry and version

- Latest **published prerelease**: [v0.28.0](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.28.0); original tested release tag preserved.
- Existing development work: [draft PR #70](https://github.com/samjuniors/Orbit-Core/pull/70), branch `dev/v0.29.0-skill-discovery`, original source `4308b0ff2082ed940cc46368e7515cbd7f51ad32`.
- New separate integration branch: `fix/v029-main-reconcile`, merging latest published-v0.28 `main` commit `015bf5d2cc294de237a129cc317bcf9d6f3062df` into the prior v0.29 source with **zero conflicts**. The preceding merge commit is `db42873d5bd8e94c5af91e02fd559bdfdd79ac79`.
- Candidate metadata: `VERSION=0.29.0`, `NEXT_VERSION=0.30.0`, matching installer, runtime, archive names and public changelog heading. Does not alter already-published v0.28 tags/assets or installed user settings.
- Upgrade suite now tests **immutable v0.28.0 → candidate v0.29.0** on Windows and Linux Python 3.12, in addition to the existing published prior-release checks.

## Actual independent engineering evidence

| Gate | Result | Evidence |
| --- | --- | --- |
| Existing skill shortlist targeted regressions | PASS with 3 SKIPs | Windows Python 3.12: 36 tests; 3 symlink/environment skips |
| Initial full source suite | FAIL, repaired | 458 tests; three inherited hardcoded v0.28 assertions uncovered at version promotion, not skill-planner execution defects |
| Corrected full source suite | **PASS** | Windows Python 3.12: 458 tests, 26 skipped, 0 failures; exit 0 |
| Candidate bundle preparation | **PASS** | `prepare_release_candidate.py` generated new 0.29.0 MCPB without changing previous bundles |
| Version/readiness/parity | **PASS** | `check_release_readiness.py` and `check_version.py --strict-bundle` |
| Reproducible ZIP package build | **PASS** | `build_release.py --verify`: Universal Setup 137 files, Antigravity plugin 46 files, plugin suite 173 files |
| Disposable installed stdio smoke | **PASS** | `smoke_release_zip.py`: 47 MCP tools; no user install/IDE touched |
| Latest published release upgrade | **PASS** | `smoke_upgrade_previous.py --previous-root <immutable v0.28.0 checkout>`; preserves owner-custom guidance, .orbit checkpoint, SQLite bytes and v0.28 runtime |
| New integration exact-head CI | **NOT RUN at document creation** | Require Ubuntu Python 3.10–3.13 and Windows Python 3.12 on the pushed PR head |
| Real Antigravity/Codex skill execution/consent | **NOT VERIFIED** | Needs authorized isolated host profiles and explicit real-host evidence; read-only source tests do not attest it |
| Symlink-specific runtime protection on Windows | **SKIPPED in local environment** | Review Linux CI and host filesystem permissions; do not claim Windows symlink acceptance |
| Release merge/tag/public assets | **NOT RUN** | Separate owner decision after source/host QA; do not publish now |

## 2026-11-03 — Interactive Antigravity acceptance (owner-supplied report)

**Source:** Owner-provided report headed *Orbit Core v0.29 — Real-Host Acceptance Report*, for Antigravity interactive Windows host `DESKTOP-AND1FUJ`, isolated workspace `%TEMP%\\Orbit-v029-HostQA-20261103` and project-local `orbit_v029_qa`. **Scope:** read-only declared project/host skill-selection tests; the reporting host was Antigravity for all seven cases, even when input `host="codex"` was supplied. These are **host-reported actual tool responses**, not fresh independent capture of the interactive GUI session.

| Antigravity interactive test | Evidence and result |
| --- | --- |
| Project-local connection | **HOST-REPORTED PASS**: 47 tool descriptors, `orbit_update_status` installed candidate `0.29.0`, published `0.28.0`; no global `orbit-core-native` invoked |
| React web / Flutter Android / Codex-declared Rust CLI | **HOST-REPORTED PASS**: exact `SKILL_SHORTLIST_READY` for synthetic `react-ui`, `flutter-navigation`, `cargo-testing`; excludes web-only React from Flutter |
| Pin revalidation | **HOST-REPORTED PASS**: `PINS_MATCH_CURRENT_PREVIEW_ONLY`, no activation verified |
| Permission denied | **HOST-REPORTED PASS**: `HOLD_PERMISSION_DENIED`, `activation_allowed=false`, adaptive/browser workflow HOLD |
| Missing explicitly requested skill | **HOST-REPORTED PASS**: `HOLD_REQUESTED_SKILLS_UNAVAILABLE`; no catalog fetch or third-party execution |
| Host-context drift | **HOST-REPORTED PASS**: `HOLD_STALE_MANIFEST`, `context_changed=true` |
| Fixture integrity/permissions | Host report states no skills executed, no project edits, no global server invocation; Windows symlink testing **NOT RUN**; host restart **NOT VERIFIED** |

**Independent corroboration on connected Windows PC:** Compared actual SHA-256 bytes of all three synthetic `SKILL.md` files against the report, **3/3 MATCH**:
- `react-ui`: `d4522b2a98102644dac3f5f6502714e86bb1b2dd3439d666cc223d2dababba5f`
- `flutter-navigation`: `73de2c6c9894b8e828635b5f4d6246f1c63f2dab942da4744044944a9bcfaef0`
- `cargo-testing`: `ecbff0d1a0328e60c1517b40e84b6df8541661caf505d7770e85717a4c206bc1`

The candidate runtime is still `VERSION=0.29.0` and the development checkout head remained `d361e54eece4f98e69a68b3ea7de9e2184715b7d` at that inspection. File-hash agreement supports the reported fixture identity, **not** attestation that each interactive GUI invocation was captured independently.

### Separate actual Codex CLI attempt — BLOCKED (not a skill-plan failure)

Codex CLI `0.166.0` accepted an **ephemeral configuration override** for `orbit_v029_qa`; `codex mcp get orbit_v029_qa` reported enabled stdio pointing to the isolated v0.29 candidate. A real `codex exec` attempt then used `--ignore-user-config --ignore-rules --ephemeral --sandbox read-only` in the disposable workspace. It produced a thread-start/turn-start JSONL record and exited **1** after **HTTP 403**; there was **no Codex MCP tool result**. `codex login status` independently reported "Logged in using ChatGPT", which does not establish valid server authorization or explain the 403. Do not label the Codex selector PASS or attribute this definitively to an Orbit defect. No permission bypass, global config change, skill installation or source modification was performed.

**Remaining real-host gates:** running-version attestation, further native Codex pin/denial/drift revalidation and any required restart-recovery evidence in an explicitly authorized interactive session; independent source/security review and owner-controlled merge/release decision. Keep existing [integration PR #77](https://github.com/samjuniors/Orbit-Core/pull/77) unmerged until separately approved. The previous published v0.28 tag and packages remain immutable.

### Codex interactive single-tool acceptance — owner report (2026-11-03)

The owner separately reported a **successful actual native Codex tool invocation** using `orbit_v029_qa`. The result was `SKILL_SHORTLIST_READY` for the synthetic `cargo-testing` skill, with `orbit-skill-plan-v2` manifest; the MCP exposed 47 tools and reported `activation_allowed=false`, `state_written=false`. The owner observed **no permission prompt and no HTTP 403** on this successful attempt, and reports no skill installation, agent spawning, third-party code execution, project file modification or global settings changes.

**Evidence status:** **HOST-REPORTED PASS — one read-only selector call.** The response did **not include a version identifier**, so the exact *running server* version remains **NOT VERIFIED** by that call; earlier fixture configuration/source inspection pointing at `0.29.0` is contextual evidence, not a substitute for a real running-version tool response. The owner stopped after this single call in accordance with the acceptance checklist; native Codex **pin revalidation, denied-permission HOLD, stale manifest and host restart recovery remain NOT RUN/NOT VERIFIED**. There is no independently retained native Codex transcript in this project acceptance record.

The preceding Codex CLI HTTP 403 attempt remains a separate **historical BLOCKED** observation, not an active failure of this later reported Codex single-tool invocation. Neither event proves the root cause of the earlier HTTP 403.

**Next owner-approval gate:** Explicitly authorize continuing *read-only, project-local* native Codex validation (running server-version check, pin revalidation, denial and drift) with no skill activation or settings changes, then independently review the combined security evidence before deciding on any development-branch merge or release. Current published prerelease remains `v0.28.0`.

### Native Codex real-host continuation — owner-approved, independently inspected (2026-11-03)

**Authorization:** On 2026-11-03 the owner explicitly approved the previously deferred **read-only Codex version, pin, denial and host-context drift tests**. Scope was the existing disposable v0.29 test workspace, **only** project-local `orbit_v029_qa`, with no global settings/permissions changes, skill activation, third-party execution, agent spawning, merge or publication. The later approved test supersedes the earlier single-tool STOP, not the historical fact of that first test.

**Actual real Codex tool execution:** Windows `DESKTOP-AND1FUJ`, `codex-cli 0.166.0`. Launched a genuine `codex exec` session in the isolated workspace with `--ignore-user-config --ignore-rules --ephemeral --sandbox read-only` plus **ephemeral MCP configuration overrides** for `orbit_v029_qa` pointing to the v0.29 source checkout; no persistent/global tool changes or blanket permission bypass. The session produced a saved JSONL event log at `%TEMP%\\Orbit-v029-HostQA-20261103\\codex_v029_remaining_acceptance_20261103.jsonl` and returned **exit code 0**, with **one completed turn**.

An independent subsequent log parser verified **exactly five completed real MCP tool invocations**, all to `orbit_v029_qa`; zero MCP call errors, **zero other tool starts**, and only `orbit_update_status` and `orbit_capability_select` among the invoked MCP tools:

| Actual native Codex gate | Result | Source-returned fields |
| --- | --- | --- |
| 1. Version-status tool | **PASS for reported installed version** | `orbit_update_status.status=UP_TO_DATE`, `installed_version=0.29.0`; **no independent running `serverInfo.version` attestation** in this response |
| 2. Rust CLI project-aware shortlist | **PASS** | `skill_plan.status=SKILL_SHORTLIST_READY`, only synthetic `cargo-testing`, `manifest.format=orbit-skill-plan-v2`; `activation_allowed=false`, `state_written=false` |
| 3. Exact manifest pin replay | **PASS** | `skill_plan.revalidation.status=PINS_MATCH_CURRENT_PREVIEW_ONLY`, `context_changed=false`, no host activation |
| 4. Caller-declared permission denial | **PASS for Orbit policy** | `skill_plan.status=HOLD_PERMISSION_DENIED` despite matching prior pins, `activation_allowed=false`, `state_written=false`. **This is not a native IDE permission prompt/denial test**. |
| 5. Host-context drift without modifying source | **PASS** | Prior Codex manifest replayed with caller-declared `host=antigravity`: `skill_plan.status=HOLD_STALE_MANIFEST`, `revalidation.status=HOLD_CHANGED_OR_MISSING_SKILLS`, `diff.context_changed=true`; no state write |

The test result fields were parsed **from actual `item.completed` `mcp_tool_call` events**, not inferred from Codex's final natural-language summary. All three synthetic `SKILL.md` SHA-256 digests still match the previously recorded fixture baselines. The global Antigravity Orbit registration still points to old `v0.25.1`; it was **not invoked**. A generated v0.29 desktop candidate bundle was already untracked in the disposable source checkout before these tests; no tracked development source edits occurred. Test logs were written inside the disposable QA workspace only.

**Important diagnostic distinction:** Codex's stderr contains a **nonfatal HTTP 403** emitted by a transport worker during this otherwise successful session. Its cause and any unrelated connection are **not established**. All five requested `orbit_v029_qa` MCP calls nevertheless returned successful, parsed tool responses and the native session exited 0. Do not claim the earlier HTTP 403 was fixed or that the entire Codex environment is error-free.

**Remaining independent gates:** stronger running-server version attestation via native MCP initialization metadata (not equivalent to the reported installed version), any actual host-level permission-denial prompt, host restart recovery, Windows symlink privilege-dependent cases, independent security review of untrusted `SKILL.md` parsing/tree hashing, and release/rollback acceptance. The five read-only selector checks above **are complete**; do not repeat them or request reauthorization without a new reason. **v0.29 remains a reviewed development candidate, not merged or published.**

## Acceptance and release blockers

1. **Completed on exact pre-documentation head:** CI #41617998877 5/5 PASS including v0.28 immutable upgrade and strict bundle parity. Recheck exact CI on any subsequent documentation or source head before merge.
2. Independently review untrusted skill parsing, bounded tree hashing, host-specific locations, symlinks, project-scope isolation, stale v1/v2 manifest behavior, explicit permission-denial HOLD and all unverified license/provenance metadata.
3. **Completed:** Antigravity interactive selector matrix (owner-reported) and native Codex five-call read-only selector/manifest/policy-denial/context-drift matrix (independent JSONL event verification), each using the isolated project-local MCP. **Still not verified:** real IDE permission-prompt denial, stronger running-server version attestation, genuine host restart recovery and platform-specific symlinks.
4. Review owner-specified version cutline, updated draft PR #70, v0.30 stack compatibility, installer upgrade/backups and truthful public documentation before a release candidate is promoted. Require explicit owner merge/publication approval. No Claude Code acceptance required in this cycle.

**Evidence semantics:** PASS means actually executed; documented source tests and local MCP smoke are not live IDE/agent acceptance, and a SHA-256 fingerprint is not a trust or security certificate.
