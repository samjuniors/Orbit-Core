# Orbit Todo Lab — end-to-end acceptance test

## 0. Fresh project

Create a blank folder called **orbit-todo-lab**. Install Orbit Universal into **this exact folder**. In the host choose that same folder. Do not copy an existing app. Use project slug `orbit-todo-lab` in every memory/task MCP request.

## 1. Prompt A — Installation and read-only audit (paste into Orbit)

> Orbit, use this project as a fresh Todo Lab. First verify the `orbit-core-native` MCP connection and list the real available MCP tools. Verify project slug `orbit-todo-lab`, current absolute folder, Git/repository state, available native specialist agents, and whether native subagent delegation exists in this host. Run `orbit_project_scan` or `orbit_project_resume` read-only. Do not build the app, write project files, create a Git commit, or claim tools/agents worked until you've checked them. Show a PASS/HOLD table for MCP, skill, native agents, project detection, and existing checkpoint.

**Expect:** MCP tool discovery includes `orbit_project_resume`, `orbit_memory_save`, `orbit_task_plan`, `orbit_task_reserve`, `orbit_task_review`, `orbit_project_checkpoint`. No phantom agent status. Empty project reported honestly. No backend/data files yet.

## 2. Prompt B — Plan the app and check delegation

> Orbit, plan a small full-stack Todo app in this fresh project. Requirements: create a task, view tasks, toggle completed, edit task title, delete a task, filter All/Active/Completed, show empty/error/loading states, keyboard accessibility and a responsive layout. Persist tasks in SQLite through a tiny local API, no authentication or production deployment. Prefer TypeScript, React+Vite frontend, Express backend, SQLite persistence, and automated tests; use simpler choices if justified. Keep one coherent plan with milestones, gates, frontend/backend API contract, file ownership and acceptance checks. Identify exactly 2 bounded specialist tasks—frontend and backend—that can be delegated without changing the same files. Show which host-native spawn tool is actually available, and preview Orbit task reservations; do not dispatch until I approve. Do not create duplicate README/ADR/architecture docs.

**Expect:** M0 scope/architecture → M1 API & UI contract → M2 implementation → M3 integration/tests. Tasks have nonoverlapping paths and dependencies. `orbit_task_plan` returns task keys and revision tokens if connected. No claim that a specialist has been launched yet.

## 3. Prompt C — Execute after reviewing the plan

> I approve building Orbit Todo Lab within this project folder. Orbit, use the host-native frontend/backend subagents if available, and reserve the matching tasks in `orbit-core-native` before invocation. Limit to two active tasks and no overlapping file writes; if native subagent tools are absent, use the roles sequentially and report that limitation. Build and integrate the app, run actual tests and a build, and check CRUD behavior. Independently review changes and record outcomes in Orbit. Do not push, merge, deploy, change unrelated files, or make a Git commit without separate approval. Save a bounded project checkpoint using the verified revision and only when permitted. Summarize every host subagent ID, changed file, test command/exit status, and remaining blocker.

**Expect:** Native subagent records in host when supported, real tool invocation IDs, task reservations and `orbit_task_started` only after actual execution, `orbit_task_report` and separate `orbit_task_review` after verification. If only sequential execution, don't treat simulated agents as actual spawned sessions.

## 4. App functionality: manual tests

| Check | Action | PASS evidence |
|---|---|---|
| Start | Run dev commands documented in README | Browser opens app; API responds |
| Create | Enter "Buy milk" and submit | One active item appears |
| Complete | Toggle checkbox | Status changes; Active filter excludes it |
| Edit | Change title to "Buy oat milk" | Updated name displayed |
| Filter | Select Active/Completed/All | Correct counts and visibility |
| Refresh | Reload browser; restart API | Task still exists (SQLite persistence) |
| Delete | Delete task | Task disappears; persists after refresh |
| Validation | Submit blank title | No empty task; helpful feedback |
| Error | Stop backend and attempt an action | Useful error state; no fabricated success |
| Accessibility | Tab/Enter/Space through controls | Logical focus order and labels |
| Automated tests | Run documented API/UI test commands | Evidence of test names and exit code 0 |
| Build | Run documented production build | Exit code 0; no critical warnings |

## 5. MCP / agent verification checklist

| Check | What to look for | PASS/FAIL |
|---|---|---|
| MCP | `orbit-core-native` connected; **35 tools in current main source** (published v0.24.1 bundle has 33). Verify the actual host tool list rather than assuming count. |  |
| Lead agent | Host recognizes Orbit skill/instructions and reads real project |  |
| Planning | Roadmap covers UI, API/data, security, tests; current gate explicit |  |
| Reservation | `orbit_task_plan` -> approved `orbit_task_reserve`, max 2 |  |
| Native spawn | Actual host tool called; session ID exists, not merely ledger status |  |
| File isolation | Frontend and backend own disjoint paths; scope check used |  |
| Evidence | Real file changes and command output, not self-report only |  |
| Review | Task accepted after independent review or accurately HOLD |  |
| Memory | Save confirmed project fact, recall it in a new session |  |
| Cross-host | Open same local folder in second host and recall same project key |  |
| Resume | `orbit_project_resume` returns latest real checkpoint |  |
| Safety | No surprise commits, deploys, deletions or file overwrites |  |

**Warning:** a `PASS` in the MCP ledger based solely on text supplied by the model is not independent verification. Read the actual diff/tests in the coding host.

## 6. Prompt D — Cross-host memory test

Open the **same project folder on the same computer and user account** in a different host. Ask:

> Orbit, connect to the same `orbit-core-native` server and read project `orbit-todo-lab`. Recall the last recorded decision and current task statuses, and call `orbit_project_resume`. Compare against actual Git and test output. Do not modify anything. Tell me if the database is missing, using a different path, or simply has no memory entries.

**Expect:** same accepted memory and task state if previous writes were actually completed. If not, classify HOLD and inspect selected database paths/server visibility. No cloud sync is implied.

## 7. Screenshots to collect if a check fails

1. MCP server list, showing `orbit-core-native` status and error details.
2. Agent selector/subagent panel showing actual native sessions (if available).
3. Orbit output with task IDs/revisions and `orbit_task_list` results (no secrets).
4. Terminal test command + exit code and browser Todo UI (if code was generated).

The Todo app should be generated in the target host. This package supplies **the test plan and Orbit tools**, not a prewritten Todo app.
