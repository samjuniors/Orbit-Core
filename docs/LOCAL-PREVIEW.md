# Orbit Local Preview Manager — v0.24.0 vertical slice

Status: feature branch, not a published stable release.

## Purpose
From the agent host, preview a proposed command, ask approval, run a local app server, check that a loopback HTTP endpoint actually responds, inspect bounded logs and stop the spawned process. This does not build the app or drive a browser automatically.

## Example, Vite Todo app
1. First inspect project scripts and dependencies, including `package.json` and locks. Trust the source before running.
2. Call `orbit_preview_start` with `project_root` an existing absolute project folder, `preview_id: "todo-ui"`, `command: ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", "5173"]`, `port: 5173`, `health_path: "/"` and `confirm_run: false`.
3. Display the exact command and request the host's real execution approval. Re-call with `confirm_run: true` only if approved.
4. Inspect `orbit_preview_status`. A READY response means only localhost HTTP readiness, **not** that UI/UX or functionality tests passed. Copy the returned `http://127.0.0.1:5173/` into the IDE browser.
5. Use host-native browser or Playwright after separate review to test real Todo behavior, mobile layout, console/network errors. Save screenshots as evidence only if actually produced.
6. Call `orbit_preview_stop` with `confirm_stop: true` before closing the MCP session when possible.

## Security and limitations
- `shell=False`; only recognized development runtimes allowed; preview commands are still potentially dangerous project code. User + host must approve execution.
- Orbit only probes `127.0.0.1`. The supplied app script might ignore HOST and listen on a public interface; verify its flags/implementation before approving. No tunnels and no deployments.
- Preview IDs and ports are scoped to the chosen local directory. The MCP tracks at most three processes in memory per server session. A restarted MCP cannot safely stop or adopt the old process; close it manually with the IDE/OS if needed. Persisted supervisor work is planned.
- Session logs live under the user's `.orbit-universal/preview-logs` directory or explicit `ORBIT_PREVIEW_LOG_HOME`. Logs may include secrets printed by apps—do not check them into Git.
- HTTP readiness checks only, not actual visual browser QA, security scanning, functional tests, health of other services, or remote link sharing.
- Do not run the preview manager against untrusted projects or privileged environments.

## Acceptance
`python -m unittest discover -s tests -v`, `python scripts/check_version.py`, and `python scripts/build_release.py --verify`. The preview integration tests start a real loopback server, check readiness, logs, foreign-port refusal and stop it.
