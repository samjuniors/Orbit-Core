"""Opt-in disposable Windows LPAC acceptance rehearsal (never run by CI).

Requires explicit --apply and the confirmation string. Creates one *new*
per-user AppContainer profile and synthetic files, scopes ACL changes to a
new temporary project, and removes them in finally. No real credentials,
user-project paths, external network addresses, or system-wide ACL changes.
Every outcome remains HOLD until separately verified by the owner/reviewer.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import http.server
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import time

CONFIRM = "CREATE DISPOSABLE ORBIT APPCONTAINER"


def plan():
    return {"status": "HOLD_OPERATOR_CONFIRMATION_REQUIRED",
            "creates_profile": False, "changes_acls": False,
            "launches_child": False, "reads_real_credentials": False,
            "external_network": False, "ci_auto_execution": False}


def run_disposable():
    if os.name != "nt":
        return {"status": "HOLD_WINDOWS_ONLY", "profile_created": False}
    from ctypes import wintypes
    runtime = Path(__file__).resolve().parents[1] / "source" / "runtime"
    if not (runtime / "orbit_appcontainer.py").is_file():
        return {"status": "HOLD_ORBIT_RUNTIME_MISSING", "profile_created": False}
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
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    advapi.ConvertSidToStringSidW.argtypes = (
        ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))
    advapi.ConvertSidToStringSidW.restype = wintypes.BOOL
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.LocalFree.argtypes = (ctypes.c_void_p,)
    k32.LocalFree.restype = ctypes.c_void_p

    report = {"status": "HOLD_REAL_OS_ACCEPTANCE_INCOMPLETE",
              "profile_created": False, "profile_deleted": False,
              "test_directory_deleted": False, "real_lpac_token_verified": False,
              "allowed_file": "NOT_RUN", "sibling_denial": "NOT_RUN",
              "local_network_denial": "NOT_RUN", "isolation_certified": False,
              "real_credentials_accessed": False, "external_network": False}
    temp = None
    profile = None
    sid = ctypes.c_void_p()
    job = None
    child = None
    server = None

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path != "/synthetic":
                self.send_error(404)
                return
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ORBIT_P2_SYNTHETIC_ONLY")
        def log_message(self, *_):
            pass

    def change_test_acl(folder, *args):
        proc = subprocess.run(["icacls.exe", str(folder), *args],
                              capture_output=True, text=True, timeout=15)
        return {"exit": proc.returncode,
                "message": (proc.stdout + proc.stderr).strip()[:220]}

    try:
        temp = Path(tempfile.mkdtemp(prefix="orbit-rad-p2-approved-"))
        project, sibling = temp / "synthetic-project", temp / "sealed-sibling"
        project.mkdir()
        sibling.mkdir()
        (project / "allowed.txt").write_text("ORBIT_ALLOWED", encoding="ascii")
        (sibling / "fake-credential.txt").write_text(
            "FAKE_DATA_ONLY", encoding="ascii")
        if project.is_symlink() or project.is_junction():
            raise RuntimeError("Synthetic root unexpectedly redirected")
        root = str(project.resolve(strict=True))
        profile = "orbit-rad-" + hashlib.sha256(
            os.path.normcase(root).encode()).hexdigest()[:24]
        report["temporary_root"] = str(temp)
        report["profile_name"] = profile
        # A collision must fail; NEVER adopt or delete an existing profile.
        hr = userenv.CreateAppContainerProfile(
            profile, "Orbit disposable RAD P2", "Synthetic acceptance only",
            None, 0, ctypes.byref(sid))
        report["create_hresult"] = f"0x{hr & 0xffffffff:08x}"
        # S_OK means this invocation created a profile even if the SID
        # output is unexpectedly missing: still delete *our* new profile
        # in finally instead of leaking per-user registration.
        if hr == 0:
            report["profile_created"] = True
        if hr != 0 or not sid.value:
            report["blocker"] = "PROFILE_CREATION_FAILED_OR_MISSING_SID"
            return report

        ptr = ctypes.c_void_p()
        if not advapi.ConvertSidToStringSidW(sid, ctypes.byref(ptr)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            sid_string = ctypes.wstring_at(ptr)
        finally:
            k32.LocalFree(ptr)
        report["profile_sid"] = sid_string
        # The ONLY user-visible ACL changes are to the new synthetic folder.
        grant = change_test_acl(project, "/grant", "*" + sid_string + ":(OI)(CI)M")
        low = change_test_acl(project, "/setintegritylevel", "(OI)(CI)L")
        report["synthetic_folder_grant"] = grant
        report["synthetic_folder_integrity"] = low
        if grant["exit"] or low["exit"]:
            report["blocker"] = "SYNTHETIC_ACL_CHANGE_FAILED"
            return report

        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        system_root = Path(os.environ.get("SystemRoot", r"C:\Windows"))
        cmd = str(system_root / "System32" / "cmd.exe")
        curl = str(system_root / "System32" / "curl.exe")
        script = project / "probe.cmd"
        # Generated paths are local synthetic paths only, never user inputs.
        script.write_text(
            "@echo off\n"
            + f'type "{project / "allowed.txt"}" > "{project / "allowed.out"}" 2>nul\n'
            + f'echo A_RC=%errorlevel% > "{project / "allowed.rc"}"\n'
            + f'type "{sibling / "fake-credential.txt"}" > "{project / "sibling.out"}" 2>nul\n'
            + f'echo S_RC=%errorlevel% > "{project / "sibling.rc"}"\n'
            + f'"{curl}" --silent --connect-timeout 1 --max-time 2 http://127.0.0.1:{server.server_port}/synthetic > "{project / "network.out"}" 2>nul\n'
            + f'echo N_RC=%errorlevel% > "{project / "network.rc"}"\n'
            + f'echo COMPLETE > "{project / "finished.txt"}"\n',
            encoding="ascii")
        env = {"SystemRoot": str(system_root), "WINDIR": str(system_root),
               "PATH": str(system_root / "System32"),
               "TEMP": str(project), "TMP": str(project)}
        job = WindowsJob()
        try:
            child = app.launch_suspended_verified(
                profile=profile, executable=cmd, args=[cmd, "/D", "/C", str(script)],
                cwd=root, env=env, job=job)
            # This returns only after checking the actual LPAC child token,
            # zero effective capabilities, exact SID and Job membership.
            report["real_lpac_token_verified"] = True
            try:
                report["child_exit_code"] = child.wait(timeout=8)
            except subprocess.TimeoutExpired:
                job.terminate()
                report["child_exit_code"] = "TIMEOUT_KILLED"
        except (OSError, PermissionError, RuntimeError, ValueError) as exc:
            report["blocker"] = "LPAC_LAUNCH_OR_TOKEN_VERIFICATION_FAILED"
            report["exception_type"] = type(exc).__name__
            report["exception_summary"] = str(exc)[:220]
            return report

        if not (project / "finished.txt").is_file():
            report["blocker"] = "CHILD_PROBE_NOT_COMPLETED"
            return report
        allowed = project / "allowed.out"
        report["allowed_file"] = ("OBSERVED_PASS" if allowed.exists()
            and allowed.read_text(errors="replace").strip() == "ORBIT_ALLOWED"
            else "FAIL_OR_INCONCLUSIVE")
        sibling_out, sibling_rc = project / "sibling.out", project / "sibling.rc"
        report["sibling_denial"] = ("OBSERVED_DENIED" if sibling_rc.exists()
            and sibling_rc.read_text().strip() != "S_RC=0"
            and (not sibling_out.exists() or "FAKE_DATA_ONLY" not in
                 sibling_out.read_text(errors="replace"))
            else "FAIL_OR_INCONCLUSIVE")
        network_out, network_rc = project / "network.out", project / "network.rc"
        # curl failure alone is not network isolation proof: it may not launch.
        report["local_network_denial"] = ("OBSERVED_NOT_ATTESTED"
            if network_rc.exists() and network_rc.read_text().strip() != "N_RC=0"
            and (not network_out.exists() or "ORBIT_P2_SYNTHETIC_ONLY" not in
                 network_out.read_text(errors="replace"))
            else "FAIL_OR_INCONCLUSIVE")
    except Exception as exc:
        report["blocker"] = "DISPOSABLE_PROBE_EXCEPTION"
        report["exception_type"] = type(exc).__name__
        report["exception_summary"] = str(exc)[:220]
    finally:
        if server:
            server.shutdown()
            server.server_close()
        if job:
            try:
                job.terminate()
            except OSError as exc:
                report["job_cleanup_error"] = str(exc)[:180]
            job.close()
        if child:
            try:
                child.wait(timeout=3)
            except (OSError, subprocess.TimeoutExpired):
                pass
            child.close()
        if sid.value:
            advapi.FreeSid(sid)
        if report["profile_created"] and profile:
            for _ in range(2):
                hr = userenv.DeleteAppContainerProfile(profile)
                report["delete_hresult"] = f"0x{hr & 0xffffffff:08x}"
                if hr == 0:
                    report["profile_deleted"] = True
                    break
                time.sleep(0.3)
        if temp:
            try:
                shutil.rmtree(temp)
                report["test_directory_deleted"] = True
            except OSError as exc:
                report["test_directory_cleanup_error"] = str(exc)[:180]
        report["status"] = "HOLD_REQUIRES_INDEPENDENT_OS_ACCEPTANCE"
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="Explicitly create the disposable profile and synthetic folder")
    parser.add_argument("--confirm", default="", help="Exact confirmation phrase")
    args = parser.parse_args(argv)
    if not args.apply or args.confirm != CONFIRM:
        print(json.dumps(plan(), sort_keys=True))
        return 2
    result = run_disposable()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2  # Deliberately HOLD even when synthetic observations look good.


if __name__ == "__main__":
    raise SystemExit(main())
