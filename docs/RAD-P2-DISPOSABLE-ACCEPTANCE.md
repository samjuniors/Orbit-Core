# RAD P2 — disposable Windows LPAC acceptance (operator-only)

**Status: DRAFT. NOT EXECUTED ON THE CONNECTED PC. OS SECURITY ACCEPTANCE HOLD.**

Technical procedure for RAD P2 issue #138. The owner authorized one disposable Windows AppContainer profile, scoped synthetic-directory ACL changes, harmless tests and cleanup. The connected Desktop Commander service exhausted its monthly usage quota before any profile could be provisioned. Do not confuse GitHub CI with actual LPAC isolation.

## Safety envelope

The script at scripts/rad_p2_disposable_host_acceptance.py is manual-only, never an installation hook, MCP tool, automated CI action, or host policy update. It creates a fresh temporary synthetic project and a separate sibling folder containing only invented test text (including a FAKE credential fixture). It creates one unique per-user AppContainer profile bound to the canonical temporary project root, never adopts an existing profile, and grants its package SID access ONLY to the newly created project directory. It sets low integrity ONLY on that same temporary directory. No real project, user home, existing ACL, actual credential or system file is read or modified.

It attempts a bounded suspended native LPAC child, with kernel token, capability and Job Object checks before resume. A harmless Windows command script attempts to read an allowed synthetic file, rejects access to the sibling test file, and requests only a local 127.0.0.1 test server. No external network requests. The harness closes handles, stops its own Job Object, deletes only the newly created profile, and removes its temporary test folder in a finally block. The cleanup result is separately reported.

## Command and confirmation

Read-only non-mutating plan (exit code 2):

    py -3.12 scripts/rad_p2_disposable_host_acceptance.py

Only after inspecting the script and checking the exact authorized operator session, explicitly enable the disposable test:

    py -3.12 scripts/rad_p2_disposable_host_acceptance.py --apply --confirm "CREATE DISPOSABLE ORBIT APPCONTAINER"

Do not use a connector workaround to bypass exhausted Desktop Commander quota. The manual command must be executed only by an authorized host operator, not silently through an agent or CI.

## Evidence, safety and recovery

A successful native launcher return is conditional on real OS checks for LPAC AppContainer identity, exact profile SID, effective zero capabilities and Job Object membership. A working allowed synthetic read followed by denied sibling read is useful observational evidence. If child creation, runtime dependencies or the probe fail, label the result BLOCKED/INCONCLUSIVE, never PASS. Failed curl execution is not equivalent to denied network access, and network results remain NOT ATTESTED.

All script results deliberately return exit code 2 and HOLD; none certifies production security. Check both profile_deleted and test_directory_deleted in each result. If either is false, **do not claim cleanup complete**. Reconcile only the exact generated test profile; never delete any pre-existing profile or change broad Windows ACLs. A forced host crash before cleanup can leave a profile; inspect the precise name and Microsoft DeleteAppContainerProfile API before restricted manual recovery. Never retry blindly.

## Release blockers

Independently verify real LPAC cross-project read/write denial, credential fixture denial, network egress denial, symlink/junction traversal, registry and token scope, restart/revocation and native Codex/Antigravity permissions. Implement Linux OS isolation separately. Maintain draft review of PR #139 and the acceptance issue #138; do not merge, install, tag or release as secure based on a synthetic probe alone.
