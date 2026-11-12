# [PRODUCT] — vX.Y.Z mission and scope

**Status:** PROPOSED / APPROVED / IN DEVELOPMENT / FEATURE FREEZE / TESTING /
BLOCKED / READY TO MERGE / MERGED / PUBLISHED / SUPERSEDED  
**Owner / decision date:** [name / YYYY-MM-DD]  
**Target branch:** `release/vX.Y.Z-candidate` (when stabilization begins)  
**Baseline:** [last published tag + exact commit]  
**Scope owner:** [team or person]  
**Product workspace:** [this project's own knowledge and research link]

## Goal and user benefit

[What will be measurably better for users after this version?]

## Committed scope

| Feature or repair | User benefit | Implementation PR | Status | Acceptance evidence |
| --- | --- | --- | --- | --- |
| [Item] | [Benefit] | [URL] | [Proposed / merged / verified] | [Test result or pending] |

## Exclusions and dependencies

- **Not in this release:** [Work intentionally deferred].
- **Depends on:** [Host SDK, runtime, earlier branch, migration, external permission].
- **Supported targets:** [Platforms and variants].
- **Compatibility and security risks:** [Specific issues].

## Scope freeze and release candidate

- **Feature freeze date:** [YYYY-MM-DD or not yet set].
- **Frozen commit:** [Exact SHA, required when testing begins].
- **Allowed on release branch after freeze:** Defect, compatibility and
  documentation fixes needed for this version, with review/tests.
- **New features after freeze:** Separate short-lived feature branch or the next
  planned version; never silently broaden this candidate.
- **Dependencies on unreleased work:** Branch explicitly from the dependency and
  mark stacked; rebase or retarget after the prior version is merged.

## Acceptance gates

[Link to the version-specific release readiness checklist and actual CI.
Mark PASS only after executed evidence. Record FAIL / BLOCKED / NOT RUN.]

## Decisions and continuity

- [YYYY-MM-DD] [Decision; PROPOSED/APPROVED/SUPERSEDED; rationale and linked proof].
- **Current blocker:** [Issue or None].
- **Next action:** [One concrete action].
- **Release authorization:** NOT GRANTED until explicit owner approval.

<!-- Reuse this template per project. Do not store one project's choices, model
preferences, memory or release commitments in another project's workspace. -->