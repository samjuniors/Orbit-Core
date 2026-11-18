"""Orbit RAD P0 deterministic guard tests (no real host agents or code execution).

These exercise dispatcher enforcement and denial isolation against disposable
project roots. The host/OS must still implement actual identity and sandboxing.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source" / "runtime"))

import orbit_autopilot
import orbit_defense
import orbit_mcp
import orbit_tasks


class RADGuardTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = (Path(temp.name) / "project-one").resolve()
        self.other = (Path(temp.name) / "project-two").resolve()
        self.root.mkdir()
        self.other.mkdir()
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.addCleanup(self.conn.close)
        orbit_tasks.setup(self.conn)
        orbit_autopilot.setup(self.conn)

    def preview_args(self, root=None):
        return {
            "project_root": str(root or self.root),
            "preview_id": "security-e2e",
            "command": ["python", "-c", "print('NEVER_EXECUTE')"],
            "port": 43122,
            "confirm_run": True,
        }

    def test_normal_mode_preserves_legacy_dispatch(self):
        self.assertEqual(orbit_defense.Defense("normal").host_mode, "NORMAL")
        with patch.object(orbit_mcp.orbit_preview, "start",
                          return_value={"status": "MOCK_ONLY"}) as start:
            value = orbit_mcp.execute(
                self.conn, "orbit_preview_start",
                self.preview_args(), defense=orbit_defense.Defense("NORMAL"))
        self.assertEqual(value["status"], "MOCK_ONLY")
        start.assert_called_once()

    def test_guarded_blocks_all_project_execution_before_handler(self):
        defense = orbit_defense.Defense("GUARDED")
        with patch.object(orbit_mcp.orbit_preview, "start") as start:
            one = orbit_mcp.execute(
                self.conn, "orbit_preview_start", self.preview_args(),
                defense=defense)
            self.assertEqual(one["status"], "HOLD_DEFENSE_GUARDED")
            self.assertFalse(one["state_written"])
            self.assertFalse(one["host_permission_verified"])
            start.assert_not_called()
        browser_args = {
            "project_root": str(self.root), "project": "lab",
            "build_id": "scenario-one", "preview_id": "security-e2e",
            "confirm_run": True,
        }
        with patch.object(orbit_mcp.orbit_browser, "run") as browser:
            result = orbit_mcp.execute(
                self.conn, "orbit_browser_qa", browser_args,
                defense=defense)
            self.assertEqual(result["status"], "HOLD_DEFENSE_GUARDED")
            browser.assert_not_called()
        self.assertEqual(defense.mode_for(self.root), "GUARDED")

    def test_three_denied_execution_attempts_contain_only_same_project_root(self):
        defense = orbit_defense.Defense("GUARDED", threshold=3)
        statuses = [
            orbit_mcp.execute(self.conn, "orbit_preview_start",
                              self.preview_args(), defense=defense)["status"]
            for _ in range(3)
        ]
        self.assertEqual(statuses, [
            "HOLD_DEFENSE_GUARDED", "HOLD_DEFENSE_GUARDED",
            "HOLD_DEFENSE_CONTAINED",
        ])
        self.assertEqual(defense.mode_for(self.root), "CONTAINED")
        self.assertEqual(defense.mode_for(self.other), "GUARDED")

        # The escalation also blocks non-execution MCP writes in this project.
        write = {
            "project_root": str(self.root), "project": "lab",
            "task_key": "init", "step": "IMPLEMENT", "role": "backend",
            "goal": "Synthetic security regression; no real host source",
            "reason": "Check that containment blocks SQLite task changes",
            "confirm_write": True,
        }
        before = self.conn.total_changes
        blocked = orbit_mcp.execute(
            self.conn, "orbit_task_plan", write, defense=defense)
        self.assertEqual(blocked["status"], "HOLD_DEFENSE_CONTAINED")
        self.assertEqual(self.conn.total_changes, before)
        row = self.conn.execute(
            "SELECT COUNT(*) FROM orbit_agent_tasks WHERE project='lab'"
        ).fetchone()
        self.assertEqual(row[0], 0)
        other = orbit_mcp.execute(
            self.conn, "orbit_task_plan", {**write, "project_root": str(self.other)},
            defense=defense)
        self.assertEqual(other["status"], "PLANNED")
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM orbit_agent_tasks WHERE project='lab'"
        ).fetchone()[0], 1)
        self.assertEqual(defense.mode_for(self.root), "CONTAINED")

    def test_containment_preserves_small_safe_recovery_surface(self):
        defense = orbit_defense.Defense("CONTAINED")
        root = str(self.root)
        # A "read-only" scan still returns untrusted project checkpoint text;
        # its contents must not be available to a compromised MCP caller.
        (self.root / ".orbit").mkdir()
        (self.root / ".orbit" / "STATE.md").write_text(
            "DO_NOT_LEAK_SYNTHETIC_SECRET", encoding="utf-8")
        for name, args in (
            ("orbit_project_scan", {"project_root": root, "project": "lab"}),
            ("orbit_autopilot_charter", {"project_root": root, "project": "lab",
                                        "mission_id": "missing", "action": "status"}),
            ("orbit_task_list", {"project_root": root, "project": "lab"}),
            ("orbit_memory_recall", {"project": "lab"}),
        ):
            with self.subTest(name=name):
                result = orbit_mcp.execute(self.conn, name, args, defense=defense)
                self.assertEqual(result["status"], "HOLD_DEFENSE_CONTAINED")
                self.assertNotIn("DO_NOT_LEAK_SYNTHETIC_SECRET", str(result))
        pure = orbit_mcp.execute(
            self.conn, "orbit_gate_evaluate",
            {"checks": [{"id": "hold", "status": "NOT_RUN"}]},
            defense=defense)
        self.assertEqual(pure["gate"], "HOLD")
        self.assertTrue(orbit_defense.Defense._safe_recovery(
            "orbit_update_status", {}))
        self.assertFalse(orbit_defense.Defense._safe_recovery(
            "orbit_update_status", {"refresh": True}))
        with patch.object(orbit_mcp.orbit_preview, "stop",
                          return_value={"status": "STOPPED_TEST_ONLY"}) as stop:
            result = orbit_mcp.execute(
                self.conn, "orbit_preview_stop",
                {"project_root": root, "preview_id": "security-e2e",
                 "confirm_stop": True}, defense=defense)
        self.assertEqual(result["status"], "STOPPED_TEST_ONLY")
        stop.assert_called_once()
        denied = orbit_mcp.execute(
            self.conn, "orbit_preview_stop",
            {"project_root": root, "preview_id": "security-e2e"},
            defense=defense)
        self.assertEqual(denied["status"], "HOLD_DEFENSE_CONTAINED")
        blocked = orbit_mcp.execute(
            self.conn, "orbit_autopilot_charter",
            {"project_root": root, "project": "lab",
             "mission_id": "missing", "action": "timeline"},
            defense=defense)
        self.assertEqual(blocked["status"], "HOLD_DEFENSE_CONTAINED")

    def test_invalid_host_mode_fails_closed_and_is_snapshot_at_startup(self):
        with patch.dict(os.environ, {"ORBIT_DEFENSE_MODE": "not-a-mode"}):
            defense = orbit_defense.Defense()
        self.assertEqual(defense.host_mode, "CONTAINED")
        with patch.dict(os.environ, {"ORBIT_DEFENSE_MODE": "NORMAL"}):
            self.assertEqual(defense.mode_for(self.root), "CONTAINED")
        self.assertEqual(
            orbit_mcp.execute(self.conn, "orbit_preview_start",
                              self.preview_args(), defense=defense)["status"],
            "HOLD_DEFENSE_CONTAINED")

    def test_untrusted_caller_cannot_update_security_mode(self):
        defense = orbit_defense.Defense("GUARDED")
        payload = {**self.preview_args(), "defense_mode": "NORMAL"}
        with self.assertRaisesRegex(ValueError, "Unexpected properties"):
            orbit_mcp.execute(
                self.conn, "orbit_preview_start", payload, defense=defense)
        self.assertEqual(defense.mode_for(self.root), "GUARDED")
        # A fresh trusted host session is the only reset in this slice.
        for _ in range(3):
            orbit_mcp.execute(self.conn, "orbit_preview_start",
                              self.preview_args(), defense=defense)
        self.assertEqual(defense.mode_for(self.root), "CONTAINED")
        with patch.dict(os.environ, {"ORBIT_DEFENSE_MODE": "NORMAL"}):
            self.assertEqual(defense.mode_for(self.root), "CONTAINED")
            self.assertEqual(orbit_defense.Defense().mode_for(self.root), "NORMAL")

    def test_rejected_untrusted_root_never_escalates_other_workspace(self):
        defense = orbit_defense.Defense("GUARDED")
        with patch.dict(os.environ, {"ORBIT_TRUSTED_ROOTS": str(self.root)}):
            for _ in range(5):
                with self.assertRaisesRegex(ValueError, "ORBIT_TRUSTED_ROOTS"):
                    orbit_mcp.execute(
                        self.conn, "orbit_preview_start",
                        self.preview_args(self.other), defense=defense)
        self.assertEqual(defense.mode_for(self.other), "GUARDED")
        self.assertEqual(defense.mode_for(self.root), "GUARDED")

    def test_scoped_memory_budget_cannot_force_global_lockout(self):
        defense = orbit_defense.Defense("GUARDED", threshold=2, max_scopes=1)
        for _ in range(2):
            orbit_mcp.execute(
                self.conn, "orbit_preview_start", self.preview_args(),
                defense=defense)
        self.assertEqual(defense.mode_for(self.root), "CONTAINED")
        for _ in range(15):
            hold = orbit_mcp.execute(
                self.conn, "orbit_preview_start", self.preview_args(self.other),
                defense=defense)
            self.assertEqual(hold["status"], "HOLD_DEFENSE_GUARDED")
        self.assertEqual(defense.mode_for(self.other), "GUARDED")
        self.assertEqual(len(defense._denied_exec), 1)

    def test_mcp_wire_response_is_bounded_and_no_tool_is_added(self):
        self.assertEqual(len(orbit_mcp.TOOLS), 57)
        # A future code-executing tool must not silently be absent from the
        # independent denial policy when the MCP annotation set changes.
        self.assertEqual(orbit_defense.EXECUTES_PROJECT_CODE,
                         orbit_mcp.EXECUTES_PROJECT_CODE)
        self.assertTrue(orbit_defense.EXECUTES_PROJECT_CODE <=
                        set(orbit_mcp.TOOL_MAP))
        defense = orbit_defense.Defense("GUARDED")
        req = {
            "jsonrpc": "2.0", "id": 12, "method": "tools/call",
            "params": {"name": "orbit_preview_start",
                       "arguments": self.preview_args()}
        }
        response = orbit_mcp.handle(self.conn, req, defense=defense)
        self.assertFalse(response["result"]["isError"])
        self.assertEqual(response["id"], 12)
        self.assertIn("HOLD_DEFENSE_GUARDED",
                      response["result"]["content"][0]["text"])
        self.assertNotIn("NEVER_EXECUTE",
                         response["result"]["content"][0]["text"])
        self.assertNotIn(str(self.root),
                         response["result"]["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
