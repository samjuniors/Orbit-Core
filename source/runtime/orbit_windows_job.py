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

    # Python 3.12 Popen closes the initial thread handle after CreateProcess.
    # A CREATE_SUSPENDED process has only its initial thread; recover that
    # thread's ID using the documented Tool Help snapshot API and resume it
    # only after AssignProcessToJobObject succeeds.
    CREATE_SUSPENDED = 0x00000004
    SNAP_THREADS = 0x00000004
    THREAD_SUSPEND_RESUME = 0x0002
    INVALID_HANDLE = ctypes.c_void_p(-1).value

    class THREADENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ThreadID", wintypes.DWORD),
            ("th32OwnerProcessID", wintypes.DWORD),
            ("tpBasePri", wintypes.LONG),
            ("tpDeltaPri", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
        ]

    _win.CreateToolhelp32Snapshot.argtypes = (wintypes.DWORD, wintypes.DWORD)
    _win.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    _win.Thread32First.argtypes = (wintypes.HANDLE, ctypes.POINTER(THREADENTRY32))
    _win.Thread32First.restype = wintypes.BOOL
    _win.Thread32Next.argtypes = (wintypes.HANDLE, ctypes.POINTER(THREADENTRY32))
    _win.Thread32Next.restype = wintypes.BOOL
    _win.OpenThread.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    _win.OpenThread.restype = wintypes.HANDLE
    _win.ResumeThread.argtypes = (wintypes.HANDLE,)
    _win.ResumeThread.restype = wintypes.DWORD


def _win_error():
    return ctypes.WinError(ctypes.get_last_error())


class WindowsJob:
    """Own one handle; do not allow inherited or duplicated job handles.

    The preview launcher creates the process SUSPENDED, assigns it to this
    job, and only then resumes its initial thread. This closes the earlier
    user-code execution window before assignment. Job Objects still DO NOT
    constrain filesystem, network, tokens, or host permissions.
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

    def resume(self, proc):
        """Resume only a single suspended initial thread after job assignment.

        A fresh CREATE_SUSPENDED process must have exactly one thread: no
        process code has run and no other thread can have been created by it.
        Reject ambiguity or inaccessible threads rather than guessing.
        """
        if not self._handle:
            raise RuntimeError("Cannot resume without an owned Job Object")
        snapshot = _win.CreateToolhelp32Snapshot(SNAP_THREADS, 0)
        if snapshot == INVALID_HANDLE or not snapshot:
            raise _win_error()
        try:
            entry = THREADENTRY32()
            entry.dwSize = ctypes.sizeof(entry)
            if not _win.Thread32First(snapshot, ctypes.byref(entry)):
                raise _win_error()
            threads = []
            while True:
                if entry.th32OwnerProcessID == proc.pid:
                    threads.append(entry.th32ThreadID)
                entry.dwSize = ctypes.sizeof(entry)
                if not _win.Thread32Next(snapshot, ctypes.byref(entry)):
                    # Do not confuse snapshot enumeration failures with the
                    # documented normal end-of-list (ERROR_NO_MORE_FILES).
                    error = ctypes.get_last_error()
                    if error != 18:  # ERROR_NO_MORE_FILES
                        raise ctypes.WinError(error)
                    break
            if len(threads) != 1:
                raise RuntimeError(
                    "A suspended new preview must have exactly one initial thread")
            thread = _win.OpenThread(THREAD_SUSPEND_RESUME, False, threads[0])
            if not thread:
                raise _win_error()
            try:
                previous = _win.ResumeThread(thread)
                if previous == 0xFFFFFFFF:
                    raise _win_error()
                if previous != 1:
                    raise RuntimeError("Unexpected initial thread suspend count")
            finally:
                _win.CloseHandle(thread)
        finally:
            _win.CloseHandle(snapshot)

    def terminate(self):
        if self._handle and not _win.TerminateJobObject(self._handle, 1):
            raise _win_error()

    def close(self):
        handle, self._handle = self._handle, None
        if handle:
            _win.CloseHandle(handle)

    def __del__(self):
        self.close()
