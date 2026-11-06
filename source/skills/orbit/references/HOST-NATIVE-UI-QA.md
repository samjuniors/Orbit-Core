# Host-native UI testing in Orbit Core (v0.32 development candidate)

Orbit coordinates app testing but does **not** own Codex's desktop, browser, Computer Use, Chrome, or tool permissions. Prefer tools already exposed by the **active coding host**. A Codex desktop Browser/Computer integration is not automatically available to Codex CLI or to an MCP stdio server. Never launch an unrelated Codex session as a substitute for the real host.

## Host decision

1. Inspect the project, actual host tool inventory and existing signed-in UI capabilities. Use `orbit_capability_select` for a read-only browser recommendation. A plugin name, installed package or MCP registration does not prove interactive tool access.
2. For eligible Codex desktop users, open the in-app browser from the Codex/ChatGPT desktop UI (Ctrl+Shift+B on Windows) and grant page access only as needed. Browser Use and Computer Use availability depends on the installed plugin, plan, workspace and user's consent. Computer Use accesses desktop apps; browser tools are preferable for web pages. Codex CLI cannot be assumed to share the desktop plugin's tool registry.
3. Launch an Orbit-managed loopback app preview after user-approved code execution. Only the exact returned `http://127.0.0.1:PORT/` is in the proposed test scope. Before browser actions, obtain host-specific permission. A denial or unknown permission is a HOLD, not permission to try a different browser.
4. Perform real UI actions and read the actual result, including a screenshot (or host screenshot reference) and an interaction assertion. Check layout, clicks, input, error/empty states, responsiveness and console/network errors where the actual host makes them available. Browser/Computer actions may be image-based or DOM-based; do not invent unsupported CDP or inspection abilities.
5. At BROWSER_QA, send `orbit_build_advance` with `host_browser_qa` only after actual host execution. This is a source- and preview-pinned, **caller-reported** evidence record; Orbit cannot independently attest the host session, screenshot, host approval or network isolation. A PASS prepares later review, **not a security certification or deployment authorization**.

## Codex desktop's real plugin bridge (Windows acceptance, 2026-11-06)

The **bundled** Codex desktop plugins have their own host-native setup. On the owner's Windows PC, `codex plugin list` reports `browser@openai-bundled`, `computer-use@openai-bundled`, `unified-computer-use@openai-bundled` and `chrome@openai-bundled` as installed/enabled. This is **local inventory only**; the Codex desktop task still needs the plugin's actual JS bridge and permission.

- **Browser** uses the host-provided Browser plugin skill `control-in-app-browser` and its documented JS tool bridge (typically `mcp__node_repl__js` in an eligible desktop session). The agent must load the bundled host skill, initialize its own supported browser runtime and use that runtime's actual page and screenshot APIs. Do **not** expect a generic `browser_click` command.
- **Windows Computer Use** uses the host-provided `computer-use` skill and its supported JS runtime, not a universal `computer_use_click` MCP command. The bundled unified mode may expose `mcp__cua_repl__js`. Do not launch the internal helper executables directly or copy the proprietary runtime into Orbit.
- Orbit's capability selector accepts **host-reported** `host_plugins` alongside `host_tools`. For example, only **if the active Codex desktop session itself confirms them**, the caller may report `host="codex"`, `host_plugins=["browser@openai-bundled"]`, `host_tools=["mcp__node_repl__js"]`. `HOST_PLUGIN_BRIDGE_REVIEW_REQUIRED` is an initialization/permission check, not a working browser or a PASS. A plugin without its runtime tool (or a bare runtime tool without its plugin) is not a verified provider.
- Codex CLI and IDE extension do **not** automatically provide Codex desktop's built-in browser, even if the machine-wide plugin inventory shows it installed. Keep the native test in an authorized Codex **desktop** thread and follow the host's actual Browser/Computer skill. Do not switch to CLI or Playwright to work around a denied browser permission.

This is host integration guidance, not an Orbit dependency on proprietary Codex code. In other hosts, use only their genuinely exposed native tools. Never infer a permission grant from `codex plugin list` or from a process named Computer Use.

## Host report fields

`host_browser_qa` is an object with exactly these keys:

| Field | Meaning |
| --- | --- |
| `provider` | One of `host_browser`, `host_browser_use`, `host_computer_use` |
| `tool_name` | Exact native host tool used; never invent an API name |
| `session_reference` | A real host thread/session identifier, caller-reported |
| `screenshot_reference` | Host screenshot artifact path/ID, caller-reported; do not paste secrets |
| `observed_url` | Exact Orbit-managed preview root URL |
| `approval_reference` | Actual scope-specific user/host approval reference, caller-reported |
| `permission_state` | Must be `APPROVED` from an actual host authorization; DENIED/UNKNOWN must HOLD |
| `actions` | Two to twenty `{kind,status,observation}` records, all PASS, including an interactive action and separate UI check |

A recorded action `kind` may be `click`, `fill`, `type`, `press`, `scroll`, `navigate`, `assert`, `inspect` or `screenshot`. At least one of click/fill/type/press/scroll and one of assert/inspect/screenshot are required. `observation` must identify what the actual host saw, not what it hoped would happen.

The ordinary `orbit_build_advance` fields also require `project_root`, `project`, `build_id`, `expected_revision`, `outcome=PASS`, `evidence`, `preview_id` and `confirm_write` (after preview/approval). A changed code fingerprint, stale build revision, stopped preview or wrong origin HOLD. The result records `host-native-browser-caller-reported`, not `browser-tool`. Integration review stays `READY_FOR_INDEPENDENT_REVIEW`, with unverified host flags.

## Existing Playwright option

If no suitable host tool exists **and a new permission has been given**, Orbit's own `orbit_browser_qa` uses the installed Python Playwright package with local Edge/Chrome/Chromium, strict loopback HTTP/WebSocket routing and a real screenshot. This remains a separate, stronger locally executed QA record. Orbit does not auto-install Python dependencies, import Codex's browser session, attach a private Chrome/CDP profile or grant Windows accessibility/screen permissions.

## Verification and recovery

Use a disposable local app first. Inspect actual host event logs, the screenshot, UI assertions, current code and permissions. Test a deliberately failing assertion; do not record PASS. Modify source after a successful test and verify the old record cannot be reused. Stop/start the preview and confirm stale sessions HOLD. In a permission-denied case report BLOCKED and request fresh approval. For desktop/mobile apps, use their respective NATIVE_QA lifecycle, not a pretend web preview.

Official references:
- [Codex plan and browser guidance](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan)
- [Built-in browser](https://help.openai.com/en/articles/20001277-using-the-built-in-browser-in-the-chatgpt-desktop-app)
- [OpenAI computer-use integration and verification](https://developers.openai.com/api/docs/guides/tools-computer-use)
