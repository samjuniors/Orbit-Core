# Orbit Core RAD P2 — trusted local preview transport

**Status: PROPOSED / NOT IMPLEMENTED / acceptance HOLD.** This records the next bounded Windows acceptance design; it does not claim that a Python web app is currently served inside LPAC.

## Current evidence and hard boundaries

The [RAD P2 draft](https://github.com/samjuniors/Orbit-Core/pull/140) has manual native evidence for scoped file access, staged CPython startup and no-network-capability socket denials. The normal Orbit preview path still launches with zero capabilities and refuses readiness because endpoint ownership is not independently verified. Do not confuse a synthetic startup marker or an arbitrary HTTP 200 with a working isolated application.

Microsoft documents AppContainer loopback isolation and SID-restricted IPC. A global loopback exemption is **not** an approved Orbit solution.

- [Microsoft Windows IPC](https://learn.microsoft.com/en-us/windows/apps/develop/communication/interprocess-communication)
- [Named-pipe security and access rights](https://learn.microsoft.com/en-us/windows/win32/ipc/named-pipe-security-and-access-rights)
- [AppContainer launch](https://learn.microsoft.com/en-us/windows/win32/secauthz/implementing-an-appcontainer)
- [Windows Firewall and app isolation](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/troubleshooting-uwp-firewall)

## Proposed acceptance prototype, not authorized default behavior

Explore a bounded **host-owned, same-machine IPC broker** for a disposable LPAC preview. One candidate is a Windows named pipe with a DACL for the exact profile SID plus required host session identity. Microsoft documents the LOCAL namespace convention for packaged AppContainer; support for Orbit's unpackaged LPAC fixture must be verified, not assumed. The broker must not grant broad internet or private-network capabilities, disable the firewall, add machine-wide exemptions, or forward privileged host file access.

A request must be bound to a freshly generated session nonce and **kernel-observed** client process identity, token/package SID, exact project, session and Job Object membership. Client-provided names, PIDs, nonces or HTTP headers are not sufficient authentication. A host-owned browser URL is not evidence that the content originated from the LPAC child.

### Required gates before reporting READY

1. **Positive identity control:** Native IPC communication from the exact verified child. Reject foreign/same-user processes, wrong profile, stale sessions, PID reuse and wrong nonce.
2. **Least privilege:** Positive synthetic project I/O, denial of sibling and credential access, scoped registry and reparse-point tests. Assess the deliberate registryRead capability separately.
3. **Network:** Verify OS outbound/private-network/unauthorized-loopback denial and a legitimate host-side preview path with positive controls and exact kernel errors.
4. **Representative Python app:** Run a disposable Python HTTP application through the chosen constrained transport. A marker file or simple IPC handshake does not satisfy this gate.
5. **Lifetime:** Prove descendant/grandchild cleanup, forced controller exit, cancellation, revocation, recovery and no READY after partial cleanup.
6. **Bounded broker:** Limit request size, method, path, concurrency, duration, origin and forwarded headers. No arbitrary host files, upstream URLs, cookies, tokens or credentials.
7. **Provenance:** Record source/executable SHA-256 hashes, commit, OS, exact commands, raw redacted results and cleanup. Reject environment-supplied native probe binaries; review PE signatures, licensing and compatibility before distributing modified Python DLLs.

Do not replace Orbit's fail-closed preview gate until real Windows acceptance, independent adversarial assessment and owner approval. Existing RAD issue [#138](https://github.com/samjuniors/Orbit-Core/issues/138) stays OPEN. This is neither an implementation authorization for privileged machine changes nor a release decision.


## Experimental code checkpoint — opt-in one-shot handshake, NOT a web preview

This design now has a **scripts-only, non-installed** prototype in
`scripts/rad_p2_preview_ipc/`, consisting of:

- `protocol.py`: a bounded, replay-limited protocol for an exact profile,
  process, Windows session and canonical project. It rejects duplicate JSON
  keys, arbitrary URLs/methods, traversal, oversized frames/bodies, stale
  sessions, mismatched peers and unapproved forwarded headers.
- `winpipe.py`: a disposable-only named pipe using a fresh `LOCAL` name,
  explicit host-user and exact package SID ACL, low-integrity label, remote
  client rejection, an exclusive first pipe instance, overlapped bounded I/O,
  kernel-reported opening PID/session, pinned live process token and Job
  membership. Unsupported Windows/ACL combinations HOLD, not fall back.
- `client.py`: an opt-in staged Python client that validates the server
  process PID and sends one hello response to the host challenge. A PID and
  nonce alone do NOT establish a production channel or prevent delegated
  handle reuse; the host must still verify the kernel-reported opener before
  issuing any challenge.

The existing manual harness exposes `--ipc-handshake`. It requires
`--python-startup`, zero network/registryRead capabilities, the normal
`--apply` flag and its exact confirmation. It copies **only trusted** CPython
standard-library extension modules and these reviewed prototype scripts into
the disposable runtime, which is later cleaned up. It never installs them.

**Read-only dry run** (cannot create a profile and exits HOLD):

```powershell
py -3.12 scripts/rad_p2_disposable_host_acceptance.py --ipc-handshake
```

**Manual security acceptance only with fresh owner/host approval:**

```powershell
py -3.12 scripts/rad_p2_disposable_host_acceptance.py --apply --confirm "CREATE DISPOSABLE ORBIT APPCONTAINER" --python-startup --ipc-handshake
```

Check the returned `checks.ipc_handshake`, exit codes, exact created profile,
cleanup and native OS observations. The harness itself always exits 2 to
preserve HOLD until independent review. A successful handshake, if achieved,
means only **HANDSHAKE_VERIFIED_NOT_READY**, never an authenticated HTTP
application, browser QA or production permission grant.

### Why the production boundary remains intact

The prototype is intentionally **not** included under `source/runtime`, in
the installer, in any MCP tool, or in the normal `orbit_preview` code path.
No global loopback exemption, WFP changes, credential access, network
capabilities, service startup or release artifact changes are made.

The next engineering step is not to flip a readiness flag. Real tests must
first prove that unpackaged LPAC can open this particular `LOCAL` pipe under
the proposed security descriptor, that a same-user impostor/delegated-handle
attack cannot inject responses, and that a genuine disposable Python
application can serve bounded HTTP content through an authorized host broker.
GetNamedPipeClientProcessId identifies the *opening* process, not necessarily
every later writer of a duplicated pipe handle. If this boundary cannot be
demonstrated safely, use HOLD and review another Windows IPC primitive.

Automated Windows/Linux tests on the prototype check **pure protocol and
fail-closed behavior**. They do not provision an AppContainer or certify
native LPAC IPC. Independent OS testing and owner acceptance are still
required before the proposed broker could be integrated into Orbit.

**Release inventory note:** The current `scripts/build_release.py` source-setup
ZIP deliberately includes the repository's `scripts/` tree. Thus
scripts-only placement prevents installation into the shared MCP runtime
but does **not** automatically exclude these experimental files from a
future source-setup archive if this branch is merged. Before *any*
release-bearing merge, decide whether to exclude this directory from all
distributed archives or complete acceptance and conduct package-content
review. This draft does not alter published artifacts.

## 2026-11-20 — Synthetic WSGI-over-IPC milestone (DRAFT, no HTTP listener)

The next [stacked draft](https://github.com/samjuniors/Orbit-Core/pulls) adds a
*deliberately non-production* WSGI transport fixture. All code remains under
`scripts/rad_p2_preview_ipc/`; the normal `orbit_preview` MCP tool is unchanged.

- `fixture_wsgi.py` is a **real Python WSGI callable**, with only fixed
  synthetic routes `/health`, `/` and `/index.html`. No project-supplied
  code, filesystem reads, arbitrary imports, network access or URL forwarding.
  Responses are validated, bounded and encoded in the existing IPC envelope.
- The host's `PreviewIPCSession.begin_host_request` issues exactly one
  GET/HEAD transaction after the internal Win32 peer attestation and one-shot
  handshake. The child decodes and executes the WSGI callable in-process and
  sends a response on the **same** pipe. Native `winpipe.accept_handshake`
  checks the response's sequence, type, body and fixed `/health` marker.
- `--ipc-wsgi` opts the manual disposable harness into this extra request.
  It requires **all** of `--ipc-handshake`, `--python-startup` and the
  existing explicit `--apply --confirm` approval. The fixture requests
  zero added LPAC capabilities and continues to leave `READY` unavailable.
  No shell command, source import or externally supplied HTTP endpoint is run.
- Nonprivileged tests cover successful health/index/HEAD/404 responses,
  request replay/sequence mismatch, header/URL/path/method injection, invalid
  JSON and response size limits, and no socket or project-data side effects.

Safe read-only plan (returns HOLD; changes no Windows profiles or ACLs):

```powershell
py -3.12 scripts/rad_p2_disposable_host_acceptance.py --ipc-handshake --ipc-wsgi
```

For a separately **owner- and host-approved** disposable native test
(the following is documentation, **not** a test that was run from ChatGPT):

```powershell
py -3.12 scripts/rad_p2_disposable_host_acceptance.py --apply --confirm "CREATE DISPOSABLE ORBIT APPCONTAINER" --python-startup --ipc-handshake --ipc-wsgi
```

Read `checks.ipc_handshake`, `checks.ipc_wsgi`, `ipc_child_exit`,
`ipc_wsgi_response_bytes`, exact profile deletion/fixture removal, and
redacted Win32 errors. An exception, missing response or failed cleanup must
not be accepted as PASS. The manual harness retains its overall HOLD exit code.

**Not yet completed:** actual LPAC pipe compatibility, independent per-message
handle ownership (the Windows API identifies the opener, not necessarily a
later writer with a delegated handle), an authenticated **browser-facing**
host-owned HTTP server, an arbitrary user Python web app, job descendant
containment, denied synthetic registry/reparse attacks and sensitive
Antigravity host permissions. Neither GitHub CI nor this synthetic WSGI
round trip proves those properties. Do not label this "production HTTP
preview", enable a global loopback exemption or change the normal fail-closed
`HOLD_OS_ISOLATION_ENDPOINT_UNVERIFIED` behavior.


## 2026-11-21 — Host-owned one-shot HTTP snapshot (experimental, inactive)

A new scripts-only `rad_p2_preview_ipc/http_snapshot.py` implements the
**next narrow boundary**: an owner-activated, one-use local HTTP viewer for
already-validated, bounded **synthetic** WSGI response bytes. This is an
**in-memory snapshot**, not a live dynamic app or an arbitrary HTTP proxy.

- Binds **IPv4 127.0.0.1 only**, on a random OS-assigned port. Never opens
  a listener at import time or through the production MCP runtime.
- Uses a fresh 192-bit bearer token in an exact, single-use path; any wrong
  path, query, method, foreign/duplicate `Host`, `Origin`, `Referer`,
  `Cookie`, `Authorization`, forwarded header or cross-site fetch holds.
  A rejected first request consumes the one-request budget.
- Expires after a short deadline and shuts down the listener. Never logs
  the URL/token, response body or sensitive browser headers.
- Responds with a strict content-type allowlist, bounded bytes, CSP
  `sandbox; default-src 'none'`, no referrers, no cache, no framing, no
  CORS, no cookie and `nosniff`. The user-provided project web app is
  **not** loaded or allowed to execute scripts.
- The existing manual disposable Windows fixture may opt into
  `--http-snapshot`, **only after** `--ipc-wsgi --ipc-handshake
  --python-startup` and the existing `--apply --confirm` gate, with
  zero added LPAC capabilities. Once the verified native pipe returns the
  fixed WSGI health marker, the host replays those **same checked bytes**
  to a local HTTP client. No browser QA is claimed; the child has already
  exited. The harness retains its overall HOLD exit code.

Read-only preflight (no profiles/ACLs/listener):

```powershell
py -3.12 scripts/rad_p2_disposable_host_acceptance.py --http-snapshot
```

**Operator/host approval required before running the native disposable
experiment:** `py -3.12 scripts/rad_p2_disposable_host_acceptance.py
--apply --confirm "CREATE DISPOSABLE ORBIT APPCONTAINER"
--python-startup --ipc-handshake --ipc-wsgi --http-snapshot`.
This command is documented but was **NOT run through ChatGPT**.
No Windows profile, ACL or host credential was touched by this work.

GitHub CI tests the synthetic in-process WSGI → IPC frame → host snapshot →
real loopback HTTP response, plus source/runtime separation, Host/origin
rejection (including DNS rebinding/duplicate Host), method and path denial,
token isolation, response headers, timeout and listener cleanup. Passing
these tests does **not** prove an actual LPAC pipe works, that each message
has OS-bound authorship after handle delegation, or that the browser can
safely preview general user code.

**Explicit security limitations:** `http.server` is suitable only for this
disposable, local, bounded smoke test and is not approved as production
web infrastructure. A bearer token in a URL can appear in browser history;
its very short lifetime, one-use limit and no-referrer header reduce but do
not eliminate exposure. A genuine dynamic browser-facing preview requires
a separately reviewed transport and native, adversarial Windows tests.
All production `READY` transitions remain fail-closed. Before merging into
release branches, review or exclude this scripts directory from source
package archives (the current build includes scripts recursively).

External review references: [Python HTTP server security notes](https://docs.python.org/3.12/library/http.server.html) and
[OWASP DNS rebinding test guidance](https://wstg.owasp.org/latest/4-Web_Application_Security_Testing/11-Client-side/21-DNS_Rebinding/).

## 2026-11-21 — Source-setup archive containment (DRAFT)

The follow-on stacked draft branch `security/rad-p2-exclude-experimental-source-20261121`
adds an explicit **source-setup ZIP** exclusion policy for unaccepted
`scripts/rad_p2_*` and their matching `tests/test_rad_p2_*` test modules.
The read-only `rad_p2_preflight.py` script and its test are preserved.
The complete experimental source and tests remain in GitHub for independent
review and CI; this is an archive-inventory restriction, **not a deletion**
or a change to the installed 57-tool MCP runtime.

Both ZIP construction and the existing extracted-ZIP smoke check reject an
accidental prototype inclusion. New focused tests enforce the allowlist and
safe relative paths. This is a defense-in-depth packaging precaution, **not**
LPAC security acceptance or approval to merge/release. The previous statement
that every `scripts/` file is shipped describes the pre-change behavior;
no published archive has been updated by this draft.
