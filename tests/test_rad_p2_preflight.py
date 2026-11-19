"""RAD P2 read-only preflight: no profile writes, no executable launch."""
from __future__ import annotations
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "source" / "runtime"))
import rad_p2_preflight
import orbit_preview


class PreflightTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "disposable-project"
        self.root.mkdir()

    def run_cli(self, extra_env=None, path=None):
        env = {**os.environ, "ORBIT_PREVIEW_ISOLATION": "appcontainer-required",
               "ORBIT_APPCONTAINER_PROFILES": "{}"}
        env.update(extra_env or {})
        output = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "rad_p2_preflight.py"),
             "--project-root", str(path or self.root)],
            env=env, capture_output=True, timeout=10, text=True)
        self.assertEqual(output.returncode, 2, output.stderr)
        data = json.loads(output.stdout)
        self.assertEqual(data["status"], "HOLD_OS_ISOLATION_NOT_VERIFIED")
        for key in ("execution_allowed", "profile_created", "acl_modified",
                    "real_lpac_execution_verified", "filesystem_denial_verified",
                    "network_denial_verified", "host_permission_verified"):
            self.assertIs(data[key], False)
        return data

    def test_absent_profile_is_read_only_hold(self):
        self.run_cli()
        self.assertEqual(list(self.root.iterdir()), [])

    def test_malformed_binding_fails_closed(self):
        data = self.run_cli({"ORBIT_APPCONTAINER_PROFILES": "{invalid-json"})
        self.assertIn("invalid", data["reason"])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_home_path_rejected_without_profile_probe(self):
        data = self.run_cli(path=Path.home())
        self.assertIn("specific project", data["reason"])

    def test_relative_project_path_rejected_without_probe(self):
        data = self.run_cli(path=Path("relative-project"))
        self.assertIn("absolute", data["reason"])

    @unittest.skipUnless(os.name == "nt", "Win32 profile APIs only")
    def test_discovered_profile_is_not_treated_as_security_acceptance(self):
        import orbit_appcontainer as app
        def fake_derive(_name, pointer):
            ctypes.cast(pointer, ctypes.POINTER(ctypes.c_void_p)).contents.value = 123
            return 0

        with (patch.object(orbit_preview, "isolated_profile_for",
                           return_value=("orbit-rad-synthetic", None)),
              patch.object(app._userenv,
                           "DeriveAppContainerSidFromAppContainerName",
                           side_effect=fake_derive),
              patch.object(app, "_require_registered_profile",
                           return_value=None) as profile,
              patch.object(app._adv, "FreeSid") as free):
            report = rad_p2_preflight.inspect(str(self.root))
        profile.assert_called_once()
        free.assert_called_once()
        self.assertEqual(report["read_only_profile_probe"], "PROFILE_PATH_FOUND")
        self.assertEqual(report["status"], "HOLD_OS_ISOLATION_NOT_VERIFIED")
        self.assertFalse(report["execution_allowed"])
        self.assertFalse(report["filesystem_denial_verified"])


if __name__ == "__main__":
    unittest.main()
