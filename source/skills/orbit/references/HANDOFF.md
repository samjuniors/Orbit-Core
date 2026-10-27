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
