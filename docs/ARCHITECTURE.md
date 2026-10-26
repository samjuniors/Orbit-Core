# Architecture / source authority

Reviewed against development candidate `84ac7dd` on 2026-10-26. This describes
implemented behavior, not a claim of production or desktop acceptance.

## Runtime and host boundary

Orbit Core MCP is a local orchestration service for a coding host. The host owns
model inference, code edits, terminal execution, specialist agent invocation,
and permission enforcement. The Python stdio server exposes 29 tools:

| Module | Responsibility | Important boundary |
| --- | --- | --- |
| `orbit_mcp.py` | JSON-RPC, validation, SQLite memory, project scan/resume, checkpoints | No model inference; memory is keyed by caller-supplied project slug |
| `orbit_intake.py` | Persistent project classification, choices, autonomy review, doc inventory | User consent is host-reported; doc discovery is a filename heuristic |
| `orbit_tasks.py` | Task dependencies, writable-scope reservations, reports and reviews | Does not launch agents, inspect Git, enforce filesystem access or verify host session IDs |
| `orbit_capabilities.py` | Local skill/config inventory and keyword-based selection | Configured does not mean connected; no installation or execution |
| `orbit_preview.py` | Approved dev-process launch, HTTP probes, logs and stop | Process handles live only in this MCP session; project commands are not sandboxed |
| `orbit_browser.py` | Optional installed Playwright browser, bounded DOM actions, screenshots | Loopback HTTP request policy is not an OS network sandbox or visual/security audit |
| `orbit_build.py` | Durable revision-checked PLAN → IMPLEMENT → PREVIEW → BROWSER_QA → REVIEW → CHECKPOINT → DONE | Records progress; does not run an autonomous repair loop |

`source/agents` and `source/skills` supply host instructions. Agent definitions
are not evidence that an agent executed. `installer.py` adapts these instructions
and merges selected host configuration; `orbit_cli.py` detects likely hosts and
previews checksum-checked release updates.

## State and verification

SQLite lives outside the repository in the OS app-data directory (or an explicit
`ORBIT_LOCAL_DB`). Task, intake and build records include project roots; memories
currently use project slugs only. Avoid reusing a slug across unrelated projects.
This is local organization, not authenticated multi-tenant isolation.

Specs and ADRs remain in their original projects. `.orbit/STATE.md` owns the
bounded Orbit checkpoint section and uses an expected content hash. Its file
write is not cross-process locked or transactional with SQLite.

The PREVIEW gate requires a ready Orbit-managed process. BROWSER_QA requires a
stored passing result with actions. These results are not yet bound to a source
revision, preview generation or acceptance-spec hash. PLAN, IMPLEMENT and REVIEW
remain caller-reported; CHECKPOINT checks for a managed marker, not complete
build-specific proof. A DONE record is therefore not a production certification.

Build stages survive restart; preview process ownership does not. There is no
background agent, durable worker supervisor, public tunnel or hosted deployment.
Optional external browser tools provide supplemental host evidence and cannot
currently satisfy the internal Playwright gate.

## Source and distribution

This repository owns the independent local MCP runtime and installer. The
separate ChatGPT plugin and `samjuniors/orbit` CLI have separate source/release
boundaries. Neither is implicitly updated or integrated by a commit here.

Runtime Python files are canonical. `scripts/build_desktop_extension.py` refreshes
the candidate desktop archive from those files while preserving its manifest;
tests check byte-for-byte runtime parity. Rebuild and test before preparing a
release. No version is published by that script.

See [next milestones](NEXT-VERSION.md) for prioritized gaps and acceptance gates.
