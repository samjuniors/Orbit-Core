# Orbit v0.25.1 — Release acceptance checklist

**Status: PUBLISHED PRERELEASE on 2026-10-29; production certification still HOLD.** GitHub Release [`v0.25.1`](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.25.1) contains all four ZIP/MCPB/checksum assets. The source version and successful CI are not independent attestation of host approvals, real GUI interactions, cross-PC migration, or Issue #9 security closure. This checklist is a historical acceptance ledger with open post-publication verification.

## Published release and older version controls
- [ ] Confirm the v0.25.1 `CHANGELOG.md` section accurately states new features, fixes, security warnings, and limits. `.github/workflows/release.yml` uses this section as the published GitHub Release description.
- [x] Published GitHub Release has four versioned ZIP/MCPB/checksum assets and release notes ([release](https://github.com/samjuniors/Orbit-Core/releases/tag/v0.25.1), [successful publication workflow](https://github.com/samjuniors/Orbit-Core/actions/runs/40832407417)). This confirms publication, **not** provenance signing.
- [ ] Verify the **Older versions** link from the GUI and `orbit versions` open the official `https://github.com/samjuniors/Orbit-Core/releases` archive and **do not** invoke a downgrade or execute installer code.
- [x] v0.23.0 and v0.24.1 remain listed with release assets, alongside v0.25.1 (checked 2026-10-29); do not repoint, replace, or hide older tags.
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

## Real IDE installer/update acceptance (each separately; distinct from M1/M2 native-task tests)
| Host | Update notice shown (native action or text) | Backup-first update, real session restart | Status |
| --- | --- | --- | --- |
| Antigravity | NOT RUN | NOT RUN | HOLD |
| Codex | NOT RUN | NOT RUN | HOLD |
| Claude Code | NOT RUN | NOT RUN | HOLD |
| VS Code + MCP extension | NOT RUN | NOT RUN | HOLD |
| Claude Desktop MCPB | Separate extension update workflow **not implemented** | NOT RUN | HOLD |
| ChatGPT connector/plugin | Managed by ChatGPT platform; local CLI cannot update | NOT RUN | HOLD |

## M1/M2 host-functional acceptance — owner-reported (NOT independently attested)

- **Antigravity: REPORTED PASS.** Owner reported native delegation, Todo execution/testing, research save/readback and restart/resume. This is not proof of native permission attestation or actual installer/update GUI acceptance.
- **Codex: REPORTED PASS.** Owner reported native delegation, 14 regression checks, `todo-filter-codex` REVIEW_ACCEPTED revision 5 and recovery of checkpoint/source files after restart. This is not independently verified CI provenance for the host actions.
- **Cross-PC data transfer: NOT VERIFIED.** The merged `orbit_project_transfer` (PR #22) only establishes implementation and automated checks; actual two-machine export/import and destination-native delegation remain untested. No imported approval is transferable.
- **Scope:** M1/M2 core host-functional milestones are **OWNER-ACCEPTED**; Issue #9 threat-model checks, broader fallback/denial paths and M3 independent QA remain open. See [roadmap](NEXT-VERSION.md).

## Automated evidence
- [x] GitHub `main` CI passed 5/5 (Ubuntu Python 3.10–3.13, Windows Python 3.12) at commit `47f3721` ([run #40818364910](https://github.com/samjuniors/Orbit-Core/actions/runs/40818364910)); separate versioned publication workflow passed ([run #40832407417](https://github.com/samjuniors/Orbit-Core/actions/runs/40832407417)).
- [x] Versioned release completed with v0.25.1 ZIP, MCPB and SHA256 assets; release notes report 40 MCP tools. Full real-host inventory is a separate acceptance condition.
- [x] CI includes disposable installation, protocol/tool inventory and prior-tag stock upgrade checks on Linux/Windows. Released inventory is **40 tools**, not the older 36-/39-tool candidate count; customized-profile and physical GUI tests remain open.
- [ ] Update/older version/release notes unit tests pass (publisher notes bounded, no draft or incomplete asset eligible, no implicit downgrade, no code download on status).
- [ ] Outstanding Issue #9 AUD-01 verifiable publisher origin, AUD-24 host-attested approvals, AUD-25/27 root-scoped security and AUD-28/30 browser/Windows command safety, macOS and actual IDE GUI host tests addressed or explicitly accepted by release owner.

**Current status: PUBLISHED PRERELEASE; broader security/production acceptance HOLD.** Do not claim publisher signing, native host permission attestation, real GUI/update acceptance, cross-PC transfer or compatibility-verified rollback without separate evidence. Issue #9 remains open.
