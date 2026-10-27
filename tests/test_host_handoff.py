"""M2 handoff: actual host execution is required, never simulated by the MCP."""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source/runtime"))
import orbit_delegation
import orbit_evidence
import orbit_mcp
import orbit_tasks


class HostHandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "demo"
        self.other = Path(self.tmp.name) / "other"
        self.root.mkdir()
        self.other.mkdir()
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.addCleanup(self.db.close)
        orbit_tasks.setup(self.db)
        orbit_evidence.setup(self.db)

    def call(self, name, **fields):
        return orbit_mcp.execute(self.db, name, {
            "project_root": str(self.root), "project": "todo", **fields})

    def register(self, *, key="frontend", deps=None, scope=None):
        answer = self.call("orbit_task_plan", task_key=key, step="IMPLEMENT",
                          role="frontend", goal="Research memory and build an accessible todo interface",
                          reason="Deliver a verified working feature without replacing user files",
                          depends_on=deps or [], write_paths=scope or ["src/ui/"],
                          confirm_write=True)
        self.assertEqual(answer["status"], "PLANNED")
        return answer["task"]

    def reserve(self, key="frontend"):
        task = self.db.execute(
            "SELECT revision FROM orbit_agent_tasks WHERE project=? AND task_key=?",
            ("todo", key)).fetchone()
        return self.call("orbit_task_reserve", task_key=key,
                         expected_revision=task["revision"],
                         approval_reference="host-approved-plan-123",
                         confirm_write=True)

    def handoff(self, *, host="antigravity", tools=None, key="frontend",
                include_research=False, **overrides):
        return self.call("orbit_task_handoff",
                         task_key=key, host=host,
                         available_host_tools=(["invoke_subagent"] if tools is None else tools),
                         include_research=include_research, **overrides)

    def test_without_reservation_never_claims_delegation(self):
        self.register()
        result = self.handoff()
        self.assertEqual(result["status"], "HOLD_RESERVE_TASK_FIRST")
        self.assertIsNone(result["handoff"])
        self.assertFalse(result["native_invoked"])
        self.assertFalse(result["host_execution_verified"])
        self.assertFalse(result["approval_verified"])

    def test_supported_antigravity_handoff_does_not_invoke(self):
        self.register()
        self.assertEqual(self.reserve()["status"], "RESERVED")
        prior = self.db.execute("SELECT revision,status FROM orbit_agent_tasks").fetchone()
        packet = self.handoff()
        self.assertEqual(packet["status"], "HOST_INVOCATION_REQUIRED")
        self.assertEqual(packet["native_tool"], "invoke_subagent")
        self.assertEqual(packet["handoff"]["write_paths"], ["src/ui/"])
        self.assertEqual(packet["handoff"]["task_revision"], 2)
        self.assertFalse(packet["native_invoked"])
        self.assertIsNone(packet.get("host_session"))
        now = self.db.execute("SELECT revision,status FROM orbit_agent_tasks").fetchone()
        self.assertEqual(tuple(prior), tuple(now))
        self.assertFalse((self.root / ".orbit").exists())

    def test_host_name_mismatch_is_honest_hold(self):
        self.register()
        self.reserve()
        result = self.handoff(host="codex", tools=["invoke_subagent"])
        self.assertEqual(result["status"], "HOLD_NATIVE_TOOL_UNAVAILABLE")
        self.assertIn("orbit_task_release", result["next_action"])
        self.assertIsNone(result["native_tool"])
        self.assertIsNone(result["handoff"])

    def test_codex_and_claude_code_reported_native_tool_names(self):
        self.register()
        self.reserve()
        for host, tools, expected in (
            ("codex", ["spawn_agent"], "spawn_agent"),
            ("claude-code", ["Agent"], "Agent"),
            ("claude-code", ["Task"], "Task")):
            with self.subTest(host=host, tools=tools):
                packet = self.handoff(host=host, tools=tools)
                self.assertEqual(packet["native_tool"], expected)
                self.assertEqual(packet["status"], "HOST_INVOCATION_REQUIRED")

    def test_unsupported_hosts_and_empty_tool_set_fail_closed(self):
        self.register()
        self.reserve()
        for host in ("vscode", "claude-desktop", "generic"):
            with self.subTest(host=host):
                self.assertEqual(
                    self.handoff(host=host, tools=["invoke_subagent"])["status"],
                    "HOLD_NATIVE_TOOL_UNAVAILABLE")
        self.assertEqual(self.handoff(tools=[])["status"], "HOLD_NATIVE_TOOL_UNAVAILABLE")

    def test_delegation_does_not_enable_cross_project_or_folder_access(self):
        self.register()
        self.reserve()
        with self.assertRaises(ValueError):
            self.call("orbit_task_handoff", project="different",
                      task_key="frontend", host="antigravity",
                      available_host_tools=["invoke_subagent"])
        with self.assertRaises(ValueError):
            self.call("orbit_task_handoff", project_root=str(self.other),
                      task_key="frontend", host="antigravity",
                      available_host_tools=["invoke_subagent"])

    def test_research_context_is_optional_and_scoped_source_pointer(self):
        self.register()
        self.reserve()
        record = orbit_evidence.save(self.db, self.root.resolve(), "todo", {
            "source_key": "research-guide", "title": "Research memory architecture",
            "url": "https://example.com/agent/research", "tags": ["research","agent"],
            "note": "Read current source independently", "confirm_write": True})
        self.assertEqual(record["status"], "SAVED")
        self.assertEqual(self.handoff()["handoff"]["research_pointers_untrusted"], [])
        with_notes = self.handoff(include_research=True)
        links = with_notes["handoff"]["research_pointers_untrusted"]
        self.assertEqual(len(links), 1)
        self.assertEqual(links[0]["url"], "https://example.com/agent/research")
        self.assertNotIn("external content", json.dumps(with_notes))

    def test_handoff_rejects_malformed_reported_tool_names(self):
        self.register()
        self.reserve()
        for tool_names in (["invoke_subagent", "invoke_subagent"],
                           ["invoke_subagent; rm -rf /"], ["../invoke_subagent"]):
            with self.subTest(names=tool_names), self.assertRaises(ValueError):
                self.handoff(tools=tool_names)
        with self.assertRaises(ValueError):
            self.handoff(host="randomhost")

    def test_running_task_is_not_reinvoked(self):
        self.register()
        self.reserve()
        started = self.call("orbit_task_started", task_key="frontend",
                            expected_revision=2,
                            host_session="native-session-12345",
                            confirm_write=True)
        self.assertEqual(started["status"], "RUNNING_REPORTED")
        packet = self.handoff()
        self.assertEqual(packet["status"], "HOLD_RESERVE_TASK_FIRST")
        self.assertFalse(packet["native_invoked"])

    def test_tool_contract_read_only_and_arguments_tight(self):
        tool = next(t for t in orbit_mcp.TOOLS if t["name"] == "orbit_task_handoff")
        self.assertTrue(tool["annotations"]["readOnlyHint"])
        self.assertFalse(tool["annotations"]["destructiveHint"])
        with self.assertRaises(ValueError):
            orbit_mcp.validate("orbit_task_handoff", {
                "project_root": str(self.root), "project": "todo", "task_key": "frontend",
                "host": "antigravity", "confirm_write": True})


if __name__ == "__main__":
    unittest.main()
