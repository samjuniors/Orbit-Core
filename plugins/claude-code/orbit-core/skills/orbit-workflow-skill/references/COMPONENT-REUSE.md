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

Caller declares only the project facts already known: `project_profile.product_type`, `platform`, a short `technologies` list and `operation`. Optionally pass `host=codex|claude-code|antigravity|unknown`. This is a caller-declared host hint, not a live capability or permission check: a Claude-only local directory cannot be presumed usable from Codex; the shared `.agents/skills` path remains a *candidate* and must be verified in the actual IDE. An omitted profile remains intentionally generic and does not assert the codebase's actual stack. Use `requested_skill_names` to preview up to five exact installed names, otherwise Orbit selects at most five by metadata overlap. Host-compatible skill activation is **not** implemented; the original `orbit-<role>` specialist definitions and current native host tools remain authoritative.

The result's `skill_plan` provides:
- `shortlist`: installed skill name, SHA-256 of `SKILL.md`, bounded recursive helper/reference-tree SHA-256, hashed local source location, match score, PROJECT_LOCAL/USER_LOCAL **unverified** directory hint and author-claimed **unverified** license/version; never treat local presence or hash as proof of publisher, license or runtime suitability
- `manifest`: `orbit-skill-plan-v2` snapshot with context digest and exact name/`sha256`/`tree_sha256`/`location_sha256` per selection; v1 manifests remain readable only to report `HOLD_LEGACY_MANIFEST_REVIEW_REQUIRED` and require fresh review (not auto-upgraded or approved)
- `revalidation`: inspect exact previous `review_manifest` and identify changed project context, added/removed/changed skill identities, selection order and format changes; stale or v1 input returns `HOLD_STALE_MANIFEST` for new approval
- `integrity_scope`: bounded traversal (at most 64 files/directories and 512 KiB per skill, 256 KiB per helper file) and at most 24 automatic tree fingerprints; exact requested names (max five) bypass automatic ranking but not safety caps; deferred count is visible. No symlink or junction traversal; oversized/unsafe trees are ineligible rather than partially fingerprinted
- `coverage_hint`: declared framework labels matched *by skill-name tokens* and unmatched labels; neither exact token match nor author description proves semantic fit or installed toolchains
- `handoff`: human review and host-owned, permission-gated activation checklist, not a command or installer; no installation, project writes, host config changes or rollback needed from a preview
- `duplicate_skill_ids` and `missing_requested`: refuse silently choosing among same-named project/user skills; conflicting, absent or unsafe requested skills HOLD
- `context_budget`: at most five selected candidates, no skill-body instructions returned or context flooded; project-constrained installed-candidate results omit raw untrusted frontmatter; empty lists use host-native fallback

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

Never copy this example as proof Flutter is installed. The selector labels all local skill content and claimed metadata untrusted, rejects symlinked skill directories and nested helper-file traversal, and has no network, subprocess, install, config-write, memory-write, agent-invoke or owner-consent path. Independent host review must inspect real skill text, source/license/provenance and actual supported host installation semantics. SHA-256 and directory hints are consistency checks only. A caller-reported APPROVED field is not authenticated permission; DENIED stops action. Revalidation cannot prevent changes after checking, so any separately approved host activation must recheck the full skill snapshot immediately before loading and preserve an actual rollback path if it changes a host configuration. The unified Orbit installer now includes the skill planner module in its canonical runtime inventory; other bundle builders already copy canonical runtime files. Actual activation/update/revert remains a **separate host-authorized integration**, not a feature of this preview.

**Development status:** source branch only; v0.28 real-host acceptance is deferred by owner. Do not merge/publish this v0.29 feature as part of v0.28 or mistake source CI for production acceptance.
