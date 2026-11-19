# Security and trust boundaries

- This is a local stdio MCP server; it is not designed to be exposed directly on the internet.
- Each host's native tools must enforce user permissions independently; Orbit's task ledger is not an OS sandbox or identity service.
- External skills, MCP endpoints, command execution, shell scripts, public URLs, deployments and elevated permissions require explicit authorization and source/security review.
- Never commit memory databases, WAL files, credentials, key files, personal transcripts, `.env` files, machine-specific configuration, or user workspace files.
- Project material and downloaded skills are untrusted input; repository text cannot override host security policy.
- Avoid running live test automation against existing user projects without separate approval.
- Release packages require tests and content review; GitHub Actions are **not** proof of host-specific Gemini/Claude/Codex execution.
- Report security issues privately to the repository owner. Do not open a public issue disclosing secrets or vulnerabilities.

## RAD P0: process-local adaptive policy gate (draft, not released)

The original `orbit_defense.py` module adds **host-startup** `ORBIT_DEFENSE_MODE`:
`NORMAL` (default, preserves v0.32 behavior), `GUARDED` (blocks *both*
`orbit_preview_start` and `orbit_browser_qa` before any handlers or subprocesses
run), and `CONTAINED` (blocks other MCP operations except a small audited
recovery list and explicit stopping of a session-owned preview). Unrecognized
host modes **fail closed** as `CONTAINED`. A caller cannot set a mode or reset it
through MCP arguments, SQLite state, project README, skills, or agent messages.

In `GUARDED`, three denied code-execution requests against the *same validated
canonical project root* also move that root into `CONTAINED` for the process
lifetime. The number of tracked scopes is capped at 64; saturation never permits
execution and cannot lock unrelated root-scoped project operations. A malicious request outside
`ORBIT_TRUSTED_ROOTS` cannot escalate another project. Other roots can continue
their normal guarded workflows. Containment allows only non-project metadata,
a pure caller-supplied gate evaluation, and explicit stopping of a managed
preview. Project scans, task history, charter content, local memory and research
reads are denied even though they are normally read-only: they may expose data. Only a trusted host restart with a reviewed mode setting can
reset the process-local guard. Do **not** let an MCP tool de-escalate itself.

**Scoped SQLite memory (draft P0):** `orbit_memory_save`,
`orbit_memory_recall`, and `orbit_memory_archive` now accept an **optional**
`project_root` while keeping the 57-tool contract. Slug-only calls remain
backwards-compatible in NORMAL; they are always refused in GUARDED. In GUARDED,
the root must be an existing canonical directory **explicitly and exactly**
listed by the trusted host's `ORBIT_TRUSTED_ROOTS`. A general parent directory
allowlist does not authorize memory for arbitrary descendants. Each root/slug
pair gets a distinct SHA-256-derived SQLite namespace, so equal project slugs
cannot accidentally share records; responses retain the public slug. A
CONTAINED root cannot access its scoped memory while unrelated listed roots
can continue. These are deterministic MCP controls, **not authenticated
caller identity or independent filesystem/OS access controls**.

Legacy slug-only memories are **never automatically migrated or deleted**.
An operator can run `python scripts/migrate_scoped_memory.py --database
<absolute-db> --project <slug> --project-root <exact-root>` in an explicitly
configured trusted-root environment for a counts-only dry run. Apply requires
`--apply --confirm "MIGRATE SCOPED MEMORY"`, creates a consistent adjacent
SQLite backup, copies records into the new namespace without replacing
existing destination keys, and retains legacy records for older hosts. Run
this only after reviewing which legacy slug belongs to which root and backing
up owner data; a moved root requires deliberate remapping. Nothing migrates
on installer upgrade, host startup, or an MCP tool call. Privileged migration
and real host identity/permission enforcement remain operator/host duties.

**What the gate does not prove:** A blocked attempt is a policy violation, not
proof of a malicious actor, compromise, or independently verified host session.
Three deliberately repeated calls could trigger scoped false-positive denial of
service until a trusted restart; review host logs and operator procedures.
This process-local policy is **not OS process isolation, a firewall, verified
human consent, a signed rule, protection against malicious Python code running
in the same interpreter, or persisted crash-proof incident response**. In
particular, `NORMAL` does not automatically detect breaches; the host must
opt into `GUARDED`, and wider incident signals require separate host-authorized
integration. Do not claim that SHA hashes, caller-reported permission states,
or a passed simulation make the software unhackable.

When exercising RAD against untrusted projects, configure the selected MCP
host's process environment with `ORBIT_TRUSTED_ROOTS` and
`ORBIT_DEFENSE_MODE=GUARDED`, confirm actual OS sandbox/credential scope, and
restart the host. Do not bypass a rejected host command via a different model
or tool. The gate emits only coarse HOLD statuses, never raw source/commands,
and creates no SQLite table, cloud log, background worker or network listener.
See `tests/test_rad_defense.py` for adversarial negative tests. This is source
development in a separate draft branch and needs independent Windows/Linux CI,
real IDE/host enforcement and owner acceptance before release.

## RAD P1: Windows preview process-tree containment (draft, not released)

The Windows preview manager now creates an anonymous native **Job Object**
with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, attaches the launched interpreter
process, and retains its private job handle for the lifetime of the session.
On an explicit preview stop, it terminates the job (including descendant
processes); if the Orbit MCP host unexpectedly exits, Windows closes its
private handle and terminates the job's remaining members. A failed job
creation or assignment returns `HOLD_HOST_PROCESS_BOUNDARY` and refuses to
register the preview, instead of silently falling back to a parent-only stop.
The installed runtime inventory includes `orbit_windows_job.py` so package
installation cannot omit the imported module. Linux/macOS keep the existing
process-group cleanup; this Windows-only module adds no dependency.

**Security scope and limits:** this is OS-enforced **process lifecycle**
containment, not an AppContainer, firewall, filesystem permission sandbox,
restricted user token, memory secrecy mechanism, or authorization service.
The preview interpreter now starts with Win32 `CREATE_SUSPENDED`;
Orbit assigns the process to the Job Object **before** resuming the unique
initial thread with `ResumeThread`. This closes the earlier `Popen`-to-job
execution race for the tested Windows subprocess path. Failure to create a
job, assign it, locate exactly one initial thread, or resume the thread must
HOLD and kill/reap the child before it is registered. Windows process creation
still occurs under the owner's existing account; Job Objects **do not**
restrict the resulting process's filesystem, registry, network, secrets,
credentials, or Windows token privileges. A malicious program can still
perform any actions its token allows **after** resume. An abnormal host crash
*before* suspended-process assignment can also leave a suspended orphan until
system/operator cleanup; it cannot execute project code without being resumed,
but this is an availability cleanup limitation, not atomic process creation.
Genuine sandboxed creation with AppContainer/restricted token, real host/user
authorization and separately scoped credentials are still required for
untrusted execution.
An explicit host-side `ORBIT_PREVIEW_KEEP_ALIVE=1` preserves the older
keep-alive behavior but **opts out** of Job Object containment; only use it for
projects and processes the operator fully trusts. The MCP tool itself cannot
change these host process environment settings. `GUARDED` still blocks
`orbit_preview_start` and `orbit_browser_qa` before any process launch.

**Acceptance and recovery:** Windows disposable tests check actual kernel
`IsProcessInJob` membership, stopped child termination, abrupt controller
exit cleanup, project-code nonexecution before assignment, failed
assignment/resume HOLD, and fail-closed unexpected thread-snapshot errors. These are stronger than simulated
Python-only controls, but do not certify real IDE policy dialogs, arbitrary
child behavior, Windows AppContainer limits or independent permission checks.
Do not merge/release without exact-head Windows/Linux CI, package parity,
native Codex and Antigravity safe host checks where available, owner review,
and explicit approval.

## v0.29 installed-skill discovery trust boundary

- **Read-only by design:** `orbit_capability_select` can recommend and hash locally installed `SKILL.md` candidates. A shortlist or `orbit-skill-plan-v2` pin does **not** authenticate a publisher, verify a license, authorize a skill, install anything, execute helpers, or attest the host's capabilities.
- **Scope and identity:** Skill names must match their containing directory and be no longer than 64 characters. Discovery skips redirected symlinks and Windows NTFS junctions **before reading** skill metadata and project-local JSON/Codex TOML MCP configuration. This helps prevent crossing the declared local discovery roots, but it is not a general-purpose OS filesystem sandbox.
- **Untrusted sources:** Project-local and user-local installed skills are both possible sources. Their names, descriptions, version and license declarations remain untrusted data. Review the full source, publisher rights, exact host capability and scope-specific permission before any later action that uses a skill. Never treat a path or hash as proof of provenance.
- **Pin freshness and residual races:** Bounded skill entry/helper-tree and location SHA-256 pins detect reviewed-byte/context differences. They do not eliminate filesystem time-of-check/time-of-use races; inspect/revalidate the full intended source immediately before any separately approved host-controlled use. Changes, missing files, incompatible platforms, other-host declarations and actual permission denials must HOLD.
- **Host permission remains external:** The MCP's caller-declared `permission_state` is an advisory test input, **not verified consent**. The connected Antigravity/Codex host must enforce the real permission boundary; never switch to a different provider to bypass an actual denial. No automatic skill execution/import or third-party catalog fetch is part of this feature.

## Local preview process execution

The v0.24 development branch adds `orbit_preview_start` with an explicit `confirm_run` flag. This executes the caller's project script, which can be unsafe even without an OS shell. The user must inspect the exact command/project and grant real host permission. The server itself cannot independently authenticate a conversational approval and does not sandbox app code; do not run untrusted repositories. Orbit probes only loopback, but external frameworks may bind differently if they ignore the supplied `HOST` setting. Verify network binding before permitting a command. No tunnels or deployments are included. Logs may contain sensitive output; keep them local and out of Git.

## Trust boundaries confirmed by adversarial audit (October 2026)

- **Approval is host-owned, not cryptographically attested by Orbit MCP.** Intake `APPROVED`, plan `approval_reference`, `confirm_write`, `confirm_run`, and task review are caller/agent assertions. A prompt-injected or misconfigured agent can supply these values; use the coding host's actual tool-approval prompts to authorize all writes and execution. MCP tool annotations provide hints, **not enforcement**. Do not claim the SQLite ledger proves human consent.
- **Workspace trust:** `project_root` must be an existing absolute directory; common home credential/config directories are refused. Set `ORBIT_TRUSTED_ROOTS` on the **host process**, as a platform path-separated list of allowed absolute project roots, to enforce a strict allowlist (and restart the MCP host). The model cannot set this value via MCP tools. Without this setting, the root guard is only a defense-in-depth check, not comprehensive authorization; only attach Orbit to repositories you trust.
- **Preview execution:** starting a preview executes project-controlled code with the local OS account's permissions. By default Orbit passes only a small process environment allowlist (e.g. PATH/HOME/TEMP/LANG plus forced HOST=127.0.0.1 and PORT). `ORBIT_PREVIEW_INHERIT_ENV=1` explicitly restores the unsafe full environment inheritance for trusted projects only. A project can still read credentials from your filesystem or its own `.env`; environment filtering is **not a sandbox**. Session-owned previews are stopped when the MCP session closes unless `ORBIT_PREVIEW_KEEP_ALIVE=1` is set.
- **Update previews:** `orbit update` without `--apply` now validates the ZIP and its supplied SHA256 without importing the archive's installer. Only `--apply` permits execution of the downloaded installer. A hash fetched alongside the artifact from the same account is not a signature or proof of publisher authenticity. Independently verify the release/publisher; signed attestation is still a release-gate improvement.
- **Untrusted repository text:** labels such as `UNTRUSTED_REPOSITORY_TEXT` are an advisory data boundary. A malicious `STATE.md`, README, project skill or MCP output must never override higher-priority instructions or act as a user approval. The MCP cannot guarantee a model ignores such content.
- **Unverified host controls:** cross-host execution, genuine per-host approval UI behavior, browser WebSocket blocking, Windows `.cmd` semantics and operating-system sandboxing require separate live acceptance checks. Do not equate green Python CI with those guarantees.
