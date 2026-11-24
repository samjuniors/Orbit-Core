# [PRODUCT] vX.Y.Z — release readiness

**Status:** HOLD / IN REVIEW / APPROVED / PUBLISHED  
**Candidate branch / frozen SHA:** [release/vX.Y.Z-candidate / exact SHA]  
**Compared with published version:** [tag/commit]  
**Decision owner and date:** [owner / YYYY-MM-DD]  
**GitHub release URL:** [leave blank until actually published]

| Gate | State (PASS / FAIL / BLOCKED / NOT RUN) | Evidence / owner |
| --- | --- | --- |
| Version and scope matches the approved mission | NOT RUN | [Spec, PR and changelog] |
| Code review and exact-head CI checks | NOT RUN | [Run URL and OS matrix] |
| Clean build with version and asset parity | NOT RUN | [Commands and outputs] |
| Reproducible package and checksums | NOT RUN | [Asset names and SHA256] |
| New-user install and launch | NOT RUN | [Host / date / result] |
| Existing-user update with custom files and DB | NOT RUN | [Source version / result] |
| Permission denial, failure and recovery | NOT RUN | [Actual host evidence] |
| Backups, rollback and previous release preserved | NOT RUN | [Restore test details] |
| Security/dependency/provenance review | NOT RUN | [Findings and unresolved risks] |
| Public notes and migration guide reviewed | NOT RUN | [CHANGELOG and docs] |
| Owner approved exact version and publication | NOT RUN | [Approval reference] |
| Tag, GitHub Release and downloads verified | NOT RUN | [Post-publication links] |

## Exceptions and residual risks

[Explicitly list unsupported hosts, SKIPPED tests, migration warnings and known
release blockers. CI PASS is not live-host PASS.]

## Decision

**Go / no-go:** HOLD  
**Rationale:** [Why publication is or is not safe today]  
**Next evidence required:** [Specific blocked gate]  
**Publication authority:** [Only the product owner, after all required gates]

## Post-release verification (fill after publication)

- Tag: [vX.Y.Z, exact commit; immutable]
- Release date and URL: [YYYY-MM-DD, URL]
- Downloaded artifacts and SHA256 verification: [PASS or FAILURE + evidence]
- Installed version and rollback smoke: [result and link]
- Follow-up issues: [links]

<!-- This is a per-version acceptance record. Engineering truth comes from
the repository/CI; product decisions belong to the project's own knowledge
workspace. No checkboxes are assumed passed. -->