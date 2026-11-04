# Orbit Core architecture and implementation status

This document describes the **v0.29.0 development candidate** architecture, not a claim of end-to-end production acceptance. Version-specific evidence lives in the `RELEASE-ACCEPTANCE-*.md` records.

```text
Coding host: Antigravity / Codex / Claude Code / supported VS Code
  - Host LLM chooses tools, reads targeted repository evidence, edits source
  - Host-native specialist agents (when actually available) execute scoped work
  - Host permissions govern terminal commands, installs, secrets and Git
       |
  stdio MCP: orbit_mcp.py (47 tools in v0.29.0 candidate; JSON-RPC 2.0)
       |-- SQLite project intake (custom answers, branching decisions, autonomy)
       |-- Project checkpoint (.orbit/STATE.md) + concise recovery state
       |-- SQLite task reservations, ownership, reports and review records
       |-- Build stage ledger, per-type workflows, revision checks
       |-- Read-only capability/model and reusable component suggestions
       |-- Opt-in session-managed loopback preview and Playwright QA
```

## Source modules and trust boundaries

| Module | Implemented | Critical limitation |
|---|---|---|
| `orbit_mcp.py` | JSON-RPC stdio, bounded frame reader, schema-subset validation, local SQLite + checkpoints | Host-reported approval/QA cannot be independently authenticated |
| `orbit_intake.py` | Product classification, recommended/free-form answers, dependent follow-ups, consent references, doc inventory | Profile choices may not automatically reconcile every derived architectural assumption |
| `orbit_decisions.py` | Type-specific stage recommendations, library candidates, model tier advice | Does not browse, install libraries, read live model quotas or change model |
| `orbit_capabilities.py` | Local installed skill/config discovery + curated role preferences | Config file presence is **not** proof an MCP or specialist connected |
| `orbit_tasks.py` | SQLite task ledger, dependencies, advisory file scopes, reservations, review status | Does not invoke subagents or enforce filesystem permissions |
| `orbit_build.py` | Stage-specific gates and SQLite checkpoints, read-only recover/continue | Evidence claims are host-supplied except stored managed-browser result; results lack code-revision attestation |
| `orbit_preview.py` | Explicit approved localhost process commands and health checks | Process handles are session-local; no durable OS job supervisor |
| `orbit_browser.py` | Optional installed Playwright using loopback Edge/Chrome/Chromium | Requires installed Playwright and browser; remote requests blocked at browser layer, not OS sandbox |
| `orbit_skill_plan.py` | Bounded read-only project/host-aware installed skill shortlist and v2 review manifest | Skill content and license claims remain untrusted; no execution or host approval attested |
| `orbit_delegation.py` | Portable host-native specialist handoff packets | Non-executing: never spawns agents or authenticates approval |
| `orbit_delivery.py` | Read-only adaptive end-to-end software delivery blueprint (`orbit_software_delivery_preview`) | Generates reviewable intent, never code, approvals or host sessions; the host supplies specialists, permissions and test evidence |
| `orbit_swarm.py` | Bounded dependency-DAG preview over the existing project task ledger | Read-only: no registration, reservation, invocation or verified approval |
| `orbit_swarm_draft.py` | Preview of a user/host-proposed task DAG before any ledger writes | Preview only: no model calls, subprocesses, reservations or agent execution |
| `orbit_swarm_host.py` | Fail-closed pre-invocation review for up to two host-native subagents | Planning, not execution: never launches, resumes, cancels, releases or approves a host agent |
| `orbit_swarm_integrity.py` | Read-only integration readiness over actual source bytes and local QA records | Pre-review guard, not a test runner; host-reported task and browser metadata stay untrusted until independently inspected |
| `orbit_evidence.py` | Bounded external research pointers | Not a crawler or skill runner; external annotations are untrusted display data |
| `orbit_pulse.py` | Read-only, project-scoped one-glance task pulse | Counts represent local task records; they do not attest real host execution |
| `orbit_portable.py` | Explicit, bounded project transfer between PCs | Bundles are untrusted data, never permissions |
| `orbit_updates.py` | Opt-in, read-only GitHub release notices | Advisory only: never downloads executables or invokes an installer |

`source/agents` and `source/skills` contain host-specific instructions: their existence does not prove execution. The installer merges compatible host configs while preserving other registrations and owner docs. SQLite lives in local user data storage, **outside Git**. `.orbit/PROJECT.md` is only a small accepted-brief/index; canonical owner ADRs/specs remain where they exist.

## Lifecycle and evidence

Initial build intake is approval-gated; the lead host verifies the actual owner's answers and approves the editable plan before implementation. New web stages follow `RESEARCH, PLAN, IMPLEMENT, VERIFY, PREVIEW, BROWSER_QA, REVIEW, CHECKPOINT, DONE`. Native desktop/mobile replace browser-specific gates with `NATIVE_QA`. Non-web SDK/CLI/API/MCP/OS workloads have tailored stages and acceptance cases. Existing SQLite rows retain their original flow after upgrade.

`RESEARCH` accepts structured sources/options/risks; `VERIFY` records actual host-reported CLI exit codes and edge-case/security checks. The built-in `BROWSER_QA` gate requires a passing stored Playwright run; screenshots alone from other browser providers do not satisfy it. The host must evaluate **code and requirements freshness** independently; a saved PASS is not irrevocable proof after source changes. `DONE` is a coordination record, not an independent release approval.

## Packaging, release and security

`VERSION`, `installer.py`, `orbit_mcp.py`, bundled Claude Desktop manifest, release artifacts and changelog must agree. `scripts/build_desktop_extension.py` rebuilds the .mcpb from canonical runtime files. Protocol regression tests compare all bundled runtime modules byte-for-byte. `scripts/build_release.py` generates a deterministic ZIP and sha256 sidecar. GitHub CI covers Linux Python 3.10–3.13 and Windows Python 3.12; user-local desktop/browser end-to-end acceptance is still separately required.

No standalone model runner, remote public tunnel, automatic Git push, OAuth scope escalation or proprietary Scram component library is bundled. See [security](../SECURITY.md), [roadmap](NEXT-VERSION.md) and [component routing](ADAPTIVE-DECISION-ENGINE.md).
