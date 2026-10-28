# Orbit v0.25.1 — Release acceptance checklist

**Status: UNPUBLISHED CANDIDATE.** `VERSION=0.25.1` on `main` is development source, not evidence of a published release or installed version. Last published Orbit installer is v0.24.1. Do not tag, publish, or auto-roll out without external owner release approval and Issue #9's remaining security/host acceptance gates.

## Published release and older version controls
- [x] Confirm the v0.25.1 `CHANGELOG.md` section covers accumulated candidate features, fixes, security warnings, and limits (release candidate branch; subject to final owner review). `.github/workflows/release.yml` uses this section as the published GitHub Release description.
- [ ] After publishing **only with approval**, verify the release has all four versioned ZIP/MCPB/checksum assets and release notes, not only a tag. Before publication this remains NOT RUN.
- [ ] Verify the **Older versions** link from the GUI and `orbit versions` open the official `https://github.com/samjuniors/Orbit-Core-MCP/releases` archive and **do not** invoke a downgrade or execute installer code.
- [ ] Preserve v0.23.0 and v0.24.1 tags/release assets. Do not repoint, replace, or hide these to make the new release appear current.
- [ ] Older version installation or rollback requires user choice, backups, workspace/profile compatibility review and a documented restoration plan; do not assume an older runtime can parse newer SQLite schema or checkpoint documents.

## What's New, notification and safe approval
- [ ] **Fresh user**: full v0.25.1 installer creates installed runtime, persistent per-user Orbit Update Manager launchers and CLI in the selected host. No external AI CLI/PATH change or background service.
- [ ] **Resume, offline**: MCP responds immediately even without network. It may asynchronously refresh *metadata only* once per 24h; tool response never executes/downloads new code. `ORBIT_UPDATE_CHECK=0` disables this behavior.
- [ ] **New published version**: only actual complete, nondraft published GitHub Releases from selected candidate/stable channel produce an update notice; no prompt for a newer unreleased main branch.
- [ ] The notice shows **what's new** from the publisher's bounded release description, plus original release link, and clearly labels it as *display-only data*; absence of release notes must be explicit.
- [ ] Open Update Manager; inspect current and new versions, release notes and known limitations; change selected hosts/project; press Install; verify confirmation repeats version and notable changes.
- [ ] Clicking **Later**, canceling confirmation or closing the manager causes **no** installation. If approved, version pinning rejects a changed remote version; ZIP SHA256 and unsafe member validation are enforced; recognized stock files backed up and customized/unknown files preserved.
- [ ] When a real update starts, GUI cannot close prematurely; after completion, prompt to restart/refresh affected host MCP connections, and report failure without claiming installation success.
- [ ] On Windows/macOS/Linux, test actual UI click behavior, accessibility and app restart. CI-only mock/unit tests do **not** count as a real GUI acceptance.
- [ ] Confirm existing published v0.24.1 clients can use their old `orbit update --apply` for a **one-time transition** to a future approved release containing the new manager, without manual ZIP download. Also confirm old ZIP and old source aren't modified.

## Real IDE acceptance (each separately)
| Host | Update notice shown (native action or text) | Backup-first update, real session restart | Status |
| --- | --- | --- | --- |
| Antigravity | NOT RUN | NOT RUN | HOLD |
| Codex | NOT RUN | NOT RUN | HOLD |
| Claude Code | NOT RUN | NOT RUN | HOLD |
| VS Code + MCP extension | NOT RUN | NOT RUN | HOLD |
| Claude Desktop MCPB | Separate extension update workflow **not implemented** | NOT RUN | HOLD |
| ChatGPT connector/plugin | Managed by ChatGPT platform; local CLI cannot update | NOT RUN | HOLD |

## Automated evidence
- **2026-10-28 baseline:** `main` commit `ba51b1363718cca3539a3820f0e4f06d83a22363` passed all five Linux/Windows CI jobs ([run #40675572257](https://github.com/samjuniors/Orbit-Core-MCP/actions/runs/40675572257)); the candidate branch must pass its own CI before further promotion. These results do not establish IDE/GUI acceptance.
- [ ] 5/5 GitHub CI matrix passes (Ubuntu Python 3.10–3.13; Windows Python 3.12), with source/bundle strict parity and source release ZIP digest check.
- [ ] Release ZIP/Claude Desktop MCPB have v0.25.1 in all package manifests and canonical runtime inventory.
- [ ] Disposable install + JSON-RPC 39 tools and v0.24.1-tag to v0.25.1 stock upgrade rehearsal passes on Linux/Windows.
- [ ] Update/older version/release notes unit tests pass (publisher notes bounded, no draft or incomplete asset eligible, no implicit downgrade, no code download on status).
- [ ] Outstanding Issue #9 AUD-01 verifiable publisher origin, AUD-24 host-attested approvals, AUD-25/27 root-scoped security and AUD-28/30 browser/Windows command safety, macOS and actual IDE GUI host tests addressed or explicitly accepted by release owner.

**Current release gate: HOLD.** No release signing, native host prompt rendering, actual GUI acceptance or compatibility-verified rollback should be claimed based solely on this source branch.
