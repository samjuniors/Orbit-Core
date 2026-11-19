"""Real disposable MCP stdio negative checks for host-owned AppContainer mode.

Never creates a Windows profile, changes ACLs, accesses credentials or runs a
project interpreter. This verifies the early refusal path, not full OS sandbox.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AppContainerStdioTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name) / "synthetic"
        self.root.mkdir()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]

    def call(self, mode, *, defense="NORMAL", profiles="{}"):
        command = [sys.executable, "-m", "http.server"]
        request = {
            "jsonrpc": "2.0", "id": 1, "method": "tools/call",
            "params": {"name": "orbit_preview_start", "arguments": {
                "project_root": str(self.root),
                "preview_id": "p2-dry-run",
                "command": command, "port": self.port, "confirm_run": True,
            }},
        }
        env = {**os.environ,
               "ORBIT_DEFENSE_MODE": defense,
               "ORBIT_PREVIEW_ISOLATION": mode,
               "ORBIT_APPCONTAINER_PROFILES": profiles,
               "ORBIT_LOCAL_DB": str(self.root.parent / "synthetic.sqlite3")}
        result = subprocess.run(
            [sys.executable, str(ROOT / "source/runtime/orbit_mcp.py")],
            input=(json.dumps(request) + "\n").encode("utf-8"),
            capture_output=True, timeout=15, env=env, cwd=str(ROOT))
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        self.assertEqual(len(result.stdout.splitlines()), 1)
        response = json.loads(result.stdout.splitlines()[0])
        self.assertIn("result", response)
        return json.loads(response["result"]["content"][0]["text"])

    def test_required_missing_profile_is_denied_before_launch(self):
        result = self.call("appcontainer-required")
        self.assertEqual(result["status"], "HOLD_OS_ISOLATION_REQUIRED")
        self.assertFalse(result["execution_started"])
        self.assertFalse((self.root / "server_marker").exists())

    def test_invalid_policy_is_fail_closed(self):
        result = self.call("invalid_mode")
        self.assertEqual(result["status"], "HOLD_OS_ISOLATION_REQUIRED")
        self.assertFalse(result["execution_started"])

    def test_guarded_defense_keeps_prelaunch_denial_priority(self):
        result = self.call("appcontainer-required", defense="GUARDED")
        self.assertEqual(result["status"], "HOLD_DEFENSE_GUARDED")
        self.assertFalse(result["execution_started"])


if __name__ == "__main__":
    unittest.main()
