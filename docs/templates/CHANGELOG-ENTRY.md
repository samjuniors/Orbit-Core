# Reusable changelog entry template

> Copy the applicable sections into the project's EXISTING root `CHANGELOG.md`.
> Do not create a second changelog. Replace every bracketed placeholder, delete
> empty headings, and never describe a candidate as already published.

## [Unreleased]

### Added
- [What users can now do; product surface and availability, if relevant] ([PR or issue])

### Changed
- [Behavior that differs from the previously **published** version]

### Fixed
- [Problem the user actually experienced and what no longer fails]

### Security
- [Security issue mitigated and advisory/link; don't assert certification]

### Deprecated / Removed
- [Affected capability, replacement and deadline, if applicable]

## [X.Y.Z] — Candidate (NOT PUBLISHED)

**[Short benefit-led title]**

[One or two sentences describing the practical user outcome, not just a feature name.]

### What's new
- **[Feature]:** [Who benefits, supported platform or host, and user-visible result]

### Improvements
- [Performance, reliability, UX, onboarding, compatibility or workflow improvement]

### Fixes
- [Specific reproducible problem and verified behavior after the fix]

### Security and permissions
- [Material security change with evidence; mark NOT VERIFIED when appropriate]

### Breaking changes, migration and rollback
- **Affected users:** [Audience or None]
- **What changed:** [Incompatible behavior, required environment or data format]
- **Before upgrading:** [Back up config, memory, database/WAL, user files as applicable]
- **Required steps:** [Concise, tested migration steps or NOT VERIFIED]
- **Rollback:** [Verified path or explicit warning when not established]

### Requirements and availability
- **Supported platforms:** [OS / host / interface tested]
- **Dependencies:** [Runtime and version constraints]
- **Known limitations:** [Unsupported workflows, unavailable hosts, blocked gates]

### Verification
- **Source:** [PR(s) and exact commit]
- **Automated:** [CI URL, platform matrix, PASS/FAIL, test counts]
- **Live-host:** [Host, permission, upgrade and rollback evidence; NOT RUN if missing]
- **Release status:** Candidate — **not yet published**; owner approval pending.

<!--
When the release is ACTUALLY published: replace the candidate status and add an
ISO 8601 date; retain the exact published version and evidence. Never change
a previously published entry to falsely claim new features were shipped.
Our current Orbit Core workflow extracts the matching ## [X.Y.Z] section to
create GitHub Release notes; keep it self-contained and user-friendly.
-->