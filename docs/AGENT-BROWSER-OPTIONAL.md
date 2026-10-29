# Optional Vercel Labs agent-browser — host-aware browser QA fallback (M3)

Official source: https://github.com/vercel-labs/agent-browser
License: Apache-2.0. This is third-party tooling and not redistributed by Orbit.

## Purpose and boundary

- An optional **host-connected MCP or already-installed CLI** provider for semantic accessibility snapshots,
  browser interactions, responsive viewports, screenshots and UI review.
- Orbit continues to own local preview, task ledger, build stage, and checkpoint.
- Antigravity/Claude/Codex host owns model actions, approvals, and actual provider calls.
- Never treat a configured MCP as connected, nor its claimed PASS as a recorded
  Orbit Playwright pass. Existing `orbit_browser_qa` remains the gate for
  BROWSER_QA in this version; this provider is supplemental pending a verified
  adapter. No new MCP tool is added by this provider-selection feature.

## Host-first provider selection

- Call `orbit_capability_select(objective="orbit-qa: browser testing", host_tools=...)` with the connected host's *actual* tool names. Inspect `browser_workflow` for ordered candidates and readiness. This is a recommendation, not an executable selector.
- Prefer native host browser actions; if unavailable, use approved host computer-use or connected Browser Use actions; then installed local Playwright using Edge/Chrome/Chromium; finally consider this Vercel provider.
- Real host execution is mandatory. Browser navigation, computer screen/click access and provider connections may access private session data; obtain genuine scope-specific consent, prefer an isolated loopback app and do not auto-attach existing user browser profiles, CDP sessions or remote/cloud browsers.
- Even successful native-browser/agent-browser actions are supplemental host evidence. The current Orbit BROWSER_QA gate still requires Orbit-recorded, source- and preview-bound Playwright PASS; report BLOCKED instead of bypassing the gate.
- **M3 local QA network boundary (development branch):** Orbit's built-in Playwright runner only permits HTTP traffic to its own exact `http://127.0.0.1:<preview port>` origin, and WebSockets to the matching `ws://127.0.0.1:<preview port>`. Other loopback ports (including localhost aliases) and external origins are blocked; `data:`, `blob:`, and `about:` inline resources remain usable. WebSocket routing requires Playwright **1.48+**; older versions return a reviewable dependency HOLD instead of a security claim. This does **not** make the browser an operating-system network sandbox: other transports (such as WebRTC), installed extensions and host tools require separate security controls. Real host-browser/Computer Use providers have their **own** permissions and are not controlled by the built-in Playwright routes. Multi-service apps need a separately reviewed explicit allowlist, not a silent wildcard.


## Approval-first installation (optional)

1. Review the upstream README/license/current release and security permissions.
2. With explicit approval, on Windows with npm in PATH:

   ```powershell
   npm install -g agent-browser
   where.exe agent-browser
   ```

   The package installs a CLI and optionally exposes a stdio MCP server via `agent-browser mcp`; a Chrome-compatible browser is also required.
   Upstream documents `agent-browser install` to download Chrome for Testing,
   **but Orbit never runs this**. An existing Chrome/Brave/browser install may
   work; follow upstream docs and inspect any proposed download beforehand.
   Do not confuse this provider with the separate Python Playwright dependency.
3. In Antigravity **Manage MCP Servers -> View raw config**, preserve all
   existing entries, and add a separate sibling entry under `mcpServers`:

   ```json
   "agent-browser": {
     "command": "agent-browser",
     "args": ["mcp", "--tools", "core"],
     "env": {
       "AGENT_BROWSER_ALLOWED_DOMAINS": "127.0.0.1,localhost",
       "AGENT_BROWSER_NO_WEBMCP": "1"
     }
   }
   ```

   This is a **fragment**, not a replacement config. Keep `linear-mcp-server`,
   `rea`, and `orbit-core-native` unchanged. If Windows cannot resolve the
   executable, inspect `where.exe agent-browser` and configure the supported
   installed launcher path; do not use `npx -y` or auto-download scripts.
4. Restart/refresh the host; verify one **real** `agent_browser_snapshot` call
   on an approved Orbit preview before enabling state-changing interactions.
   Never direct the browser to untrusted external domains, use a real Chrome
   profile, attach a CDP-controlled personal browser, inject arbitrary JavaScript,
   enable a remote/cloud provider, or access credentials without
   independent authorization. The allowlist is defense-in-depth, not a full
   process sandbox or file-security boundary. Review app behavior, because
   a localhost web app itself can make outbound requests.

## Suggested usage

- Start the app with the approved `orbit_preview_start` flow and verify READY.
- Open the verified loopback URL with the host's `agent_browser_open` tool.
- Take an accessibility `agent_browser_snapshot`; identify actual selectors.
- After approval, test create/edit/complete/delete/filter with bounded native
  browser actions; capture screenshots at desktop and mobile dimensions.
- Record precise tool names, input, outputs, screenshot paths and failures.
- When testing finishes, close the third-party browser session. Never
  terminate unrelated processes.
- If `orbit_browser_qa` is unavailable, report BROWSER_QA as BLOCKED; optional
  agent-browser screenshots don't bypass this version's evidence gate.

Upstream version, APIs, and Windows launcher behavior may change. This guide
records an integration strategy, not a claim of successful end-to-end host QA.
