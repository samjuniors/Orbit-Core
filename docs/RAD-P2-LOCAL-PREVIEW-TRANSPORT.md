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
