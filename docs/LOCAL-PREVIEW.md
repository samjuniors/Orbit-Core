# Orbit localhost preview + real browser QA — v0.24.0 candidate

1. Inspect project scripts and obtain host approval. `orbit_preview_start` with `confirm_run: false` previews the exact argv. Set `confirm_run: true` only after actual permission.
2. Check `orbit_preview_status` == READY for real loopback HTTP health and return its `preview_url`. This does not imply app functional correctness.
3. Create a durable build with `orbit_build_begin`, use revision-guarded `orbit_build_advance` for PLAN/IMPLEMENT and, after READY, PREVIEW.
4. At BROWSER_QA use `orbit_browser_qa` with project, build_id, preview_id, optional viewport (desktop/mobile), actions like `[{"op":"fill","selector":"#task","value":"Test"},{"op":"click","selector":"#add"},{"op":"expect_text","selector":"#list","value":"Test"}]`. First preview, then user/host approve and pass `confirm_run=true`, `confirm_interactions=true`. If Playwright/Chromium is not installed, the tool returns DEPENDENCY_MISSING or FAIL: never mark PASS. It saves a private screenshot and records PASS/FAIL evidence in SQLite. Browser network requests outside localhost are blocked.
5. `orbit_build_advance` on BROWSER_QA PASS requires a stored interactive browser result, preventing caller-only success claims. On CHECKPOINT PASS it requires a real Orbit-managed `.orbit/STATE.md`. The build ledger can be resumed across MCP restarts.
6. `orbit_preview_stop` only manages a preview from the **same live MCP session**. It will not adopt or kill a foreign PID. Close previews before quitting the host; manual OS process cleanup may be needed after crashes. No cloud deployment or public link is implemented.

Run `python -m unittest discover -s tests -v`, `python scripts/check_version.py`, and `python scripts/build_release.py --verify` before release.
