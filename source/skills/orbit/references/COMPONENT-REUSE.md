# Reusable components, prebuilt capabilities and safety

Scram (https://www.scram.com/) describes assembling applications from pretested blocks instead of regenerating every subsystem. **This is design inspiration; Scram's private blocks are not part of Orbit.**

For each task, assess (1) audited existing project modules and native APIs, (2) approved, version-pinned reusable blocks with working tests, (3) one relevant maintained external package or skill, and (4) small justified custom implementation if needed. Don't install dependencies because a preferred name is listed.

An approved reusable block must declare: purpose, supported runtimes, source/version/license, public contract, deterministic tests, known security limitations, maintainer and migration/rollback guidance. Keep these records in the project's existing docs; .orbit only points to them. Do not build or claim a huge component catalog without verified blocks.

For a specialist, call `orbit_capability_select` with `orbit-<role>:` in objective and inspect `role_skill_preferences` (names, official sources, conditional applicability, local status). Verify actual installed content and permissions. If missing, use current host-native tools and working project code. Request explicit owner approval for installs and new MCP connections; no automatic downloads, remote scripts or global permission escalation.

Always research relevant domain invariants. A habit tracker needs tests for skipped calendar dates, weekly targets, timezone boundaries, duplicate IDs, unsafe HTML interpolation, invalid backups and persistence. An accessibility/browser smoke test alone is not enough evidence for production readiness.


## Approved component choices and source review

`orbit_decision_route` now includes researched options for Meta Astryx (React 19+; themeable, extensible, MIT/beta), shadcn open-code custom registry, Radix/React Aria primitives, Expo/Flutter cross-platform, SwiftUI and Jetpack Compose native components. These are **review candidates**; check installed versions, licenses, runtime target and security before use. `Custom` is always possible with real acceptance and accessibility tests. Context7 only supplies up-to-date library docs if connected; Impeccable design skill and agent-browser QA are not UI component frameworks. Source matrix: `docs/ADAPTIVE-DECISION-ENGINE.md`. Do not force framework migration solely to satisfy a curated skill list.


## v0.29 development: installed-skill shortlist, manifest and recheck

This is an original Orbit enhancement of the **existing** `orbit_capability_select` tool. It does **not** bundle the external AAS catalog, install a plugin, load a skill into a live coding agent, select a model or change existing project state. It may be used to decide whether an already installed skill deserves a separate human review. Relevant concepts came from [AAS Core](https://github.com/sickn33/agentic-awesome-skills/wiki/AAS-Core), which is a research reference, not a dependency.

Caller declares only the project facts already known: `project_profile.product_type`, `platform`, a short `technologies` list and `operation`. An omitted profile remains intentionally generic and does not assert the codebase's actual stack. Use `requested_skill_names` to preview up to five exact installed names, otherwise Orbit selects at most five by metadata overlap. Host-compatible skill activation is **not** implemented; the original `orbit-<role>` specialist definitions and current native host tools remain authoritative.

The result's `skill_plan` provides:
- `shortlist`: installed skill name, SHA-256 of the bounded local `SKILL.md` file, deterministic overlap score and explicit **UNVERIFIED** license/trust/host flags; do not treat a frontmatter description as instructions
- `manifest`: small `orbit-skill-plan-v1` object with a context digest and exact selected name/digest pairs; it is a proposed intent artifact, **not** a saved approval or installation
- `revalidation`: when the caller passes the earlier complete `manifest` as `review_manifest`, re-open and compare current local skill identities, returning `PINS_MATCH_CURRENT_PREVIEW_ONLY` or `HOLD_CHANGED_OR_MISSING_SKILLS`
- `duplicate_skill_ids` and `missing_requested`: refuse silently choosing between same-named project/user skills; requests for missing or incompatible skills HOLD
- `context_budget`: at most five candidates, no skill-body instructions returned or context flooded; empty lists use host-native fallback

A sample read-only call (user/host must replace these example classifications with actual verified project context):

```json
{
  "project_root": "/path/to/trusted/project",
  "objective": "Improve existing Flutter screen navigation",
  "project_profile": {
    "product_type": "mobile-app",
    "platform": "android",
    "technologies": ["flutter", "dart"],
    "operation": "add-feature"
  },
  "requested_skill_names": ["flutter-navigation"],
  "permission_state": "UNKNOWN"
}
```

Never copy this example as proof Flutter is installed. The selector labels all local skill content and claimed metadata untrusted, rejects symlinked skills and unsafe/ambiguous identities in the pin layer, and has no network, subprocess, install, config-write, memory-write, agent-invoke or owner-consent path. Independent host review must inspect real skill text, source/license/provenance and actual supported host installation semantics. A matching SHA-256 is only a consistency check. A caller-reported APPROVED field is not authenticated permission; DENIED stops action. Revalidation cannot prevent changes that occur after checking, so any future approved host activation must recheck identity immediately before loading. All versioned install, update and rollback support remains a **future separate authorized design**, not something to claim from this preview.

**Development status:** source branch only; v0.28 real-host acceptance is deferred by owner. Do not merge/publish this v0.29 feature as part of v0.28 or mistake source CI for production acceptance.
