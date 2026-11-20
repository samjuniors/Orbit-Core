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
