# Versioning, tags, and GitHub Releases

Orbit Core MCP uses Semantic Versioning `MAJOR.MINOR.PATCH`. `VERSION` is authoritative; `installer.py`, `source/runtime/orbit_mcp.py`, the Claude Desktop `.mcpb` filename/manifest, and release assets must agree. The repository's first Git baseline is **v0.23.0**. Older ChatGPT-plugin ZIP iterations are not retroactively represented as Git tags or commits.

## Published versus planned versions

- `VERSION` is the **current repository source/package candidate** (prepared for `0.26.0` after M3/M4 source merges), not proof that GitHub has published a release. `NEXT_VERSION` records the **proposed** next version (`0.26.1`), not authorization to publish it. The latest GitHub published version is **v0.25.1 (prerelease; 2026-10-29)**. Every new release requires a matching `CHANGELOG.md` section and independently reviewed packaging, host acceptance and explicit owner publication approval. The main source may include fixes that do not exist in any published desktop bundle.
- Never change `VERSION` alone. On a reviewed release branch, update `VERSION`, `NEXT_VERSION` (to the next planned version), `installer.py`, `source/runtime/orbit_mcp.py`, and add the release's `CHANGELOG.md` entry together.
- Prepare a **new, unpublished** MCPB from an immutable prior bundle via `python scripts/prepare_release_candidate.py` (CI does this before tests). The helper detects the latest older bundled release, copies non-code resources/metadata into the new version and enforces exact runtime module/source parity. It does **not** modify the older published artifact, tag, or release. CI uploads the candidate ZIP/MCPB as downloadable *test artifacts* for host evaluation. Do **not** mark these test artifacts as published releases or as cryptographically attested.
- Explicitly verify upgrade compatibility with customized user installs, including stock digest allowlist updates; an unknown file must stay protected. Do **not** delete old versioned bundles, Git tags, owner documents or other work to make a new version appear clean.
- A release workflow now builds the versioned desktop bundle and then requires `python scripts/check_version.py --strict-bundle` before tagging/publishing. A release version bump alone does not grant permission to publish. Source/desktop mismatch is allowed on ordinary development CI, but **not** when publishing a release.

## Prepare a release

1. Create a `release/vX.Y.Z-candidate` branch from `main`, review the diff in a pull request, and update `VERSION`, runtime/installer version declarations, `NEXT_VERSION`, and `CHANGELOG.md` together. CI generates the new bundle from a pinned older template before running tests; binary artifacts do not have to be committed to the source branch. Do not generate a fake historic release.
2. Run `python scripts/prepare_release_candidate.py`, `python -m unittest discover -s tests -v`, `python scripts/check_version.py --strict-bundle`, and `python scripts/build_release.py --verify`. Check the installation package on a disposable project. CI also tests supported Python versions.
3. Merge the reviewed pull request into `main` when Linux/Windows CI passes, source/archive parity holds, and owner approval is complete. Live desktop/browser acceptance is separately required for production claims.
4. In **GitHub → Actions → Publish versioned release → Run workflow**, select `main`, enter the exact approved value of `VERSION`, and run it. No local Git CLI required. The workflow retests source, builds artifacts, creates an **annotated tag** `vMAJOR.MINOR.PATCH` on the tested commit if missing, and creates a GitHub Release.
5. Alternatively, an authorized maintainer may push a new `vMAJOR.MINOR.PATCH` tag pointing at a commit already on `main`. This triggers the same tested publication path. A tag pushed by the workflow's `GITHUB_TOKEN` does not trigger another workflow; manual publication completes within that original run.
6. Verify the GitHub **Releases** and **Tags** pages, CI execution, ZIP and `.mcpb` downloads, and their `.sha256` checksums. Only after verification, publish any separately managed ChatGPT plugin version in Plugin Creator.

## Published assets

- `ORBIT-Universal-Setup-vX.Y.Z.zip` — portable installer and source bundle.
- `ORBIT-Universal-Setup-vX.Y.Z.zip.sha256` — SHA-256 checksum.
- `ORBIT-Claude-Desktop-vX.Y.Z.mcpb` — Claude Desktop extension.
- `ORBIT-Claude-Desktop-vX.Y.Z.mcpb.sha256` — checksum.
- GitHub's automatically generated source archives for the immutable tag.

The release body is generated from the matching section `## [X.Y.Z]` in `CHANGELOG.md`. Releases for version `0.x` are marked **pre-release candidates** until live host acceptance has been separately verified. The installed Orbit updater defaults to the explicit `candidate` channel for these 0.x assets. A stable channel is opt-in with `--channel stable`, and no production suitability is implied.

## Safety and consistency rules

- **Never force-push, retag, or silently repoint a published version.** Use the next SemVer patch for corrections and record them in the changelog.
- The workflow refuses a manual release whose requested version differs from `VERSION`, and rejects a pushed tag that differs from `VERSION` or points outside main's history.
- Re-running a successful workflow does not replace an existing GitHub Release. A matching tag can be reused if a previous release attempt failed halfway through.
- GitHub Actions requires repository Actions enabled and an available `GITHUB_TOKEN` with `contents: write`; repository rules or restricted Actions settings can block tag creation or release upload. Review the failure logs rather than bypassing protections.
- Keep project-specific memory (`.sqlite3`, WAL files), `.env`, credentials, personal host config and project transcripts out of Git and release artifacts.
- Require code-review and CI checks before merging; configure branch protection/rulesets in GitHub Settings if your permissions and plan support them. A workflow does not substitute for review.

## Links

- [Release workflow](../.github/workflows/release.yml)
- [Releases](https://github.com/samjuniors/Orbit-Core-MCP/releases)
- [Tags](https://github.com/samjuniors/Orbit-Core-MCP/tags)