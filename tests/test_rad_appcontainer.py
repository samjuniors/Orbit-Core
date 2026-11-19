"""RAD P2 fail-closed AppContainer opt-in (disposable Windows tests).

There is intentionally NO real AppContainer profile creation in this suite.
Mocked process entry points prove negative outcomes, not independent sandbox
attestation of a working profile or network/file access controls.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source" / "runtime"))
import orbit_appcontainer
import orbit_browser
import orbit_defense
import orbit_preview


class AppContainerGateTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.temp = Path(temp.name)
        self.one = self.temp / "project-one"
        self.two = self.temp / "project-two"
        self.one.mkdir()
        self.two.mkdir()
        self.original_mode = orbit_preview.PREVIEW_ISOLATION_MODE
        self.original_profiles = orbit_preview.PREVIEW_PROFILE_BINDINGS
        self.addCleanup(self.restore)
        orbit_preview.PREVIEW_ISOLATION_MODE = "appcontainer-required"
        orbit_preview.PREVIEW_PROFILE_BINDINGS = "{}"
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        self.addCleanup(lambda: orbit_preview.shutdown_all())

    def restore(self):
        orbit_preview.PREVIEW_ISOLATION_MODE = self.original_mode
        orbit_preview.PREVIEW_PROFILE_BINDINGS = self.original_profiles

    def args(self):
        return {"preview_id": "p2-probe", "port": self.port, "confirm_run": True,
                "command": [sys.executable, "-m", "http.server"]}

    def name_for(self, root):
        canonical = str(root.resolve())
        digest = hashlib.sha256(os.path.normcase(canonical).encode()).hexdigest()[:24]
        return "orbit-rad-" + digest

    def test_missing_profile_binding_never_launches(self):
        with patch.object(orbit_preview.subprocess, "Popen") as regular, \
             patch.object(orbit_appcontainer, "launch_suspended_verified") as isolated:
            result = orbit_preview.start(self.one, self.args())
        self.assertEqual(result["status"], "HOLD_OS_ISOLATION_REQUIRED")
        self.assertFalse(result["execution_started"])
        regular.assert_not_called()
        isolated.assert_not_called()

    def test_bad_mode_and_bad_bindings_fail_closed(self):
        for mode in ("unexpected", "", "sandbox", "appcontainer-optional"):
            orbit_preview.PREVIEW_ISOLATION_MODE = mode
            self.assertEqual(orbit_preview.isolated_profile_for(self.one)[1]["status"],
                             "HOLD_OS_ISOLATION_REQUIRED")
        orbit_preview.PREVIEW_ISOLATION_MODE = "appcontainer-required"
        for text in ("", "[]", '{"other":"orbit-rad-a"}',
                     json.dumps({str(self.one): "orbit-rad-forged"})):
            orbit_preview.PREVIEW_PROFILE_BINDINGS = text
            self.assertEqual(orbit_preview.isolated_profile_for(self.one)[1]["status"],
                             "HOLD_OS_ISOLATION_REQUIRED")

    def test_exact_project_profile_cannot_authorize_other_root(self):
        orbit_preview.PREVIEW_PROFILE_BINDINGS = json.dumps({
            str(self.one.resolve(strict=True)): self.name_for(self.one)})
        first, error = orbit_preview.isolated_profile_for(self.one)
        if os.name == "nt":
            self.assertIsNone(error)
            self.assertEqual(first, self.name_for(self.one))
        else:
            self.assertEqual(error["status"], "HOLD_OS_ISOLATION_REQUIRED")
        self.assertEqual(orbit_preview.isolated_profile_for(self.two)[1]["status"],
                         "HOLD_OS_ISOLATION_REQUIRED")

    def test_noncanonical_profile_binding_does_not_bypass_exact_root(self):
        canonical = str(self.one.resolve(strict=True))
        alias = canonical + os.sep + "."
        self.assertNotEqual(alias, canonical)
        orbit_preview.PREVIEW_PROFILE_BINDINGS = json.dumps({
            alias: self.name_for(self.one)})
        profile, hold = orbit_preview.isolated_profile_for(self.one)
        self.assertIsNone(profile)
        self.assertEqual(hold["status"], "HOLD_OS_ISOLATION_REQUIRED")

    def test_host_opt_out_flags_are_rejected_for_isolated_process(self):
        orbit_preview.PREVIEW_PROFILE_BINDINGS = json.dumps({
            str(self.one.resolve(strict=True)): self.name_for(self.one)})
        for flag in ("ORBIT_PREVIEW_KEEP_ALIVE", "ORBIT_PREVIEW_INHERIT_ENV"):
            with patch.dict(os.environ, {flag: "1"}):
                self.assertEqual(orbit_preview.isolated_profile_for(self.one)[1]["status"],
                                 "HOLD_OS_ISOLATION_REQUIRED")

    def test_profile_set_only_in_tool_args_cannot_bypass_host_binding(self):
        args = {**self.args(), "appcontainer_profile": self.name_for(self.one)}
        self.assertEqual(orbit_preview.isolated_profile_for(self.one)[1]["status"],
                         "HOLD_OS_ISOLATION_REQUIRED")
        with patch.object(orbit_preview.subprocess, "Popen") as regular:
            self.assertEqual(orbit_preview.start(self.one, args)["status"],
                             "HOLD_OS_ISOLATION_REQUIRED")
            regular.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "Win32 only")
    def test_native_launcher_error_does_not_fallback_to_regular_process(self):
        orbit_preview.PREVIEW_PROFILE_BINDINGS = json.dumps({
            str(self.one.resolve(strict=True)): self.name_for(self.one)})
        with patch.object(orbit_appcontainer, "launch_suspended_verified",
                          side_effect=PermissionError("SYNTHETIC_UNVERIFIED_TOKEN")) as native, \
             patch.object(orbit_preview.subprocess, "Popen") as regular:
            outcome = orbit_preview.start(self.one, self.args())
        self.assertEqual(outcome["status"], "HOLD_OS_ISOLATION_REQUIRED")
        self.assertFalse(outcome["execution_started"])
        native.assert_called_once()
        regular.assert_not_called()
        self.assertNotIn((str(self.one), "p2-probe"), orbit_preview.SESSIONS)

    @unittest.skipUnless(os.name == "nt", "Win32 only")
    def test_invalid_token_is_never_accepted_as_sandbox(self):
        app = orbit_appcontainer
        def open_token(_process, _access, pointer):
            ctypes.cast(pointer, ctypes.POINTER(ctypes.c_void_p)).contents.value = 11
            return 1
        def false_token(_token, klass, pointer, _size, _length):
            self.assertEqual(klass, app.TOKEN_IS_APP_CONTAINER)
            ctypes.cast(pointer, ctypes.POINTER(ctypes.c_uint32)).contents.value = 0
            return 1

        with patch.object(app._adv, "OpenProcessToken", side_effect=open_token), \
             patch.object(app._adv, "GetTokenInformation", side_effect=false_token), \
             patch.object(app._adv, "EqualSid") as equal:
            with self.assertRaises(PermissionError):
                app._token_matches_appcontainer(999, ctypes.c_void_p(111))
            equal.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "Win32 only")
    def test_lpac_access_rejects_ordinary_denied_or_malformed_results(self):
        app = orbit_appcontainer

        def duplicate(_primary, level, pointer):
            self.assertEqual(level, app.SECURITY_IDENTIFICATION)
            ctypes.cast(pointer, ctypes.POINTER(ctypes.c_void_p)).contents.value = 23
            return 1

        def descriptor(_sddl, _revision, pointer, _size):
            ctypes.cast(pointer, ctypes.POINTER(ctypes.c_void_p)).contents.value = 111
            return 1

        for succeeded, allowed, mask in ((1, 1, 1), (1, 1, 3), (1, 0, 2), (0, 1, 2), (1, 1, 2)):
            with self.subTest(succeeded=succeeded, allowed=allowed, mask=mask):
                def access(_descriptor, _token, desired, _mapping, _privs, _size, granted, status):
                    self.assertEqual(desired, app.MAXIMUM_ALLOWED)
                    ctypes.cast(granted, ctypes.POINTER(app.wintypes.DWORD)).contents.value = mask
                    ctypes.cast(status, ctypes.POINTER(app.wintypes.BOOL)).contents.value = allowed
                    return succeeded

                with (patch.object(app._adv, "DuplicateToken", side_effect=duplicate),
                      patch.object(app._adv, "ConvertStringSecurityDescriptorToSecurityDescriptorW",
                                   side_effect=descriptor),
                      patch.object(app._adv, "AccessCheck", side_effect=access),
                      patch.object(app._k32, "LocalFree") as free,
                      patch.object(app._k32, "CloseHandle") as close):
                    if (succeeded, allowed, mask) == (1, 1, 2):
                        app._require_lpac_access(999)
                    else:
                        with self.assertRaises(OSError):
                            app._require_lpac_access(999)
                    free.assert_called_once()
                    close.assert_called_once()

    @unittest.skipUnless(os.name == "nt", "Win32 only")
    def test_unregistered_profile_refused_before_createprocess(self):
        import orbit_windows_job
        app = orbit_appcontainer
        job = orbit_windows_job.WindowsJob()
        self.addCleanup(job.close)
        with patch.object(app._k32, "CreateProcessW") as create:
            with self.assertRaises(PermissionError):
                app.launch_suspended_verified(
                    profile=self.name_for(self.one),
                    executable=sys.executable,
                    args=[sys.executable, "-m", "http.server"],
                    cwd=str(self.one),
                    env={"SystemRoot": os.environ.get("SystemRoot", "C:\\Windows")},
                    job=job)
            create.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "Win32 only")
    def test_lpac_environment_seeds_host_localappdata_and_filters_other_variables(self):
        app = orbit_appcontainer
        with patch.dict(os.environ, {"LOCALAPPDATA": r"C:\Host\Local", "SECRET": "host-secret"}, clear=True):
            block = app._environment_block({
                "SystemRoot": r"C:\Windows", "Port": "8765", "localappdata": r"C:\wrong",
                "USERPROFILE": r"C:\Host", "SECRET": "project-value",
            })
            self.assertEqual(block[:].rstrip("\0").split("\0"), [
                r"LOCALAPPDATA=C:\Host\Local", "PORT=8765", r"SYSTEMROOT=C:\Windows",
            ])
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(PermissionError, "LOCALAPPDATA"):
                app._environment_block({})

    @unittest.skipUnless(os.name == "nt", "Win32 only")
    def test_native_attribute_list_contains_atomic_job_security_capabilities(self):
        import orbit_windows_job
        app = orbit_appcontainer
        job = orbit_windows_job.WindowsJob()
        self.addCleanup(job.close)
        attributes = []
        real_update = app._k32.UpdateProcThreadAttribute

        def track_attribute(*args):
            attributes.append(args[2])
            return real_update(*args)

        with (patch.object(app, "_require_registered_profile", return_value=None),
              patch.object(app._k32, "UpdateProcThreadAttribute",
                           side_effect=track_attribute),
              patch.object(app._k32, "CreateProcessW", return_value=0) as create):
            with self.assertRaises(OSError):
                app.launch_suspended_verified(
                    profile=self.name_for(self.one),
                    executable=sys.executable,
                    args=[sys.executable, "-m", "http.server"],
                    cwd=str(self.one),
                    env={"SystemRoot": os.environ.get("SystemRoot", "C:\\Windows")},
                    job=job)
            create.assert_called_once()
        self.assertEqual(set(attributes), {
            app.PROC_THREAD_ATTRIBUTE_SECURITY_CAPABILITIES,
            app.PROC_THREAD_ATTRIBUTE_ALL_APPLICATION_PACKAGES_POLICY,
            app.PROC_THREAD_ATTRIBUTE_JOB_LIST,
        })

    @unittest.skipUnless(os.name == "nt", "Win32 only")
    def test_real_windows_atomic_job_list_before_first_instruction(self):
        """Actual Win32 JOB_LIST on a harmless suspended, non-AppContainer child.

        This confirms job creation-order behavior ONLY; it is not an LPAC
        filesystem/network or credentials isolation acceptance test.
        """
        import subprocess
        import orbit_windows_job
        app = orbit_appcontainer
        job = orbit_windows_job.WindowsJob()
        self.addCleanup(job.close)
        marker = self.temp / "JOB_LIST_EXECUTED.txt"
        cmd = subprocess.list2cmdline([
            sys.executable, "-c",
            "from pathlib import Path;Path(" + repr(str(marker)) + ").write_text('OK')"])
        buffer = ctypes.create_unicode_buffer(cmd)
        needed = ctypes.c_size_t()
        app._k32.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(needed))
        self.assertGreater(needed.value, 0)
        attrs = ctypes.create_string_buffer(needed.value)
        addr = ctypes.cast(attrs, ctypes.c_void_p)
        self.assertTrue(app._k32.InitializeProcThreadAttributeList(
            addr, 1, 0, ctypes.byref(needed)))
        pi = app.PROCESS_INFORMATION()
        try:
            handles = (app.wintypes.HANDLE * 1)(job._handle)
            self.assertTrue(app._k32.UpdateProcThreadAttribute(
                addr, 0, app.PROC_THREAD_ATTRIBUTE_JOB_LIST,
                ctypes.cast(handles, ctypes.c_void_p),
                ctypes.sizeof(handles), None, None))
            startup = app.STARTUPINFOEXW()
            startup.StartupInfo.cb = ctypes.sizeof(startup)
            startup.lpAttributeList = addr
            flags = (app.EXTENDED_STARTUPINFO_PRESENT |
                     app.CREATE_SUSPENDED | app.CREATE_NO_WINDOW)
            self.assertTrue(app._k32.CreateProcessW(
                sys.executable, buffer, None, None, False, flags, None,
                str(self.one), ctypes.byref(startup), ctypes.byref(pi)),
                ctypes.get_last_error())
            member = app.wintypes.BOOL()
            self.assertTrue(app._k32.IsProcessInJob(
                pi.hProcess, job._handle, ctypes.byref(member)))
            self.assertEqual(member.value, 1)
            self.assertFalse(marker.exists(), "Child code ran before resume")
            self.assertEqual(app._k32.ResumeThread(pi.hThread), 1)
            self.assertEqual(app._k32.WaitForSingleObject(pi.hProcess, 3000),
                             app.WAIT_OBJECT_0)
            self.assertEqual(marker.read_text(), "OK")
        finally:
            if pi.hProcess:
                app._k32.TerminateProcess(pi.hProcess, 1)
                app._k32.CloseHandle(pi.hProcess)
            if pi.hThread:
                app._k32.CloseHandle(pi.hThread)
            app._k32.DeleteProcThreadAttributeList(addr)

    @unittest.skipUnless(os.name == "nt", "Win32 only")
    def test_unowned_healthy_endpoint_never_attests_isolated_preview(self):
        """Even HTTP 200 cannot certify a token-bound listening socket."""
        from unittest.mock import MagicMock
        orbit_preview.PREVIEW_PROFILE_BINDINGS = json.dumps({
            str(self.one.resolve(strict=True)): self.name_for(self.one)})

        class FakeProcess:
            pid = 223344
            returncode = None
            def poll(self):
                return None
            def wait(self, timeout=None):
                self.returncode = 0
                return 0

        fake_job = MagicMock()
        fake_job._handle = 1
        with (patch.dict(os.environ, {
                  "ORBIT_PREVIEW_LOG_HOME": str(self.temp / "preview-logs")}),
              patch.object(orbit_preview, "WindowsJob", return_value=fake_job),
              patch.object(orbit_appcontainer, "launch_suspended_verified",
                           return_value=FakeProcess()) as launched,
              patch.object(orbit_preview, "http_probe",
                           return_value={"healthy": True, "reachable": True,
                                         "http_status": 200}) as health,
              patch.object(orbit_preview, "occupied", return_value=False),
              patch.object(orbit_preview.subprocess, "Popen") as unrestricted):
            answer = orbit_preview.start(self.one, self.args())
        self.assertEqual(answer["status"], "HOLD_OS_ISOLATION_ENDPOINT_UNVERIFIED")
        self.assertFalse(answer["running"])
        self.assertNotIn((str(self.one), "p2-probe"), orbit_preview.SESSIONS)
        launched.assert_called_once()
        unrestricted.assert_not_called()
        health.assert_not_called()
        fake_job.terminate.assert_called_once()
        fake_job.close.assert_called_once()

    def test_isolated_cleanup_pending_session_is_only_available_for_stop(self):
        # A recovery record is never a ready preview or a browser QA target.
        key = orbit_preview.preview_key(self.one, "p2-probe")
        proc = Mock(pid=123, returncode=1)
        proc.poll.return_value = None
        proc.wait.side_effect = [orbit_preview.subprocess.TimeoutExpired("fixture", 3), 1]
        job = Mock()
        orbit_preview.SESSIONS[key] = {
            "proc": proc, "job": job, "preview_id": key[1],
            "isolation": "APPCONTAINER_TOKEN_VERIFIED",
        }
        status_args = {"preview_id": key[1]}
        stop_args = {**status_args, "confirm_stop": True}
        with patch.object(orbit_preview, "http_probe") as http:
            for action in (lambda: orbit_preview.status(self.one, status_args),
                           lambda: orbit_preview.start(self.one, self.args()),
                           lambda: orbit_preview.stop(self.one, status_args),
                           lambda: orbit_preview.stop(self.one, stop_args)):
                result = action()
                self.assertEqual(result["status"], "HOLD_OS_ISOLATION_CLEANUP_UNVERIFIED")
                self.assertNotIn("preview_url", result)
            session, _ = orbit_browser.verify_request(self.one, status_args, orbit_preview)
            self.assertIsNone(session)
            self.assertEqual(orbit_preview.stop(self.one, stop_args)["status"], "STOPPED")
        self.assertNotIn(key, orbit_preview.SESSIONS)
        self.assertEqual(proc.wait.call_count, 2)
        http.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "Win32 only")
    def check_token_sid_buffer(self, malformed_reply):
        app = orbit_appcontainer
        seen = []
        pointer_size = ctypes.sizeof(ctypes.c_void_p)

        def open_token(_process, _access, out_pointer):
            ctypes.cast(out_pointer, ctypes.POINTER(ctypes.c_void_p)).contents.value = 23
            return 1

        def token_info(_token, klass, out_pointer, out_size, length_pointer):
            length = ctypes.cast(
                length_pointer, ctypes.POINTER(ctypes.c_uint32)).contents
            if klass == app.TOKEN_IS_APP_CONTAINER:
                ctypes.cast(out_pointer, ctypes.POINTER(ctypes.c_uint32)).contents.value = 1
                return 1
            if klass == app.TOKEN_CAPABILITIES:
                if not out_pointer:
                    length.value = 16
                    ctypes.set_last_error(122)  # ERROR_INSUFFICIENT_BUFFER
                    seen.append("cap-sized")
                    return 0
                self.assertEqual(out_size, 16)
                ctypes.cast(out_pointer, ctypes.POINTER(ctypes.c_uint32)).contents.value = 0
                seen.append("cap-read")
                return 1
            self.assertEqual(klass, app.TOKEN_APP_CONTAINER_SID)
            if not out_pointer:
                self.assertEqual(out_size, 0)
                length.value = pointer_size + 24
                ctypes.set_last_error(122)
                seen.append("sized")
                return 0
            self.assertEqual(out_size, pointer_size + 24)
            addr = ctypes.cast(out_pointer, ctypes.c_void_p).value
            offset = pointer_size if malformed_reply != "outside" else out_size
            ctypes.cast(out_pointer, ctypes.POINTER(ctypes.c_void_p)).contents.value = (
                addr + offset)
            ctypes.c_ubyte.from_address(addr + pointer_size + 1).value = (
                48 if malformed_reply == "oversized_sid" else 4)
            length.value = pointer_size if malformed_reply == "truncated" else out_size
            seen.append("read")
            return 1

        with (patch.object(app._adv, "OpenProcessToken", side_effect=open_token),
              patch.object(app._adv, "GetTokenInformation",
                           side_effect=token_info),
              patch.object(app._adv, "GetLengthSid", return_value=24),
              patch.object(app._adv, "EqualSid", return_value=1) as equal,
              patch.object(app, "_require_lpac_access") as lpac,
              patch.object(app._k32, "CloseHandle", return_value=1)):
            if malformed_reply:
                with self.assertRaisesRegex(PermissionError, "Malformed child AppContainer SID"):
                    app._token_matches_appcontainer(999, ctypes.c_void_p(77))
                equal.assert_not_called()
                lpac.assert_not_called()
            else:
                app._token_matches_appcontainer(999, ctypes.c_void_p(77))
                equal.assert_called_once()
                lpac.assert_called_once()
        self.assertEqual(seen, ["cap-sized", "cap-read", "sized", "read"])

    @unittest.skipUnless(os.name == "nt", "Win32 only")
    def test_token_sid_query_requires_full_buffer_then_compares(self):
        self.check_token_sid_buffer(None)

    @unittest.skipUnless(os.name == "nt", "Win32 only")
    def test_malformed_token_sid_rejected_before_win32_comparison(self):
        for reply in ("outside", "truncated", "oversized_sid"):
            with self.subTest(reply=reply):
                self.check_token_sid_buffer(reply)

    @unittest.skipUnless(os.name == "nt", "Win32 only")
    def test_unexpected_child_token_capabilities_block_before_sid(self):
        """Real token query must disallow capabilities not requested by Orbit."""
        app = orbit_appcontainer
        observed = []

        def open_token(_process, _access, pointer):
            ctypes.cast(pointer, ctypes.POINTER(ctypes.c_void_p)).contents.value = 23
            return 1

        def token_info(_token, klass, out_pointer, out_size, length_pointer):
            length = ctypes.cast(length_pointer, ctypes.POINTER(ctypes.c_uint32)).contents
            if klass == app.TOKEN_IS_APP_CONTAINER:
                ctypes.cast(out_pointer, ctypes.POINTER(ctypes.c_uint32)).contents.value = 1
                return 1
            self.assertEqual(klass, app.TOKEN_CAPABILITIES)
            if not out_pointer:
                length.value = 16
                ctypes.set_last_error(122)
                observed.append("cap-sized")
                return 0
            self.assertEqual(out_size, 16)
            ctypes.cast(out_pointer, ctypes.POINTER(ctypes.c_uint32)).contents.value = 1
            observed.append("cap-present")
            return 1

        with (patch.object(app._adv, "OpenProcessToken", side_effect=open_token),
              patch.object(app._adv, "GetTokenInformation", side_effect=token_info),
              patch.object(app._adv, "EqualSid") as equal,
              patch.object(app._k32, "CloseHandle", return_value=1)):
            with self.assertRaisesRegex(PermissionError, "token capabilities"):
                app._token_matches_appcontainer(999, ctypes.c_void_p(77))
            equal.assert_not_called()
        self.assertEqual(observed, ["cap-sized", "cap-present"])

    @unittest.skipUnless(os.name == "nt", "Win32 only")
    def test_capability_query_api_error_fails_closed(self):
        app = orbit_appcontainer

        def open_token(_process, _access, pointer):
            ctypes.cast(pointer, ctypes.POINTER(ctypes.c_void_p)).contents.value = 23
            return 1

        def token_info(_token, klass, out_pointer, out_size, _length_pointer):
            if klass == app.TOKEN_IS_APP_CONTAINER:
                ctypes.cast(out_pointer, ctypes.POINTER(ctypes.c_uint32)).contents.value = 1
                return 1
            self.assertEqual(klass, app.TOKEN_CAPABILITIES)
            self.assertEqual(out_size, 0)
            ctypes.set_last_error(5)  # ACCESS_DENIED, not ordinary size probe
            return 0

        with (patch.object(app._adv, "OpenProcessToken", side_effect=open_token),
              patch.object(app._adv, "GetTokenInformation", side_effect=token_info),
              patch.object(app._adv, "EqualSid") as equal,
              patch.object(app._k32, "CloseHandle", return_value=1)):
            with self.assertRaisesRegex(PermissionError, "Cannot verify"):
                app._token_matches_appcontainer(999, ctypes.c_void_p(77))
            equal.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "Win32 only")
    def test_truncated_effective_capability_reply_is_rejected(self):
        app = orbit_appcontainer
        def open_token(_process, _access, ptr):
            ctypes.cast(ptr, ctypes.POINTER(ctypes.c_void_p)).contents.value = 23
            return 1
        def token_info(_token, klass, pointer, size, length_ptr):
            length = ctypes.cast(length_ptr, ctypes.POINTER(ctypes.c_uint32)).contents
            if klass == app.TOKEN_IS_APP_CONTAINER:
                ctypes.cast(pointer, ctypes.POINTER(ctypes.c_uint32)).contents.value = 1
                return 1
            self.assertEqual(klass, app.TOKEN_CAPABILITIES)
            if not pointer:
                length.value = 16
                ctypes.set_last_error(122)
                return 0
            length.value = 0  # Malformed success: no actual TOKEN_GROUPS bytes
            return 1
        with (patch.object(app._adv, "OpenProcessToken", side_effect=open_token),
              patch.object(app._adv, "GetTokenInformation",
                           side_effect=token_info),
              patch.object(app._adv, "EqualSid") as equal,
              patch.object(app._k32, "CloseHandle", return_value=1)):
            with self.assertRaisesRegex(PermissionError, "Malformed"):
                app._token_matches_appcontainer(999, ctypes.c_void_p(77))
            equal.assert_not_called()

    @unittest.skipUnless(os.name == "nt", "Win32 only")
    def test_read_only_appcontainer_sid_derivation_api_available(self):
        # This does not establish that the named profile exists.
        sid = ctypes.c_void_p()
        profile = self.name_for(self.one)
        hr = orbit_appcontainer._userenv.DeriveAppContainerSidFromAppContainerName(
            profile, ctypes.byref(sid))
        self.assertEqual(hr, 0)
        self.assertTrue(sid.value)
        orbit_appcontainer._adv.FreeSid(sid)

    def test_guarded_mode_still_denies_project_code_execution(self):
        defense = orbit_defense.Defense("GUARDED")
        hold = defense.check("orbit_preview_start", self.args(), root=self.one)
        self.assertEqual(hold["status"], "HOLD_DEFENSE_GUARDED")
        self.assertFalse(hold["execution_started"])


if __name__ == "__main__":
    unittest.main()
