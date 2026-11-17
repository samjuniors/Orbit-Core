# Install, update and uninstall published Orbit Core releases

**Choose your release from [GitHub Releases](https://github.com/samjuniors/Orbit-Core/releases).** Verified on 2026-11-07: **v0.30.0** is the newest stable-channel release, while **v0.31.0** is the newer published prerelease. GitHub `main`, an open PR or CI artifact is **not** an official published release. Neither channel certifies security or production readiness.

## 1. Windows — easiest setup

1. Download **`ORBIT-Universal-Setup-vX.Y.Z.zip`** and its matching **`.sha256`** sidecar from the **same [official release](https://github.com/samjuniors/Orbit-Core/releases)**. Compare the sidecar with `Get-FileHash .\ORBIT-Universal-Setup-vX.Y.Z.zip -Algorithm SHA256`. This proves integrity against the published sidecar, not independent publisher signing.
2. Extract the ZIP and double-click **`Orbit Setup.cmd`**. Windows needs Python 3.10–3.13 with Tkinter (3.12 recommended). Orbit's core MCP does not need administrator rights or its own model/API key.
3. Choose **This computer** (current OS user) or **One project**, select one or more of Antigravity, Codex, Claude Code and VS Code, and review the planned CREATE / UPGRADE / SKIP / MERGE / PRESERVE changes before applying.
4. Save work and restart each selected IDE. Ask the host to **actually call `orbit_project_scan`** and report the tool response and version. Config files or installer success alone do not prove live connection.

**macOS/Linux:** From the verified, extracted ZIP, run `python3 orbit_setup.py install --scope machine --hosts codex` to preview and repeat with `--apply` after reviewing. Use a supported Python 3.10–3.13. For a single existing workspace add `--scope project --project /absolute/existing/project`.

## 2. Windows PowerShell — from the verified ZIP

If you prefer the terminal instead of the setup wizard, from the extracted Universal Setup folder:

```powershell
py -3.12 .\orbit_setup.py install --scope machine --hosts antigravity codex
py -3.12 .\orbit_setup.py install --scope machine --hosts antigravity codex --apply
```

The **v0.31.0 ZIP** also includes `Orbit.ps1` and the release-aware `orbit_cli.py`. Its default channel is **stable**. To install the **exact v0.31.0 published prerelease**, specify both `--channel candidate` and `--version 0.31.0`:

```powershell
.\Orbit.ps1 install --channel candidate --version 0.31.0 --hosts antigravity codex
.\Orbit.ps1 install --channel candidate --version 0.31.0 --hosts antigravity codex --apply
```

If PowerShell policy blocks the local script, use `py -3.12 .\orbit_cli.py` with the same arguments instead. Do not weaken Windows execution policy.

## 3. Update after the first installation (no new ZIP required)

The installer places launchers in `%USERPROFILE%\.orbit-universal\bin` for the current OS account. It does not modify PATH automatically.

**Windows GUI:** Double-click `%USERPROFILE%\.orbit-universal\bin\Orbit Update Manager.cmd` in File Explorer. Select **Stable** (default) or **Candidate**, scope and hosts; check release information and approve. No background install, automatic IDE restart or overwrite of unknown owner customizations.

**PowerShell, from any directory:**

```powershell
# Installed version / local diagnostics:
& "$HOME\.orbit-universal\bin\orbit.cmd" status
& "$HOME\.orbit-universal\bin\orbit.cmd" doctor

# Check the newest published prerelease without installing:
& "$HOME\.orbit-universal\bin\orbit.cmd" update --channel candidate --check

# Check the package and intended scope without executing its installer:
& "$HOME\.orbit-universal\bin\orbit.cmd" update --channel candidate --hosts antigravity codex

# Apply only after reviewing the official release:
& "$HOME\.orbit-universal\bin\orbit.cmd" update --channel candidate --hosts antigravity codex --apply
```

Use `--channel stable` for published stable releases. **Stable is the CLI default; candidate requires an explicit opt-in.** If a newer prerelease is already installed, choosing the older stable channel does **not** silently downgrade it. **Published v0.31 limitation:** an older stable-channel `--check` can return a downgrade-block error even though no update is applied. Use `--channel candidate` to check the prerelease track; [PR #106](https://github.com/samjuniors/Orbit-Core/pull/106) proposes a friendlier read-only result for a future release. `--version X.Y.Z` selects an exact published release on its channel; `--expect-version X.Y.Z` pins an earlier approved check.

**CMD:** Call `"%USERPROFILE%\.orbit-universal\bin\orbit.cmd"` directly with the same subcommand options (omit PowerShell's `&`).

**What preview means:** `--check` fetches public release metadata only. An update without `--apply` checks the ZIP and SHA-256 but does **not run the downloaded installer** or print a complete target-file plan. To inspect each proposed file change without applying, extract the verified ZIP and run its `orbit_setup.py install` or `orbit_setup.py update` **without** `--apply`. The latter reapplies that extracted package, rather than checking GitHub for a newer release.

## 4. Uninstall a selected host; keep project memory

With the v0.31.0 release-aware CLI, preview before removing only selected Orbit host integrations:

```powershell
& "$HOME\.orbit-universal\bin\orbit.cmd" uninstall --channel candidate --version 0.31.0 --hosts codex
& "$HOME\.orbit-universal\bin\orbit.cmd" uninstall --channel candidate --version 0.31.0 --hosts codex --apply
```

Use your **actual installed published release version and its channel**. For a previous v0.30.0 installation, extract its matching checksum-verified ZIP and use `py -3.12 .\orbit_setup.py uninstall --scope machine --hosts antigravity codex` to preview; repeat with `--apply` only after review.

A scoped uninstall preserves shared runtime, SQLite memory, project checkpoints, other MCP services and owner files. The separate `clean` operation may be destructive. There is **no automatic database-schema downgrade**; take compatible backups before considering an older release.

## 5. Which release package?

| Published file | Purpose |
| --- | --- |
| `ORBIT-Universal-Setup-vX.Y.Z.zip` | Recommended one installer for multiple local coding hosts |
| `Orbit-Antigravity-Plugin-vX.Y.Z.zip` | Optional Antigravity-native plugin packaging; not an additional requirement |
| `Orbit-Core-Plugin-Suite-vX.Y.Z.zip` | Alternate multi-host packaging, not required alongside Universal Setup |
| `ORBIT-Claude-Desktop-vX.Y.Z.mcpb` | Separate Claude **Desktop** extension; not updated by the local Python CLI |

The updater verifies a release ZIP against its published checksum, rejects unsafe archives and preserves unrecognized customizations for review. A checksum is **not a cryptographic publisher signature**. Do not use development-branch ZIPs as releases, install extra browser/agent dependencies without approval, bypass IDE permissions, or assume a successful installer enables a native subagent.

**Troubleshooting:** Save work, restart your IDE, run `orbit doctor` from the installed launcher and test a genuine `orbit_project_scan` response. An Antigravity headless command can still be denied by the host's MCP permission policy; use normal scoped approval rather than bypassing it.

More detail: [README quick start](../README.md#quick-start), [update experience](UPDATE-EXPERIENCE.md), [installation options](MCP-INSTALLATION-OPTIONS.md), [release engineering process](RELEASE-PROCESS.md).
