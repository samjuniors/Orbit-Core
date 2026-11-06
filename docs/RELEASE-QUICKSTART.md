# Orbit Core - installing and managing published releases

**Current published versions (verified 2026-11-05):** [v0.30.0 stable](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.30.0) and [v0.29.0 stable](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.29.0). Always check [Releases](https://github.com/samjuniors/Orbit-Core/releases) for newer versions; a Git branch is not a published distribution. A stable-channel version is not a production/security certification.

## Windows: easiest setup

1. Download `ORBIT-Universal-Setup-vX.Y.Z.zip` and its matching `.sha256` from the **same official GitHub release**. Verify the checksum (for example `Get-FileHash .\ORBIT-Universal-Setup-vX.Y.Z.zip -Algorithm SHA256`). A matching checksum establishes integrity against the published sidecar, not independent publisher signing.
2. Extract. Double-click **Orbit Setup.cmd**. Pick **This computer** (your OS account) or **One project**; select **Antigravity, Codex, Claude Code and/or VS Code**. You can select several hosts in one installation.
3. Review the exact path changes. Apply only with explicit approval. Other MCP integrations and custom owner files must be retained or flagged for manual review.
4. Restart the chosen IDE. Ask the host to call `orbit_project_scan` and report live MCP version/tools; a written config is not proof of a successful connection.

**Requirements:** Python 3.10-3.13, Windows Python 3.12 recommended, Tkinter for the GUI. No administrator account and no model/API keys are required for the local MCP server itself.

## Windows: PowerShell installation from the official v0.30.0 ZIP

```powershell
# In the extracted Universal Setup directory:
py -3.12 orbit_setup.py install --scope machine --hosts antigravity codex
py -3.12 orbit_setup.py install --scope machine --hosts antigravity codex --apply

# Current installed launcher, no ZIP redownload needed for subsequent updates:
& "$HOME\.orbit-universal\bin\orbit.cmd" doctor
& "$HOME\.orbit-universal\bin\orbit.cmd" update --channel stable --check
& "$HOME\.orbit-universal\bin\orbit.cmd" update --channel stable
& "$HOME\.orbit-universal\bin\orbit.cmd" update --channel stable --apply

# Scoped uninstall from the original verified v0.30.0 Universal Setup directory:
py -3.12 orbit_setup.py uninstall --scope machine --hosts antigravity codex
py -3.12 orbit_setup.py uninstall --scope machine --hosts antigravity codex --apply
```

Use `--scope project --project "C:\absolute\path\to\project"` to act on exactly one workspace. Uninstall preserves SQLite, checkpoints, shared runtime and other MCP registrations; do not use the separate destructive `clean` path for normal uninstall.

## New published-release-aware CLI: next release, not v0.30.0

Work in progress on a separate feature branch: same `orbit` command will manage **install, update, uninstall** from a selected published release. The permanent CLI will choose newest **stable** by default, support `--version X.Y.Z` and `--channel candidate`, verify released ZIP SHA256 and refuse an unpublished version. No action applies without `--apply`.

```powershell
# From a future checksum-verified Universal Setup ZIP:
.\Orbit.ps1 install --hosts antigravity codex
.\Orbit.ps1 install --hosts antigravity codex --apply

# Once that newer version is installed:
& "$HOME\.orbit-universal\bin\orbit.cmd" update --check
& "$HOME\.orbit-universal\bin\orbit.cmd" update --version X.Y.Z --hosts codex
& "$HOME\.orbit-universal\bin\orbit.cmd" uninstall --version X.Y.Z --hosts codex
# Add --apply only after reviewing the preview/selected release.
```

If your PowerShell policy blocks local `Orbit.ps1`, run `py -3.12 orbit_cli.py` with the same arguments from the verified ZIP instead; no global policy change is needed.

For macOS/Linux use `python3 orbit_cli.py install ...` from the official future Universal ZIP, or the installed `~/.orbit-universal/bin/orbit` launcher. The `--version` switch is pinned to the selected release and is not a request to download arbitrary Git commits. An explicit downgrade remains a separately reviewed compatibility risk.

**Limits:** CLI preview checks release metadata and ZIP integrity without executing downloaded installer code. To see exact target file actions for a published ZIP, extract and run its `orbit_setup.py install/uninstall` **without** `--apply`. The CLI `--apply` boundary authorizes verified released installer code and may still fail closed on an owner-customized path. Backups are necessary; releases are not automatically reversible.

## Separate packages

- **Universal Setup ZIP:** one installer for the currently supported local coding hosts.
- **Antigravity Plugin ZIP / Plugin Suite ZIP:** alternative host-specific/native distribution layouts; don't layer them blindly over the same existing custom installation.
- **Claude Desktop `.mcpb`:** installed and updated through its desktop extension workflow, **not** automatically installed by the local Python launcher.
- **ChatGPT/other remote plugins:** separately distributed by their host platforms; not a local Orbit CLI target.

## Maintainer release process

[RELEASE-PROCESS.md](RELEASE-PROCESS.md) governs source/version parity, candidate branches, reviews, exact-head CI, genuine IDE acceptance, owner approval and immutable GitHub release publication. Release automation reads the exact changelog version section; never republish or retag old versions to change instructions.
