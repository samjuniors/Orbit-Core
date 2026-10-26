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
