"""Synthetic v0.32 host-native browser QA evidence contract, never a real UI test.

The host controls the actual Browser/Computer tool, screenshots and permissions.
Orbit pins caller-reported observations to a live preview and current source,
then leaves independent review (and all real host acceptance) outstanding.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source" / "runtime"))

import orbit_build
import orbit_capabilities
import orbit_mcp
import orbit_preview
import orbit_tasks
import orbit_swarm_integrity


class FakeProcess:
    def poll(self):
        return None


class HostNativeBrowserQATests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = (Path(temp.name) / "app").resolve()
        self.root.mkdir()
        self.index = self.root / "index.html"
        self.index.write_text("<!doctype html><title>fixture</title><button>save</button>", encoding="utf-8")
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.addCleanup(self.db.close)
        orbit_build.setup(self.db)
        orbit_build.setup_browser(self.db)
        orbit_tasks.setup(self.db)
        self.project = "host-browser-qa"
        self.build_id = "web-app"
        self.preview_id = "test-web"
        self.port = 43123
        self.session = {"proc": FakeProcess(), "port": self.port, "started_at": 12345.0}
        self.key = orbit_preview.preview_key(self.root, self.preview_id)
        orbit_preview.SESSIONS[self.key] = self.session
        self.addCleanup(orbit_preview.SESSIONS.pop, self.key, None)
        self.patch_ready = patch.object(orbit_preview, "status", return_value={"status": "READY"})
        self.patch_ready.start()
        self.addCleanup(self.patch_ready.stop)
        self.db.execute(
            "INSERT INTO build_runs(project,root,build_id,stage,revision,objective,evidence_json,updated_at)"
            " VALUES(?,?,?,?,?,?,?,?)",
            (self.project, str(self.root), self.build_id, "BROWSER_QA", 4,
             "Synthetic UI fixture to test host-native evidence", "{}", "2026-11-06"))
        self.db.commit()

    def report(self):
        return {
            "provider": "host_browser",
            "tool_name": "codex.browser_use",
            "session_reference": "codex-fixture-session-123",
            "screenshot_reference": "host-screenshot-fixture-123",
            "observed_url": f"http://127.0.0.1:{self.port}/",
            "approval_reference": "owner-approved-fixture-123",
            "permission_state": "APPROVED",
            "actions": [
                {"kind": "click", "status": "PASS", "observation": "Clicked Save in the disposable fixture"},
                {"kind": "assert", "status": "PASS", "observation": "Observed expected Save confirmation in the fixture"},
            ],
        }

    def args(self, **overrides):
        return {
            "project_root": str(self.root), "project": self.project,
            "build_id": self.build_id, "expected_revision": 4,
            "outcome": "PASS", "evidence": "Synthetic caller-reported UI actions; no real browser run",
            "preview_id": self.preview_id,
            "host_browser_qa": self.report(),
            "confirm_write": True,
            **overrides,
        }

    def advance(self, **overrides):
        return orbit_build.advance(self.db, self.root, self.args(**overrides))

    def accepted_task(self):
        self.db.execute(
            "INSERT INTO orbit_agent_tasks"
            " (project,project_root,task_key,step,role,goal,reason,write_paths,"
            " depends_on,status,revision,changed_paths,created_at,updated_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (self.project, str(self.root), "ui", "Implement", "frontend",
             "Synthetic UI implementation task only", "Scoped test fixture",
             '["index.html"]', "[]", "REVIEW_ACCEPTED", 2, '["index.html"]',
             "2026-11-06", "2026-11-06"))
        self.db.commit()

    def review(self):
        return orbit_swarm_integrity.review(self.db, self.root, self.project, {
            "project_root": str(self.root), "project": self.project,
            "tasks": [{"task_key": "ui", "expected_revision": 2}],
            "expected_source_fingerprint": orbit_build.code_fingerprint(self.root),
            "build_id": self.build_id, "qa_mode": "web",
        })

    def test_host_qa_preview_and_advance_pin_source_and_provenance(self):
        before = self.db.total_changes
        prev = self.advance(confirm_write=False)
        self.assertEqual(prev["status"], "PREVIEW_ONLY")
        self.assertTrue(prev["source_pin_required"])
        self.assertEqual(self.db.total_changes, before)
        actual = self.advance()
        self.assertEqual(actual["status"], "ADVANCED")
        self.assertEqual(actual["run"]["stage"], "REVIEW")
        record = json.loads(self.db.execute("SELECT evidence_json FROM build_runs").fetchone()[0])["BROWSER_QA"]
        self.assertEqual(record["source_fingerprint"], orbit_build.code_fingerprint(self.root))
        self.assertEqual(record["verification"], "host-native-browser-caller-reported")
        self.assertEqual(record["qa_build_revision"], 4)
        self.assertEqual(record["preview_started_at"], 12345.0)
        for flag in ("host_execution_attested", "host_permission_verified",
                     "screenshot_independently_verified", "evidence_independently_verified"):
            self.assertFalse(record[flag])
        self.assertFalse(record["host_browser_qa"]["origin_policy_attested"])
        self.assertFalse(record["host_browser_qa"]["host_permission_attested"])
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM browser_results").fetchone()[0], 0)

    def test_web_integration_review_accepts_report_for_independent_review_only(self):
        self.accepted_task()
        self.advance()
        # The preview session need not survive a later independent integration review.
        orbit_preview.SESSIONS.pop(self.key, None)
        result = self.review()
        self.assertEqual(result["status"], "READY_FOR_INDEPENDENT_REVIEW")
        self.assertTrue(result["recorded_host_browser_qa_matches_source"])
        for key in ("actual_host_browser_execution_verified", "host_permission_verified",
                    "network_origin_policy_attested", "screenshot_independently_verified",
                    "merge_performed", "tests_independently_verified", "approval_verified"):
            self.assertFalse(result[key])

    def test_missing_browser_record_still_holds_without_host_evidence(self):
        result = self.advance(host_browser_qa=None)
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("Playwright", result["reason"])

    def test_denied_unknown_and_missing_permissions_cannot_pass(self):
        for state in ("DENIED", "UNKNOWN", False, None):
            with self.subTest(state=state):
                report = self.report()
                report["permission_state"] = state
                with self.assertRaises(ValueError):
                    self.advance(host_browser_qa=report)
        self.assertEqual(self.db.execute("SELECT stage FROM build_runs").fetchone()[0], "BROWSER_QA")

    def test_mismatched_url_and_failed_or_passive_actions_cannot_pass(self):
        variants = [
            {"observed_url": "http://localhost:43123/"},
            {"observed_url": "http://127.0.0.1:43124/"},
            {"actions": [{"kind": "screenshot", "status": "PASS", "observation": "Screenshot of fixture exists"},
                         {"kind": "inspect", "status": "PASS", "observation": "Only inspected fixture"}]},
            {"actions": [{"kind": "click", "status": "PASS", "observation": "Clicked the fixture button"},
                         {"kind": "assert", "status": "FAIL", "observation": "Expected text was not present"}]},
            {"actions": []},
            {"session_reference": ""},
            {"screenshot_reference": ""},
        ]
        for override in variants:
            with self.subTest(override=override):
                report = {**self.report(), **override}
                with self.assertRaises(ValueError):
                    self.advance(host_browser_qa=report)

    def test_no_source_or_preview_drift_during_record(self):
        self.session["proc"] = type("Dead", (), {"poll": lambda self: 1})()
        with self.assertRaisesRegex(ValueError, "READY preview"):
            self.advance()
        self.session["proc"] = FakeProcess()
        self.index.unlink()
        prev = self.advance(confirm_write=False)
        self.assertEqual(prev["status"], "HOLD")
        self.assertIn("source", prev["reason"].lower())

    def test_source_changed_after_record_holds_integrator(self):
        self.accepted_task()
        self.advance()
        self.index.write_text("<title>modified after QA</title>", encoding="utf-8")
        result = self.review()
        # Expected fingerprint is updated to the new bytes, so historical QA is stale.
        self.assertEqual(result["status"], "HOLD_STALE_OR_INVALID_QA")
        self.assertFalse(result["tests_independently_verified"])

    def test_tampered_host_provenance_holds_integration(self):
        self.accepted_task()
        self.advance()
        raw = self.db.execute("SELECT evidence_json FROM build_runs").fetchone()[0]
        obj = json.loads(raw)
        obj["BROWSER_QA"]["host_execution_attested"] = True
        self.db.execute("UPDATE build_runs SET evidence_json=?", (json.dumps(obj),))
        self.db.commit()
        self.assertEqual(self.review()["status"], "HOLD_STALE_OR_INVALID_QA")

    def test_codex_native_provider_preferred_but_tool_consent_never_assumed(self):
        plan = orbit_capabilities.browser_workflow(
            ["browser_click", "computer_use"], [], host="codex",
            permission_state="UNKNOWN")
        self.assertEqual(plan["preferred"]["id"], "host_browser")
        self.assertIn("Codex desktop", plan["host_specific_guidance"])
        self.assertIn("Codex CLI", plan["host_specific_guidance"])
        self.assertFalse(plan["execution_verified"])
        self.assertFalse(plan["host_native_qa_recording"]["host_consent_attested"])
        self.assertTrue(plan["host_native_qa_recording"]["no_separate_playwright_install_required"])
        blocked = orbit_capabilities.browser_workflow(
            ["browser_click", "computer_use"], [], host="codex",
            permission_state="DENIED")
        self.assertIsNone(blocked["preferred"])
        self.assertEqual(blocked["decision"], "HOLD_PERMISSION_DENIED")
        self.assertFalse(blocked["install_performed"])

    def test_desktop_plugin_name_alone_does_not_prove_action(self):
        plan = orbit_capabilities.browser_workflow(
            ["Browser", "Computer"], [], host="codex")
        self.assertFalse(any(
            provider["status"] == "HOST_REPORTED_ACTION_TOOL"
            for provider in plan["providers"]
        ))
        self.assertFalse(plan["execution_verified"])

    def test_codex_browser_plugin_and_native_bridge_are_review_candidates(self):
        # These are names reported by the current host, not a global plugin
        # installation scan or permission attestation.
        plugin = ["browser@openai-bundled"]
        tools = ["mcp__node_repl__js"]
        planned = orbit_capabilities.browser_workflow(
            tools, [], host="codex", host_plugins=plugin)
        browser = planned["providers"][0]
        self.assertEqual(browser["status"], "HOST_PLUGIN_BRIDGE_REVIEW_REQUIRED")
        self.assertTrue(browser["bridge_reported"])
        self.assertEqual(planned["preferred"]["id"], "host_browser")
        self.assertFalse(planned["execution_verified"])
        self.assertFalse(planned["permission_verified"])
        self.assertIn("official host-provided bridge", planned["host_skill_setup"])
        self.assertEqual(planned["reported_host_plugins"], ["browser"])
        self.assertFalse(planned["host_native_qa_recording"]["host_consent_attested"])

    def test_codex_computer_use_plugin_bridge_does_not_claim_a_click(self):
        plan = orbit_capabilities.browser_workflow(
            ["mcp__node_repl__js"], [], host="codex",
            host_plugins=["computer-use@openai-bundled"])
        self.assertEqual(plan["preferred"]["id"], "host_computer_use")
        self.assertEqual(plan["providers"][1]["status"],
                         "HOST_PLUGIN_BRIDGE_REVIEW_REQUIRED")
        self.assertFalse(plan["execution_verified"])
        cua = orbit_capabilities.browser_workflow(
            ["mcp__cua_repl__js"], [], host="codex",
            host_plugins=["unified-computer-use@openai-bundled"])
        self.assertEqual(cua["preferred"]["id"], "host_computer_use")
        self.assertFalse(cua["host_native_qa_recording"]["screenshot_verified"])

    def test_plugin_or_generic_bridge_alone_cannot_be_used_as_browser(self):
        plugin_only = orbit_capabilities.browser_workflow(
            [], [], host="codex", host_plugins=["browser@openai-bundled"])
        self.assertEqual(plugin_only["providers"][0]["status"],
                         "PLUGIN_REPORTED_TOOL_UNAVAILABLE")
        self.assertFalse(plugin_only["providers"][0]["bridge_reported"])
        bridge_only = orbit_capabilities.browser_workflow(
            ["mcp__node_repl__js"], [], host="codex")
        self.assertEqual(bridge_only["providers"][0]["status"], "NOT_REPORTED")
        self.assertFalse(bridge_only["providers"][0]["bridge_reported"])
        # Same names in Antigravity do not constitute a Codex desktop plugin.
        unrelated = orbit_capabilities.browser_workflow(
            ["mcp__node_repl__js"], [], host="antigravity",
            host_plugins=["browser@openai-bundled"])
        self.assertEqual(unrelated["providers"][0]["status"], "NOT_REPORTED")

    def test_codex_bridge_permission_denial_blocks_all_candidates(self):
        denied = orbit_capabilities.browser_workflow(
            ["mcp__node_repl__js"], [], host="codex",
            host_plugins=["browser@openai-bundled"],
            permission_state="DENIED")
        self.assertIsNone(denied["preferred"])
        self.assertEqual(denied["decision"], "HOLD_PERMISSION_DENIED")
        self.assertFalse(denied["permission_verified"])

    def test_capability_schema_accepts_host_plugin_inventory_but_never_certifies_it(self):
        schema = next(t["inputSchema"] for t in orbit_mcp.TOOLS
                      if t["name"] == "orbit_capability_select")
        self.assertIn("host_plugins", schema["properties"])
        self.assertEqual(schema["properties"]["host_plugins"]["maxItems"], 24)
        result = orbit_mcp.execute(self.db, "orbit_capability_select", {
            "project_root": str(self.root),
            "objective": "orbit-qa: browser testing this web page",
            "host": "codex",
            "host_tools": ["mcp__node_repl__js"],
            "host_plugins": ["browser@openai-bundled"],
        })
        self.assertEqual(result["browser_workflow"]["preferred"]["id"], "host_browser")
        self.assertFalse(result["browser_workflow"]["execution_verified"])
        self.assertFalse(result["browser_workflow"]["permission_verified"])
        with self.assertRaises(ValueError):
            orbit_capabilities.select(self.root, "browser testing",
                                      host_plugins=["@Browser"] * 25)
        with self.assertRaises(ValueError):
            orbit_capabilities.select(self.root, "browser testing",
                                      host_plugins=[42])

    def test_wrong_stage_or_unapproved_host_report_cannot_pass(self):
        self.advance()
        args = self.args(expected_revision=5)
        with self.assertRaisesRegex(ValueError, "only accepted for BROWSER_QA PASS"):
            orbit_build.advance(self.db, self.root, args)
        schema = next(t["inputSchema"] for t in orbit_mcp.TOOLS
                      if t["name"] == "orbit_build_advance")
        self.assertEqual(schema["properties"]["host_browser_qa"]["type"], "object")
        self.assertIn("permission_state",
                      schema["properties"]["host_browser_qa"]["required"])
        self.assertEqual(len(orbit_mcp.TOOLS), 52)


if __name__ == "__main__":
    unittest.main()
