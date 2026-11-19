"""Real local stdio defense acceptance using disposable Windows/Linux roots.

This never invokes a real IDE, host agent, or credential and deliberately uses
only a harmless synthetic command that would create a temp-file if executed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RADLiveStdioTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.temp = Path(tmp.name)
        self.one = self.temp / "workspace-one"
        self.two = self.temp / "workspace-two"
        self.one.mkdir()
        self.two.mkdir()

    @staticmethod
    def request(identifier, name, arguments):
        return {
            "jsonrpc": "2.0", "id": identifier, "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }

    def run_host(self, mode, requests):
        env = {**os.environ,
               "ORBIT_DEFENSE_MODE": mode,
               "ORBIT_TRUSTED_ROOTS": str(self.temp),
               "ORBIT_LOCAL_DB": str(self.temp / "test.sqlite3")}
        raw = b"".join(
            (json.dumps(req, separators=(",", ":")) + "\n").encode("utf-8")
            for req in requests
        )
        result = subprocess.run(
            [sys.executable, str(ROOT / "source/runtime/orbit_mcp.py")],
            input=raw, capture_output=True, timeout=20, env=env,
            cwd=str(ROOT),
        )
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        responses = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(responses), len(requests), result.stdout[:2000])
        return [json.loads(r["result"]["content"][0]["text"]) for r in responses]

    def test_guarded_stdio_containment_memory_quarantine_and_restart(self):
        marker = self.temp / "NEVER_RUN.txt"
        code = "from pathlib import Path; Path(" + repr(str(marker)) + ").write_text('FAIL')"
        preview = {
            "project_root": str(self.one), "preview_id": "security-live",
            "command": [sys.executable, "-c", code],
            "port": 43483, "confirm_run": True,
        }
        root_one = {"project_root": str(self.one), "project": "lab-one"}
        root_two = {"project_root": str(self.two), "project": "lab-two"}
        requests = [
            self.request(i, "orbit_preview_start", preview) for i in range(1, 4)
        ] + [
            self.request(4, "orbit_task_list", root_one),
            self.request(5, "orbit_task_list", root_two),
            self.request(6, "orbit_memory_recall", {"project": "lab-one"}),
            self.request(7, "orbit_gate_evaluate", {
                "checks": [{"id": "not-run", "status": "NOT_RUN"}],
            }),
        ]
        result = self.run_host("GUARDED", requests)
        self.assertEqual(
            [item["status"] for item in result[:4]],
            ["HOLD_DEFENSE_GUARDED", "HOLD_DEFENSE_GUARDED",
             "HOLD_DEFENSE_CONTAINED", "HOLD_DEFENSE_CONTAINED"],
        )
        self.assertFalse(marker.exists(), "Blocked preview executed anyway")
        self.assertNotIn("HOLD_DEFENSE", str(result[4]))
        self.assertEqual(result[5]["status"], "HOLD_DEFENSE_GUARDED")
        self.assertEqual(result[6]["gate"], "HOLD")
        # A new trusted host process forgets its scoped denial counter.
        after_restart = self.run_host(
            "GUARDED", [self.request(8, "orbit_task_list", root_one)])
        self.assertNotIn("HOLD_DEFENSE", str(after_restart[0]))
        self.assertFalse(marker.exists())

    def test_invalid_host_mode_fails_closed_on_real_stdio(self):
        res = self.run_host("UNRECOGNIZED", [
            self.request(1, "orbit_task_list", {
                "project_root": str(self.one), "project": "lab-one",
            }),
        ])
        self.assertEqual(res[0]["status"], "HOLD_DEFENSE_CONTAINED")

    def test_normal_mode_keeps_legacy_memory_compatible(self):
        res = self.run_host("NORMAL", [
            self.request(1, "orbit_memory_recall", {"project": "lab-one"}),
        ])
        self.assertEqual(res[0], [])


if __name__ == "__main__":
    unittest.main()
