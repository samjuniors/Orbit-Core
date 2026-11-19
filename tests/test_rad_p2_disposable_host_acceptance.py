"""Non-invasive tests for manual RAD P2 host acceptance harness.

These MUST NOT call --apply with its valid confirmation; CI must never
create real Windows AppContainer profiles or modify ACLs.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "rad_p2_disposable_host_acceptance.py"


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
        spec = importlib.util.spec_from_file_location("rad_p2_manual_host", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertFalse(module.plan()["ci_auto_execution"])
        self.assertFalse(module.plan()["external_network"])
        self.assertFalse(module.plan()["reads_real_credentials"])

    def test_harness_is_not_in_automatic_workflow(self):
        """Only allow manual script invocation, never auto-run from CI."""
        workflow = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
        if workflow.exists():
            content = workflow.read_text(encoding="utf-8")
            self.assertNotIn("rad_p2_disposable_host_acceptance.py", content)


if __name__ == "__main__":
    unittest.main()
