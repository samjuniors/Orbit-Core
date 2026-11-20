"""Windows-only experimental SID-restricted, one-shot RAD P2 named pipe.

Not imported by orbit_preview and not a production broker. The pipe requires
a pre-existing profile, uses an explicit security descriptor, refuses remote
clients and verifies the kernel-reported opener against the pinned live LPAC
process, token and Job Object before any handshake. Handle-delegation remains
a separate unverified threat; do not treat a handshake as READY.
"""
from __future__ import annotations

import ctypes
import os
import secrets
import struct
import time

from orbit_lpac_ipc import IPCSecurityHold, MAX_ENVELOPE, verify_connected_pipe_peer

if os.name == "nt":
    from ctypes import wintypes

    class SECURITY_ATTRIBUTES(ctypes.Structure):
        _fields_ = [("nLength", wintypes.DWORD),
                    ("lpSecurityDescriptor", ctypes.c_void_p),
                    ("bInheritHandle", wintypes.BOOL)]

    class OVERLAPPED(ctypes.Structure):
        _fields_ = [("Internal", ctypes.c_void_p),
                    ("InternalHigh", ctypes.c_void_p),
                    ("Offset", wintypes.DWORD),
                    ("OffsetHigh", wintypes.DWORD),
                    ("hEvent", wintypes.HANDLE)]

    _win = ctypes.WinDLL("kernel32", use_last_error=True)
    _adv = ctypes.WinDLL("advapi32", use_last_error=True)
    _procedures = (
        (_win.CreateNamedPipeW, (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                 wintypes.DWORD, wintypes.DWORD, wintypes.DWORD,
                                 wintypes.DWORD, ctypes.POINTER(SECURITY_ATTRIBUTES)),
         wintypes.HANDLE),
        (_win.ConnectNamedPipe, (wintypes.HANDLE, ctypes.POINTER(OVERLAPPED)), wintypes.BOOL),
        (_win.ReadFile, (wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                         ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(OVERLAPPED)),
         wintypes.BOOL),
        (_win.WriteFile, (wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
                          ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(OVERLAPPED)),
         wintypes.BOOL),
        (_win.GetOverlappedResult, (wintypes.HANDLE, ctypes.POINTER(OVERLAPPED),
                                    ctypes.POINTER(wintypes.DWORD), wintypes.BOOL),
         wintypes.BOOL),
        (_win.CancelIoEx, (wintypes.HANDLE, ctypes.POINTER(OVERLAPPED)), wintypes.BOOL),
        (_win.CreateEventW, (ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR),
         wintypes.HANDLE),
        (_win.WaitForSingleObject, (wintypes.HANDLE, wintypes.DWORD), wintypes.DWORD),
        (_win.CloseHandle, (wintypes.HANDLE,), wintypes.BOOL),
        (_win.DisconnectNamedPipe, (wintypes.HANDLE,), wintypes.BOOL),
        (_win.GetCurrentProcess, (), wintypes.HANDLE),
        (_adv.OpenProcessToken, (wintypes.HANDLE, wintypes.DWORD,
                                 ctypes.POINTER(wintypes.HANDLE)), wintypes.BOOL),
        (_adv.GetTokenInformation, (wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p,
                                    wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)), wintypes.BOOL),
        (_adv.ConvertSidToStringSidW, (ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)),
         wintypes.BOOL),
    )
    for function, args, output in _procedures:
        function.argtypes, function.restype = args, output

    INVALID_HANDLE = ctypes.c_void_p(-1).value
    PIPE_ACCESS_DUPLEX = 3
    FILE_FLAG_OVERLAPPED = 0x40000000
    FILE_FLAG_FIRST_PIPE_INSTANCE = 0x00080000
    PIPE_REJECT_REMOTE_CLIENTS = 0x00000008
    ERROR_IO_PENDING = 997
    ERROR_PIPE_CONNECTED = 535
    WAIT_OBJECT_0 = 0
    WAIT_TIMEOUT = 258
    TOKEN_QUERY = 0x0008
    TOKEN_USER = 1


def _current_user_sid():
    """Use the host process's actual token user, not an environment name."""
    if os.name != "nt":
        raise IPCSecurityHold("Windows-only named-pipe security")
    token = wintypes.HANDLE()
    if not _adv.OpenProcessToken(_win.GetCurrentProcess(), TOKEN_QUERY, ctypes.byref(token)):
        raise IPCSecurityHold("Cannot query host token for private pipe DACL")
    try:
        length = wintypes.DWORD()
        if _adv.GetTokenInformation(token, TOKEN_USER, None, 0, ctypes.byref(length)):
            raise IPCSecurityHold("Unexpected host token user response")
        if ctypes.get_last_error() != 122 or not 16 <= length.value <= 65536:
            raise IPCSecurityHold("Cannot size host token user SID")
        buffer = ctypes.create_string_buffer(length.value)
        if not _adv.GetTokenInformation(token, TOKEN_USER, buffer,
                                        len(buffer), ctypes.byref(length)):
            raise IPCSecurityHold("Cannot obtain host token user")
        sid_pointer = ctypes.c_void_p.from_buffer_copy(
            buffer.raw[:ctypes.sizeof(ctypes.c_void_p)]).value
        if not sid_pointer:
            raise IPCSecurityHold("Missing host token user SID")
        string_sid = ctypes.c_void_p()
        if not _adv.ConvertSidToStringSidW(sid_pointer, ctypes.byref(string_sid)):
            raise IPCSecurityHold("Cannot format host token user SID")
        try:
            return ctypes.wstring_at(string_sid)
        finally:
            _win.LocalFree(string_sid)
    finally:
        _win.CloseHandle(token)


def _trusted_profile_sid(profile):
    if os.name != "nt" or type(profile) is not str or not profile.startswith("orbit-rad-"):
        raise IPCSecurityHold("Missing trusted registered LPAC profile")
    import orbit_appcontainer as app
    pointer = ctypes.c_void_p()
    try:
        result = app._userenv.DeriveAppContainerSidFromAppContainerName(
            profile, ctypes.byref(pointer))
        if result != 0 or not pointer.value:
            raise IPCSecurityHold("Could not derive LPAC pipe package SID")
        app._require_registered_profile(pointer)
        rendered = ctypes.c_void_p()
        if not app._adv.ConvertSidToStringSidW(pointer, ctypes.byref(rendered)):
            raise IPCSecurityHold("Cannot render verified LPAC package SID")
        try:
            return ctypes.wstring_at(rendered)
        finally:
            app._k32.LocalFree(rendered)
    finally:
        if pointer.value:
            app._adv.FreeSid(pointer)


def _pipe_descriptor(user_sid, package_sid):
    """Host user + exact LPAC SID; no Everyone/Authenticated Users ACE.

    The low mandatory label may still be rejected by some host policies,
    in which case pipe creation MUST HOLD. Do not substitute a default ACL.
    """
    if (not isinstance(user_sid, str) or not isinstance(package_sid, str)
            or not all(s.startswith("S-1-") and len(s) < 200 for s in
                       (user_sid, package_sid))):
        raise IPCSecurityHold("Invalid exact pipe principal")
    # The client access mask deliberately excludes FILE_CREATE_PIPE_INSTANCE.
    # A session-random name and FIRST_PIPE_INSTANCE further reduce spoofing.
    sddl = ("D:P(A;;GA;;;SY)(A;;0x00120083;;;" + user_sid
            + ")(A;;0x00120083;;;" + package_sid + ")S:(ML;;NW;;;LW)")
    descriptor = ctypes.c_void_p()
    import orbit_appcontainer as app
    if not app._adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            sddl, 1, ctypes.byref(descriptor), None) or not descriptor.value:
        raise IPCSecurityHold("Cannot build least-privilege Windows pipe ACL")
    return descriptor


class DisposableLPACPipe:
    """One-use pre-provisioned LPAC pipe, inactive outside explicit caller."""

    def __init__(self, *, profile):
        if os.name != "nt":
            raise IPCSecurityHold("Windows-only pipe; no nonisolated fallback")
        self.profile = profile
        self.handle = None
        self.name = None
        package_sid = _trusted_profile_sid(profile)
        user_sid = _current_user_sid()
        descriptor = _pipe_descriptor(user_sid, package_sid)
        try:
            self.name = "\\\\.\\pipe\\LOCAL\\orbit-rad-p2-" + secrets.token_hex(16)
            attributes = SECURITY_ATTRIBUTES(
                ctypes.sizeof(SECURITY_ATTRIBUTES), descriptor.value, False)
            handle = _win.CreateNamedPipeW(
                self.name, PIPE_ACCESS_DUPLEX | FILE_FLAG_OVERLAPPED
                | FILE_FLAG_FIRST_PIPE_INSTANCE, PIPE_REJECT_REMOTE_CLIENTS,
                1, 4096, 4096, 0, ctypes.byref(attributes))
            if not handle or handle == INVALID_HANDLE:
                raise IPCSecurityHold("Cannot create SID-restricted LPAC pipe")
            self.handle = handle
        finally:
            _win.LocalFree(descriptor)

    def _overlapped(self, operation, size_or_bytes, deadline):
        """Bounded overlapped read/write with cancellation before freeing buffers."""
        if self.handle is None:
            raise IPCSecurityHold("Named pipe already closed")
        event = _win.CreateEventW(None, True, False, None)
        if not event:
            raise IPCSecurityHold("Cannot create named-pipe wait event")
        ov = OVERLAPPED()
        ov.hEvent = event
        transferred = wintypes.DWORD()
        if operation == "read":
            buffer = ctypes.create_string_buffer(size_or_bytes)
            nbytes = size_or_bytes
        else:
            buffer = ctypes.create_string_buffer(size_or_bytes)
            nbytes = len(size_or_bytes)
        try:
            if operation == "read":
                okay = _win.ReadFile(self.handle, buffer, nbytes,
                                     ctypes.byref(transferred), ctypes.byref(ov))
            else:
                okay = _win.WriteFile(self.handle, buffer, nbytes,
                                      ctypes.byref(transferred), ctypes.byref(ov))
            if not okay:
                if ctypes.get_last_error() != ERROR_IO_PENDING:
                    raise IPCSecurityHold("Native named-pipe I/O rejected")
                remain = deadline - time.monotonic()
                result = _win.WaitForSingleObject(event, max(0, int(remain * 1000)))
                if result != WAIT_OBJECT_0:
                    _win.CancelIoEx(self.handle, ctypes.byref(ov))
                    # Drain the pending operation before buffers go out of scope.
                    _win.GetOverlappedResult(self.handle, ctypes.byref(ov),
                                             ctypes.byref(transferred), True)
                    raise IPCSecurityHold("Named-pipe I/O deadline exceeded")
                if not _win.GetOverlappedResult(self.handle, ctypes.byref(ov),
                                                ctypes.byref(transferred), False):
                    raise IPCSecurityHold("Named-pipe overlapped I/O failed")
            if transferred.value != nbytes and operation == "write":
                raise IPCSecurityHold("Partial named-pipe write")
            if not transferred.value:
                raise IPCSecurityHold("Pipe closed before frame completed")
            return buffer.raw[:transferred.value] if operation == "read" else None
        finally:
            _win.CloseHandle(event)

    def _read_exact(self, length, deadline):
        chunks = []
        left = length
        while left:
            piece = self._overlapped("read", left, deadline)
            chunks.append(piece)
            left -= len(piece)
        return b"".join(chunks)

    def _read_message(self, deadline):
        length = struct.unpack(">I", self._read_exact(4, deadline))[0]
        if not 0 < length <= MAX_ENVELOPE:
            raise IPCSecurityHold("Named-pipe frame length rejected")
        return self._read_exact(length, deadline)

    def _write_message(self, data, deadline):
        if not isinstance(data, bytes) or not 0 < len(data) <= MAX_ENVELOPE:
            raise IPCSecurityHold("Named-pipe outbound frame length rejected")
        self._overlapped("write", struct.pack(">I", len(data)), deadline)
        self._overlapped("write", data, deadline)

    def accept_handshake(self, *, child, job, session, timeout_seconds=3):
        """Verify kernel peer and one-shot nonce; NEVER mark preview READY."""
        if (type(timeout_seconds) not in (int, float)
                or not 0 < timeout_seconds <= 10 or self.handle is None):
            raise IPCSecurityHold("Invalid bounded LPAC pipe handshake")
        if self.profile != session.profile or child.pid != session.child_pid:
            raise IPCSecurityHold("Pipe host session mismatch")
        deadline = time.monotonic() + timeout_seconds
        event = _win.CreateEventW(None, True, False, None)
        if not event:
            raise IPCSecurityHold("Cannot wait for named-pipe client")
        ov = OVERLAPPED()
        ov.hEvent = event
        count = wintypes.DWORD()
        try:
            okay = _win.ConnectNamedPipe(self.handle, ctypes.byref(ov))
            if not okay:
                error = ctypes.get_last_error()
                if error == ERROR_IO_PENDING:
                    remain = deadline - time.monotonic()
                    waited = _win.WaitForSingleObject(event, max(0, int(remain * 1000)))
                    if waited != WAIT_OBJECT_0:
                        _win.CancelIoEx(self.handle, ctypes.byref(ov))
                        _win.GetOverlappedResult(self.handle, ctypes.byref(ov),
                                                 ctypes.byref(count), True)
                        raise IPCSecurityHold("Named-pipe client connection timed out")
                    if not _win.GetOverlappedResult(self.handle, ctypes.byref(ov),
                                                    ctypes.byref(count), False):
                        raise IPCSecurityHold("Cannot complete named-pipe connection")
                elif error != ERROR_PIPE_CONNECTED:
                    raise IPCSecurityHold("Unverified named-pipe connection")
            peer = verify_connected_pipe_peer(
                self.handle, child=child, job=job, profile=self.profile)
            if peer.session_id != session.session_id:
                raise IPCSecurityHold("Native Windows session mismatch")
            self._write_message(session.challenge(), deadline)
            return session.accept_hello(self._read_message(deadline), peer)
        finally:
            _win.CloseHandle(event)
            self.close()

    def close(self):
        handle, self.handle = self.handle, None
        if handle:
            _win.CancelIoEx(handle, None)
            _win.DisconnectNamedPipe(handle)
            _win.CloseHandle(handle)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
