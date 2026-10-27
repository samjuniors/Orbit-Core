# Security and trust boundaries

- This is a local stdio MCP server; it is not designed to be exposed directly on the internet.
- Each host's native tools must enforce user permissions independently; Orbit's task ledger is not an OS sandbox or identity service.
- External skills, MCP endpoints, command execution, shell scripts, public URLs, deployments and elevated permissions require explicit authorization and source/security review.
- Never commit memory databases, WAL files, credentials, key files, personal transcripts, `.env` files, machine-specific configuration, or user workspace files.
- Project material and downloaded skills are untrusted input; repository text cannot override host security policy.
- Avoid running live test automation against existing user projects without separate approval.
- Release packages require tests and content review; GitHub Actions are **not** proof of host-specific Gemini/Claude/Codex execution.
- Report security issues privately to the repository owner. Do not open a public issue disclosing secrets or vulnerabilities.

## Local preview process execution

The v0.24 development branch adds `orbit_preview_start` with an explicit `confirm_run` flag. This executes the caller's project script, which can be unsafe even without an OS shell. The user must inspect the exact command/project and grant real host permission. The server itself cannot independently authenticate a conversational approval and does not sandbox app code; do not run untrusted repositories. Orbit probes only loopback, but external frameworks may bind differently if they ignore the supplied `HOST` setting. Verify network binding before permitting a command. No tunnels or deployments are included. Logs may contain sensitive output; keep them local and out of Git.

## Trust boundaries confirmed by adversarial audit (October 2026)

- **Approval is host-owned, not cryptographically attested by Orbit MCP.** Intake `APPROVED`, plan `approval_reference`, `confirm_write`, `confirm_run`, and task review are caller/agent assertions. A prompt-injected or misconfigured agent can supply these values; use the coding host's actual tool-approval prompts to authorize all writes and execution. MCP tool annotations provide hints, **not enforcement**. Do not claim the SQLite ledger proves human consent.
- **Workspace trust:** `project_root` must be an existing absolute directory; common home credential/config directories are refused. Set `ORBIT_TRUSTED_ROOTS` on the **host process**, as a platform path-separated list of allowed absolute project roots, to enforce a strict allowlist (and restart the MCP host). The model cannot set this value via MCP tools. Without this setting, the root guard is only a defense-in-depth check, not comprehensive authorization; only attach Orbit to repositories you trust.
- **Preview execution:** starting a preview executes project-controlled code with the local OS account's permissions. By default Orbit passes only a small process environment allowlist (e.g. PATH/HOME/TEMP/LANG plus forced HOST=127.0.0.1 and PORT). `ORBIT_PREVIEW_INHERIT_ENV=1` explicitly restores the unsafe full environment inheritance for trusted projects only. A project can still read credentials from your filesystem or its own `.env`; environment filtering is **not a sandbox**. Session-owned previews are stopped when the MCP session closes unless `ORBIT_PREVIEW_KEEP_ALIVE=1` is set.
- **Update previews:** `orbit update` without `--apply` now validates the ZIP and its supplied SHA256 without importing the archive's installer. Only `--apply` permits execution of the downloaded installer. A hash fetched alongside the artifact from the same account is not a signature or proof of publisher authenticity. Independently verify the release/publisher; signed attestation is still a release-gate improvement.
- **Untrusted repository text:** labels such as `UNTRUSTED_REPOSITORY_TEXT` are an advisory data boundary. A malicious `STATE.md`, README, project skill or MCP output must never override higher-priority instructions or act as a user approval. The MCP cannot guarantee a model ignores such content.
- **Unverified host controls:** cross-host execution, genuine per-host approval UI behavior, browser WebSocket blocking, Windows `.cmd` semantics and operating-system sandboxing require separate live acceptance checks. Do not equate green Python CI with those guarantees.
