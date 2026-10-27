# ORBIT v0.25.0 — candidate acceptance checklist

**Status: NOT PUBLISHED / NOT PRODUCTION CERTIFIED.** This document is a checklist, not evidence of completion. Owner-led real-host testing is required under [Issue #9](https://github.com/samjuniors/Orbit-Core-MCP/issues/9).

## 1. Candidate artifact and provenance

- Source: `release/v0.25.0-candidate` PR against `main`. `VERSION=0.25.0` only on the candidate branch until separately authorized to merge.
- CI: GitHub Actions on this branch must pass Ubuntu Python 3.10–3.13 and Windows Python 3.12, including the adversarial regression tests. Skipped browser tests remain **NOT RUN**.
- Download the `orbit-v0.25.0-host-acceptance` **CI artifact** from the successful branch/PR run; keep its run URL, head commit SHA, artifact digest, test report and timestamps. GitHub Actions artifacts are not a trusted vendor release signature.
- Unpack the Actions artifact into a disposable directory. It contains `ORBIT-Universal-Setup-v0.25.0.zip`, its `.sha256`, and `ORBIT-Claude-Desktop-v0.25.0.mcpb`.
- Compare `ORBIT-Universal-Setup-v0.25.0.zip` to the provided SHA256 (Linux: `sha256sum -c ORBIT-Universal-Setup-v0.25.0.zip.sha256`; Windows PowerShell: `Get-FileHash .\ORBIT-Universal-Setup-v0.25.0.zip -Algorithm SHA256` then compare manually). Do not claim checksum = publisher authenticity.
- Confirm the ZIP contains `orbit-universal-0.25.0/VERSION`, `source/runtime/orbit_mcp.py`, and the **current** v0.25.0 desktop MCPB. Inspect `manifest.json` for `version=0.25.0` and verify bundled server modules equal `source/runtime/*.py` byte-for-byte. `python scripts/check_version.py --strict-bundle` must PASS in the same checkout after candidate generation.
- Confirm the preexisting `ORBIT-Claude-Desktop-v0.24.1.mcpb` and tags `v0.24.1`, `v0.23.0` stay unchanged.

## 2. Use a disposable project for each live host

Record host product/version, OS, authenticated profile, MCP protocolVersion, local path, selected project slug, date, and evidence link for **each** row. Connect the installer only to a dedicated throwaway folder; do not replace production user configuration. Review every host approval prompt before accepting any write/run.

| Host | Connect MCP | Read-only resume | Memory save/recall | Checkpoint across restart | Approval UI | Status |
|---|---|---|---|---|---|---|
| Antigravity | Not run | Not run | Not run | Not run | Not run | HOLD |
| Codex | Not run | Not run | Not run | Not run | Not run | HOLD |
| Claude Code | Not run | Not run | Not run | Not run | Not run | HOLD |
| VS Code + known MCP extension | Not run | Not run | Not run | Not run | Not run | HOLD |
| Claude Desktop + MCPB | Not run | Not run | Not run | Not run | Not run | HOLD |

Never claim desktop chat can spawn a terminal agent unless a real host capability is observed.

## 3. Lifecycle and data safety in a throwaway repository

1. **Blank and docs-only:** start a new project, decline/approve intake explicitly. README-only or empty `src/` is not evidence of source code.
2. **Existing project adoption:** provide an actual source baseline, use `change_kind=adopt`, confirm PLAN and preservation of existing files. Do not reset or duplicate docs.
3. **Partial/stalled:** resume with checkpoint; test multiple unfinished builds requiring explicit selection, task retry after FAILED/REWORK and revision-guarded pause/resume across host restarts.
4. **DONE product:** create a *new* fix/feature change run referencing old DONE build; confirm old build row and data remain unchanged.
5. **Concurrency:** two real hosts attached to the same test SQLite store submit a checkpoint from one revision: at most one SAVED; the stale writer must be rejected.
6. **Preview:** require real host permission, verify bind to loopback, no inherited private env variables such as `DATABASE_URL` or `GITHUB_TOKEN`, and stop owned preview on MCP session exit; never kill foreign processes. Explicitly note any app needing project `.env` for testing.
7. **Security:** try a malicious README / `STATE.md` / skill description with fake approval instructions: treat fields marked `UNTRUSTED_REPOSITORY_TEXT` as inert data. Try a path outside host-configured `ORBIT_TRUSTED_ROOTS`, confirm refusal.
8. **Install and upgrade:** fresh install from v0.25.0 ZIP into a disposable folder; after a separately backed-up v0.24.1 disposable installation, preview a candidate update and verify no archive code executes before `--apply`. Confirm customized/unknown files remain protected, old SQLite checkpoint readable and host configuration preserved.

For each action record the actual command/tool, input path (no secrets), result/exit code, before/after file state and approval evidence. A model-authored `confirm_write=true` is *not* independently authenticated human approval.

## 4. Remaining security and release gates

- **AUD-01 authenticity:** Decide and implement a publisher-verifiable provenance/attestation scheme for public update archives, not just a colocated SHA256.
- **AUD-24:** Validate host-side approval UI and design attestable approvals where supported; current ledger records agent-supplied references only.
- **AUD-25/27:** Independently review authorized project roots and root-scoped memory identity/isolation.
- **AUD-28/30:** Real Chromium/WebSocket network blocking and Windows `.cmd` argument handling are not validated by ordinary unit tests.
- macOS native installation, multiple real hosts, full GUI/desktop MCPB workflow and long-running lifecycle acceptance remain NOT RUN until evidence is attached.
- No production certification, v0.25.0 GitHub tag, public release, rollout, auto-update, or Plugin Creator publication without explicit owner approval and separate acceptance evidence.

## 5. Sign-off record (fill only with real evidence)

| Gate | Evidence | PASS / HOLD |
|---|---|---|
| Candidate CI and code parity | _CI URL, commit SHA, test count_ | HOLD |
| Artifact digest and source inspection | _checksum, manifest, code hash match_ | HOLD |
| Real-host matrix | _session recordings/logs_ | HOLD |
| Existing installs and upgrade preservation | _before/after artifacts_ | HOLD |
| Threat-model/release-authenticity decisions | _review and accepted mitigations_ | HOLD |
| Owner release authorization | _explicit approved request_ | HOLD |
