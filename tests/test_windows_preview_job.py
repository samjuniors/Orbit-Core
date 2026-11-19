"""Windows Job Object acceptance on disposable processes only.

No real user project, IDE session, network service, credentials or system
security configuration is used. These tests verify child process lifetime,
not an OS file/network sandbox or authenticated consent.
"""
from __future__ import annotations

import ctypes
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source" / "runtime"))
import orbit_preview
import orbit_windows_job


@unittest.skipUnless(os.name == "nt", "Windows Job Objects only")
class WindowsPreviewJobTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "test-project"
        self.root.mkdir()
        self.prev_logs = os.environ.get("ORBIT_PREVIEW_LOG_HOME")
        self.prev_keepalive = os.environ.get("ORBIT_PREVIEW_KEEP_ALIVE")
        os.environ["ORBIT_PREVIEW_LOG_HOME"] = str(Path(self.tmp.name) / "logs")
        os.environ.pop("ORBIT_PREVIEW_KEEP_ALIVE", None)
        self.addCleanup(self.restore_environment)
        self.preview_id = "job-qa"
        self.addCleanup(lambda: orbit_preview.stop(
            self.root, {"preview_id": self.preview_id, "confirm_stop": True}))
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]

    def restore_environment(self):
        for key, value in (
            ("ORBIT_PREVIEW_LOG_HOME", self.prev_logs),
            ("ORBIT_PREVIEW_KEEP_ALIVE", self.prev_keepalive),
        ):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def args(self):
        return {
            "preview_id": self.preview_id,
            "port": self.port,
            "command": [sys.executable, "-m", "rad_process_fixture"],
            "confirm_run": True,
        }

    @staticmethod
    def open_child(pid):
        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.OpenProcess.argtypes = (ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32)
        api.OpenProcess.restype = ctypes.c_void_p
        api.IsProcessInJob.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int))
        api.IsProcessInJob.restype = ctypes.c_int
        api.WaitForSingleObject.argtypes = (ctypes.c_void_p, ctypes.c_uint32)
        api.WaitForSingleObject.restype = ctypes.c_uint32
        api.CloseHandle.argtypes = (ctypes.c_void_p,)
        api.CloseHandle.restype = ctypes.c_int
        h = api.OpenProcess(0x00100000 | 0x1000, False, pid)  # SYNCHRONIZE|QUERY_LIMITED
        if not h:
            raise OSError(ctypes.get_last_error(), "Unable to open test child")
        return api, h

    def test_stop_terminates_child_process_in_kernel_job(self):
        # Parent starts a child only after a file created by the test exists,
        # avoiding the pre-assignment race while inspecting the actual kernel
        # Job Object. This does not certify creation-time containment.
        (self.root / "rad_process_fixture.py").write_text(
            "from pathlib import Path\n"
            "import os, subprocess, sys, threading, time\n"
            "from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler\n"
            "base=Path(__file__).parent\n"
            "def child_worker():\n"
            "    for _ in range(8000):\n"
            "        if (base/'go.txt').exists(): break\n"
            "        time.sleep(0.01)\n"
            "    else: return\n"
            "    p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'])\n"
            "    (base/'child.pid').write_text(str(p.pid))\n"
            "threading.Thread(target=child_worker,daemon=True).start()\n"
            "ThreadingHTTPServer(('127.0.0.1',int(os.environ['PORT'])),SimpleHTTPRequestHandler).serve_forever()\n",
            encoding="utf-8",
        )
        started = orbit_preview.start(self.root, self.args())
        self.assertIn(started["status"], {"STARTED_NOT_READY", "READY"}, started)
        session = orbit_preview.SESSIONS[(str(self.root), self.preview_id)]
        job = session["job"]
        self.assertIsInstance(job, orbit_windows_job.WindowsJob)
        (self.root / "go.txt").write_text("test", encoding="utf-8")
        pidfile = self.root / "child.pid"
        for _ in range(80):
            if pidfile.exists():
                break
            time.sleep(0.1)
        self.assertTrue(pidfile.exists(), "Disposable child did not start")
        pid = int(pidfile.read_text())
        api, h = self.open_child(pid)
        api.IsProcessInJob.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int))
        api.IsProcessInJob.restype = ctypes.c_int
        api.WaitForSingleObject.argtypes = (ctypes.c_void_p, ctypes.c_uint32)
        api.WaitForSingleObject.restype = ctypes.c_uint32
        api.CloseHandle.argtypes = (ctypes.c_void_p,)
        api.CloseHandle.restype = ctypes.c_int
        try:
            member = ctypes.c_int(0)
            self.assertTrue(api.IsProcessInJob(h, job._handle, ctypes.byref(member)))
            self.assertEqual(member.value, 1, "Child is outside the Windows kernel Job Object")
            self.assertEqual(api.WaitForSingleObject(h, 0), 0x102)  # WAIT_TIMEOUT
            done = orbit_preview.stop(
                self.root, {"preview_id": self.preview_id, "confirm_stop": True})
            self.assertEqual(done["status"], "STOPPED", done)
            self.assertEqual(api.WaitForSingleObject(h, 3000), 0)  # WAIT_OBJECT_0
        finally:
            api.CloseHandle(h)

    def test_job_closes_descendants_on_abrupt_controller_exit(self):
        child_pid_file = self.root / "abrupt-child.pid"
        signal = self.root / "release.txt"
        controller = self.root / "controller.py"
        controller.write_text(
            "import os, subprocess, sys, time\n"
            "from pathlib import Path\n"
            "from orbit_windows_job import WindowsJob\n"
            "job=WindowsJob()\n"
            "p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)'], "
            "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)\n"
            "job.assign(p)\n"
            f"Path({str(child_pid_file)!r}).write_text(str(p.pid))\n"
            f"signal=Path({str(signal)!r})\n"
            "while not signal.exists(): time.sleep(0.02)\n"
            "os._exit(0)\n",
            encoding="utf-8",
        )
        env = {**os.environ, "PYTHONPATH": str(ROOT / "source" / "runtime")}
        owner = subprocess.Popen(
            [sys.executable, str(controller)],
            cwd=str(self.root), env=env,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        api, handle = None, None
        try:
            for _ in range(100):
                if child_pid_file.exists():
                    break
                if owner.poll() is not None:
                    break
                time.sleep(0.05)
            self.assertTrue(child_pid_file.exists(), "Controller failed before child assignment")
            api, handle = self.open_child(int(child_pid_file.read_text()))
            self.assertEqual(api.WaitForSingleObject(handle, 0), 0x102)
            signal.write_text("release", encoding="utf-8")
            self.assertEqual(owner.wait(timeout=5), 0)
            self.assertEqual(api.WaitForSingleObject(handle, 3000), 0,
                             "Child survived an abrupt controller crash")
        finally:
            if owner.poll() is None:
                owner.kill()
                owner.wait(timeout=3)
            if handle:
                api.CloseHandle(handle)

    def test_project_code_stays_suspended_until_job_assigned_and_resumed(self):
        """Real Windows process never runs fixture code before job association."""
        marker = self.root / "first-instruction.txt"
        (self.root / "rad_process_fixture.py").write_text(
            "from pathlib import Path\n"
            "import os\n"
            "from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler\n"
            "Path('first-instruction.txt').write_text('RAN')\n"
            "ThreadingHTTPServer(('127.0.0.1',int(os.environ['PORT'])),"
            " SimpleHTTPRequestHandler).serve_forever()\n",
            encoding="utf-8",
        )
        original_assign = orbit_preview.WindowsJob.assign
        original_resume = orbit_preview.WindowsJob.resume
        observed = []

        def asserted_assign(job, proc):
            self.assertFalse(marker.exists(), "Project code ran before job assignment")
            observed.append("assign")
            return original_assign(job, proc)

        def asserted_resume(job, proc):
            self.assertFalse(marker.exists(), "Project code ran before resume")
            self.assertEqual(observed, ["assign"])
            observed.append("resume")
            return original_resume(job, proc)

        with (patch.object(orbit_preview.WindowsJob, "assign", asserted_assign),
              patch.object(orbit_preview.WindowsJob, "resume", asserted_resume)):
            result = orbit_preview.start(self.root, self.args())
        self.assertEqual(observed, ["assign", "resume"])
        self.assertEqual(result["status"], "READY", result)
        self.assertTrue(marker.exists(), "The suspended process never resumed")

    def test_failed_resume_cannot_run_project_code(self):
        marker = self.root / "NEVER_EXECUTED.txt"
        (self.root / "rad_process_fixture.py").write_text(
            "from pathlib import Path\n"
            "Path('NEVER_EXECUTED.txt').write_text('FAIL')\n",
            encoding="utf-8",
        )
        with patch.object(orbit_preview.WindowsJob, "resume",
                          side_effect=OSError("TEST_RESUME_DENIED")):
            result = orbit_preview.start(self.root, self.args())
        self.assertEqual(result["status"], "HOLD_HOST_PROCESS_BOUNDARY", result)
        self.assertFalse(marker.exists(), "Suspended child ran despite resume denial")
        self.assertNotIn((str(self.root), self.preview_id), orbit_preview.SESSIONS)

    def test_job_creation_failure_does_not_spawn_process(self):
        (self.root / "rad_process_fixture.py").write_text(
            "import time; time.sleep(30)\n", encoding="utf-8")
        with patch.object(orbit_preview, "WindowsJob",
                          side_effect=OSError("TEST_DENY_CREATE")), \
             patch.object(orbit_preview.subprocess, "Popen") as spawn:
            result = orbit_preview.start(self.root, self.args())
        self.assertEqual(result["status"], "HOLD_HOST_PROCESS_BOUNDARY")
        spawn.assert_not_called()
        self.assertNotIn((str(self.root), self.preview_id), orbit_preview.SESSIONS)

    def test_assignment_failure_returns_hold_and_no_owned_session(self):
        # Safe synthetic failure; runtime must not claim success.
        marker = self.root / "UNASSIGNED_EXECUTION.txt"
        (self.root / "rad_process_fixture.py").write_text(
            "from pathlib import Path\n"
            "Path('UNASSIGNED_EXECUTION.txt').write_text('FAIL')\n",
            encoding="utf-8")
        with patch.object(orbit_preview.WindowsJob, "assign",
                          side_effect=OSError("TEST_DENY_ASSIGN")):
            result = orbit_preview.start(self.root, self.args())
        self.assertEqual(result["status"], "HOLD_HOST_PROCESS_BOUNDARY", result)
        self.assertFalse(marker.exists(), "Unassigned preview executed project code")
        self.assertNotIn((str(self.root), self.preview_id), orbit_preview.SESSIONS)


if __name__ == "__main__":
    unittest.main()
