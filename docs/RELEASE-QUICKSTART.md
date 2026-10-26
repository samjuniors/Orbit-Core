# Release and installation quickstart

**This page describes the v0.24.1 candidate.** Do not try to download it until a maintainer has published the tag and attached verified release assets.

## User: install once

Download `ORBIT-Universal-Setup-v0.24.1.zip` plus its `.sha256` from [GitHub Releases](https://github.com/samjuniors/Orbit-Core-MCP/releases). Verify SHA256, extract, and run `py -3 install_orbit_gui.pyw` on Windows. Choose detected IDEs, preview changes, approve the installation and refresh the IDE's MCP list. Existing apps and SQLite records are preserved. Machine-wide means current OS user's host configuration, not Administrator-level installation.

Then run in PowerShell:

```powershell
& "$HOME\.orbit-universal\bin\orbit.cmd" doctor
& "$HOME\.orbit-universal\bin\orbit.cmd" update --check
& "$HOME\.orbit-universal\bin\orbit.cmd" update --apply
```

Default update channel is `candidate` for 0.x prereleases. No PATH edit is necessary. `--channel stable` is available when verified stable versions exist. Before `--apply`, `update` without that flag previews. Follow GUI/manual-review conflict instructions rather than deleting customized files.

## Maintainer: publish an immutable candidate

Merge reviewed tested code to `main`; then in GitHub **Actions → Publish versioned release** run the workflow from `main` with VERSION `0.24.1`. It verifies tests, builds ZIP, checks SHA256, creates immutable tag `v0.24.1` if necessary and publishes the ZIP, sidecar, Desktop `.mcpb` and sidecar. By policy 0.x releases are **prerelease candidates**. Do not publish or assert full production readiness without real host acceptance.

See [full release policy](RELEASE-PROCESS.md) and [README](../README.md).
