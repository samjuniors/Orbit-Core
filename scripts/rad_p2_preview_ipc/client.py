"""Disposable Windows LPAC named-pipe hello client, NOT a web preview.

Designed to run from a staged, owner-authorized synthetic Python fixture. It
cannot create profiles/ACLs, reach the network, or read arbitrary project data.
The host checks actual kernel client identity before issuing a challenge.
"""
from __future__ import annotations

import ctypes
import os
import re
import sys
import time

from .protocol import IPCSecurityHold, encode_envelope, parse_envelope
from . import winpipe

_PIPE_NAME = re.compile(r"^\\\\\.\\pipe\\LOCAL\\orbit-rad-p2-[0-9a-f]{32}$")


def disposable_child_hello(pipe_name, *, expected_server_pid, timeout_seconds=3):
    """Proof-only handshake; never mark HTTP preview or host authorization READY."""
    if os.name != "nt":
        raise IPCSecurityHold("LPAC IPC client requires Windows")
    if (type(pipe_name) is not str or not _PIPE_NAME.fullmatch(pipe_name)
            or type(expected_server_pid) is not int or expected_server_pid <= 0
            or type(timeout_seconds) not in (int, float)
            or not 0 < timeout_seconds <= 10):
        raise IPCSecurityHold("Malformed trusted host pipe bootstrap")
    from ctypes import wintypes
    kernel = winpipe._win
    kernel.WaitNamedPipeW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD)
    kernel.WaitNamedPipeW.restype = wintypes.BOOL
    kernel.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD,
                                   wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                                   wintypes.DWORD, wintypes.HANDLE)
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.GetNamedPipeServerProcessId.argtypes = (
        wintypes.HANDLE, ctypes.POINTER(wintypes.ULONG))
    kernel.GetNamedPipeServerProcessId.restype = wintypes.BOOL

    if not kernel.WaitNamedPipeW(pipe_name, int(timeout_seconds * 1000)):
        raise IPCSecurityHold("Expected host named pipe unavailable")
    # Do not request GENERIC_WRITE: its mapped rights include
    # FILE_CREATE_PIPE_INSTANCE (0x0004), deliberately absent from our DACL.
    # Request only the exact client mask granted by the SID-scoped pipe.
    PIPE_CLIENT_ACCESS = winpipe.CLIENT_GRANTED_ACCESS
    OPEN_EXISTING = 3
    FILE_FLAG_OVERLAPPED = 0x40000000
    SECURITY_SQOS_PRESENT = 0x00100000
    SECURITY_IDENTIFICATION = 0x00010000
    pipe = kernel.CreateFileW(
        pipe_name, PIPE_CLIENT_ACCESS, 0, None, OPEN_EXISTING,
        FILE_FLAG_OVERLAPPED | SECURITY_SQOS_PRESENT | SECURITY_IDENTIFICATION,
        None)
    if not pipe or pipe == winpipe.INVALID_HANDLE:
        raise IPCSecurityHold("Cannot open exact host-owned named pipe")
    # Reuse the same bounded overlapped byte-frame handling as the host. The
    # client never creates a named pipe or changes its DACL.
    io = object.__new__(winpipe.DisposableLPACPipe)
    io.handle = pipe
    io.name = pipe_name
    try:
        actual_host = wintypes.ULONG()
        if (not kernel.GetNamedPipeServerProcessId(pipe, ctypes.byref(actual_host))
                or actual_host.value != expected_server_pid):
            raise IPCSecurityHold("Named-pipe server PID does not match trusted parent")
        deadline = time.monotonic() + timeout_seconds
        challenge = parse_envelope(io._read_message(deadline))
        if (set(challenge) != {"v", "type", "nonce"}
                or challenge["type"] != "challenge"
                or type(challenge["nonce"]) is not str
                or not re.fullmatch(r"[0-9a-f]{64}", challenge["nonce"])):
            raise IPCSecurityHold("Untrusted pipe challenge")
        io._write_message(encode_envelope(
            {"v": 1, "type": "hello", "nonce": challenge["nonce"]}), deadline)
        return {"status": "CHILD_HANDSHAKE_SENT_NOT_READY",
                "preview_ready": False}
    finally:
        io.handle = None
        kernel.CancelIoEx(pipe, None)
        kernel.CloseHandle(pipe)


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) != 2:
        return 2
    try:
        disposable_child_hello(args[0], expected_server_pid=int(args[1]))
    except (IPCSecurityHold, ValueError):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
