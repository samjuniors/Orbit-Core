# Orbit specialist handoff

Project key and authorized root:
Verified Git branch and worktree:
Milestone / gate / task:
Requested specialist role:
Objective and constraints:
Canonical file paths and existing decisions:
Read scope:
Write scope (disjoint from other workers):
Dependencies and prerequisite evidence:
Host model: inherit (do not switch providers without approval)
Prohibited side effects: delete, merge, push, deploy, send secrets, spend money
Acceptance checks and test commands (verify they exist):
Evidence required: changed file list, diff, command exit codes, test outputs, visual proof when useful
Result: actual host session ID if available, done / blocked / failed, unresolved risks and next action

`orbit_task_handoff` generates this bounded packet from an approved registered task. Status `HOST_INVOCATION_REQUIRED` means **the host still must invoke its real native agent tool**; `HOLD_*` means no agent delegation occurred. Never treat caller-reported `available_host_tools` as host-attested permission, or fabricate a native agent session.

Before real native delegation: registered task key, `write_paths`, dependencies, latest task revision, and verified host/user permission reference. After delegation: actual host session reference, reported changed paths, independently inspected diff/tests, and separately recorded review. Ledger data is not a security boundary.

For an integration batch after specialist reviews, call read-only `orbit_swarm_integration_review` with current task revisions and a previously inspected source fingerprint. For web apps supply the existing build ID so the latest local browser QA record is checked against current code. Any `HOLD_*` blocks integration; `READY_FOR_INDEPENDENT_REVIEW` only indicates that local task/source/QA records are consistent, **not** that a human reviewed the Git diff, tests actually ran in the host, or the change may be merged. Independently inspect test commands, output and source changes. Native/mobile QA remains a separate host-specific review.
