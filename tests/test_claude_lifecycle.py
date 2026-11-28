"""Tests for the opt-in Claude Code lifecycle adapter and minimal event ledger."""
import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone

RUNTIME = Path(__file__).resolve().parents[1] / "source" / "runtime"
sys.path.insert(0, str(RUNTIME))
import orbit_claude_hook
import orbit_claude_lifecycle


class ClaudeLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project"
        self.root.mkdir()
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.addCleanup(self.conn.close)
        orbit_claude_lifecycle.setup(self.conn)


    def test_optional_hook_configuration_is_not_auto_discovered(self):
        plugin_root = Path(__file__).resolve().parents[1] / "plugins" / "claude-code" / "orbit-core"
        optional = plugin_root / "hooks" / "optional" / "orbit-lifecycle.hooks.json"
        auto_loaded = plugin_root / "hooks" / "hooks.json"
        self.assertTrue(optional.is_file())
        self.assertFalse(auto_loaded.exists())
        config = json.loads(optional.read_text(encoding="utf-8"))
        self.assertEqual(
            set(config["hooks"]),
            {"SessionStart", "PreCompact", "PostCompact", "SessionEnd"},
        )

    def test_only_allowlisted_events_are_recorded(self):
        result = orbit_claude_hook.process_payload({
            "hook_event_name": "SessionStart", "cwd": str(self.root),
            "session_id": "private-session-id",
        }, self.conn)
        self.assertEqual(result["status"], "RECORDED")
        ignored = orbit_claude_hook.process_payload({
            "hook_event_name": "UserPromptSubmit", "cwd": str(self.root),
            "user_prompt": "sensitive prompt",
        }, self.conn)
        self.assertEqual(ignored["status"], "IGNORED")
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM orbit_host_lifecycle_events"
        ).fetchone()[0], 1)

    def test_raw_session_id_and_sensitive_hook_payload_are_never_stored(self):
        raw_session = "session-secret-value"
        orbit_claude_hook.process_payload({
            "hook_event_name": "PreCompact", "cwd": str(self.root),
            "session_id": raw_session,
            "transcript_path": "/private/transcript.jsonl",
            "user_prompt": "private prompt text",
            "tool_input": {"command": "private command"},
            "tool_result": "private output",
            "permission_mode": "bypassPermissions",
        }, self.conn)
        row = self.conn.execute(
            "SELECT * FROM orbit_host_lifecycle_events"
        ).fetchone()
        self.assertNotIn(raw_session, tuple(row))
        self.assertEqual(row["session_digest"], hashlib.sha256(raw_session.encode()).hexdigest())
        self.assertNotIn("private prompt text", json.dumps(dict(row)))
        self.assertNotIn("transcript.jsonl", json.dumps(dict(row)))
        self.assertNotIn("private command", json.dumps(dict(row)))
        self.assertNotIn("private output", json.dumps(dict(row)))

    def test_invalid_root_is_rejected_by_orbit_host_policy(self):
        with self.assertRaises(ValueError):
            orbit_claude_hook.process_payload({
                "hook_event_name": "SessionStart", "cwd": str(self.root / "missing")
            }, self.conn)


    def test_recent_events_without_initialized_ledger_are_read_only(self):
        empty = sqlite3.connect(":memory:")
        self.addCleanup(empty.close)
        before = empty.total_changes
        result = orbit_claude_lifecycle.recent_events(empty, self.root)
        self.assertEqual(result["status"], "NO_EVENTS_RECORDED")
        self.assertEqual(empty.total_changes, before)

    def test_recent_events_accepts_path_objects_from_resume(self):
        result = orbit_claude_lifecycle.recent_events(self.conn, self.root)
        self.assertEqual(result["status"], "NO_EVENTS_RECORDED")

    def test_events_are_isolated_by_exact_project_root(self):
        other = self.root.parent / "other"
        other.mkdir()
        orbit_claude_hook.process_payload({
            "hook_event_name": "SessionStart", "cwd": str(self.root)
        }, self.conn)
        result = orbit_claude_lifecycle.recent_events(self.conn, str(other.resolve()))
        self.assertEqual(result["status"], "NO_EVENTS_RECORDED")
        # The hook stores Orbit's validated, canonical root. Windows resolve()
        # may normalize the path spelling/case, so compare against that same identity.
        self.assertEqual(orbit_claude_lifecycle.recent_events(
            self.conn, str(self.root.resolve())
        )["status"], "EVENTS_AVAILABLE")

    def test_retention_is_bounded_to_500_events_per_project(self):
        now = datetime.now(timezone.utc)
        for i in range(505):
            orbit_claude_lifecycle.record_event(
                self.conn, str(self.root), "SessionStart",
                occurred_at=(now + timedelta(seconds=i)).isoformat()
            )
        count = self.conn.execute(
            "SELECT COUNT(*) FROM orbit_host_lifecycle_events WHERE project_root=?",
            (str(self.root),)
        ).fetchone()[0]
        self.assertEqual(count, 500)

    def test_old_events_are_pruned_by_retention(self):
        old = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        orbit_claude_lifecycle.record_event(
            self.conn, str(self.root), "SessionStart", occurred_at=old
        )
        recent = orbit_claude_lifecycle.record_event(
            self.conn, str(self.root), "SessionEnd"
        )
        self.assertEqual(recent["status"], "RECORDED")
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM orbit_host_lifecycle_events WHERE project_root=?",
            (str(self.root),)
        ).fetchone()[0], 1)

    def test_recent_events_do_not_expose_session_digest(self):
        orbit_claude_lifecycle.record_event(
            self.conn, str(self.root), "SessionStart", session_id="private-session"
        )
        result = orbit_claude_lifecycle.recent_events(self.conn, str(self.root))
        self.assertEqual(result["events"][0]["event_name"], "SessionStart")
        self.assertNotIn("session_digest", result["events"][0])
        self.assertFalse(result["host_execution_attested"])


if __name__ == "__main__":
    unittest.main()
