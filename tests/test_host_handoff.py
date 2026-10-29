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

    def test_m3_attempt_budget_counts_retries_of_same_task(self):
        self.register()
        for attempt in (1,2,3):
            reservation=self.reserve()
            self.assertEqual(reservation['status'],'RESERVED')
            self.assertEqual(reservation['attempt_number'],attempt)
            self.assertEqual(reservation['attempt_budget']['step_used'],attempt)
            revision=reservation['task']['revision']
            started=self.call('orbit_task_started',task_key='frontend',
                expected_revision=revision,host_session=f'native-session-{attempt}-abc',
                confirm_write=True)
            failed=self.call('orbit_task_report',task_key='frontend',
                expected_revision=started['task']['revision'],outcome='FAILED',
                evidence='Host reported a real failing regression test result',
                confirm_write=True)
            self.assertEqual(failed['status'],'FAILED')
        with self.assertRaisesRegex(ValueError,'Per-step agent budget exhausted'):
            self.reserve()
        records=self.db.execute(
            'SELECT attempt_number,disposition FROM orbit_task_attempts WHERE task_key=? ORDER BY attempt_number',
            ('frontend',)).fetchall()
        self.assertEqual([x['attempt_number'] for x in records],[1,2,3])
        self.assertEqual([x['disposition'] for x in records],['HOST_REPORTED_FAILED']*3)

    def test_m3_daily_budget_counts_distinct_steps_and_retries(self):
        # Distinct step labels previously concealed repeated same-day execution.
        for n in range(12):
            key=f'job-{n}'
            planned=self.call('orbit_task_plan',task_key=key,
                step=f'milestone-{n//3}',role='backend',
                goal='Work on one bounded task and verify behavior with tests',
                reason='Run a recorded attempt without assuming host permissions',
                write_paths=[f'packages/module-{n}/'],confirm_write=True)
            self.assertEqual(planned['status'],'PLANNED')
            reservation=self.call('orbit_task_reserve',task_key=key,
                expected_revision=1,approval_reference='host-consent-report-12345',
                confirm_write=True)
            self.assertEqual(reservation['status'],'RESERVED')
            self.assertEqual(reservation['attempt_budget']['day_used'],n+1)
            started=self.call('orbit_task_started',task_key=key,
                expected_revision=2,host_session=f'native-{n}-session',confirm_write=True)
            self.call('orbit_task_report',task_key=key,
                expected_revision=started['task']['revision'],outcome='FAILED',
                evidence='Host reported failed validation for this module',
                confirm_write=True)
        planned=self.call('orbit_task_plan',task_key='over-limit',
            step='new-step',role='backend',
            goal='A separate new task that should be blocked by day budget',
            reason='The daily attempt limit is shared by project root',
            write_paths=['packages/over-limit/'],confirm_write=True)
        self.assertEqual(planned['status'],'PLANNED')
        with self.assertRaisesRegex(ValueError,'Daily agent budget exhausted'):
            self.call('orbit_task_reserve',task_key='over-limit',expected_revision=1,
                approval_reference='host-consent-report-12345',confirm_write=True)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM orbit_task_attempts').fetchone()[0],12)

    def test_m3_unused_reservations_are_refunded_without_erasing_history(self):
        for n in range(4):
            key=f'unused-{n}'
            self.register(key=key,scope=[f'src/component-{n}/'])
            reservation=self.reserve(key=key)
            self.assertEqual(reservation['attempt_budget']['step_used'],1)
            released=self.call('orbit_task_release',task_key=key,
                expected_revision=reservation['task']['revision'],
                reason='No native host agent was started; user cancelled the slot',
                confirm_write=True)
            self.assertEqual(released['status'],'CANCELLED')
        rows=self.db.execute('SELECT disposition FROM orbit_task_attempts').fetchall()
        self.assertEqual(len(rows),4)
        self.assertEqual({row['disposition'] for row in rows},{'RELEASED_UNUSED'})

    def test_m3_legacy_failed_task_is_counted_without_rewriting_history(self):
        self.register()
        with self.db:
            self.db.execute("""UPDATE orbit_agent_tasks SET status='FAILED',
                revision=4, host_session='previous-native-host-session',
                reserved_at=? WHERE project='todo' AND task_key='frontend'""",
                (orbit_tasks.utc_now(),))
        first=self.call('orbit_task_reserve',task_key='frontend',
            expected_revision=4,approval_reference='fresh-user-consent-12345',
            confirm_write=True)
        self.assertEqual(first['attempt_number'],2)
        self.assertEqual(first['attempt_budget']['step_used'],2)
        legacy=self.db.execute("""SELECT disposition,attempt_number FROM orbit_task_attempts
                                  WHERE task_key='frontend' ORDER BY attempt_number""").fetchall()
        self.assertEqual([(r['disposition'],r['attempt_number']) for r in legacy],
                         [('LEGACY_UNVERIFIED',1),('RESERVED',2)])
        self.assertEqual(first['task']['revision'],5)
        self.assertEqual(first['task']['host_session'],'')
        self.assertEqual(self.db.execute(
            "SELECT host_session FROM orbit_task_attempts WHERE task_key='frontend' AND attempt_number=1"
        ).fetchone()[0],'previous-native-host-session')
        # Simulate a second terminal result after actual host invocation.
        self.call('orbit_task_started',task_key='frontend',expected_revision=5,
            host_session='current-real-native-session',confirm_write=True)
        self.call('orbit_task_report',task_key='frontend',expected_revision=6,
            outcome='FAILED',evidence='Host confirmed this second attempt failed',
            confirm_write=True)
        third=self.call('orbit_task_reserve',task_key='frontend',
            expected_revision=7,approval_reference='fresh-third-user-consent',
            confirm_write=True)
        self.assertEqual(third['attempt_number'],3)
        self.assertEqual(third['attempt_budget']['step_used'],3)

    def test_m3_retry_never_inherits_prior_host_session_or_burns_unused_slot(self):
        self.register()
        first=self.reserve()
        self.call('orbit_task_started',task_key='frontend',
            expected_revision=2,host_session='first-real-native-session-123',
            confirm_write=True)
        failed=self.call('orbit_task_report',task_key='frontend',
            expected_revision=3,outcome='FAILED',
            evidence='Host reported failed validation and stopped',
            confirm_write=True)
        retry=self.call('orbit_task_reserve',task_key='frontend',
            expected_revision=failed['task']['revision'],
            approval_reference='fresh-real-approval-reference',
            confirm_write=True)
        self.assertEqual(retry['attempt_number'],2)
        self.assertEqual(retry['task']['host_session'],'')
        release=self.call('orbit_task_release',task_key='frontend',
            expected_revision=retry['task']['revision'],
            reason='Second attempt never launched a host agent, release it',
            confirm_write=True)
        self.assertEqual(release['status'],'CANCELLED')
        rows=self.db.execute(
            "SELECT disposition,host_session FROM orbit_task_attempts WHERE task_key='frontend' ORDER BY attempt_number"
        ).fetchall()
        self.assertEqual([(x['disposition'],x['host_session']) for x in rows],
                         [('HOST_REPORTED_FAILED','first-real-native-session-123'),
                          ('RELEASED_UNUSED','')])
        # The first started agent is still budgeted even if the retry was unused.
        step,day=orbit_tasks._attempt_usage(self.db,'todo',
            orbit_mcp.project_root({'project_root':str(self.root)}),
            'IMPLEMENT',orbit_tasks.utc_now()[:10])
        self.assertEqual((step,day),(1,1))

    def test_m3_attempt_budget_survives_sqlite_restart(self):
        self.register()
        reserved=self.reserve()
        self.call('orbit_task_started',task_key='frontend',
            expected_revision=reserved['task']['revision'],
            host_session='session-before-restart-1234',confirm_write=True)
        terminal=self.call('orbit_task_report',task_key='frontend',
            expected_revision=3,outcome='FAILED',
            evidence='Host reported regression failure before restarting MCP',
            confirm_write=True)
        self.assertEqual(terminal['status'],'FAILED')
        path=Path(self.tmp.name)/'attempt-restart.sqlite'
        saved=sqlite3.connect(str(path))
        try:
            self.db.backup(saved)
        finally:
            saved.close()
        reopened=sqlite3.connect(str(path))
        reopened.row_factory=sqlite3.Row
        try:
            orbit_tasks.setup(reopened)
            canonical=orbit_mcp.project_root({'project_root':str(self.root)})
            retried=orbit_tasks.reserve(reopened,{
                'project':'todo','task_key':'frontend','expected_revision':4,
                'approval_reference':'approved-after-restart-1234',
                'confirm_write':True},canonical)
            self.assertEqual(retried['status'],'RESERVED')
            self.assertEqual(retried['attempt_number'],2)
            self.assertEqual(retried['attempt_budget']['step_used'],2)
            self.assertEqual(retried['task']['host_session'],'')
            prior=reopened.execute(
                "SELECT host_session FROM orbit_task_attempts WHERE task_key='frontend' AND attempt_number=1"
            ).fetchone()
            self.assertEqual(prior['host_session'],'session-before-restart-1234')
        finally:
            reopened.close()

    def test_m3_stale_reservation_has_no_attempt_history_side_effect(self):
        self.register()
        stale=self.call('orbit_task_reserve',task_key='frontend',
            expected_revision=99,approval_reference='user-consent-12345',
            confirm_write=True)
        self.assertEqual(stale['status'],'STALE_REVISION')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM orbit_task_attempts').fetchone()[0],0)
        good=self.reserve()
        self.assertEqual(good['attempt_number'],1)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM orbit_task_attempts').fetchone()[0],1)

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
