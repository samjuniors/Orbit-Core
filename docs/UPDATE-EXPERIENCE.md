# Orbit install-once update experience

**Status:** source implementation on a feature branch; public installers do not gain this feature until the owner approves a newer published release and existing installations update to that version once. This document is not evidence of real IDE UI integration.

## What an installed user sees

1. Orbit's local stdio server starts without waiting for the internet. At most once every 24 hours, an **asynchronous metadata-only check** looks up published GitHub releases on the chosen channel (default `candidate`). It does not download installer code, open project files or apply changes.
2. On `orbit_project_resume`, if the cache says a newer **published** version exists, the server adds a structured `update_notice` with version, official release page and `orbit manager` action. The coding host can show **Update / Later** if that host has real interaction controls; otherwise it should show the notice in plain chat and not invent UI.
3. Users can ask **“Orbit, check for updates”**: `orbit_update_status(refresh=true)` only fetches public metadata; it never runs an installer. The host can show a suggestion but must not execute updates automatically as part of MCP handling.
4. The user opens the persistent launcher: **`orbit manager`** (or uses the **Manage updates** button in Orbit Universal Setup). Without PATH configuration, Windows users can double-click `%USERPROFILE%\\.orbit-universal\\bin\\Orbit Update Manager.cmd`; macOS/Linux users can launch `~/.orbit-universal/bin/orbit-manager`. This launcher is installed in the current user's home and survives disposal of the original ZIP. The manager checks the release channel, lists the installed version, permits selection of machine scope vs one approved project, and shows supported hosts. It has **Check for updates** and **Install update** buttons.
5. **Install update** requires a real confirmation dialog naming the exact selected release, hosts, scope and security limitations. The updater pins the approved release version and rechecks it before downloading. It validates SHA256 and ZIP member safety, previews code without executing it, and runs the package installer only after approval. Recognized stock changes receive backups. Unknown customized files cause a hard stop, not a forced overwrite.
6. Restart or refresh the relevant IDE's MCP server to load the new runtime. If the host or Windows installer cannot restart automatically, Orbit must say so rather than silently restarting active user projects.

## Multiple hosts, platform and edition boundaries

- **Windows/macOS/Linux local Python installation:** same Orbit Manager and universal installer approach. Machine scope updates chosen local host configurations in one action. Project scope updates **one selected project**; it is not yet a batch registry of every project on disk.
- **Antigravity, Codex, Claude Code and VS Code:** managers control their installed local Orbit MCP + skill configuration, but each host decides whether to show an update button and how to restart. Do not claim native IDE toast notifications are present unless implemented and tested per host.
- **Claude Desktop packaged `.mcpb`:** distributed separately as a desktop extension; host-supported extension updating must be tested before claiming a single MCP update also replaces an installed desktop extension. The manager currently updates local installer-supported hosts, **not** installed desktop extensions.
- **ChatGPT plugin / connector users:** these are managed by their application/platform and cannot be updated by a local Python installer. A separately deployed ChatGPT plugin needs its own review/publishing path.
- **Other OS users / shared computers:** updates apply to the current OS user/profile and approved workspace, not other OS accounts or administrator-managed installations.
- **Machine-wide local installation** is per-user *configuration across projects*, not privilege-elevated installation for all accounts.

## What's New and older versions

- On update availability, Orbit shows the **official published release notes** before installation in its local Update Manager, including a bounded preview in the confirmation dialog. `orbit update --check` also displays a bounded, control-character-safe release description, and MCP `orbit_update_status` may supply an abbreviated `whats_new` field as **untrusted display-only data**. If published notes are missing, show that fact rather than invented feature benefits.
- **Older versions** in the manager and `orbit versions` open the official GitHub Releases archive, where v0.23.0 and v0.24.1 remain downloadable with checksums. This button/command must not execute downgrades, replace installed files or automatically change update channels.
- **Default:** update to the newest approved published version in the chosen channel. Older versions are an optional user-controlled recovery path, not the default. Before an older version is installed, explicitly review compatibility with SQLite/checkpoints, back up projects/user data and verify the older archive/checksum. There is currently no automatic data-schema downgrade or click-to-rollback guarantee.

## Channels and preferences

- `ORBIT_UPDATE_CHECK=0` disables automatic MCP update metadata checks and notices. The user can still open the manager manually.
- `ORBIT_UPDATE_CHANNEL=stable` shows stable-only releases in MCP notices; `candidate` is the default while Orbit is at v0.x.
- The cache at `~/.orbit-universal/update-status.json` contains only the last check time, release version/channel/link and failure status; never model chats, project memory, secrets or credentials.
- No automatic scheduled service, cron job, web sockets or external notifications. **Checks happen while Orbit is running**; no promises when the app is closed or offline.
- A release advertised by GitHub is not necessarily safe: SHA256 verifies bytes against release-published digest but does not authenticate the publisher. Before broad rollout, Issue #9 still requires trusted provenance/signing, real-host and upgrade acceptance.

## Acceptance before public release

- New user: first install once, open manager, see no update when current; not prompted for an unreleased main commit.
- Existing user from v0.24.1: **one transitional update** to a future published version that bundles the manager and runtime notification module, then subsequent updates require no repeated ZIP downloads or installer wizard.
- Newer published version: cached notice appears in Orbit project resume, while user receives no host pop-up unless the host supports one; explicit manager click installs selected host with backup; opening a new session runs new version.
- Offline or GitHub rate limited: app starts normally and shows no false update success; graceful error on check; no downloaded code or missing database.
- Unknown/customized files, untrusted ZIPs, missing publisher proof, mismatched pinned version, symlinked paths: fail closed with review instructions.
- Linux/Windows CI coverage of metadata cache, opt-out, publication eligibility, pinned release and installer package; actual GUI/IDE host flow remains unverified until manual evidence exists.
