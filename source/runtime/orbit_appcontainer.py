"""RAD P2 Windows AppContainer preview launch: host-provisioned profiles only.

An opted-in host supplies a pre-existing, project-specific AppContainer
profile. This module never provisions profiles, edits ACLs, grants network
capabilities, or permits a fallback to a regular Windows process. It creates
the child suspended and *atomically* inside a Job Object, verifies its
registered profile, kernel Job membership and actual LPAC token SID, then
resumes the initial thread.

This is a bounded, review-only implementation. Availability and correctness
of specific filesystem/network rights still require independent OS tests.
"""
from __future__ import annotations

import ctypes
import os
import subprocess

if os.name == "nt":
    from ctypes import wintypes

    class STARTUPINFOW(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("lpReserved", wintypes.LPWSTR),
            ("lpDesktop", wintypes.LPWSTR),
            ("lpTitle", wintypes.LPWSTR),
            ("dwX", wintypes.DWORD),
            ("dwY", wintypes.DWORD),
            ("dwXSize", wintypes.DWORD),
            ("dwYSize", wintypes.DWORD),
            ("dwXCountChars", wintypes.DWORD),
            ("dwYCountChars", wintypes.DWORD),
            ("dwFillAttribute", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("wShowWindow", wintypes.WORD),
            ("cbReserved2", wintypes.WORD),
            ("lpReserved2", ctypes.c_void_p),
            ("hStdInput", wintypes.HANDLE),
            ("hStdOutput", wintypes.HANDLE),
            ("hStdError", wintypes.HANDLE),
        ]

    class STARTUPINFOEXW(ctypes.Structure):
        _fields_ = [("StartupInfo", STARTUPINFOW),
                    ("lpAttributeList", ctypes.c_void_p)]

    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [("hProcess", wintypes.HANDLE),
                    ("hThread", wintypes.HANDLE),
                    ("dwProcessId", wintypes.DWORD),
                    ("dwThreadId", wintypes.DWORD)]

    class SECURITY_CAPABILITIES(ctypes.Structure):
        _fields_ = [("AppContainerSid", ctypes.c_void_p),
                    ("Capabilities", ctypes.c_void_p),
                    ("CapabilityCount", wintypes.DWORD),
                    ("Reserved", wintypes.DWORD)]

    class GENERIC_MAPPING(ctypes.Structure):
        _fields_ = [(right, wintypes.DWORD) for right in (
            "GenericRead", "GenericWrite", "GenericExecute", "GenericAll")]

    class PRIVILEGE_SET(ctypes.Structure):
        _fields_ = [
            ("PrivilegeCount", wintypes.DWORD),
            ("Control", wintypes.DWORD),
            ("Privilege", wintypes.DWORD * 3),  # one LUID_AND_ATTRIBUTES
        ]

    EXTENDED_STARTUPINFO_PRESENT = 0x00080000
    CREATE_SUSPENDED = 0x00000004
    CREATE_NO_WINDOW = 0x08000000
    CREATE_UNICODE_ENVIRONMENT = 0x00000400
    PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES = 0x00020009
    PROC_THREAD_ATTRIBUTE_JOB_LIST = 0x0002000D
    PROC_THREAD_ATTRIBUTE_ALL_APPLICATION_PACKAGES_POLICY = 0x0002000F
    PROCESS_CREATION_ALL_APPLICATION_PACKAGES_OPT_OUT = 1
    TOKEN_QUERY = 0x0008
    TOKEN_DUPLICATE = 0x0002
    TOKEN_IS_APP_CONTAINER = 29
    TOKEN_CAPABILITIES = 30
    TOKEN_APP_CONTAINER_SID = 31
    ERROR_INSUFFICIENT_BUFFER = 122
    SECURITY_IDENTIFICATION = 1
    MAXIMUM_ALLOWED = 0x02000000
    LPAC_ONLY_ACCESS = 2
    WAIT_TIMEOUT = 0x102
    WAIT_OBJECT_0 = 0
    INFINITE = 0xFFFFFFFF

    _k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _adv = ctypes.WinDLL("advapi32", use_last_error=True)
    _userenv = ctypes.WinDLL("userenv", use_last_error=True)
    _ole = ctypes.WinDLL("ole32", use_last_error=True)
    _apis = [
        (_k32.InitializeProcThreadAttributeList, (ctypes.c_void_p, wintypes.DWORD,
                                                  wintypes.DWORD, ctypes.POINTER(ctypes.c_size_t)),
         wintypes.BOOL),
        (_k32.UpdateProcThreadAttribute, (ctypes.c_void_p, wintypes.DWORD, ctypes.c_size_t,
                                          ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p,
                                          ctypes.c_void_p), wintypes.BOOL),
        (_k32.DeleteProcThreadAttributeList, (ctypes.c_void_p,), None),
        (_k32.CreateProcessW, (wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p,
                              ctypes.c_void_p, wintypes.BOOL, wintypes.DWORD,
                              ctypes.c_void_p, wintypes.LPCWSTR, ctypes.c_void_p,
                              ctypes.POINTER(PROCESS_INFORMATION)), wintypes.BOOL),
        (_k32.WaitForSingleObject, (wintypes.HANDLE, wintypes.DWORD), wintypes.DWORD),
        (_k32.GetExitCodeProcess, (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)),
         wintypes.BOOL),
        (_k32.TerminateProcess, (wintypes.HANDLE, wintypes.UINT), wintypes.BOOL),
        (_k32.ResumeThread, (wintypes.HANDLE,), wintypes.DWORD),
        (_k32.CloseHandle, (wintypes.HANDLE,), wintypes.BOOL),
        (_k32.IsProcessInJob, (wintypes.HANDLE, wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)), wintypes.BOOL),
        (_k32.LocalFree, (ctypes.c_void_p,), ctypes.c_void_p),
        (_adv.FreeSid, (ctypes.c_void_p,), ctypes.c_void_p),
        (_adv.ConvertSidToStringSidW, (ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)), wintypes.BOOL),
        (_userenv.GetAppContainerFolderPath, (wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p)), ctypes.c_long),
        (_ole.CoTaskMemFree, (ctypes.c_void_p,), None),
        (_userenv.DeriveAppContainerSidFromAppContainerName,
         (wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p)), ctypes.c_long),
        (_adv.OpenProcessToken, (wintypes.HANDLE, wintypes.DWORD,
                                 ctypes.POINTER(wintypes.HANDLE)), wintypes.BOOL),
        (_adv.GetTokenInformation, (wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p,
                                    wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)),
         wintypes.BOOL),
        (_adv.EqualSid, (ctypes.c_void_p, ctypes.c_void_p), wintypes.BOOL),
        (_adv.GetLengthSid, (ctypes.c_void_p,), wintypes.DWORD),
        (_adv.DuplicateToken, (wintypes.HANDLE, ctypes.c_int,
                               ctypes.POINTER(wintypes.HANDLE)), wintypes.BOOL),
        (_adv.ConvertStringSecurityDescriptorToSecurityDescriptorW,
         (wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p),
          ctypes.POINTER(wintypes.DWORD)), wintypes.BOOL),
        (_adv.AccessCheck, (ctypes.c_void_p, wintypes.HANDLE, wintypes.DWORD,
                            ctypes.POINTER(GENERIC_MAPPING), ctypes.POINTER(PRIVILEGE_SET),
                            ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
                            ctypes.POINTER(wintypes.BOOL)), wintypes.BOOL),
    ]
    for _fn, _args, _restype in _apis:
        _fn.argtypes = _args
        _fn.restype = _restype


def _error(api=None):
    code = ctypes.get_last_error()
    if api:
        return ctypes.WinError(code, f"{api}: {ctypes.FormatError(code).strip()}")
    return ctypes.WinError(code)


def _environment_block(env):
    allowed = {"SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "PORT", "HOST"}
    clean = {key.upper(): value for key, value in env.items() if key.upper() in allowed}
    # Windows uses the host LocalAppData to locate the registered profile
    # during process creation, then supplies the scoped value to the child.
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if not os.path.isabs(local_app_data):
        raise PermissionError("Windows AppContainer launch requires host LOCALAPPDATA")
    clean["LOCALAPPDATA"] = local_app_data
    if any("\0" in value for value in clean.values()):
        raise ValueError("Invalid sandbox environment")
    return ctypes.create_unicode_buffer(
        "\0".join(f"{key}={value}" for key, value in sorted(clean.items())) + "\0\0")


def _require_registered_profile(sid):
    """Conservative read-only registration check; never create an OS profile.

    A derived SID alone is not evidence of a provisioned AppContainer.
    GetAppContainerFolderPath may also reject some valid profiles: reject
    those as unsupported instead of falling back to ordinary execution.
    """
    sid_string = ctypes.c_void_p()
    if not _adv.ConvertSidToStringSidW(sid, ctypes.byref(sid_string)):
        raise _error()
    folder = ctypes.c_void_p()
    try:
        hr = _userenv.GetAppContainerFolderPath(
            ctypes.wstring_at(sid_string), ctypes.byref(folder))
        if hr != 0 or not folder.value:
            raise PermissionError(
                f"Host AppContainer profile not verifiably provisioned (0x{hr & 0xffffffff:08x})")
        return ctypes.wstring_at(folder)
    finally:
        if folder.value:
            _ole.CoTaskMemFree(folder)
        _k32.LocalFree(sid_string)


def _require_lpac_access(primary_token):
    """Require the kernel to grant only the restricted application package right."""
    token = wintypes.HANDLE()
    descriptor = ctypes.c_void_p()
    # Everyone covers the normal identity pass. In the restricted pass,
    # ALL APPLICATION PACKAGES grants bit 1, and the restricted package
    # group grants bit 2. The only acceptable result is bit 2 by itself.
    sddl = "O:SYG:SYD:(A;;0x3;;;WD)(A;;0x1;;;AC)(A;;0x2;;;S-1-15-2-2)"
    if not _adv.DuplicateToken(primary_token, SECURITY_IDENTIFICATION, ctypes.byref(token)):
        raise _error("DuplicateToken (LPAC access check)")
    try:
        if not _adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                sddl, 1, ctypes.byref(descriptor), None):
            raise _error("ConvertStringSecurityDescriptorToSecurityDescriptorW")
        mapping = GENERIC_MAPPING()
        privileges = PRIVILEGE_SET()
        size = wintypes.DWORD(ctypes.sizeof(privileges))
        granted, status = wintypes.DWORD(), wintypes.BOOL()
        if not _adv.AccessCheck(
                descriptor, token, MAXIMUM_ALLOWED, ctypes.byref(mapping),
                ctypes.byref(privileges), ctypes.byref(size), ctypes.byref(granted),
                ctypes.byref(status)):
            raise _error("AccessCheck (LPAC)")
        if not status.value or granted.value != LPAC_ONLY_ACCESS:
            raise PermissionError("Child does not have the required LPAC access semantics")
    finally:
        if descriptor.value:
            _k32.LocalFree(descriptor)
        _k32.CloseHandle(token)


def _token_matches_appcontainer(process_handle, expected_sid):
    """Read OS process token while suspended; do not trust a child response."""
    token = wintypes.HANDLE()
    if not _adv.OpenProcessToken(process_handle, TOKEN_QUERY | TOKEN_DUPLICATE, ctypes.byref(token)):
        raise _error("OpenProcessToken (LPAC)")
    try:
        length = wintypes.DWORD()
        value = wintypes.DWORD()
        if not _adv.GetTokenInformation(token, TOKEN_IS_APP_CONTAINER,
                                        ctypes.byref(value), ctypes.sizeof(value),
                                        ctypes.byref(length)):
            raise _error("GetTokenInformation (TokenIsAppContainer)")
        if value.value != 1:
            raise PermissionError("Child has no OS-verified AppContainer token")
        # Requesting zero security capabilities at creation is not a proof
        # of the *effective* child token. Check the OS token before resume.
        # TokenCapabilities returns TOKEN_GROUPS (DWORD GroupCount first).
        cap_length = wintypes.DWORD()
        cap_first = _adv.GetTokenInformation(
            token, TOKEN_CAPABILITIES, None, 0, ctypes.byref(cap_length))
        if (cap_first or ctypes.get_last_error() != ERROR_INSUFFICIENT_BUFFER
                or not 4 <= cap_length.value <= 65536):
            raise PermissionError("Cannot verify child token capabilities")
        cap_buffer = ctypes.create_string_buffer(cap_length.value)
        if not _adv.GetTokenInformation(
                token, TOKEN_CAPABILITIES, ctypes.cast(cap_buffer, ctypes.c_void_p),
                ctypes.sizeof(cap_buffer), ctypes.byref(cap_length)):
            raise _error("GetTokenInformation (TokenCapabilities)")
        if not 4 <= cap_length.value <= ctypes.sizeof(cap_buffer):
            raise PermissionError("Malformed child token capability response")
        cap_count = wintypes.DWORD.from_buffer_copy(cap_buffer.raw[:4]).value
        if cap_count != 0:
            raise PermissionError("Child unexpectedly has token capabilities")
        # TokenAppContainerSid returns TOKEN_APPCONTAINER_INFORMATION and
        # additional SID bytes, not merely one pointer-sized field.
        required = wintypes.DWORD()
        pointer_size = ctypes.sizeof(ctypes.c_void_p)
        sid_size = _adv.GetLengthSid(expected_sid)
        first = _adv.GetTokenInformation(
            token, TOKEN_APP_CONTAINER_SID, None, 0, ctypes.byref(required))
        if (first or ctypes.get_last_error() != ERROR_INSUFFICIENT_BUFFER
                or not 8 <= sid_size <= 68
                or not pointer_size + sid_size <= required.value <= 65536):
            raise PermissionError("Unverifiable AppContainer SID buffer length")
        sid_buffer = ctypes.create_string_buffer(required.value)
        if not _adv.GetTokenInformation(
                token, TOKEN_APP_CONTAINER_SID, ctypes.cast(sid_buffer, ctypes.c_void_p),
                ctypes.sizeof(sid_buffer), ctypes.byref(required)):
            raise _error("GetTokenInformation (TokenAppContainerSid)")
        actual_sid = ctypes.cast(sid_buffer, ctypes.POINTER(ctypes.c_void_p)).contents.value
        start = ctypes.addressof(sid_buffer)
        if (not pointer_size + sid_size <= required.value <= ctypes.sizeof(sid_buffer)
                or not actual_sid
                or not start + pointer_size <= actual_sid <= start + required.value - sid_size):
            raise PermissionError("Malformed child AppContainer SID response")
        # A SID's second byte is the subauthority count. Check its encoded
        # length before passing the returned pointer back to Win32.
        if 8 + 4 * ctypes.c_ubyte.from_address(actual_sid + 1).value != sid_size:
            raise PermissionError("Malformed child AppContainer SID length")
        if not _adv.EqualSid(actual_sid, expected_sid):
            raise PermissionError("Child AppContainer SID does not match host profile")
        _require_lpac_access(token)
    finally:
        _k32.CloseHandle(token)


class IsolatedProcess:
    """Minimal Popen-compatible, native-handle-owning Windows process."""
    def __init__(self, handle, pid):
        self._handle = 0
        self._handle = int(handle)
        self.pid = int(pid)
        self.returncode = None

    def poll(self):
        if self.returncode is not None:
            return self.returncode
        state = _k32.WaitForSingleObject(self._handle, 0)
        if state == WAIT_TIMEOUT:
            return None
        if state != WAIT_OBJECT_0:
            raise _error()
        exit_code = wintypes.DWORD()
        if not _k32.GetExitCodeProcess(self._handle, ctypes.byref(exit_code)):
            raise _error()
        self.returncode = ctypes.c_int32(exit_code.value).value
        return self.returncode

    def wait(self, timeout=None):
        ms = INFINITE if timeout is None else max(0, min(int(timeout * 1000), INFINITE - 1))
        state = _k32.WaitForSingleObject(self._handle, ms)
        if state == WAIT_TIMEOUT:
            raise subprocess.TimeoutExpired("AppContainer process", timeout)
        if state != WAIT_OBJECT_0:
            raise _error()
        return self.poll()

    def kill(self):
        if self.poll() is None and not _k32.TerminateProcess(self._handle, 1):
            raise _error()

    def close(self):
        if self._handle:
            _k32.CloseHandle(self._handle)
            self._handle = 0

    def __del__(self):
        if os.name == "nt":
            self.close()


def launch_suspended_verified(*, profile, executable, args, cwd, env, job):
    """Launch only through OS AppContainer token and explicit bound Job Object.

    Host must pre-provision profile and ACLs outside Orbit. No capability SID,
    including internetClient/internetClientServer, is granted automatically.
    No child standard handles are inherited, preventing host-handle leakage.
    """
    if os.name != "nt":
        raise OSError("AppContainer preview requires Windows")
    if not job or not getattr(job, "_handle", None):
        raise PermissionError("A private Windows Job Object is required")
    if not isinstance(profile, str) or not profile.startswith("orbit-rad-"):
        raise ValueError("Host profile must be project-bound orbit-rad-*")
    if not os.path.isabs(executable) or not os.path.isabs(cwd):
        raise ValueError("Executable and project root must be absolute")
    if not isinstance(args, list) or not args or args[0] != executable:
        raise ValueError("Command must begin with the checked absolute interpreter")
    if any(not isinstance(x, str) or not x or "\0" in x for x in args):
        raise ValueError("Invalid command arguments")
    block = _environment_block(env)
    command = ctypes.create_unicode_buffer(subprocess.list2cmdline(args))
    sid = ctypes.c_void_p()
    size = ctypes.c_size_t()
    attributes = None
    initialized = False
    pi = PROCESS_INFORMATION()
    try:
        result = _userenv.DeriveAppContainerSidFromAppContainerName(
            profile, ctypes.byref(sid))
        if result != 0 or not sid.value:
            raise OSError("Could not derive host-provisioned AppContainer SID")
        _require_registered_profile(sid)
        probe = _k32.InitializeProcThreadAttributeList(None, 3, 0, ctypes.byref(size))
        if probe or ctypes.get_last_error() != ERROR_INSUFFICIENT_BUFFER or not size.value:
            raise _error()
        attributes = ctypes.create_string_buffer(size.value)
        attr_addr = ctypes.cast(attributes, ctypes.c_void_p)
        if not _k32.InitializeProcThreadAttributeList(attr_addr, 3, 0,
                                                       ctypes.byref(size)):
            raise _error()
        initialized = True
        caps = SECURITY_CAPABILITIES(sid, None, 0, 0)
        if not _k32.UpdateProcThreadAttribute(
                attr_addr, 0, PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES,
                ctypes.cast(ctypes.byref(caps), ctypes.c_void_p),
                ctypes.sizeof(caps), None, None):
            raise _error()
        opt_out = wintypes.DWORD(PROCESS_CREATION_ALL_APPLICATION_PACKAGES_OPT_OUT)
        if not _k32.UpdateProcThreadAttribute(
                attr_addr, 0, PROC_THREAD_ATTRIBUTE_ALL_APPLICATION_PACKAGES_POLICY,
                ctypes.cast(ctypes.byref(opt_out), ctypes.c_void_p),
                ctypes.sizeof(opt_out), None, None):
            raise _error()
        # Atomic job membership at process creation: no post-CreateProcess
        # suspended orphan can remain outside the owned Job Object.
        job_handles = (wintypes.HANDLE * 1)(job._handle)
        if not _k32.UpdateProcThreadAttribute(
                attr_addr, 0, PROC_THREAD_ATTRIBUTE_JOB_LIST,
                ctypes.cast(job_handles, ctypes.c_void_p),
                ctypes.sizeof(job_handles), None, None):
            raise _error()
        startup = STARTUPINFOEXW()
        startup.StartupInfo.cb = ctypes.sizeof(startup)
        startup.lpAttributeList = attr_addr
        flags = (EXTENDED_STARTUPINFO_PRESENT | CREATE_SUSPENDED |
                 CREATE_NO_WINDOW | CREATE_UNICODE_ENVIRONMENT)
        if not _k32.CreateProcessW(executable, command, None, None, False,
                                    flags, ctypes.cast(block, ctypes.c_void_p),
                                    cwd, ctypes.byref(startup), ctypes.byref(pi)):
            raise _error("CreateProcessW (LPAC)")
        child = None
        try:
            child = IsolatedProcess(pi.hProcess, pi.dwProcessId)
            # Job membership is assigned by the OS during CreateProcess.
            # Independently read it BEFORE ResumeThread, as well as the token.
            member = wintypes.BOOL()
            if not _k32.IsProcessInJob(pi.hProcess, job._handle, ctypes.byref(member)):
                raise _error()
            if member.value != 1:
                raise PermissionError("Sandbox child is outside its private Job Object")
            _token_matches_appcontainer(pi.hProcess, sid)
            previous = _k32.ResumeThread(pi.hThread)
            if previous == 0xFFFFFFFF:
                raise _error()
            if previous != 1:
                raise RuntimeError("Unexpected sandbox primary-thread suspend count")
            return child
        except BaseException as exc:
            try:
                if child:
                    child.kill()
                    child.wait(timeout=3)
                else:
                    job.terminate()
            except (OSError, subprocess.TimeoutExpired):
                try:
                    job.terminate()
                    if child:
                        child.wait(timeout=3)
                except (OSError, subprocess.TimeoutExpired):
                    raise RuntimeError("Could not confirm sandbox child exit; close its private Job Object") from exc
            finally:
                if child:
                    child.close()
                elif pi.hProcess:
                    _k32.CloseHandle(pi.hProcess)
            raise
    finally:
        if pi.hThread:
            _k32.CloseHandle(pi.hThread)
        if initialized:
            _k32.DeleteProcThreadAttributeList(ctypes.cast(attributes, ctypes.c_void_p))
        if sid.value:
            _adv.FreeSid(sid)
