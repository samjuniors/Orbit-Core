# Reusable release notes and parallel-version workflow

**Owner request:** 2026-10-30 · **Template scope:** reusable, copy/adapt to each
independent GitHub project · **Orbit Core implementation:** this repository's
actual release workflow remains authoritative.

## Research findings — why a hybrid is better

| Reference | Observed approach | Reusable idea | Limitation for our use |
| --- | --- | --- | --- |
| [Antigravity changelog](https://antigravity.google/docs/changelog/) | Separate App/CLI/SDK/IDE surfaces, dated versions with concise headlines plus Improvements and Fixes | Version-specific summaries, organized by host/product surface | Don't promise features on an untested host or copy rollout wording |
| [Claude Code changelog](https://code.claude.com/docs/en/changelog) and [upstream GitHub releases](https://github.com/anthropics/claude-code/releases) | High-frequency version history with concrete Added, Changed, Fixed and platform-specific behavior | Precise, developer-friendly technical changes with exact versions | A long technical list alone is not a user-friendly release announcement |
| [OpenAI API changelog](https://developers.openai.com/api/docs/changelog) | Month/day update entries, Feature/Update classification and affected models/endpoints | State compatibility, affected platform/API surface and migration consequences | Not every desktop app needs API endpoint metadata |
| [OpenAI product release notes](https://openai.com/products/release-notes/) | Product filter, dated status/category and benefit-led explanation, links to source | Public, readable title and short real-world benefit before details | Marketing-style overview alone omits install, rollback and technical evidence |

**Decision for Orbit Core:** combine them into (1) a human-readable,
versioned `CHANGELOG.md` with an honest Unreleased section;
(2) product-focused GitHub Release notes **generated from the approved
matching changelog version** by our existing workflow;
(3) an evidence-based version readiness record plus a durable decision
in this project's Notion. GitHub is engineering authority; Notion does not
magically synchronize with GitHub. Avoid duplicate changelogs and invented
release statuses.

## Copy-ready templates in this repository

| Reusable template | Usage |
| --- | --- |
| [CHANGELOG-ENTRY.md](templates/CHANGELOG-ENTRY.md) | Draft or update the existing root changelog at PR merge / scope freeze |
| [GITHUB-RELEASE-NOTES.md](templates/GITHUB-RELEASE-NOTES.md) | Shape the readable public summary inside that changelog section; don't fork an independent release truth |
| [VERSION-MISSION.md](templates/VERSION-MISSION.md) | Define scope, acceptance boundaries, exclusions, branch and frozen SHA for each version |
| [RELEASE-READINESS.md](templates/RELEASE-READINESS.md) | Evidence-based go/no-go template before tagging or publishing |

These are intentionally **product-neutral**. Copy/adapt each template into
the relevant repository and its own product knowledge hub; do not propagate
Orbit-specific requirements into Helm, Aro, or other projects. The destination
repository owns the resulting file and release decisions.

## Ownership and update cadence

**As work is developed:** Write short user-facing entries into
`## [Unreleased]` in the branch/PR. Connect claims to PRs or regression
evidence. Do not mark feature tests PASS until run. Fixes with no user-facing
impact can be summarized together.

**At a version freeze:** Open or update the version-specific mission and
readiness record. Compare proposed features against the **latest published
tag** rather than simply comparing source versions. Build a `## [X.Y.Z]`
candidate section in the changelog with highlights, changes, migration,
requirements, verification and unsupported hosts. Review it as part of the
release PR. Do not insert placeholder text into a published version.

**At approved publication:** The exact versioned changelog section becomes
the GitHub Release body. Confirm source SHA, immutable tag, asset inventory,
download SHA256 and live accepted support status, then record the actual
release URL/date in the existing Notion decision page. Do not auto-adopt
external tools or create another Notion product database.

**After publication:** Reopen `[Unreleased]` for the next changes. Never
retroactively pretend an unshipped feature existed in an earlier release.
Fix published mistakes in a new patch release where applicable.

## Parallel release branches without blocked development

We deliberately use **short-lived feature branches + short-lived
release-candidate branches**, not a new permanent `develop` branch for
each product. This follows GitHub's [branch/PR model](https://docs.github.com/en/get-started/using-github/github-flow)
while meeting the owner's need to keep coding during slow host tests.

```text
main (reviewed, integrated source; may be ahead of last public release)
  ├── release/v0.26.0-candidate  → version freeze / QA / only critical fixes
  ├── feat/new-work-A           → independent future work keeps moving
  └── feat/new-work-B           → independent future work keeps moving

PASS + owner signoff → merge release PR → main
                   → publish exact tested main commit as immutable v0.26.0
                   → verify GitHub Release and checksums
```

**Important constraints:**

1. Branch a release candidate at the appropriate accepted feature cutline, not
   from arbitrary unreviewed work. Record the exact base SHA and test it. A
   freeze means no feature creep into that candidate.
2. Keep unrelated new work on independently reviewable `feat/*` branches.
   If a new feature depends on an unmerged release candidate, mark it as
   stacked and rebase/retarget after the dependency lands.
3. Choose release names against published versions; never reserve or reuse
   tags as mere branch names. A newer version branch may be *planned*
   concurrently but must account for earlier dependency and migrations.
4. The existing Orbit Core `release.yml` deliberately accepts manual
   publication **only from `main`** and requires pushed tags to exist in
   `main`'s history. A branch is not a GitHub release; **do not publish
   straight from the unmerged candidate branch**. Change that contract only
   through a separately reviewed workflow/security policy.
5. Release branch acceptance includes GUI/IDE, permission, local memory,
   upgrade and rollback evidence where relevant; CI alone does not attest
   real-host readiness. No scripts or branch naming bypass owner approval.
6. Merge the reviewed release branch when ready. If main advanced with
   independent work that must **not** ship in the target release, **stop**:
   do not publish all of main by accident. Either defer merging that newer
   work until after publication, or propose a separate reviewed workflow
   for publishing the exact frozen release commit (including tag protections).
7. Published tags and assets remain immutable. Urgent fixes get new
   `hotfix/vX.Y.Z` branches and new patch versions.

## Example lifecycle (Orbit Core; illustrative only)

- `0.26.0`: development source already on main; release remains **HOLD**
  for outstanding real-host and migration/security acceptance.
- Candidate stabilization could use `release/v0.26.0-candidate` **after**
  its release scope, accepted base, requirements and support matrix are
  frozen; this document does not create or approve it.
- New independent work can use `feat/*` branches meanwhile. Do not merge
  changes meant only for a later version into main before publishing
  `v0.26.0` using the **current** main-only release workflow.
- `NEXT_VERSION` is planning metadata and does not authorize publication.

## Human-facing writing guidelines

Use: date + version, an explanatory headline, 1–3 clear benefits, the
relevant technical changes, migration and compatibility details, known
limitations, concrete verification/links and transparent status. Avoid
copying commit titles verbatim, long marketing prose, speculative claims,
unverified security promises or presenting unmerged candidates as releases.

**No automatic sync:** Each GitHub repo keeps its own version/changelog
and immutable published releases. Each product's Notion hub retains only
its own approved choices, evidence pointers and rationale.
