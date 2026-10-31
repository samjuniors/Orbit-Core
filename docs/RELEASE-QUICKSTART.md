# Release and installation quickstart

**For users:** Always choose the current published version from [GitHub Releases](https://github.com/samjuniors/Orbit-Core-MCP/releases). The version and asset names below use `X.Y.Z` placeholders; do not download an unpublished candidate or assume that `main` is a release. Orbit `0.x` releases are prereleases.

## First installation

1. Open the official GitHub Releases page; choose the intended published version and read **Known limitations**.
2. Download `ORBIT-Universal-Setup-vX.Y.Z.zip` and its exact `.sha256` sidecar. Verify the ZIP SHA-256. The checksum proves file integrity, **not** publisher identity.
3. Extract into a new folder. Windows: install Python 3.10–3.13 with Tkinter (3.12 recommended), then double-click **Orbit Setup.cmd**. macOS/Linux: use `python3 orbit_setup.py`. No administrator privileges or additional LLM service are required for the local stdio MCP.
4. Choose your coding host(s) and either **This computer** (current user profile, not all OS accounts) or **One project**. Preview exactly which files will change. Approve only your intended changes; edited/unrecognized configurations must be reviewed, not overwritten automatically.
5. Refresh or restart your host MCP connection; ask Orbit to call `orbit_project_scan` and confirm the reported version/tool inventory. An installer success message alone does not prove a live IDE connection.

**Other packages:** `Orbit-Core-Plugin-Suite-vX.Y.Z.zip` holds separate host-specific Antigravity/Codex/Claude Code manifests, `Orbit-Antigravity-Plugin-vX.Y.Z.zip` is the Antigravity-specific package, and `ORBIT-Claude-Desktop-vX.Y.Z.mcpb` is a separate Claude Desktop extension. These are not interchangeable; the single ZIP does not imply automatic native plugin activation in all hosts.

## Updating an existing installation

Back up custom configuration and SQLite data (including WAL sidecars) before a significant update. Use the installed Update Manager or the installed `orbit` launcher to **check and preview** a published candidate, then explicitly apply only the reviewed changes. The updater must not silently overwrite customized files or imply a guaranteed data downgrade. Refresh the host afterward and re-check `orbit_project_scan`.

On Windows, if Orbit's per-user launcher exists:

```powershell
& "$HOME\.orbit-universal\bin\orbit.cmd" doctor
& "$HOME\.orbit-universal\bin\orbit.cmd" update --check
& "$HOME\.orbit-universal\bin\orbit.cmd" update
# Only after reviewing the preview:
& "$HOME\.orbit-universal\bin\orbit.cmd" update --apply
```

## Maintainer: every version

Follow the **single authoritative** [release process and reusable checklist](RELEASE-PROCESS.md). Stage consistent version/changelog/manifest changes on a new release branch; require code review, all exact-head CI jobs, genuine host/security/rollback acceptance and owner approval. **Publish using GitHub Actions → Publish versioned release**, from `main` with `version=X.Y.Z`. The workflow reads the matching changelog section, builds the ZIP/MCPB/checksums and creates the tag. Verify the actual published tag, assets, checksums and readme links. Never retag an existing release to fix old documentation.
