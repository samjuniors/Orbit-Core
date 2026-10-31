# Versioning, tags, and GitHub Releases

Orbit Core MCP uses Semantic Versioning `MAJOR.MINOR.PATCH`. `VERSION` is authoritative; `installer.py`, `source/runtime/orbit_mcp.py`, the Claude Desktop `.mcpb` filename/manifest, and release assets must agree. The repository's first Git baseline is **v0.23.0**. Older ChatGPT-plugin ZIP iterations are not retroactively represented as Git tags or commits.

## Published versus planned versions

- `VERSION` is the version being built in the active checkout, not proof that GitHub published it. `NEXT_VERSION` is a proposal, not release authorization. The **only current publication authority** is [GitHub Releases](https://github.com/samjuniors/Orbit-Core/releases). The v0.27.0 prerelease was published 2026-10-31; subsequent versions must follow the same verification and owner-approval procedure. Source may be ahead of released desktop artifacts.
- Never change `VERSION` alone. On a reviewed release branch, update `VERSION`, `NEXT_VERSION` (to the next planned version), `installer.py`, `source/runtime/orbit_mcp.py`, and add the release's `CHANGELOG.md` entry together.
- Prepare a **new, unpublished** MCPB from an immutable prior bundle via `python scripts/prepare_release_candidate.py` (CI does this before tests). The helper detects the latest older bundled release, copies non-code resources/metadata into the new version and enforces exact runtime module/source parity. It does **not** modify the older published artifact, tag, or release. CI uploads the candidate ZIP/MCPB as downloadable *test artifacts* for host evaluation. Do **not** mark these test artifacts as published releases or as cryptographically attested.
- Explicitly verify upgrade compatibility with customized user installs, including stock digest allowlist updates; an unknown file must stay protected. Do **not** delete old versioned bundles, Git tags, owner documents or other work to make a new version appear clean.
- A release workflow now builds the versioned desktop bundle and then requires `python scripts/check_version.py --strict-bundle` before tagging/publishing. A release version bump alone does not grant permission to publish. Source/desktop mismatch is allowed on ordinary development CI, but **not** when publishing a release.

## Mandatory reusable release checklist (every version)

This is the **single maintained release procedure**; do not create a new competing release-policy page. Update the existing version-specific engineering acceptance record with test evidence, and update the Orbit Core Notion hub with the version, decision, unresolved limitations, GitHub PR and release links. These records **link** to each other; they do not sync automatically.

### Gate A — Prepare the correct code, scope and notes

1. Confirm the repo is **Orbit-Core**, inspect `main`, active release/development branches, past published tags and current Notion decisions. Select the exact version and reviewed source branch. Never substitute an older candidate branch with a different MCP inventory.
2. Create **one** `release/vX.Y.Z-candidate` branch from the reviewed source/appropriate `main`. Ensure `VERSION`, `NEXT_VERSION`, `installer.py`, `source/runtime/orbit_mcp.py`, manifests and all ZIP/MCPB package names are consistent; `NEXT_VERSION` must be greater than `VERSION`.
3. Update **the existing `CHANGELOG.md`** under `## [X.Y.Z]` with a public-facing version note: short user benefits under `### Highlights`, host/OS/Python requirements and steps under `### Install and upgrade`, compatibility and migration/backup under `### Compatibility`, and truthful unverified behavior under `### Known limitations`. Leave older entries and tags intact. The GitHub workflow builds the release body from this section; **no manual release-note copy/paste**.
4. Ensure the public `README.md`, `docs/RELEASE-QUICKSTART.md`, installation/plugin docs and `docs/RELEASE-PROCESS.md` match the actual release: no stale “latest is …” or “not published” statements. Prefer a live link to Releases instead of a hard-coded “latest” number. The **version-specific acceptance document** must distinguish publish status from actual host/production certification.
5. Prepare the new desktop bundle from the prior released bundle, **normalize display metadata**, preserve icons and non-code resources, and verify exact runtime-module/source parity. Never modify a previously published bundle.

### Gate B — Validate everything that is testable

1. Run `python scripts/prepare_release_candidate.py` and `python scripts/check_release_readiness.py` (the latter also runs in CI and in the publication workflow), `python -m unittest discover -s tests -v`, `python scripts/check_version.py --strict-bundle`, `python scripts/build_release.py --verify` and `python scripts/smoke_release_zip.py`.
2. Check checksums, release ZIP entry safety, expected manifest/tool inventory, launcher existence, exact package naming, absence of private DBs/secrets, version/title/prose polish, and **all four published packages plus matching checksum sidecars**. A SHA-256 file is not a publisher signature.
3. Run exact-head Linux and Windows GitHub CI; inspect real logs for failures. Perform fresh-install and previous-release upgrade rehearsals using **disposable** profiles, honoring custom files, backups, WAL/SQLite retention and rollback. Record PASS, FAIL, SKIPPED, BLOCKED, NOT RUN or NOT VERIFIED and why.
4. Explicitly test genuine supported-host native MCP discovery, permissions/denial, delegation, cancellation/restart reconciliation, browser safety, installer GUI (including DPI/keyboard), real installed-user migration/rollback, security/privacy and cross-device recovery as appropriate. Code tests and MCP protocol smoke **do not** substitute for these checks. If unavailable, keep the gate open and do not say “production-ready.”

### Gate C — Owner decision and publication

1. Review the release PR diff, artifact inventory, exact-head CI, version acceptance record and known limitations. Have the owner explicitly approve any remaining **unverified** risks; release approval is a separate decision from a successful merge. Do not waive high-risk checks silently.
2. Merge approved branch into `main`, check **new merge-commit CI** and exact `VERSION`; preserve prior tags/assets.
3. On GitHub: **Actions → Publish versioned release → Run workflow → branch `main` → version `X.Y.Z`**. The workflow retests the code, generates bundle, validates release-note content and version metadata, builds ZIP/MCPB/sidecars, creates an annotated immutable `vX.Y.Z` tag and uploads the packages and automatically generated notes. **Never trigger the workflow or manually push a tag on an unreviewed commit.**
4. Verify **the actual public release**, not just workflow success: release is visible, tag peels to tested `main` commit, correct `prerelease`/stable status, all four packages plus four SHA-256 sidecars download and match, release body renders well, latest installer discovers the release, and the README/docs link to the correct download entry. Check a disposable extracted package again after publishing.
5. Update the **existing acceptance record** to separate “PUBLISHED” from “PRODUCTION HOST QA NOT VERIFIED” where applicable; update existing Orbit Core Notion version tracker with publication time, tag SHA, workflow, package/checksum evidence, known risks and next version. **Never revise, repoint or overwrite a published version tag or assets.** Corrections to source/docs go through a reviewed PR; binary changes need a new SemVer release.

### Public release-note template (new versions)

Write this into the **existing `CHANGELOG.md` section**. `v0.26.0` is a legacy long-form prerelease entry; releases after it use these section headings, which the readiness validator enforces.

```markdown
## [X.Y.Z] — Prerelease (YYYY-MM-DD)

### Highlights
- Concrete user-visible improvements and the problem each solves.

### Install and upgrade
- Download the matching Universal Setup ZIP and checksum from GitHub Releases.
- Supported hosts and Python/OS requirements; how to preview and confirm setup.

### Compatibility
- Database migration/backup/rollback cautions and any changed tool contracts.

### Known limitations
- Exact unsupported hosts and unverified host/security tests, without implying certification.
```

Treat source implementation, CI, native-host acceptance and GitHub publication as **distinct states**. Version `X.Y.Z` is not released until the public GitHub Release and immutable tag have actually been verified.

## Prepare a release

1. Create a `release/vX.Y.Z-candidate` branch from `main`, review the diff in a pull request, and update `VERSION`, runtime/installer version declarations, `NEXT_VERSION`, and `CHANGELOG.md` together. CI generates the new bundle from a pinned older template before running tests; binary artifacts do not have to be committed to the source branch. Do not generate a fake historic release.
2. Run `python scripts/prepare_release_candidate.py`, `python scripts/check_release_readiness.py`, `python -m unittest discover -s tests -v`, `python scripts/check_version.py --strict-bundle`, and `python scripts/build_release.py --verify`. Check the installation package on a disposable project. CI also tests supported Python versions.
3. Merge the reviewed pull request into `main` when Linux/Windows CI passes, source/archive parity holds, and owner approval is complete. Live desktop/browser acceptance is separately required for production claims.
4. In **GitHub → Actions → Publish versioned release → Run workflow**, select `main`, enter the exact approved value of `VERSION`, and run it. No local Git CLI required. The workflow retests source, builds artifacts, creates an **annotated tag** `vMAJOR.MINOR.PATCH` on the tested commit if missing, and creates a GitHub Release.
5. Alternatively, an authorized maintainer may push a new `vMAJOR.MINOR.PATCH` tag pointing at a commit already on `main`. This triggers the same tested publication path. A tag pushed by the workflow's `GITHUB_TOKEN` does not trigger another workflow; manual publication completes within that original run.
6. Verify the GitHub **Releases** and **Tags** pages, CI execution, ZIP and `.mcpb` downloads, and their `.sha256` checksums. Only after verification, publish any separately managed ChatGPT plugin version in Plugin Creator.

## Published assets

- `ORBIT-Universal-Setup-vX.Y.Z.zip` — portable installer and source bundle.
- `Orbit-Antigravity-Plugin-vX.Y.Z.zip` — host-native Antigravity lead/skills/agents/local-MCP plugin, subject to host installation/migration acceptance.
- `Orbit-Antigravity-Plugin-vX.Y.Z.zip.sha256` — integrity checksum for the plugin ZIP.
- `ORBIT-Universal-Setup-vX.Y.Z.zip.sha256` — SHA-256 checksum.
- `Orbit-Core-Plugin-Suite-vX.Y.Z.zip` — separate Antigravity, Codex and Claude Code host-native plugin manifests bundled into one download.
- `Orbit-Core-Plugin-Suite-vX.Y.Z.zip.sha256` — SHA-256 integrity checksum for the plugin-suite ZIP.
- `ORBIT-Claude-Desktop-vX.Y.Z.mcpb` — Claude Desktop extension.
- `ORBIT-Claude-Desktop-vX.Y.Z.mcpb.sha256` — checksum.
- GitHub's automatically generated source archives for the immutable tag.

The release body is generated from the matching section `## [X.Y.Z]` in `CHANGELOG.md` (not from a pasted GitHub form). Releases for version `0.x` are marked **pre-release candidates** until live host acceptance has been separately verified. The installed Orbit updater defaults to the explicit `candidate` channel for these 0.x assets. A stable channel is opt-in with `--channel stable`, and no production suitability is implied.

## Safety and consistency rules

- **Never force-push, retag, or silently repoint a published version.** Use the next SemVer patch for corrections and record them in the changelog.
- The workflow refuses a manual release whose requested version differs from `VERSION`, and rejects a pushed tag that differs from `VERSION` or points outside main's history.
- Re-running a successful workflow does not replace an existing GitHub Release. A matching tag can be reused if a previous release attempt failed halfway through.
- GitHub Actions requires repository Actions enabled and an available `GITHUB_TOKEN` with `contents: write`; repository rules or restricted Actions settings can block tag creation or release upload. Review the failure logs rather than bypassing protections.
- Keep project-specific memory (`.sqlite3`, WAL files), `.env`, credentials, personal host config and project transcripts out of Git and release artifacts.
- Require code-review and CI checks before merging; configure branch protection/rulesets in GitHub Settings if your permissions and plan support them. A workflow does not substitute for review.

## Links

- [Release workflow](../.github/workflows/release.yml)
- [Releases](https://github.com/samjuniors/Orbit-Core/releases)
- [Tags](https://github.com/samjuniors/Orbit-Core/tags)