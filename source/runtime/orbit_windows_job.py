"""Windows-only OS Job Object for Orbit-owned preview process-tree cleanup.

A Job Object kills member processes on the last handle close, including when
the MCP host terminates unexpectedly. It is NOT a filesystem, network,
credential, AppContainer or restricted-token sandbox.

Uses only stdlib ctypes; imported on Linux without loading Win32 libraries.
"""
from __future__ import annotations

import ctypes
import os

if os.name == "nt":
    from ctypes import wintypes

    # C layout must match WinNT.h; ctypes supplies native SIZE_T padding.
    class BASIC_LIMIT(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class IO_COUNTERS(ctypes.Structure):
        _fields_ = [
            ("ReadOperationCount", ctypes.c_uint64),
            ("WriteOperationCount", ctypes.c_uint64),
            ("OtherOperationCount", ctypes.c_uint64),
            ("ReadTransferCount", ctypes.c_uint64),
            ("WriteTransferCount", ctypes.c_uint64),
            ("OtherTransferCount", ctypes.c_uint64),
        ]

    class EXTENDED_LIMIT(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", BASIC_LIMIT),
            ("IoInfo", IO_COUNTERS),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    KILL_ON_JOB_CLOSE = 0x2000
    EXTENDED_INFORMATION_CLASS = 9
    _win = ctypes.WinDLL("kernel32", use_last_error=True)
    _win.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    _win.CreateJobObjectW.restype = wintypes.HANDLE
    _win.SetInformationJobObject.argtypes = (
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
    )
    _win.SetInformationJobObject.restype = wintypes.BOOL
    _win.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    _win.AssignProcessToJobObject.restype = wintypes.BOOL
    _win.CloseHandle.argtypes = (wintypes.HANDLE,)
    _win.CloseHandle.restype = wintypes.BOOL
    _win.TerminateJobObject.argtypes = (wintypes.HANDLE, wintypes.UINT)
    _win.TerminateJobObject.restype = wintypes.BOOL


def _win_error():
    return ctypes.WinError(ctypes.get_last_error())


class WindowsJob:
    """Own one handle; do not allow inherited or duplicated job handles.

    The child is assigned immediately after Popen, but *not atomically at
    creation*. A hostile child could run before assignment; this class alone
    does not protect against malicious code or make host permissions real.
    """

    def __init__(self):
        if os.name != "nt":
            raise OSError("Windows Job Object is only available on Windows")
        self._handle = _win.CreateJobObjectW(None, None)
        if not self._handle:
            raise _win_error()
        info = EXTENDED_LIMIT()
        info.BasicLimitInformation.LimitFlags = KILL_ON_JOB_CLOSE
        if not _win.SetInformationJobObject(
            self._handle, EXTENDED_INFORMATION_CLASS,
            ctypes.byref(info), ctypes.sizeof(info),
        ):
            error = _win_error()
            self.close()
            raise error

    def assign(self, proc):
        if not self._handle:
            raise RuntimeError("Job Object handle already closed")
        if not _win.AssignProcessToJobObject(self._handle, int(proc._handle)):
            raise _win_error()

    def terminate(self):
        if self._handle and not _win.TerminateJobObject(self._handle, 1):
            raise _win_error()

    def close(self):
        handle, self._handle = self._handle, None
        if handle:
            _win.CloseHandle(handle)

    def __del__(self):
        self.close()
