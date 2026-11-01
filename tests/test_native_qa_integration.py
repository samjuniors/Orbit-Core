"""v0.30 native-device and CLI host QA integration contract (synthetic only).

All state lives inside a disposable directory/in-memory SQLite. Tests never
invoke a real IDE, device, native SDK, model, compiler or host subagent.
Recorded command exit codes below are deliberately caller-reported fixtures.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source" / "runtime"))
import orbit_build
import orbit_decisions
import orbit_mcp
import orbit_swarm_integrity
import orbit_tasks


class NativeHostQAIntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = (Path(temporary.name) / "fixture").resolve()
        self.root.mkdir()
        self.source = self.root / "main.py"
        self.source.write_text("print('fixture')\n", encoding="utf-8")
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.addCleanup(self.conn.close)
        orbit_tasks.setup(self.conn)
        orbit_build.setup(self.conn)
        self.project = "native-qa-lab"
        self.build_id = "qa-fixture"
        self._reviewed_task()
        self.fingerprint = orbit_build.code_fingerprint(self.root)
        self.assertIsNotNone(self.fingerprint)

    def _reviewed_task(self):
        self.conn.execute(
            """INSERT INTO orbit_agent_tasks
               (project, project_root, task_key, step, role, goal, reason,
                write_paths, depends_on, status, revision, changed_paths,
                created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (self.project, str(self.root), "implementation", "Implementation",
             "backend", "Implement an authorized platform feature",
             "Bounded separate specialist work", json.dumps(["main.py"]),
             "[]", "REVIEW_ACCEPTED", 2, json.dumps(["main.py"]),
             "2026-11-01", "2026-11-01"),
        )
        self.conn.commit()

    def build(self, kind, *, stage, revision):
        flow = orbit_decisions.FLOWS[kind]
        self.conn.execute(
            "INSERT INTO build_runs (project,root,build_id,stage,revision,"
            "objective,evidence_json,updated_at) VALUES (?,?,?,?,?,?,?,?)",
            (self.project, str(self.root), self.build_id, stage, revision,
             "Test real target behavior and scoped source changes",
             json.dumps({"__orbit_flow": list(flow)}), "2026-11-01"),
        )
        self.conn.commit()

    @staticmethod
    def evidence(kind):
        if kind == "native":
            return json.dumps({
                "platforms": ["android"],
                "commands": [
                    {"command": "./gradlew testDebugUnitTest", "exit_code": 0},
                ],
                "interactions": ["Launch the main screen and navigate a form"],
                "accessibility": ["Inspect TalkBack labels for all actions"],
            })
        return json.dumps({
            "commands": [
                {"command": "python -m unittest discover", "exit_code": 0},
            ],
            "edge_cases": ["empty input handling", "invalid option handling"],
            "security": ["unsafe arguments rejected"],
        })

    def advance(self, kind, **overrides):
        data = {
            "project": self.project, "build_id": self.build_id,
            "expected_revision": 5, "outcome": "PASS",
            "evidence": self.evidence(kind),
            "confirm_write": True, **overrides,
        }
        return orbit_build.advance(self.conn, self.root, data)

    def review(self, qa_mode=None, **overrides):
        request = {
            "project_root": str(self.root), "project": self.project,
            "tasks": [{"task_key": "implementation", "expected_revision": 2}],
            "expected_source_fingerprint": orbit_build.code_fingerprint(self.root),
            "build_id": self.build_id, **overrides,
        }
        if qa_mode is not None:
            request["qa_mode"] = qa_mode
        return orbit_mcp.execute(self.conn, "orbit_swarm_integration_review",
                                 request)

    def test_native_evidence_is_source_pinned_and_review_only(self):
        self.build("native", stage="NATIVE_QA", revision=5)
        before = self.conn.total_changes
        preview = self.advance("native", confirm_write=False)
        self.assertEqual(preview["status"], "PREVIEW_ONLY")
        self.assertTrue(preview["source_pin_required"])
        self.assertTrue(preview["source_pin_available"])
        self.assertEqual(self.conn.total_changes, before)
        passed = self.advance("native")
        self.assertEqual(passed["status"], "ADVANCED")
        self.assertEqual(passed["run"]["stage"], "REVIEW")
        self.assertEqual(passed["run"]["revision"], 6)
        report = passed["run"]["evidence"]["NATIVE_QA"]
        self.assertEqual(report["source_fingerprint"], self.fingerprint)
        self.assertEqual(report["qa_build_revision"], 5)
        self.assertFalse(report["evidence_independently_verified"])
        self.assertFalse(report["host_execution_attested"])
        before = self.conn.total_changes
        gate = self.review("native")
        self.assertEqual(gate["status"], "READY_FOR_INDEPENDENT_REVIEW")
        self.assertEqual(gate["qa_mode"], "native")
        self.assertEqual(gate["recorded_platforms_unverified"], ["android"])
        self.assertTrue(gate["recorded_host_qa_source_matches"])
        self.assertFalse(gate["actual_platform_execution_verified"])
        self.assertFalse(gate["host_test_results_independently_verified"])
        self.assertFalse(gate["tests_independently_verified"])
        self.assertFalse(gate["host_permission_verified"])
        self.assertFalse(gate["approval_verified"])
        self.assertFalse(gate["git_diff_verified"])
        self.assertFalse(gate["merge_performed"])
        self.assertFalse(gate["state_written"])
        self.assertEqual(self.conn.total_changes, before)

    def test_native_missing_unadvanced_or_legacy_unpinned_reports_hold(self):
        self.build("native", stage="NATIVE_QA", revision=5)
        unadvanced = self.review("native")
        self.assertEqual(unadvanced["status"], "HOLD_HOST_QA_STAGE")
        self.advance("native")
        row = self.conn.execute(
            "SELECT evidence_json FROM build_runs WHERE project=? AND root=? AND build_id=?",
            (self.project, str(self.root), self.build_id)).fetchone()
        data = json.loads(row["evidence_json"])
        data["NATIVE_QA"].pop("source_fingerprint")
        self.conn.execute(
            "UPDATE build_runs SET evidence_json=? WHERE project=? AND root=? AND build_id=?",
            (json.dumps(data), self.project, str(self.root), self.build_id))
        self.conn.commit()
        self.assertEqual(self.review("native")["status"], "HOLD_STALE_OR_INVALID_QA")

    def test_native_source_edit_invalidates_record_even_with_current_fingerprint(self):
        self.build("native", stage="NATIVE_QA", revision=5)
        self.advance("native")
        self.source.write_text("print('changed')\n", encoding="utf-8")
        new_fingerprint = orbit_build.code_fingerprint(self.root)
        self.assertNotEqual(self.fingerprint, new_fingerprint)
        self.assertEqual(self.review("native")["status"], "HOLD_STALE_OR_INVALID_QA")
        self.assertEqual(
            self.review("native",
                        expected_source_fingerprint=self.fingerprint)["status"],
            "HOLD_STALE_SOURCE")

    def test_native_invalid_report_cannot_advance(self):
        self.build("native", stage="NATIVE_QA", revision=5)
        report = json.loads(self.evidence("native"))
        report["commands"][0]["exit_code"] = 1
        before = self.conn.total_changes
        refused = self.advance("native", evidence=json.dumps(report))
        self.assertEqual(refused["status"], "HOLD")
        self.assertEqual(self.conn.total_changes, before)
        self.assertEqual(self.review("native")["status"], "HOLD_HOST_QA_STAGE")

    def test_cli_library_host_mode_uses_structured_verify_not_browser(self):
        self.build("library", stage="VERIFY", revision=5)
        self.assertEqual(self.review("host")["status"], "HOLD_HOST_QA_STAGE")
        delivered = self.advance("host")
        self.assertEqual(delivered["status"], "ADVANCED")
        self.assertEqual(delivered["run"]["stage"], "REVIEW")
        report = delivered["run"]["evidence"]["VERIFY"]
        self.assertEqual(report["qa_build_revision"], 5)
        self.assertEqual(report["source_fingerprint"], self.fingerprint)
        result = self.review("host")
        self.assertEqual(result["status"], "READY_FOR_INDEPENDENT_REVIEW")
        self.assertEqual(result["recorded_qa_stage"], "VERIFY")
        self.assertTrue(result["host_qa_reporter_unverified"])
        self.assertFalse(result["tests_independently_verified"])
        self.assertFalse(result["merge_performed"])
        self.assertEqual(self.review("native")["status"], "HOLD_QA_MODE_MISMATCH")
        self.assertEqual(self.review("web")["status"], "HOLD_QA_MODE_MISMATCH")

    def test_platform_flow_without_native_stage_uses_explicit_host_mode(self):
        self.build("platform", stage="VERIFY", revision=5)
        self.assertEqual(self.advance("host")["status"], "ADVANCED")
        self.assertEqual(self.review("host")["status"], "READY_FOR_INDEPENDENT_REVIEW")
        self.assertEqual(self.review("native")["status"], "HOLD_QA_MODE_MISMATCH")

    def test_native_flow_rejects_host_and_web_substitution(self):
        self.build("native", stage="NATIVE_QA", revision=5)
        self.advance("native")
        self.assertEqual(self.review("host")["status"], "HOLD_QA_MODE_MISMATCH")
        self.assertEqual(self.review("web")["status"], "HOLD_QA_MODE_MISMATCH")
        self.assertEqual(self.review()["status"], "HOLD_QA_MODE_MISMATCH")

    def test_host_mode_rejects_old_revision_tamper_or_open_feedback(self):
        self.build("library", stage="VERIFY", revision=5)
        self.advance("host")
        row = self.conn.execute(
            "SELECT evidence_json FROM build_runs WHERE project=? AND root=? AND build_id=?",
            (self.project, str(self.root), self.build_id)).fetchone()
        saved = json.loads(row["evidence_json"])
        for field, bad in (
            ("qa_build_revision", True),
            ("qa_build_revision", 99),
            ("source_identity_kind", "GIT_SHA_VERIFIED"),
            ("host_execution_attested", True),
            ("qa_project", "unrelated-project"),
            ("qa_build_id", "different-build"),
            ("qa_stage", "NATIVE_QA"),
        ):
            with self.subTest(field=field, bad=bad):
                edited = json.loads(json.dumps(saved))
                edited["VERIFY"][field] = bad
                self.conn.execute(
                    "UPDATE build_runs SET evidence_json=? "
                    "WHERE project=? AND root=? AND build_id=?",
                    (json.dumps(edited), self.project, str(self.root), self.build_id))
                self.conn.commit()
                self.assertEqual(self.review("host")["status"],
                                 "HOLD_STALE_OR_INVALID_QA")
        saved["__orbit_feedback"] = [{"status": "OPEN"}]
        self.conn.execute(
            "UPDATE build_runs SET evidence_json=? WHERE project=? AND root=? AND build_id=?",
            (json.dumps(saved), self.project, str(self.root), self.build_id))
        self.conn.commit()
        self.assertEqual(self.review("host")["status"], "HOLD_STALE_OR_INVALID_QA")

    def test_identical_source_cannot_reuse_another_builds_host_qa(self):
        self.build("library", stage="VERIFY", revision=5)
        first = self.advance("host")
        self.assertEqual(first["status"], "ADVANCED")
        self.assertEqual(self.review("host")["status"],
                         "READY_FOR_INDEPENDENT_REVIEW")
        self.assertEqual(first["run"]["evidence"]["VERIFY"]["qa_build_id"],
                         self.build_id)
        self.assertEqual(first["run"]["evidence"]["VERIFY"]["qa_project"],
                         self.project)
        self.assertEqual(first["run"]["evidence"]["VERIFY"]["qa_stage"],
                         "VERIFY")
        # A second build in the same project has identical source bytes and
        # stage revision, but copied QA evidence must not validate for it.
        self.conn.execute(
            "INSERT INTO build_runs (project,root,build_id,stage,revision,"
            "objective,evidence_json,updated_at) VALUES(?,?,?,?,?,?,?,?)",
            (self.project, str(self.root), "other-build", "REVIEW", 6,
             "A separate objective must receive its own host test run",
             json.dumps(first["run"]["evidence"]), "2026-11-01"),
        )
        self.conn.commit()
        before = self.conn.total_changes
        self.assertEqual(
            self.review("host", build_id="other-build")["status"],
            "HOLD_STALE_OR_INVALID_QA",
        )
        self.assertEqual(self.conn.total_changes, before)
        # The original build's reviewed evidence stays intact.
        self.assertEqual(self.review("host")["status"],
                         "READY_FOR_INDEPENDENT_REVIEW")

    def test_malformed_native_platform_values_hold_without_exception_or_write(self):
        self.build("native", stage="NATIVE_QA", revision=5)
        for malformed in ([{}], [["android"]], [None], [True]):
            with self.subTest(platforms=malformed):
                data = json.loads(self.evidence("native"))
                data["platforms"] = malformed
                before = self.conn.total_changes
                result = self.advance("native", evidence=json.dumps(data))
                self.assertEqual(result["status"], "HOLD")
                self.assertEqual(self.conn.total_changes, before)
                self.assertEqual(
                    orbit_build.get(self.conn, self.root, {
                        "project": self.project, "build_id": self.build_id,
                    })["stage"], "NATIVE_QA",
                )

    def test_invalid_qa_mode_types_reject_at_direct_review_boundary(self):
        self.build("native", stage="NATIVE_QA", revision=5)
        self.advance("native")
        base = {
            "tasks": [{"task_key": "implementation", "expected_revision": 2}],
            "expected_source_fingerprint": self.fingerprint,
            "build_id": self.build_id,
        }
        for malformed in ([], {}, None, 4, True):
            with self.subTest(qa_mode=malformed):
                with self.assertRaisesRegex(ValueError, "qa_mode"):
                    orbit_swarm_integrity.review(
                        self.conn, self.root, self.project,
                        {**base, "qa_mode": malformed},
                    )

    def test_corrupted_legacy_flow_fails_closed_in_native_qa_review(self):
        self.build("native", stage="NATIVE_QA", revision=5)
        self.advance("native")
        self.conn.execute(
            "UPDATE build_runs SET evidence_json=? WHERE project=? AND root=? "
            "AND build_id=?",
            (json.dumps([]), self.project, str(self.root), self.build_id),
        )
        self.conn.commit()
        build = orbit_build.get(self.conn, self.root, {
            "project": self.project, "build_id": self.build_id,
        })
        self.assertEqual(orbit_build.flow_for(build), orbit_build.STAGES)
        before = self.conn.total_changes
        self.assertEqual(self.review("native")["status"], "HOLD_QA_MODE_MISMATCH")
        self.assertEqual(before, self.conn.total_changes)

    def test_inconsistent_persisted_stage_holds_without_exception(self):
        self.build("native", stage="NATIVE_QA", revision=5)
        self.advance("native")
        self.conn.execute(
            "UPDATE build_runs SET stage=? WHERE project=? AND root=? AND build_id=?",
            ("NOT_A_RECORDED_STAGE", self.project, str(self.root), self.build_id),
        )
        self.conn.commit()
        before = self.conn.total_changes
        result = self.review("native")
        self.assertEqual(result["status"], "HOLD_QA_MODE_MISMATCH")
        self.assertFalse(result["tests_independently_verified"])
        self.assertEqual(before, self.conn.total_changes)

    def test_malformed_feedback_entry_invalidates_host_qa(self):
        self.build("library", stage="VERIFY", revision=5)
        self.advance("host")
        row = self.conn.execute(
            "SELECT evidence_json FROM build_runs WHERE project=? AND root=? "
            "AND build_id=?",
            (self.project, str(self.root), self.build_id),
        ).fetchone()
        saved = json.loads(row["evidence_json"])
        saved["__orbit_feedback"] = ["OPEN"]
        self.conn.execute(
            "UPDATE build_runs SET evidence_json=? WHERE project=? AND root=? "
            "AND build_id=?",
            (json.dumps(saved), self.project, str(self.root), self.build_id),
        )
        self.conn.commit()
        before = self.conn.total_changes
        self.assertEqual(self.review("host")["status"],
                         "HOLD_STALE_OR_INVALID_QA")
        self.assertEqual(before, self.conn.total_changes)

    def test_all_modes_block_active_other_project_worker_without_disclosure(self):
        self.build("native", stage="NATIVE_QA", revision=5)
        self.advance("native")
        self.conn.execute(
            """INSERT INTO orbit_agent_tasks
               (project, project_root, task_key, step, role, goal, reason,
                write_paths, depends_on, status, revision,
                created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("private-project", str(self.root), "secret-worker",
             "Implementation", "backend", "Protected task information",
             "Unrelated project", "[]", "[]", "RUNNING", 1,
             "2026-11-01", "2026-11-01"))
        self.conn.commit()
        before = self.conn.total_changes
        result = self.review("native")
        self.assertEqual(result["status"], "HOLD_HOST_RECONCILIATION")
        self.assertEqual(result["active_records_same_root"], 1)
        self.assertNotIn("private-project", json.dumps(result))
        self.assertNotIn("secret-worker", json.dumps(result))
        self.assertEqual(self.conn.total_changes, before)

    def test_missing_build_and_wrong_project_never_reuse_other_qa(self):
        self.build("native", stage="NATIVE_QA", revision=5)
        self.advance("native")
        out = self.review("native", build_id="missing")
        self.assertEqual(out["status"], "HOLD_INDEPENDENT_QA")
        other = self.review("native", project="another-project")
        self.assertEqual(other["status"], "HOLD_TASK_INTEGRATION")
        self.assertNotIn("native-qa-lab", json.dumps(other))
        with self.assertRaises(ValueError):
            self.review("external")
        self.assertEqual(len(orbit_mcp.TOOLS), 48)
        tool = next(x for x in orbit_mcp.TOOLS
                    if x["name"] == "orbit_swarm_integration_review")
        self.assertTrue(tool["annotations"]["readOnlyHint"])
        self.assertIn("qa_mode", tool["inputSchema"]["properties"])


if __name__ == "__main__":
    unittest.main()
