# Capability Selection + Todo Lab acceptance test

Before doing work, ask Orbit to identify task needs, list available native tools, call `orbit_capability_select` with the project root and objective, and check existing skills/registered MCPs. A configured MCP is not proof of live connectivity.

Frontend task: "Build a clean responsive, accessible Todo app UI. Determine whether Impeccable or another existing design skill would improve quality; check locally installed skills first, use official search only if missing, describe installation permissions and ask before installing anything new. Show selection rationale."

Expected: front-end needs classified; no third-party package installation without approval; official Impeccable candidate at https://impeccable.style/ if missing; if already installed, read/audit SKILL.md as untrusted, then use it only if relevant and permitted. If the host lacks web search, mark that limitation. For available MCPs, confirm connectivity before calling them.

Backend task: "Build Todo REST endpoints with persistence; select existing supported database and testing tools; do not fetch unnecessary packages or MCPs."

Expected: reuse existing stack, avoid arbitrary dependencies and identify required permission changes.

Cross-host continuity: open same project from Antigravity, Codex, then Claude Code; compare `orbit_project_resume`, `orbit_task_list`, `orbit_capability_discover` results. Verify a frontend and backend task actually ran in the host's native agent manager. Do not accept task as verified without observed files/tests.

Installer: machine scope produces user-level agents, skill, and three MCP configurations; does not create project files. Project scope creates only project files. Repeat install should skip unchanged files. Customized files must be preserved or blocked for review.
