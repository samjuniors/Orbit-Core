# Orbit Remote Commander — development / integration

**Status:** local stdio MCP prototype + fail-closed fallback routing. **NOT a connected ChatGPT web tool, Windows installer, or deployed remote gateway.** The Orbit ChatGPT plugin v0.26.2 contains the companion skill; this repository is the version-controlled engineering source and acceptance evidence.

## Why separate it?

Keep Orbit Core local-first. A remote PC connector is optional and must not entangle Orbit memory, checkpoints or core releases. Prefer an already-connected authorized Desktop Commander when it can complete the requested operation. If it is missing, offline, or suffers an availability outage, a separately installed, paired and scoped Orbit commander may be selected. **No provider is allowed to bypass another provider's user/policy denial, silently retry an ambiguous write, or gain wider project access.**

## Code and tests

- `source/runtime/orbit_remote_commander.py`: dependency-free local stdio MCP prototype. Requires `ORBIT_RC_ROOT` pointing to a specific existing project folder. Default read-only tools: `orbit_rc_status`, `orbit_rc_list` and `orbit_rc_read`. Opt-in existing-file, SHA-guarded `orbit_rc_write` and fixed Git diagnostics `orbit_rc_check` are disabled by default. No arbitrary shell, networking, UI control, background process, installer or shared credential service.
- `source/runtime/orbit_remote_fallback.py`: deterministic selector that works only on **actual, verified** host state and independent permission observations. It does not install, authenticate, or invoke tools.
- `tests/test_remote_commander.py` and `tests/test_remote_fallback.py`: local source, MCP framing and fallback safety regression tests.

Test using Python 3.10+:
```bash
python -m unittest discover -s tests -p 'test_remote_*.py' -v
```

## Opt-in local test (not ChatGPT web)

An MCP **stdio-capable local desktop client** can explicitly start:

```bash
python /absolute/path/to/Orbit-Core/source/runtime/orbit_remote_commander.py
```

Supply an environment limited to one disposable project, e.g. `ORBIT_RC_ROOT=D:\\Projects\\orbit-rc-lab`, `ORBIT_RC_ALLOW_WRITE=0`, and `ORBIT_RC_ALLOW_CHECKS=0`. A host's MCP config syntax varies; adding this process to one IDE does not automatically register it in ChatGPT web or other hosts. Run `orbit_rc_status` and verify `READY_LOCAL_STDIO`, then test harmless text reads and denial of traversal/secret paths.

Use a low-privilege OS account or isolated VM for testing untrusted repositories. Path filters, fixed commands, environment flags, and the model's `confirm_write` field are not a substitute for OS boundaries or a real human approval mechanism. Git config and files may influence subprocess behavior.

## Required before real internet-enabled fallback

1. Build an independent **HTTPS Streamable MCP** gateway with compliant **OAuth 2.1**, protected-resource metadata, scoped authorization and device credentials. Review the *current* MCP protocol, not a hardcoded old handshake.
2. Build an opt-in Windows companion with outbound-only device connection, pairing confirmation, device revoke, uninstall/update and project-root permissions. Do not expose an unauthenticated local listener or invent a public relay address.
3. Enforce origin checks, TLS, per-device/session permissions, expiry, rate limits, replay protection, audit metadata and authenticated dispatch on gateway **and device**. Host confirmations must not be simulated by tool fields.
4. Create idempotency/cancellation and uncertain-write recovery; never silently retry a possibly completed action. Do not auto-fallback after explicit permission denial.
5. Test two fresh ChatGPT web chats, actual offline-primary fallback success, wrong-device denial, revoked grant denial, credential rotation, stale writes and Windows disconnect/cleanup. Independent security review and reviewed CI required.
6. User must authorize real gateway deployment and ChatGPT connection/pairing. Until then report `LOCAL PROTOTYPE; REMOTE NOT VERIFIED`.

Sources: [MCP authorization](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization), [MCP security best practices](https://modelcontextprotocol.io/specification/2025-11-25/basic/security_best_practices), [OWASP MCP security cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html).

Do not merge, ship, modify user's computer or add open network listeners solely because this source passes offline tests.
