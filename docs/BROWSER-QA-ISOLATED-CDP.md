# Orbit Core — Isolated installed-browser QA (v0.29 experimental candidate)

**Status: Experimental; not yet approved for stable production use. Windows only.**
This adapter is an opt-in, dependency-free local Chrome/Edge browser runner, not a host IDE CUA tool and not an attachment to the user's existing browser or profile.

## Purpose

The existing Orbit browser gate accepts independently executed Playwright browser results bound to the current source, build revision, and managed preview. In the Field Notes P0 acceptance, native host specialists implemented a real application, but Python Playwright was unavailable and installations prohibited. Native CUA screenshots and caller-supplied actions cannot silently replace verified browser evidence.

An explicit isolated-cdp engine is added to the existing orbit_browser_qa MCP tool. Default remains playwright. No new MCP tool or external dependency is added.

## Authorized use

Start a managed local preview with orbit_preview_start, require a READY health check, then call orbit_browser_qa with project_root, project, build_id and preview_id set to the current fixture. Use:

- engine: isolated-cdp (explicit opt-in, never automatically selected)
- browser: chrome or msedge (or auto for installed branded browser)
- viewport: desktop or mobile
- actions: 1–20 bounded click, fill, press, expect_visible, expect_text or expect_count operations
- confirm_run: false for preview; then true only after review of scope
- confirm_interactions: true after host approval of actions

Press supports only Enter, Tab and Escape. No arbitrary JavaScript input, dependency download, production deployment, full browser profile attachment or global host configuration change.

## Evidence and trust

The adapter finds Chrome/Edge only in Windows recognized vendor install paths; it never executes a project-controlled browser binary on PATH. It creates a temporary user-data directory and a fresh headless Chrome/Edge process, opens a short-lived loopback DevTools port, and connects to its single new page target with a checked WebSocket handshake. Its own real browser requests, DOM events, screenshots, JS/console errors and interactions are recorded.

Chrome Fetch request interception restricts HTTP to exactly the current Orbit-owned http://127.0.0.1:PORT origin; cross-origin redirects and different loopback ports are blocked. Network and page-navigation events add fail-closed evidence. WebSocket, worker, service-worker, popup and unsupported browser transports are blocked and/or recorded as failures. A full OS network sandbox is NOT claimed.

The same code fingerprint is checked before and after browser QA. Only a real passing interactive browser result is stored by orbit_build.save_browser with the actual build revision, preview ID and generation, engine and verifier. Existing orbit_build_advance checks remain unchanged and reject stale source, different preview generation, absent actions, blocked hosts and non-PASS results. Screenshots are private Orbit QA artifacts outside the source repository.

**Important security boundary:** Chrome says direct third-party CDP use is unsupported and may change without backward compatibility; CDP is highly privileged. The local ephemeral debugging endpoint is reachable by other local applications during execution. Do not run this experimental adapter against untrusted projects, ordinary user browser sessions, sensitive data or production credentials. Treat it as an opt-in prototype pending additional security/maintenance review, not an assurance that all host-native CUA tools are attested.

## Actual disposable Windows evidence — 2026-11-04

- Original Field Notes copy: DOM assertions and screenshot worked but a missing favicon returned HTTP 404; the console-error rule correctly resulted in QA FAIL.
- Independently modified test copy, with a valid favicon served from the same origin: six real Chrome actions PASS, including fill username, fill synthetic password, click sign-in, and authenticated DOM assertions. Captured a screenshot without Python Playwright or package installation. The original P0 source was not modified.
- Test copy with CSP deliberately disabled only in that copy and an external image request: Chrome Fetch interception blocked example.com, recorded the forbidden hostname and returned FAIL.
- Separate synthetic Orbit build at BROWSER_QA revision 7: real isolated browser PASS was persisted with engine metadata; a temporary CSS source edit made build advancement return HOLD for stale source. Restoring source and retaining the same active preview advanced that synthetic build to REVIEW revision 8. This did NOT change the original Field Notes ledger.

The owner’s real P0 Field Notes project remains BROWSER_QA revision 7 and BLOCKED_BROWSER_DEPENDENCY on its old runtime. The user-reported 12 Python acceptance tests passed independently, but their existing CUA results alone must not be treated as this new browser engine’s passing evidence. Formal REVIEW/CHECKPOINT and MCP restart recovery are still pending.

## Release/implementation limitations

Separate feature branch and code review required; no automatic merge into v0.29 or publication. A future owner decision may hold this high-privilege, unsupported-protocol adapter for a separate experimental version. Cross-platform CI validates ordinary source/tests, but real isolated Chrome was only tested on the connected Windows PC. No Windows symlink-privilege, network adversary, or browser version compatibility guarantee has been established.

References:
- https://chromedevtools.github.io/devtools-protocol/
- https://chromedevtools.github.io/devtools-protocol/tot/Fetch/
- https://developer.chrome.com/blog/remote-debugging-port
