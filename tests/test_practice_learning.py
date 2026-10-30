"""M5: opt-in review of repeated caller-reported accepted task patterns."""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source/runtime"))
import orbit_evidence
import orbit_mcp
import orbit_tasks


class PracticeLearningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.one = Path(self.tmp.name) / "one"
        self.two = Path(self.tmp.name) / "two"
        self.one.mkdir()
        self.two.mkdir()
        # The MCP canonicalizes existing roots; seed fixture rows with that same
        # Windows/Unix normalized identity rather than the raw temp-dir spelling.
        self.one = self.one.resolve(strict=True)
        self.two = self.two.resolve(strict=True)
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.addCleanup(self.conn.close)
        orbit_tasks.setup(self.conn)
        orbit_evidence.setup(self.conn)

    def seed(self, key, *, root=None, project="orbit", role="qa",
             step="Review browser QA", status="REVIEW_ACCEPTED", note="",
             revision=5, review="Reviewed actual test and diff"):
        self.conn.execute("""INSERT INTO orbit_agent_tasks(
            project,project_root,task_key,step,role,goal,reason,write_paths,
            depends_on,status,revision,review_evidence,note,created_at,updated_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (project, str(root or self.one), key, step, role,
             "Check the application behavior", "Improve reliable QA checks",
             "[]", "[]", status, revision, review, note,
             "2026-10-29T00:00:00+00:00", "2026-10-29T00:00:00+00:00"))
        self.conn.commit()

    def call(self, name, *, root=None, project="orbit", **fields):
        return orbit_mcp.execute(self.conn, name, {
            "project_root": str(root or self.one), "project": project, **fields
        })

    def key(self):
        return self.call("orbit_practice_suggest")["candidates"][0]["practice_key"]

    def test_no_suggestion_without_two_separate_accepted_reviewed_tasks(self):
        self.seed("one")
        self.seed("two", status="REWORK")
        self.seed("three", review="")
        result = self.call("orbit_practice_suggest")
        self.assertEqual(result["candidates"], [])
        self.assertFalse(result["auto_promoted"])
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM orbit_practices").fetchone()[0], 0)

    def test_scoped_preview_approve_and_readback(self):
        self.seed("one")
        self.seed("two")
        proposed = self.call("orbit_practice_suggest")
        key = proposed["candidates"][0]["practice_key"]
        self.assertEqual(proposed["candidates"][0]["observed_tasks"], 2)
        self.assertIn("CALLER_REPORTED", proposed["source_trust"])
        review = dict(practice_key=key, action="approve",
                      practice_text="Check real tests and inspect the Git diff before acceptance.")
        preview = self.call("orbit_practice_review", **review)
        self.assertEqual(preview["status"], "PREVIEW_ONLY")
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM orbit_practices").fetchone()[0], 0)
        saved = self.call("orbit_practice_review", **review, confirm_write=True)
        self.assertEqual(saved["status"], "APPROVED")
        self.assertFalse(saved["execution_permissions_granted"])
        self.assertEqual(saved["revision"], 1)
        result = self.call("orbit_practice_suggest")
        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["practices"][0]["practice_text"], review["practice_text"])
        self.assertTrue(result["practices"][0]["evidence_current"])
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM orbit_practice_history").fetchone()[0], 1)
        for root, project in ((self.two, "orbit"), (self.one, "different")):
            output = self.call("orbit_practice_suggest", root=root, project=project)
            self.assertEqual(output["practices"], [])
            self.assertEqual(output["candidates"], [])

    def test_reject_is_durable_but_not_active_or_auto_promoted(self):
        self.seed("one")
        self.seed("two")
        key = self.key()
        r = self.call("orbit_practice_review", practice_key=key,
                      action="reject", rationale="Two results are not representative",
                      confirm_write=True)
        self.assertEqual(r["status"], "REJECTED")
        self.assertEqual(self.call("orbit_practice_suggest")["practices"], [])
        inactive = self.call("orbit_practice_suggest", include_inactive=True)
        self.assertEqual(inactive["practices"][0]["status"], "REJECTED")
        self.assertEqual(inactive["candidates"], [])
        self.assertEqual(self.call("orbit_practice_review", practice_key=key,
                         action="approve", practice_text="A repeated pattern should be reviewed",
                         expected_revision=1, confirm_write=True)["status"], "ALREADY_REVIEWED")

    def test_supersede_and_archive_keep_history_with_revision_checks(self):
        self.seed("one")
        self.seed("two")
        key = self.key()
        self.call("orbit_practice_review", practice_key=key, action="approve",
                  practice_text="Initially reviewed practice statement.",
                  confirm_write=True)
        base = dict(practice_key=key, action="supersede", expected_revision=1,
                    rationale="Clarified scope after user review",
                    practice_text="Updated practice: inspect actual source and regression evidence.")
        self.assertEqual(self.call("orbit_practice_review", **base, confirm_write=True)["revision"], 2)
        self.assertEqual(self.call("orbit_practice_review", **base, confirm_write=True)["status"], "STALE_REVISION")
        self.assertEqual(self.call("orbit_practice_review", practice_key=key,
                         action="archive", expected_revision=2,
                         rationale="No longer relevant", confirm_write=True)["status"], "ARCHIVED")
        self.assertEqual(self.call("orbit_practice_suggest")["practices"], [])
        rows = self.conn.execute("""SELECT action,revision FROM orbit_practice_history
            ORDER BY revision""").fetchall()
        self.assertEqual([(r["action"], r["revision"]) for r in rows],
                         [("approve", 1), ("supersede", 2), ("archive", 3)])

    def test_changed_evidence_is_not_current_and_cannot_newly_approve(self):
        self.seed("one")
        self.seed("two")
        key = self.key()
        self.call("orbit_practice_review", practice_key=key, action="approve",
                  practice_text="Reconfirm changed tests before using previous observations.",
                  confirm_write=True)
        self.conn.execute("""UPDATE orbit_agent_tasks SET status='REWORK',
            revision=revision+1 WHERE task_key='one'""")
        self.conn.commit()
        out = self.call("orbit_practice_suggest")
        self.assertFalse(out["practices"][0]["evidence_current"])
        self.assertEqual(self.call("orbit_practice_review", practice_key=key,
                         action="supersede", expected_revision=1,
                         practice_text="A newly revised text needs current review evidence.",
                         rationale="Correction", confirm_write=True)["status"],
                         "INSUFFICIENT_CURRENT_EVIDENCE")

    def test_imported_unverified_records_do_not_promote(self):
        self.seed("one", note="IMPORTED_HISTORY_UNVERIFIED; copied to new host")
        self.seed("two")
        self.assertEqual(self.call("orbit_practice_suggest")["candidates"], [])

    def test_rejects_invented_keys_invalid_text_and_invalid_revision(self):
        self.seed("one")
        self.seed("two")
        key = self.key()
        with self.assertRaises(ValueError):
            self.call("orbit_practice_review", practice_key="not-real",
                      action="approve", practice_text="A long enough note for testing")
        with self.assertRaises(ValueError):
            self.call("orbit_practice_review", practice_key=key, action="approve",
                      practice_text="short", confirm_write=True)
        with self.assertRaises(ValueError):
            self.call("orbit_practice_review", practice_key=key, action="archive",
                      expected_revision=1, confirm_write=True)
        self.assertEqual(self.call("orbit_practice_review", practice_key=key,
                         action="approve", practice_text="A fully reviewed note is required.",
                         expected_revision=4, confirm_write=True)["status"], "STALE_REVISION")

    def test_old_decisions_never_resurface_after_many_reviews(self):
        # Regression: candidate suppression must not depend on the 20 most
        # recent saved rows or on the optional inactive display filter.
        self.seed("initial-a", step="first-reviewed-step")
        self.seed("initial-b", step="first-reviewed-step")
        first = self.key()
        self.call("orbit_practice_review", practice_key=first,
                  action="approve", confirm_write=True,
                  practice_text="Keep a reviewer-accepted practice even as later notes grow.")
        for number in range(23):
            step = f"later-reviewed-step-{number}"
            self.seed(f"task-{number}-a", step=step)
            self.seed(f"task-{number}-b", step=step)
            pending = self.call("orbit_practice_suggest")["candidates"]
            self.assertEqual(len(pending), 1)
            self.call("orbit_practice_review",
                      practice_key=pending[0]["practice_key"], action="reject",
                      rationale="Not sufficiently general for reuse", confirm_write=True)
        result = self.call("orbit_practice_suggest")
        self.assertEqual(result["candidates"], [])
        self.assertEqual([r["practice_key"] for r in result["practices"]], [first])
        inactive = self.call("orbit_practice_suggest", include_inactive=True, limit=20)
        self.assertEqual(len(inactive["practices"]), 20)
        self.assertEqual(inactive["candidates"], [])

    def test_preview_never_executes_a_sqlite_write(self):
        self.seed("one")
        self.seed("two")
        key = self.key()
        traced = []
        self.conn.set_trace_callback(traced.append)
        try:
            preview = self.call("orbit_practice_review", practice_key=key,
                                action="approve", practice_text="Use reviewer notes as scoped data.")
        finally:
            self.conn.set_trace_callback(None)
        self.assertEqual(preview["status"], "PREVIEW_ONLY")
        self.assertFalse(any(command.lstrip().upper().startswith(("BEGIN", "UPDATE", "INSERT"))
                             for command in traced))
        self.assertEqual(self.conn.execute("SELECT COUNT(*) FROM orbit_practices").fetchone()[0], 0)

    def test_failed_decision_history_insert_rolls_back_state(self):
        self.seed("one")
        self.seed("two")
        key = self.key()
        self.conn.execute("""CREATE TRIGGER reject_practice_history BEFORE INSERT
            ON orbit_practice_history BEGIN SELECT RAISE(ABORT, 'history write failed'); END""")
        with self.assertRaises(sqlite3.DatabaseError):
            self.call("orbit_practice_review", practice_key=key, action="approve",
                      practice_text="Only save decisions with a durable history.",
                      confirm_write=True)
        self.assertIsNone(self.conn.execute("SELECT * FROM orbit_practices").fetchone())
        self.assertIsNone(self.conn.execute("SELECT * FROM orbit_practice_history").fetchone())

    def test_sqlite_restart_preserves_practice_review_history(self):
        self.seed("one")
        self.seed("two")
        key = self.key()
        self.call("orbit_practice_review", practice_key=key, action="approve",
                  practice_text="Preserve reviewed knowledge after an SQLite restart.",
                  confirm_write=True)
        dbfile = Path(self.tmp.name) / "persist.sqlite3"
        disk = sqlite3.connect(dbfile)
        try:
            self.conn.backup(disk)
        finally:
            disk.close()
        recovered = sqlite3.connect(dbfile)
        recovered.row_factory = sqlite3.Row
        self.addCleanup(recovered.close)
        orbit_tasks.setup(recovered)
        orbit_evidence.setup(recovered)
        response = orbit_evidence.practice_suggest(recovered, self.one, "orbit", {})
        self.assertEqual(response["practices"][0]["practice_key"], key)
        self.assertTrue(response["practices"][0]["evidence_current"])
        self.assertEqual(recovered.execute(
            "SELECT COUNT(*) FROM orbit_practice_history").fetchone()[0], 1)

    def test_tool_contract_does_not_accept_unknown_fields(self):
        tools = {tool["name"]: tool for tool in orbit_mcp.TOOLS}
        self.assertTrue(tools["orbit_practice_suggest"]["annotations"]["readOnlyHint"])
        self.assertFalse(tools["orbit_practice_review"]["annotations"]["readOnlyHint"])
        with self.assertRaises(ValueError):
            self.call("orbit_practice_suggest", import_from_notion=True)
        with self.assertRaises(ValueError):
            self.call("orbit_practice_review", practice_key="practice-" + "a"*16,
                      action="approve", install_skill=True)


if __name__ == "__main__":
    unittest.main()
