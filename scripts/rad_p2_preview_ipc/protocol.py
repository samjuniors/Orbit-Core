"""Experimental, fail-closed RAD P2 local preview message and peer checks.

No listener, public HTTP server, network exemption, privilege change, or
automatic Orbit preview activation. A native transport must supply its exact
connected pipe handle before these checks can be used. The current preview
remains HOLD until independent host/OS acceptance.
"""
from __future__ import annotations

import base64
import binascii
import ctypes
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import secrets
import time

_OS_ATTESTATION = object()  # Private minting sentinel for native Win32 observations.
PROTOCOL_VERSION = 1
MAX_ENVELOPE = 65536
MAX_BODY = 32768
MAX_REQUESTS = 16
SESSION_SECONDS = 30
CONTENT_TYPES = frozenset({
    "text/plain; charset=utf-8", "text/html; charset=utf-8",
    "text/css; charset=utf-8", "application/json",
})
_SAFE_PATH = re.compile(r"^/[A-Za-z0-9_./-]{0,199}$")


class IPCSecurityHold(PermissionError):
    """Never downgrade an IPC or identity failure to an ordinary preview."""


def _distinct_pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise IPCSecurityHold("Duplicate IPC envelope key")
        result[key] = value
    return result


def parse_envelope(data):
    """Strict JSON only; reject duplicate keys, oversized or partial frames."""
    if not isinstance(data, bytes) or not 0 < len(data) <= MAX_ENVELOPE:
        raise IPCSecurityHold("Invalid IPC envelope length")
    try:
        value = json.loads(data.decode("utf-8", errors="strict"),
                           object_pairs_hook=_distinct_pairs)
    except (ValueError, UnicodeError, TypeError, RecursionError) as exc:
        raise IPCSecurityHold("Invalid IPC envelope encoding") from exc
    if type(value) is not dict:
        raise IPCSecurityHold("IPC envelope must be an object")
    if type(value.get("v")) is not int or value["v"] != PROTOCOL_VERSION:
        raise IPCSecurityHold("Unsupported IPC protocol version")
    return value


def encode_envelope(value):
    if not isinstance(value, dict):
        raise IPCSecurityHold("IPC message must be an object")
    try:
        encoded = json.dumps(value, ensure_ascii=True, allow_nan=False,
                             separators=(",", ":")).encode("ascii")
    except (ValueError, TypeError, OverflowError) as exc:
        raise IPCSecurityHold("Invalid IPC message") from exc
    if not 0 < len(encoded) <= MAX_ENVELOPE:
        raise IPCSecurityHold("IPC message size exceeded")
    return encoded


def validate_local_path(path):
    """Never accept an URL, encoded slash, query, fragment or traversal."""
    if (type(path) is not str or not _SAFE_PATH.fullmatch(path)
            or path.startswith("//") or "//" in path
            or any(segment in (".", "..") for segment in path.split("/"))):
        raise IPCSecurityHold("Invalid preview-only relative path")
    return path


@dataclass(frozen=True)
class OSVerifiedPeer:
    """Host-native observation, not an MCP user-supplied authorization token."""

    pid: int
    session_id: int
    appcontainer_profile: str
    _native_origin: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if self._native_origin is not _OS_ATTESTATION:
            raise IPCSecurityHold("Client claims are not a kernel peer attestation")


def verify_connected_pipe_peer(pipe_handle, *, child, job, profile,
                               expected_capabilities=()):
    """Kernel-observed opening client, pinned live child token and job identity.

    This cannot authenticate messages after a pipe handle has been delegated.
    Call for each new connection, keep the handle private, use a one-shot
    transcript, and require independent adversarial acceptance before READY.
    """
    if os.name != "nt":
        raise IPCSecurityHold("Verified named-pipe peer requires Windows")
    if (type(profile) is not str or not profile.startswith("orbit-rad-")
            or not getattr(child, "_handle", None)
            or type(getattr(child, "pid", None)) is not int
            or not getattr(job, "_handle", None)
            or not pipe_handle):
        raise IPCSecurityHold("Unverified native pipe, process or job")
    import orbit_appcontainer as app
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    specs = (
        ("GetNamedPipeClientProcessId",
         (wintypes.HANDLE, ctypes.POINTER(wintypes.ULONG)), wintypes.BOOL),
        ("GetNamedPipeClientSessionId",
         (wintypes.HANDLE, ctypes.POINTER(wintypes.ULONG)), wintypes.BOOL),
        ("GetProcessId", (wintypes.HANDLE,), wintypes.DWORD),
        ("ProcessIdToSessionId",
         (wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)), wintypes.BOOL),
    )
    for name, args, restype in specs:
        api = getattr(kernel, name)
        api.argtypes, api.restype = args, restype
    pipe_pid, pipe_session = wintypes.ULONG(), wintypes.ULONG()
    if not kernel.GetNamedPipeClientProcessId(pipe_handle, ctypes.byref(pipe_pid)):
        raise IPCSecurityHold("Cannot verify named-pipe opener PID")
    if not kernel.GetNamedPipeClientSessionId(pipe_handle, ctypes.byref(pipe_session)):
        raise IPCSecurityHold("Cannot verify named-pipe opener session")
    pinned_pid = kernel.GetProcessId(child._handle)
    if not pinned_pid or pipe_pid.value != pinned_pid or pinned_pid != child.pid:
        raise IPCSecurityHold("Pipe opener differs from pinned sandbox process")
    expected_session = wintypes.DWORD()
    if (not kernel.ProcessIdToSessionId(pinned_pid, ctypes.byref(expected_session))
            or expected_session.value != pipe_session.value):
        raise IPCSecurityHold("Pipe opener is in a different Windows session")
    if app._k32.WaitForSingleObject(child._handle, 0) != app.WAIT_TIMEOUT:
        raise IPCSecurityHold("Sandbox process is no longer live")
    job_member = wintypes.BOOL()
    if (not app._k32.IsProcessInJob(child._handle, job._handle,
                                   ctypes.byref(job_member))
            or job_member.value != 1):
        raise IPCSecurityHold("Pipe process is outside its private Windows job")
    sid = ctypes.c_void_p()
    try:
        hr = app._userenv.DeriveAppContainerSidFromAppContainerName(
            profile, ctypes.byref(sid))
        if hr != 0 or not sid.value:
            raise IPCSecurityHold("Cannot derive expected AppContainer SID")
        app._require_registered_profile(sid)
        app._token_matches_appcontainer(child._handle, sid, expected_capabilities)
    finally:
        if sid.value:
            app._adv.FreeSid(sid)
    return OSVerifiedPeer(pinned_pid, pipe_session.value, profile,
                          _native_origin=_OS_ATTESTATION)


class PreviewIPCSession:
    """One-shot authenticated transcript policy; no sockets, files or HTTP.

    The trusted host must pass its fresh OSVerifiedPeer from the actual
    connected pipe; another PID/session/profile is a hard HOLD. This class
    validates frames but never executes project code or reports READY.
    """

    def __init__(self, *, profile, child_pid, session_id, project_root,
                 max_requests=MAX_REQUESTS, now=None):
        if (type(profile) is not str or not profile.startswith("orbit-rad-")
                or type(child_pid) is not int or child_pid <= 0
                or type(session_id) is not int or session_id < 0
                or type(max_requests) is not int
                or not 1 <= max_requests <= MAX_REQUESTS):
            raise IPCSecurityHold("Invalid host-bound preview session")
        root = Path(project_root)
        if not root.is_absolute() or not root.is_dir() or root.is_symlink():
            raise IPCSecurityHold("Preview root must be an existing canonical directory")
        if root.resolve(strict=True) != root:
            raise IPCSecurityHold("Noncanonical preview project root")
        self.profile, self.child_pid = profile, child_pid
        self.session_id, self.project_root = session_id, str(root)
        self.max_requests = max_requests
        self._clock = now if now is not None else time.monotonic
        self.expires = self._clock() + SESSION_SECONDS
        self.nonce = secrets.token_hex(32)
        self._established = False
        self._next_sequence = 1
        self._pending = None
        self._closed = False

    def _valid_peer(self, peer):
        if (type(peer) is not OSVerifiedPeer
                or peer.pid != self.child_pid
                or peer.session_id != self.session_id
                or peer.appcontainer_profile != self.profile):
            raise IPCSecurityHold("IPC peer does not match pinned LPAC process")
        if self._closed or self._clock() >= self.expires:
            raise IPCSecurityHold("IPC preview session expired or closed")

    def challenge(self):
        if self._closed or self._established:
            raise IPCSecurityHold("IPC challenge already consumed")
        return encode_envelope({"v": PROTOCOL_VERSION, "type": "challenge",
                                "nonce": self.nonce})

    def accept_hello(self, data, peer):
        self._valid_peer(peer)
        if self._established:
            raise IPCSecurityHold("IPC hello cannot be replayed")
        msg = parse_envelope(data)
        if (set(msg) != {"v", "type", "nonce"}
                or msg["type"] != "hello" or type(msg["nonce"]) is not str
                or not secrets.compare_digest(msg["nonce"], self.nonce)):
            raise IPCSecurityHold("IPC handshake challenge mismatch")
        self._established = True
        return {"status": "HANDSHAKE_VERIFIED_NOT_READY",
                "preview_ready": False, "host_approval_verified": False}

    def accept_request(self, data, peer):
        self._valid_peer(peer)
        if not self._established or self._pending is not None:
            raise IPCSecurityHold("IPC request not authorized or pending")
        if self._next_sequence > self.max_requests:
            raise IPCSecurityHold("IPC request budget exhausted")
        msg = parse_envelope(data)
        if (set(msg) != {"v", "type", "seq", "method", "path"}
                or msg["type"] != "request"
                or type(msg["seq"]) is not int or msg["seq"] != self._next_sequence
                or msg["method"] not in ("GET", "HEAD")):
            raise IPCSecurityHold("Invalid bounded IPC request")
        path = validate_local_path(msg["path"])
        self._pending = self._next_sequence
        return {"method": msg["method"], "path": path, "seq": msg["seq"],
                "approved_for_execution": False}

    def accept_response(self, data, peer):
        self._valid_peer(peer)
        if not self._established or self._pending is None:
            raise IPCSecurityHold("Unexpected IPC response")
        msg = parse_envelope(data)
        if (set(msg) != {"v", "type", "seq", "status", "content_type", "body"}
                or msg["type"] != "response"
                or type(msg["seq"]) is not int or msg["seq"] != self._pending
                or type(msg["status"]) is not int
                or msg["status"] not in (200, 404, 500)
                or type(msg["content_type"]) is not str
                or msg["content_type"] not in CONTENT_TYPES
                or type(msg["body"]) is not str
                or len(msg["body"]) > 4 * ((MAX_BODY + 2) // 3)):
            raise IPCSecurityHold("Invalid bounded IPC response")
        try:
            body = base64.b64decode(msg["body"], validate=True)
        except (ValueError, binascii.Error) as exc:
            raise IPCSecurityHold("Invalid encoded IPC response") from exc
        if len(body) > MAX_BODY:
            raise IPCSecurityHold("IPC response body too large")
        self._pending = None
        self._next_sequence += 1
        return {"status": msg["status"], "content_type": msg["content_type"],
                "body": body, "preview_ready": False}

    def close(self):
        self._closed = True
        self._pending = None
