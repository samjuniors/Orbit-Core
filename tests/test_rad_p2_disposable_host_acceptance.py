"""Non-invasive tests for manual RAD P2 host acceptance harness.

These MUST NOT call --apply with its valid confirmation; CI must never
create real Windows AppContainer profiles or modify ACLs.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "rad_p2_disposable_host_acceptance.py"
SPEC = importlib.util.spec_from_file_location("rad_p2_manual_host", SCRIPT)
HARNESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HARNESS)


class DisposableHostAcceptanceTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args], capture_output=True,
            text=True, timeout=12)

    def test_default_is_a_nonmutating_hold(self):
        process = self.run_cli()
        self.assertEqual(process.returncode, 2, process.stderr)
        result = json.loads(process.stdout)
        self.assertEqual(result["status"], "HOLD_OPERATOR_CONFIRMATION_REQUIRED")
        for key in ("creates_profile", "changes_acls", "launches_child",
                    "reads_real_credentials", "external_network", "ci_auto_execution"):
            self.assertIs(result[key], False)

    def test_apply_without_exact_phrase_is_rejected(self):
        for args in (("--apply",),
                     ("--apply", "--confirm", "I AGREE"),
                     ("--confirm", "CREATE DISPOSABLE ORBIT APPCONTAINER")):
            with self.subTest(args=args):
                process = self.run_cli(*args)
                self.assertEqual(process.returncode, 2, process.stderr)
                self.assertFalse(json.loads(process.stdout)["creates_profile"])

    def test_help_is_safe_and_explains_explicit_permission(self):
        process = self.run_cli("--help")
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIn("--apply", process.stdout)
        self.assertIn("--confirm", process.stdout)

    def test_plan_contract_is_nonmutating(self):
        self.assertFalse(HARNESS.plan()["ci_auto_execution"])
        self.assertFalse(HARNESS.plan()["external_network"])
        self.assertFalse(HARNESS.plan()["reads_real_credentials"])

    def test_denial_requires_native_error_and_working_control(self):
        for expected, inconclusive in ((5, 2), (10013, 10060)):
            with self.subTest(expected=expected):
                self.assertEqual(HARNESS.denial_result({"winerror": expected}, expected), "PASS")
                self.assertEqual(HARNESS.denial_result({"winerror": inconclusive}, expected), "NOT_VERIFIED")
                self.assertEqual(HARNESS.denial_result({"errno": expected}, expected), "NOT_VERIFIED")
                self.assertEqual(HARNESS.denial_result({"winerror": expected}, expected, False), "NOT_VERIFIED")
                self.assertEqual(HARNESS.denial_result({"success": True}, expected, False), "FAIL")

    def test_cleanup_records_a_failure_and_allows_remaining_steps(self):
        def fail():
            raise OSError("synthetic cleanup error")

        result = {}
        HARNESS.record_check(result, "first", fail)
        HARNESS.record_check(result, "second", lambda: None)
        self.assertEqual(result, {"first": "FAIL", "first_error": "synthetic cleanup error", "second": "PASS"})

    def test_probe_record_requires_all_fields_and_no_trailing_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = Path(tmp) / "result.bin"
            payload = struct.pack("<10I", 0, 0, 5, 5, 5, 0, 10013, 10013, 1234, 0)
            record.write_bytes(payload)
            observations = HARNESS.read_observations(record)
            self.assertEqual(observations["credential_read"], 5)
            self.assertEqual(observations["loopback"], 10013)
            self.assertEqual(observations["descendant_pid"], 1234)
            for invalid in (payload[:-1], payload + b"x"):
                record.write_bytes(invalid)
                with self.assertRaises(struct.error):
                    HARNESS.read_observations(record)

    def test_network_startup_error_blocks_both_endpoints_without_a_connect_result(self):
        checks = {}
        samples = {"winsock_startup": 10107, "loopback": 0, "external": 0}
        controls = {"loopback": {"success": True}, "external": {"success": True}}
        HARNESS.record_network_checks(checks, samples, controls)
        self.assertEqual(checks, {"loopback_denial": "BLOCKED", "external_denial": "BLOCKED"})
        self.assertIsNone(samples["loopback"])
        self.assertIsNone(samples["external"])

    def test_harness_is_not_in_automatic_workflow(self):
        """Only allow manual script invocation, never auto-run from CI."""
        workflow = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
        if workflow.exists():
            content = workflow.read_text(encoding="utf-8")
            self.assertNotIn("rad_p2_disposable_host_acceptance.py", content)


if __name__ == "__main__":
    unittest.main()
