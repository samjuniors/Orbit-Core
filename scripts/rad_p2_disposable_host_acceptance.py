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


def build_probe(destination):
    """Build the reviewed fixture source with the configured local MSVC SDK."""
    toolchain = os.environ.get("VCToolsInstallDir")
    if not toolchain:
        raise RuntimeError("Start from an x64 MSVC Developer Command Prompt")
    compiler = Path(toolchain).resolve(strict=True) / "bin" / "Hostx64" / "x64" / "cl.exe"
    source = Path(__file__).with_name("rad_p2_disposable_probe.c").resolve(strict=True)
    destination.mkdir()
    executable = destination / "probe.exe"
    options = {"CL", "_CL_", "LINK", "_LINK_"}
    env = {key: value for key, value in os.environ.items() if key.upper() not in options}
    command = [
        str(compiler), "/nologo", "/std:c11", "/W4", "/WX", "/O1", "/GS-", "/Zl",
        "/Fe:" + str(executable), str(source), "/link", "/NODEFAULTLIB",
        "/SUBSYSTEM:CONSOLE", "/ENTRY:probe_main", "kernel32.lib", "ws2_32.lib",
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


def record_cleanup(report, key, action):
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


def run_disposable():
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
        "loopback_denial", "external_denial", "process_tree", "failure_recovery",
        "job_cleanup", "recovery_job_cleanup", "profile_deletion",
        "profile_storage_absence", "acl_fixture_cleanup",
    ), "NOT_RUN")
    report = {"status": "HOLD_REQUIRES_INDEPENDENT_OS_ACCEPTANCE",
              "checks": checks, "profile_created": False,
              "real_credentials_accessed": False, "os_build": sys.getwindowsversion().build}
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
            record_cleanup(checks, "profile_storage_absence",
                           lambda: assert_absent(profile_path))

    def remove_temp(root):
        if root.resolve(strict=True) != root or root.is_symlink() or root.is_junction():
            raise RuntimeError("Disposable root identity changed")
        shutil.rmtree(root)
        assert_absent(root)

    try:
        with ExitStack() as cleanup:
            root = Path(tempfile.mkdtemp(prefix="orbit-rad-p2-approved-")).resolve(strict=True)
            cleanup.callback(record_cleanup, checks, "acl_fixture_cleanup", lambda: remove_temp(root))
            profile = "orbit-rad-" + secrets.token_hex(12)
            report.update(temporary_root=str(root), profile_name=profile)
            # Retain exact identifiers even if the controller is interrupted.
            print(json.dumps({"disposable_scope": str(root), "profile": profile}), file=sys.stderr, flush=True)
            project, sibling, credentials = (root / name for name in ("project", "sibling", "credentials"))
            for folder in (project, sibling, credentials):
                folder.mkdir()
            staged_runtime = root / "runtime"
            executable = str(build_probe(staged_runtime))
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

            hr = userenv.CreateAppContainerProfile(
                profile, "Orbit disposable RAD P2", "Synthetic acceptance only",
                None, 0, ctypes.byref(sid))
            report["create_hresult"] = f"0x{hr & 0xffffffff:08x}"
            if hr == 0:
                report["profile_created"] = True
                cleanup.callback(record_cleanup, checks, "profile_deletion", lambda: delete_profile(profile))
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

            def launch(job, mode):
                return app.launch_suspended_verified(
                    profile=profile, executable=executable, args=[executable, mode],
                    cwd=str(project), env={**env, "PORT": str(loopback[1])}, job=job)

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

                stack.callback(record_cleanup, checks, check, stop_job)
                return job, processes, handles

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
                for key in ("loopback", "external"):
                    checks[key + "_denial"] = (
                        "NOT_VERIFIED" if samples["winsock_startup"] else denial_result(
                            {"success": samples[key] == 0, "winerror": samples[key]}, WSAEACCES,
                            report["network_controls"][key].get("success") is True))

                checks["process_tree"] = "FAIL"
                if samples["descendant_error"] or not samples["descendant_pid"]:
                    raise RuntimeError("LPAC descendant did not launch")
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
                job.terminate()
                report["terminated_child_exit_code"] = child.wait(timeout=5)
                if app._k32.WaitForSingleObject(descendant, 5000) != app.WAIT_OBJECT_0:
                    raise RuntimeError("Job descendant did not exit")
                checks["process_tree"] = "PASS"

            checks["failure_recovery"] = "FAIL"
            with ExitStack() as recovery:
                job, processes, _ = open_job(recovery, "recovery_job_cleanup")
                failed = launch(job, "crash")
                processes.append(failed)
                report["forced_failure_exit_code"] = failed.wait(timeout=5)
                recovered = launch(job, "recover")
                processes.append(recovered)
                report["recovery_exit_code"] = recovered.wait(timeout=5)
                if report["forced_failure_exit_code"] == 23 and report["recovery_exit_code"] == 0:
                    checks["failure_recovery"] = "PASS"
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
    args = parser.parse_args(argv)
    if not args.apply or args.confirm != CONFIRM:
        print(json.dumps(plan(), sort_keys=True))
        return 2
    print(json.dumps(run_disposable(), indent=2, sort_keys=True))
    return 2  # HOLD pending review of the individual observations.


if __name__ == "__main__":
    raise SystemExit(main())
