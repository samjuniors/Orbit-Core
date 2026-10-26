# Versioning, tags, and GitHub Releases

Orbit Core MCP uses Semantic Versioning `MAJOR.MINOR.PATCH`. `VERSION` is authoritative; `installer.py`, `source/runtime/orbit_mcp.py`, the Claude Desktop `.mcpb` filename/manifest, and release assets must agree. The repository's first Git baseline is **v0.23.0**. Older ChatGPT-plugin ZIP iterations are not retroactively represented as Git tags or commits.

## Prepare a release

1. Create a feature/release branch from `main`, review the diff in a pull request, and update `VERSION`, runtime/installer version declarations, the release extension, and `CHANGELOG.md` together. Do not generate a fake historic release.
2. Run `python -m unittest discover -s tests -v`, `python scripts/check_version.py`, and `python scripts/build_release.py --verify`. Check the installation package on a disposable project. CI also tests supported Python versions.
3. Merge the reviewed pull request into `main` when Linux/Windows CI passes, source/archive parity holds, and owner approval is complete. Live desktop/browser acceptance is separately required for production claims.
4. In **GitHub → Actions → Publish versioned release → Run workflow**, select `main`, enter the exact value of `VERSION` (for the baseline, `0.23.0`), and run it. No local Git CLI required. The workflow retests source, builds artifacts, creates an **annotated tag** `vMAJOR.MINOR.PATCH` on the tested commit if missing, and creates a GitHub Release.
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