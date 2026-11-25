"""Tests for product-aware cybersecurity review plans and honest evidence states."""
from __future__ import annotations

import hashlib
import sys
import tempfile
import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source" / "runtime"))

import orbit_security_review
import orbit_mcp


class SecurityReviewPlanTests(unittest.TestCase):
    def profile(self, product, platform, technologies=None):
        return {"product_type": product, "platform": platform,
                "technologies": technologies or [], "operation": "review"}

    def test_plugin_mcp_includes_tool_authority_and_workspace_boundaries(self):
        result = orbit_security_review.plan(
            self.profile("plugin-mcp", "windows", ["python"]),
            "Review local MCP plugin security",
            permission_state="APPROVED",
            available_security_tools=["bandit", "gitleaks"])
        controls = {x["control"] for x in result["controls"]}
        self.assertTrue({
            "tool_authority", "workspace_isolation", "prompt_injection",
            "protocol_validation", "secrets_and_credentials",
            "dependencies_and_supply_chain",
        } <= controls)
        self.assertEqual(result["status"], "SECURITY_REVIEW_PLAN_READY")
        self.assertEqual(result["findings_status"], "NOT_SCANNED")
        self.assertEqual(result["scanner_discovery"]["caller_reported_tool_name_hints"],
                         ["bandit", "gitleaks"])
        self.assertFalse(result["scanner_discovery"]["tool_installation_verified"])
        self.assertFalse(result["scanner_discovery"]["tool_callable_verified"])
        self.assertFalse(result["vulnerability_scan_performed"])
        self.assertFalse(result["release_security_attested"])

    def test_mobile_profile_does_not_receive_web_only_controls(self):
        result = orbit_security_review.plan(
            self.profile("mobile-app", "android", ["kotlin"]),
            "Review Android application security")
        controls = {x["control"] for x in result["controls"]}
        self.assertTrue({"mobile_storage", "mobile_platform", "mobile_network"} <= controls)
        self.assertNotIn("web_sessions", controls)
        self.assertNotIn("browser_injection", controls)
        self.assertIn("OWASP MASVS", result["standards_to_consider"])

    def test_api_profile_includes_object_authorization_and_service_identity(self):
        result = orbit_security_review.plan(
            self.profile("api-service", "server", ["python"]),
            "Review API authorization")
        controls = {x["control"] for x in result["controls"]}
        self.assertTrue({"api_authorization", "service_identity"} <= controls)
        self.assertIn("OWASP ASVS 5.0", result["standards_to_consider"])

    def test_denied_permission_holds_and_no_scanning_is_claimed(self):
        result = orbit_security_review.plan(
            self.profile("desktop-app", "windows", ["electron"]),
            "Review desktop security", permission_state="DENIED",
            available_security_tools=["semgrep"])
        self.assertEqual(result["status"], "HOLD_PERMISSION_DENIED")
        self.assertFalse(result["permissions"]["host_permission_verified"])
        self.assertFalse(result["permissions"]["external_targets_authorized"])
        self.assertFalse(result["vulnerability_scan_performed"])

    def test_static_scan_requires_approval_and_redacts_source_values(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            src = root / "src"
            src.mkdir()
            secret = "AKIA1234567890ABCDEF"
            (src / "vulnerable.py").write_text(
                'KEY = "' + secret + '"\n'
                'PASSWORD = "very-secret-value-123"\n'
                'subprocess.run(command, shell=True)\n',
                encoding="utf-8")
            blocked = orbit_security_review.scan_project(root)
            self.assertEqual(blocked["status"], "HOLD_PERMISSION_UNKNOWN")
            self.assertEqual(blocked["findings_status"], "NOT_SCANNED")
            result = orbit_security_review.scan_project(
                root, permission_state="APPROVED")
            self.assertEqual(result["status"], "STATIC_REVIEW_HINTS_FOUND")
            self.assertFalse(result["source_text_returned"])
            self.assertFalse(result["secret_values_returned"])
            serialized = str(result)
            self.assertNotIn(secret, serialized)
            self.assertNotIn("very-secret-value-123", serialized)
            self.assertTrue(all(x["status"] == "LIKELY_NOT_VERIFIED"
                                and x["evidence_ref_sha256"] for x in result["findings"]))
            for finding in result["findings"]:
                expected_ref = hashlib.sha256(
                    f"{finding['rule']}:{finding['file']}:{finding['line']}".encode("utf-8")
                ).hexdigest()
                self.assertEqual(finding["evidence_ref_sha256"], expected_ref)
            self.assertFalse(result["project_code_executed"])
            self.assertFalse(result["network_accessed"])

    def test_static_scan_no_hints_is_not_a_security_pass(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            src = root / "src"
            src.mkdir()
            (src / "safe.py").write_text(
                'PASSWORD = os.environ.get("APP_PASSWORD")\n',
                encoding="utf-8")
            result = orbit_security_review.scan_project(
                root, permission_state="APPROVED")
            self.assertEqual(result["status"], "NO_STATIC_HINTS_REVIEW_REQUIRED")
            self.assertEqual(result["findings_status"], "NO_STATIC_HINTS_NOT_A_PASS")
            self.assertFalse(result["security_certification"])

    def test_invalid_profile_permission_and_untrusted_tool_inventory_rejected(self):
        with self.assertRaises(ValueError):
            orbit_security_review.plan(
                self.profile("mobile-app", "windows", ["swift"]),
                "Review mobile app")
        with self.assertRaises(ValueError):
            orbit_security_review.plan(
                self.profile("cli", "linux"), "Review CLI",
                permission_state="SUPERUSER")
        with self.assertRaises(ValueError):
            orbit_security_review.plan(
                self.profile("cli", "linux"), "Review CLI",
                available_security_tools=["bandit", "../install-and-run"])

    def test_mcp_tool_is_registered_read_only_and_dispatches_plan(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            args = {
                "project_root": str(root), "project": "security-plan",
                "objective": "Review API security",
                "project_profile": self.profile("api-service", "server", ["python"]),
            }
            self.assertIn("orbit_security_review_plan",
                          [item["name"] for item in orbit_mcp.TOOLS])
            self.assertIn("orbit_security_review_plan", orbit_mcp.READ_ONLY_TOOLS)
            source = root / "src"
            source.mkdir()
            (source / "api.py").write_text(
                'AWS_KEY = "AKIA1234567890ABCDEF"\n'
                'PASSWORD = "real-secret-value-123"\n'
                'requests.get(url, verify=False)\n'
                'subprocess.run(command, shell=True)\n',
                encoding="utf-8")
            with sqlite3.connect(":memory:") as conn:
                result = orbit_mcp.execute(
                    conn, "orbit_security_review_plan",
                    {**args, "permission_state": "APPROVED", "scan_source": True})
            self.assertEqual(result["status"], "SECURITY_REVIEW_PLAN_READY")
            self.assertFalse(result["vulnerability_scan_performed"])
            scan = result["static_scan"]
            self.assertEqual(scan["status"], "STATIC_REVIEW_HINTS_FOUND")
            self.assertTrue({"AWS_ACCESS_KEY_ID", "HARDCODED_CREDENTIAL",
                             "TLS_VERIFICATION_DISABLED", "SHELL_TRUE"} <=
                            {x["id"].removeprefix("ORBIT-") for x in scan["findings"]})
            self.assertFalse(scan["secret_values_returned"])

    def test_every_control_stays_unverified_until_real_evidence_exists(self):
        result = orbit_security_review.plan(
            self.profile("web-app", "web", ["react"]),
            "Review web application")
        self.assertTrue(result["controls"])
        self.assertTrue(all(x["status"] == "REVIEW_REQUIRED"
                            and not x["verified"] for x in result["controls"]))
        self.assertFalse(result["threat_model"]["attack_paths_verified"])
        self.assertFalse(result["threat_model"]["data_flows_verified"])
        self.assertEqual(result["release_gate"]["status"], "REVIEW_REQUIRED")
        self.assertFalse(result["release_gate"]["blanket_secure_claim_allowed"])


if __name__ == "__main__":
    unittest.main()
