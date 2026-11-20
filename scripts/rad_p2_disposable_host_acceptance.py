"""Manual, disposable Windows LPAC acceptance. No installer or CI entry point."""
from __future__ import annotations

import argparse
import ctypes
import json
import os
from pathlib import Path
import secrets
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
from contextlib import ExitStack

CONFIRM = "CREATE DISPOSABLE ORBIT APPCONTAINER"
EXTERNAL = ("1.1.1.1", 443)
ACCESS_DENIED = 5
WSAEACCES = 10013


def plan():
    return {"status": "HOLD_OPERATOR_CONFIRMATION_REQUIRED",
            "creates_profile": False, "changes_acls": False,
            "launches_child": False, "reads_real_credentials": False,
            "external_network": False, "ci_auto_execution": False}


def connect_control(endpoint):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.settimeout(2)
        try:
            client.connect(endpoint)
        except OSError as exc:
            return {"winerror": getattr(exc, "winerror", None), "errno": exc.errno}
    return {"success": True}


def denial_result(observed, expected_error, control=True):
    if observed.get("success") is True:
        return "FAIL"
    if control and observed.get("winerror") == expected_error:
        return "PASS"
    return "NOT_VERIFIED"


def record_network_checks(checks, samples, controls, *, native_control):
    for key in ("loopback", "external"):
        if samples["winsock_startup"]:
            checks[key + "_denial"] = "BLOCKED"
            samples[key] = None
        else:
            checks[key + "_denial"] = denial_result(
                {"success": samples[key] == 0, "winerror": samples[key]}, WSAEACCES,
                native_control and controls[key].get("success") is True)


def build_probe(destination):
    """Build the reviewed fixture source with the configured local MSVC SDK."""
    destination.mkdir()
    executable = destination / "probe.exe"
    # Never substitute a caller-selected binary for the reviewed native probe.
    # Such a file can report fabricated denials and invalidate OS acceptance.
    if "ORBIT_PROBE_EXECUTABLE" in os.environ:
        raise PermissionError("ORBIT_PROBE_EXECUTABLE override is forbidden; compile the reviewed source")
    toolchain = os.environ.get("VCToolsInstallDir")
    if not toolchain:
        raise RuntimeError("Start from an x64 MSVC Developer Command Prompt")
    compiler = Path(toolchain).resolve(strict=True) / "bin" / "Hostx64" / "x64" / "cl.exe"
    source = Path(__file__).with_name("rad_p2_disposable_probe.c").resolve(strict=True)
    options = {"CL", "_CL_", "LINK", "_LINK_"}
    env = {key: value for key, value in os.environ.items() if key.upper() not in options}
    command = [
        str(compiler), "/nologo", "/std:c11", "/W4", "/WX", "/O1", "/GS-", "/Zl",
        "/Fe:" + str(executable), str(source), "/link", "/NODEFAULTLIB",
        "/SUBSYSTEM:CONSOLE", "/ENTRY:probe_main", "kernel32.lib", "ws2_32.lib", "advapi32.lib",
    ]
    compiled = subprocess.run(command, cwd=destination, env=env, capture_output=True, timeout=30)
    if compiled.returncode != 0:
        output = (compiled.stdout + compiled.stderr).decode(errors="replace")
        raise RuntimeError("MSVC probe build failed: " + output.strip())
    return executable


def read_observations(path):
    keys = ("allowed_read", "allowed_write", "sibling_read", "sibling_write",
            "credential_read", "winsock_startup", "loopback", "external",
            "descendant_pid", "descendant_error")
    with path.open("rb") as result:
        values = struct.unpack("<10I", result.read(41))
    return dict(zip(keys, values))


def record_check(report, key, action):
    try:
        action()
    except Exception as exc:
        report[key] = "FAIL"
        report[key + "_error"] = str(exc)[:240]
    else:
        report[key] = "PASS"


def assert_absent(path):
    try:
        path.lstat()
    except FileNotFoundError:
        return
    raise RuntimeError("Path still exists after cleanup")


def _neutralize_pe_manifest(dll_path):
    """Patch only a structurally valid manifest entry in a *staged* DLL copy.

    This is a disposable diagnostic, not a production runtime preparation
    method. The original Python installation and signed release binaries are
    never modified. A malformed PE must be rejected without writing anything.
    """
    if not dll_path.is_file() or dll_path.is_symlink():
        return False
    if dll_path.stat().st_size > 128 * 1024 * 1024:
        return False
    data = bytearray(dll_path.read_bytes())
    if len(data) < 0x40 or data[:2] != b"MZ":
        return False
    e_lfanew = struct.unpack_from("<I", data, 0x3C)[0]
    if e_lfanew < 0x40 or e_lfanew + 24 > len(data):
        return False
    if data[e_lfanew:e_lfanew + 4] != b"PE\x00\x00":
        return False
    num_sections = struct.unpack_from("<H", data, e_lfanew + 6)[0]
    opt_size = struct.unpack_from("<H", data, e_lfanew + 20)[0]
    opt_header = e_lfanew + 24
    if not 1 <= num_sections <= 96 or opt_header + opt_size > len(data):
        return False
    if opt_size < 2:
        return False
    magic = struct.unpack_from("<H", data, opt_header)[0]
    if magic == 0x20B:
        rsrc_dir_offset = 128  # PE32+ resource entry in data directory
    elif magic == 0x10B:
        rsrc_dir_offset = 112  # PE32 resource entry
    else:
        return False
    if opt_size < rsrc_dir_offset + 8:
        return False
    rsrc_rva, rsrc_size = struct.unpack_from("<II", data, opt_header + rsrc_dir_offset)
    if not rsrc_rva or rsrc_size < 16:
        return False
    sec_offset = opt_header + opt_size
    if sec_offset + num_sections * 40 > len(data):
        return False
    rsrc_raw = None
    rsrc_limit = None
    for i in range(num_sections):
        off = sec_offset + i * 40
        virtual_size, virtual_addr, raw_size, raw_ptr = struct.unpack_from("<4I", data, off + 8)
        if virtual_addr <= rsrc_rva < virtual_addr + max(virtual_size, raw_size):
            relative = rsrc_rva - virtual_addr
            if relative + rsrc_size > raw_size or raw_ptr + raw_size > len(data):
                return False
            rsrc_raw = raw_ptr + relative
            rsrc_limit = rsrc_raw + rsrc_size
            break
    if rsrc_raw is None or rsrc_limit > len(data):
        return False
    num_named, num_id = struct.unpack_from("<HH", data, rsrc_raw + 12)
    count = num_named + num_id
    entries = rsrc_raw + 16
    if count > 4096 or entries + count * 8 > rsrc_limit:
        return False
    for i in range(num_named, count):
        offset = entries + i * 8
        type_id, _ = struct.unpack_from("<II", data, offset)
        if type_id == 24:  # Embedded RT_MANIFEST resource ID
            struct.pack_into("<I", data, offset, 0x7FFF)
            dll_path.write_bytes(data)
            return True
    return False

def stage_python(destination, *, ipc=False):
    """Stage only trusted CPython files in a disposable, bounded fixture."""
    base = Path(sys.base_prefix).resolve(strict=True)
    abi = f"python{sys.version_info.major}{sys.version_info.minor}"
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("python.exe", "python3.dll", abi + ".dll", "vcruntime140.dll",
                 "vcruntime140_1.dll"):
        shutil.copyfile(base / name, destination / name)
    shutil.copytree(base / "Lib", destination / "Lib",
                    ignore=shutil.ignore_patterns("site-packages", "__pycache__", "test"))
    if ipc:
        # ctypes uses native stdlib .pyd/.dll dependencies on Windows. These
        # are copied into the disposable tree, not installed or published.
        shutil.copytree(base / "DLLs", destination / "DLLs",
                        ignore=shutil.ignore_patterns("__pycache__", "test"))
    (destination / (abi + "._pth")).write_text(
        "Lib\nDLLs\n" if ipc else "Lib\n", encoding="ascii")
    _neutralize_pe_manifest(destination / (abi + ".dll"))
    return str(destination / "python.exe")


def verify_controller_exit(app, runtime, root, launch_args, report):
    """Verify automatic job close with a separate disposable controller."""
    from ctypes import wintypes

    handoff = root / "controller-child.handle"
    controller_code = """
import json, sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from orbit_appcontainer import launch_suspended_verified
from orbit_windows_job import WindowsJob
handoff = Path(sys.argv[2])
job = WindowsJob()
child = launch_suspended_verified(job=job, **json.loads(sys.argv[3]))
pending = handoff.with_suffix(".tmp")
pending.write_text(str(child._handle), encoding="ascii")
pending.replace(handoff)
time.sleep(30)
"""
    controller = subprocess.Popen(
        [sys.executable, "-I", "-B", "-c", controller_code, str(runtime),
         str(handoff), json.dumps(launch_args)],
        cwd=root, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    child = wintypes.HANDLE()
    try:
        deadline = time.monotonic() + 10
        while not handoff.is_file():
            if controller.poll() is not None or time.monotonic() >= deadline:
                raise RuntimeError("Disposable controller did not report a live child")
            time.sleep(0.05)
        # Duplicate the exact process handle before interrupting the controller.
        # Only retain wait and emergency termination rights in the test parent.
        duplicate = app._k32.DuplicateHandle
        duplicate.argtypes = (wintypes.HANDLE, wintypes.HANDLE, wintypes.HANDLE,
                              ctypes.POINTER(wintypes.HANDLE), wintypes.DWORD,
                              wintypes.BOOL, wintypes.DWORD)
        duplicate.restype = wintypes.BOOL
        app._k32.GetCurrentProcess.restype = wintypes.HANDLE
        access = 0x00100000 | 0x0001  # SYNCHRONIZE, TERMINATE
        if not duplicate(int(controller._handle), int(handoff.read_text(encoding="ascii")),
                         app._k32.GetCurrentProcess(), ctypes.byref(child), access, False, 0):
            raise app._error("DuplicateHandle (disposable LPAC child)")
        if app._k32.WaitForSingleObject(child, 0) != app.WAIT_TIMEOUT:
            raise RuntimeError("LPAC child exited before controller interruption")
        controller.kill()
        report["interrupted_controller_exit_code"] = controller.wait(timeout=5)
        if app._k32.WaitForSingleObject(child, 5000) != app.WAIT_OBJECT_0:
            raise RuntimeError("LPAC child did not exit after controller interruption")
        report["interrupted_child_exit_verified"] = True
    finally:
        if controller.poll() is None:
            controller.kill()
            controller.wait(timeout=5)
        if child:
            try:
                if app._k32.WaitForSingleObject(child, 0) == app.WAIT_TIMEOUT:
                    app._k32.TerminateProcess(child, 1)
                    app._k32.WaitForSingleObject(child, 5000)
            finally:
                app._k32.CloseHandle(child)


def run_disposable(*, python_startup=False, diagnose_resources=False,
                   capability_registry_read=False, ipc_handshake=False,
                   ipc_wsgi=False):
    # A pipe test is never an implicit privilege or preview-mode switch.
    if ipc_wsgi and not ipc_handshake:
        return {"status": "HOLD_IPC_WSGI_REQUIRES_HANDSHAKE", "profile_created": False}
    if ipc_handshake and not python_startup:
        return {"status": "HOLD_IPC_REQUIRES_STAGED_PYTHON", "profile_created": False}
    if ipc_handshake and capability_registry_read:
        return {"status": "HOLD_IPC_ZERO_CAPABILITY_ONLY", "profile_created": False}
    if os.name != "nt":
        return {"status": "HOLD_WINDOWS_ONLY", "profile_created": False}
    if sys.version_info < (3, 12):
        return {"status": "HOLD_WINDOWS_PYTHON_3_12_REQUIRED", "profile_created": False}
    from ctypes import wintypes

    runtime = Path(__file__).resolve().parents[1] / "source" / "runtime"
    sys.path.insert(0, str(runtime))
    import orbit_appcontainer as app
    from orbit_windows_job import WindowsJob

    userenv = ctypes.WinDLL("userenv", use_last_error=True)
    userenv.CreateAppContainerProfile.argtypes = (
        wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR,
        ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p))
    userenv.CreateAppContainerProfile.restype = ctypes.c_long
    userenv.DeleteAppContainerProfile.argtypes = (wintypes.LPCWSTR,)
    userenv.DeleteAppContainerProfile.restype = ctypes.c_long
    app._k32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    app._k32.OpenProcess.restype = wintypes.HANDLE

    checks = dict.fromkeys((
        "lpac_token", "capabilities", "allowed_read", "allowed_write",
        "sibling_read_denial", "sibling_write_denial", "credential_denial",
        "loopback_denial", "external_denial", "process_tree", "lpac_job_termination", "failure_recovery",
        "job_cleanup", "recovery_job_cleanup", "profile_deletion",
        "profile_storage_absence", "acl_fixture_cleanup",
        "ipc_handshake", "ipc_wsgi",
    ), "NOT_RUN")
    report = {"status": "HOLD_REQUIRES_INDEPENDENT_OS_ACCEPTANCE",
              "checks": checks, "profile_created": False,
              "real_credentials_accessed": False, "os_build": sys.getwindowsversion().build,
              "capabilities_requested": ["registryRead"] if capability_registry_read else []}
    sid = ctypes.c_void_p()
    profile_path = None

    def delete_profile(profile):
        for _ in range(2):
            hr = userenv.DeleteAppContainerProfile(profile)
            report["delete_hresult"] = f"0x{hr & 0xffffffff:08x}"
            if hr == 0:
                break
            time.sleep(0.3)
        else:
            raise OSError(f"DeleteAppContainerProfile failed ({report['delete_hresult']})")
        if profile_path:
            record_check(checks, "profile_storage_absence",
                           lambda: assert_absent(profile_path))

    def remove_temp(root):
        if root.resolve(strict=True) != root or root.is_symlink() or root.is_junction():
            raise RuntimeError("Disposable root identity changed")
        shutil.rmtree(root)
        assert_absent(root)

    try:
        with ExitStack() as cleanup:
            root = Path(tempfile.mkdtemp(prefix="orbit-rad-p2-approved-")).resolve(strict=True)
            cleanup.callback(record_check, checks, "acl_fixture_cleanup", lambda: remove_temp(root))
            profile = "orbit-rad-" + secrets.token_hex(12)
            report.update(temporary_root=str(root), profile_name=profile)
            # Retain exact identifiers even if the controller is interrupted.
            print(json.dumps({"disposable_scope": str(root), "profile": profile}), file=sys.stderr, flush=True)
            project, sibling, credentials = (root / name for name in ("project", "sibling", "credentials"))
            for folder in (project, sibling, credentials):
                folder.mkdir()
            staged_runtime = root / "runtime"
            executable = str(build_probe(staged_runtime))
            # Record provenance for independent acceptance: the reviewed C
            # input and actual built executable bytes are different evidence.
            import hashlib
            report["probe_source_sha256"] = hashlib.sha256(
                Path(__file__).with_name("rad_p2_disposable_probe.c").read_bytes()).hexdigest()
            report["probe_executable_sha256"] = hashlib.sha256(
                Path(executable).read_bytes()).hexdigest()
            system_root = Path(os.environ["SystemRoot"]).resolve(strict=True)
            env = {"SystemRoot": str(system_root), "WINDIR": str(system_root),
                   "PATH": str(system_root / "System32"), "TEMP": str(project), "TMP": str(project)}
            # Confirm the same executable starts before provisioning a profile.
            baseline = subprocess.run(
                [executable, "recover"], cwd=project, env=env,
                capture_output=True, timeout=10)
            report["runtime_control_exit"] = baseline.returncode
            if baseline.returncode != 0:
                raise RuntimeError("Native probe control did not start")
            winsock_control = subprocess.run(
                [executable, "winsock-control"], cwd=project,
                env={**env, "LOCALAPPDATA": os.environ["LOCALAPPDATA"]},
                capture_output=True, timeout=10)
            report["native_winsock_control_exit"] = winsock_control.returncode
            if python_startup:
                checks["python_startup"] = "NOT_RUN"
                python_exe = stage_python(staged_runtime / "python", ipc=ipc_handshake)
                if ipc_handshake:
                    # Source-scoped package, never copied to host Python or install artifacts.
                    shutil.copytree(Path(__file__).with_name("rad_p2_preview_ipc"),
                                    Path(python_exe).parent / "Lib" / "rad_p2_preview_ipc",
                                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

            hr = userenv.CreateAppContainerProfile(
                profile, "Orbit disposable RAD P2", "Synthetic acceptance only",
                None, 0, ctypes.byref(sid))
            report["create_hresult"] = f"0x{hr & 0xffffffff:08x}"
            if hr == 0:
                report["profile_created"] = True
                cleanup.callback(record_check, checks, "profile_deletion", lambda: delete_profile(profile))
                print(json.dumps({"profile_created": profile}), file=sys.stderr, flush=True)
            if sid.value:
                cleanup.callback(app._adv.FreeSid, sid)
            if hr != 0 or not sid.value:
                raise OSError(f"Profile creation failed or did not return a SID ({report['create_hresult']})")

            profile_path = Path(app._require_registered_profile(sid))
            report["profile_storage_existed"] = profile_path.is_dir()
            if not report["profile_storage_existed"]:
                raise RuntimeError("Windows returned a missing AppContainer profile directory")
            sid_string = ctypes.c_void_p()
            if not app._adv.ConvertSidToStringSidW(sid, ctypes.byref(sid_string)):
                raise app._error()
            try:
                sid_text = ctypes.wstring_at(sid_string)
            finally:
                app._k32.LocalFree(sid_string)
            report["profile_sid"] = sid_text

            acl_commands = (
                (root, "/grant", f"*{sid_text}:(X)"),
                (staged_runtime, "/grant", f"*{sid_text}:(OI)(CI)RX"),
                (project, "/grant", f"*{sid_text}:(OI)(CI)M"),
                (project, "/setintegritylevel", "(OI)(CI)L"),
            )
            report["acl_exit_codes"] = []
            for path, *args in acl_commands:
                acl = subprocess.run(
                    [str(system_root / "System32" / "icacls.exe"), str(path), *args],
                    capture_output=True, timeout=10)
                report["acl_exit_codes"].append(acl.returncode)
                if acl.returncode != 0:
                    raise OSError("icacls failed on the disposable fixture")

            (project / "allowed.txt").write_bytes(b"ORBIT_ALLOWED")
            sibling_file = sibling / "project.txt"
            credential_file = credentials / "fake.txt"
            sibling_file.write_bytes(b"SYNTHETIC_SIBLING")
            credential_file.write_bytes(b"FAKE_DATA_ONLY")
            with sibling_file.open("r+b") as fixture:
                if fixture.read() != b"SYNTHETIC_SIBLING":
                    raise RuntimeError("Sibling fixture control failed")
            if credential_file.read_bytes() != b"FAKE_DATA_ONLY":
                raise RuntimeError("Credential fixture control failed")

            listener = cleanup.enter_context(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
            listener.bind(("127.0.0.1", 0))
            listener.listen(4)
            loopback = listener.getsockname()
            report["network_controls"] = {
                "loopback": connect_control(loopback),
                "external": connect_control(EXTERNAL),
            }
            report["external_endpoint"] = f"{EXTERNAL[0]}:{EXTERNAL[1]}"

            caps_requested = [app.LPAC_REGISTRY_READ_CAPABILITY] if capability_registry_read else None

            def launch_args(mode):
                return dict(profile=profile, executable=executable, args=[executable, *mode],
                            cwd=str(project), env={**env, "PORT": str(loopback[1])},
                            capabilities=caps_requested)

            def launch(job, *mode):
                return app.launch_suspended_verified(job=job, **launch_args(mode))

            def open_job(stack, check):
                job = WindowsJob()
                stack.callback(job.close)
                processes = []
                handles = []
                def stop_job():
                    try:
                        job.terminate()
                        for child in processes:
                            child.wait(timeout=5)
                        for handle in handles:
                            if app._k32.WaitForSingleObject(handle, 5000) != app.WAIT_OBJECT_0:
                                raise RuntimeError("Owned descendant did not exit")
                    finally:
                        for handle in handles:
                            app._k32.CloseHandle(handle)
                        for child in processes:
                            child.close()

                stack.callback(record_check, checks, check, stop_job)
                return job, processes, handles

            def verify_recovery():
                with ExitStack() as recovery:
                    job, processes, _ = open_job(recovery, "recovery_job_cleanup")
                    failed = launch(job, "crash")
                    processes.append(failed)
                    report["forced_failure_exit_code"] = failed.wait(timeout=5)
                    recovered = launch(job, "recover")
                    processes.append(recovered)
                    report["recovery_exit_code"] = recovered.wait(timeout=5)
                    if (report["forced_failure_exit_code"], report["recovery_exit_code"]) != (23, 0):
                        raise RuntimeError("Unexpected forced failure or recovery exit")

            if diagnose_resources:
                modes = {
                    "winsock_protocol_catalog": ["winsock-protocol-key"],
                    "winsock_namespace_catalog": ["winsock-namespace-key"],
                    "winsock_provider_load": ["winsock-provider"],
                }
                if python_startup:
                    abi = f"{sys.version_info.major}{sys.version_info.minor}"
                    modes["cpython_dll_open"] = ["python-file", abi]
                    modes["cpython_dll_load"] = ["python-dll", abi]

                resource_results = report["resource_controls"] = {}
                with ExitStack() as diagnostics:
                    job, processes, _ = open_job(diagnostics, "resource_job_cleanup")
                    for label, mode in modes.items():
                        outside = subprocess.run(
                            [executable, *mode], cwd=project,
                            env={**env, "LOCALAPPDATA": os.environ["LOCALAPPDATA"]},
                            capture_output=True, timeout=10)
                        child = launch(job, *mode)
                        processes.append(child)
                        resource_results[label] = {"host_exit": outside.returncode,
                                                   "lpac_exit": child.wait(timeout=5)}
                record_check(checks, "interrupted_controller_cleanup", lambda: verify_controller_exit(
                    app, runtime, root, launch_args(("descendant",)), report))

            record_check(checks, "failure_recovery", verify_recovery)

            if python_startup:
                def python_command(marker):
                    script = f"with open({marker!r}, 'xb') as out: out.write(b'CPYTHON_STARTED')"
                    return [python_exe, "-I", "-S", "-B", "-c", script]

                # Both runs use the same staged interpreter and minimal environment.
                # The host control executes this fixed synthetic marker only.
                control_args = python_command("python-control.txt")
                control = subprocess.run(
                    control_args, cwd=project, env={**env, "LOCALAPPDATA": os.environ["LOCALAPPDATA"]},
                    capture_output=True, timeout=10)
                report["python_control_exit"] = f"0x{control.returncode & 0xffffffff:08x}"
                marker = project / "python-control.txt"
                if control.returncode != 0 or not marker.is_file() or marker.read_bytes() != b"CPYTHON_STARTED":
                    checks["python_startup"] = "NOT_VERIFIED"
                else:
                    with ExitStack() as python_cleanup:
                        job, processes, _ = open_job(python_cleanup, "python_job_cleanup")
                        proc = app.launch_suspended_verified(
                            profile=profile, executable=python_exe,
                            args=python_command("python-lpac.txt"), cwd=str(project), env=env, job=job,
                            capabilities=caps_requested)
                        processes.append(proc)
                        exit_code = proc.wait(timeout=10)
                        report["python_lpac_exit"] = f"0x{exit_code & 0xffffffff:08x}"
                        marker = project / "python-lpac.txt"
                        checks["python_startup"] = (
                            "PASS" if exit_code == 0 and marker.is_file()
                            and marker.read_bytes() == b"CPYTHON_STARTED" else "BLOCKED")

            if ipc_handshake:
                checks["ipc_handshake"] = "BLOCKED"
                if checks["python_startup"] == "PASS":
                    # The browser HTTP preview is deliberately NOT part of this test.
                    sys.path.insert(0, str(Path(__file__).resolve().parent))
                    from rad_p2_preview_ipc.protocol import PreviewIPCSession
                    from rad_p2_preview_ipc.winpipe import DisposableLPACPipe
                    with ExitStack() as pipe_cleanup:
                        job, processes, _ = open_job(pipe_cleanup, "ipc_job_cleanup")
                        pipe = pipe_cleanup.enter_context(DisposableLPACPipe(profile=profile))
                        child_args = [python_exe, "-I", "-B", "-m",
                                      "rad_p2_preview_ipc.client", pipe.name, str(os.getpid())]
                        if ipc_wsgi:
                            child_args.append("--wsgi-fixture")
                        proc = app.launch_suspended_verified(
                            profile=profile, executable=python_exe,
                            args=child_args, cwd=str(project), env=env, job=job,
                            capabilities=caps_requested)
                        processes.append(proc)
                        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
                        kernel.ProcessIdToSessionId.argtypes = (
                            wintypes.DWORD, ctypes.POINTER(wintypes.DWORD))
                        kernel.ProcessIdToSessionId.restype = wintypes.BOOL
                        sid_session = wintypes.DWORD()
                        if not kernel.ProcessIdToSessionId(proc.pid, ctypes.byref(sid_session)):
                            raise RuntimeError("Cannot bind LPAC IPC to real Windows session")
                        transcript = PreviewIPCSession(
                            profile=profile, child_pid=proc.pid, session_id=sid_session.value,
                            project_root=project)
                        result = pipe.accept_handshake(
                            child=proc, job=job, session=transcript, timeout_seconds=3,
                            fixture_wsgi=ipc_wsgi)
                        exit_code = proc.wait(timeout=3)
                        report["ipc_child_exit"] = exit_code
                        report["ipc_handshake_status"] = result["status"]
                        expected = ("WSGI_IPC_ROUNDTRIP_VERIFIED_NOT_READY" if ipc_wsgi
                                    else "HANDSHAKE_VERIFIED_NOT_READY")
                        accepted = exit_code == 0 and result["status"] == expected
                        checks["ipc_handshake"] = "PASS" if accepted else "BLOCKED"
                        if ipc_wsgi:
                            report["ipc_wsgi_response_bytes"] = result.get("body_length")
                            checks["ipc_wsgi"] = "PASS" if accepted else "BLOCKED"

            with ExitStack() as tree:
                job, processes, handles = open_job(tree, "job_cleanup")
                child = launch(job, "probe")
                processes.append(child)
                checks["lpac_token"] = checks["capabilities"] = "PASS"
                result_file = project / "result.bin"
                deadline = time.monotonic() + 12
                while not result_file.is_file():
                    if child.poll() is not None or time.monotonic() >= deadline:
                        report["probe_exit_code"] = child.poll()
                        raise RuntimeError("LPAC probe did not complete its observations")
                    time.sleep(0.05)
                samples = read_observations(result_file)
                report["observations"] = samples
                checks["allowed_read"] = "PASS" if samples["allowed_read"] == 0 else "FAIL"
                checks["allowed_write"] = (
                    "PASS" if samples["allowed_write"] == 0
                    and (project / "allowed.out").read_bytes() == b"ORBIT_WRITTEN" else "FAIL")
                for check, key in (("sibling_read_denial", "sibling_read"),
                                   ("sibling_write_denial", "sibling_write"),
                                   ("credential_denial", "credential_read")):
                    checks[check] = denial_result(
                        {"success": samples[key] == 0, "winerror": samples[key]}, ACCESS_DENIED)
                if sibling_file.read_bytes() != b"SYNTHETIC_SIBLING":
                    checks["sibling_write_denial"] = "FAIL"
                record_network_checks(checks, samples, report["network_controls"],
                                      native_control=winsock_control.returncode == 0)

                def verify_tree():
                    synchronize = 0x00100000
                    query_limited_information = 0x1000
                    descendant = app._k32.OpenProcess(
                        synchronize | query_limited_information, False, samples["descendant_pid"])
                    if not descendant:
                        raise app._error()
                    member = wintypes.BOOL()
                    try:
                        if not app._k32.IsProcessInJob(descendant, job._handle, ctypes.byref(member)):
                            raise app._error()
                        if not member.value:
                            raise RuntimeError("Descendant is outside the private job")
                        handles.append(descendant)
                    finally:
                        if not handles:
                            app._k32.CloseHandle(descendant)
                    if app._k32.WaitForSingleObject(descendant, 0) != app.WAIT_TIMEOUT:
                        raise RuntimeError("No live descendant verified in the private job")

                if samples["descendant_error"] or not samples["descendant_pid"]:
                    checks["process_tree"] = "BLOCKED"
                else:
                    record_check(checks, "process_tree", verify_tree)

                def terminate_members():
                    # Independent control when the isolated token cannot create
                    # a descendant itself. The launcher verifies both members.
                    peer = launch(job, "descendant")
                    processes.append(peer)
                    if child.poll() is not None or peer.poll() is not None:
                        raise RuntimeError("The two LPAC job members were not both live")
                    job.terminate()
                    report["terminated_child_exit_codes"] = [member.wait(timeout=5) for member in processes]
                    for handle in handles:
                        if app._k32.WaitForSingleObject(handle, 5000) != app.WAIT_OBJECT_0:
                            raise RuntimeError("The verified descendant did not exit")

                record_check(checks, "lpac_job_termination", terminate_members)
                if checks["process_tree"] == "PASS" and checks["lpac_job_termination"] != "PASS":
                    checks["process_tree"] = "FAIL"

    except Exception as exc:
        report["exception_type"] = type(exc).__name__
        report["exception_summary"] = str(exc)[:240]
        if getattr(exc, "winerror", None) is not None:
            report["winerror"] = exc.winerror
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Explicitly create the disposable profile and synthetic folders")
    parser.add_argument("--confirm", default="", help="Exact confirmation phrase")
    parser.add_argument("--python-startup", action="store_true",
                        help="Also check startup of the staged trusted base interpreter")
    parser.add_argument("--diagnose-resources", action="store_true",
                        help="Compare read-only dependency checks and test disposable controller interruption")
    parser.add_argument("--capability-registry-read", action="store_true",
                        help="Allow Microsoft LPAC registryRead capability to query Winsock catalog")
    parser.add_argument("--ipc-handshake", action="store_true",
                        help="Opt-in disposable LPAC named-pipe hello (NOT an HTTP preview)")
    parser.add_argument("--ipc-wsgi", action="store_true",
                        help="One synthetic in-memory WSGI request over disposable LPAC IPC; no HTTP listener")
    args = parser.parse_args(argv)
    if not args.apply or args.confirm != CONFIRM:
        print(json.dumps(plan(), sort_keys=True))
        return 2
    print(json.dumps(run_disposable(python_startup=args.python_startup,
                                    diagnose_resources=args.diagnose_resources,
                                    capability_registry_read=args.capability_registry_read,
                                    ipc_handshake=args.ipc_handshake,
                                    ipc_wsgi=args.ipc_wsgi),
                     indent=2, sort_keys=True))
    return 2  # HOLD pending review of the individual observations.


if __name__ == "__main__":
    raise SystemExit(main())
