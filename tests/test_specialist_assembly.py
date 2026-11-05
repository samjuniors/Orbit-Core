"""Read-only adaptive specialist profile selection and resource reuse tests."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source/runtime"))
import orbit_specialists
import orbit_tasks
import orbit_decisions


class SpecialistAssemblyTests(unittest.TestCase):
    def plan(self, kind="web-app", operation="build", *, tools=None,
             skills=None, selected=None, permission="UNKNOWN"):
        return orbit_specialists.plan(
            {"product_type": kind, "operation": operation}, "Build my product",
            {"skills": skills or []}, {"shortlist": selected or []},
            tools or [], permission)

    def test_web_product_infers_team_without_request_keywords(self):
        result = self.plan()
        self.assertEqual(result["status"], "RESOURCE_AND_TEAM_REVIEW_READY")
        self.assertEqual(result["decision_basis"],
                         "PROJECT_CLASSIFICATION_NOT_REQUEST_KEYWORDS")
        roles = [x["role"] for x in result["candidate_roles"]]
        self.assertIn("creative-director", roles)
        self.assertIn("project-manager", roles)
        self.assertIn("cybersecurity", roles)
        self.assertIn("software-engineer", roles)
        self.assertIn("qa", roles)
        self.assertFalse(result["permission_verified"])
        self.assertFalse(result["native_agent_spawned"])
        self.assertFalse(result["profiles_written"])
        self.assertFalse(result["external_resource_automatically_installed"])
        self.assertEqual(len(set(roles)), len(roles))

    def test_small_cli_fix_does_not_create_design_army(self):
        result = self.plan(kind="cli", operation="fix")
        roles = [x["role"] for x in result["candidate_roles"]]
        self.assertEqual(roles, ["software-engineer", "cybersecurity", "qa"])
        self.assertFalse(any(x["role"] == "creative-director" for x in result["candidate_roles"]))
        self.assertTrue(all(x["agent_spawned"] is False for x in result["candidate_roles"]))

    def test_native_tool_report_is_not_execution_proof(self):
        result = self.plan(tools=["collaboration.spawn_agent"])
        self.assertEqual(result["candidate_roles"][0]["native_host_tool_hints"],
                         ["collaboration.spawn_agent"])
        self.assertFalse(result["host_tool_verified"])
        self.assertTrue(all(not r["native_agent_verified"] for r in result["candidate_roles"]))

    def test_trusted_skills_not_assumed_from_inventory(self):
        result = self.plan(
            skills=[{"name": "orbit-security"}],
            selected=[{"name": "orbit-security", "sha256": "a" * 64}])
        sec = next(r for r in result["candidate_roles"] if r["role"] == "cybersecurity")
        self.assertTrue(sec["installed_role_profile_name_seen"])
        self.assertIsNone(sec["profile_candidate"])
        self.assertFalse(sec["profile_installed"])
        self.assertFalse(result["license_and_provenance_checked"])

    def test_denied_permissions_stop_profile_candidates(self):
        result = self.plan(permission="DENIED")
        self.assertEqual(result["status"], "HOLD_PERMISSION_DENIED")
        self.assertTrue(all(x["profile_candidate"] is None for x in result["candidate_roles"]))
        self.assertFalse(result["native_agent_spawned"])

    def test_canonical_security_agent_and_role_contracts(self):
        names = {x["role"]: x["bundled_role_profile_source"]
                 for x in self.plan()["candidate_roles"]}
        self.assertEqual(names["cybersecurity"], "source/agents/orbit-security.md")
        for name in ("project-manager", "creative-director", "software-engineer"):
            self.assertIn(name, orbit_tasks.ROLES)
            self.assertIn("orbit-" + name, orbit_decisions.ROLES)
            path = ROOT / "source/agents" / ("orbit-" + name + ".md")
            self.assertTrue(path.is_file(), str(path))
            self.assertTrue(path.read_text(encoding="utf-8").startswith("---\nname: orbit-"))


if __name__ == "__main__":
    unittest.main()
