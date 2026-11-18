"""v0.33 read-only visual decisions and coverage: no host authority inferred."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source" / "runtime"))

import orbit_decisions
import orbit_specialists


class VisualPolicyTests(unittest.TestCase):
    def test_new_project_starts_with_goals_not_mandatory_design_doc(self):
        first = orbit_specialists.visual_decision("web-app", "build")
        self.assertEqual(first["status"], "ASK_PROJECT_SCOPE_FIRST")
        self.assertFalse(first["files_written"])
        proposed = orbit_specialists.visual_decision("web-app", "build", brief_approved=True)
        self.assertEqual(proposed["status"], "RESEARCH_AND_PROPOSE_DIRECTIONS")
        approved = orbit_specialists.visual_decision(
            "web-app", "build", brief_approved=True, design_approved=True)
        self.assertEqual(approved["status"], "PLAN_APPROVED_DESIGN_IMPLEMENTATION")
        result = orbit_decisions.components("web-app", ["web"], "React 19", "reuse")
        self.assertFalse(result["design_md_required_at_project_start"])
        self.assertTrue(result["new_project_design_order"][0].startswith("Clarify"))
        self.assertFalse(result["external_sources_installed"])

    def test_nonvisual_does_not_get_ui_onboarding(self):
        self.assertEqual(orbit_specialists.visual_decision("plugin-mcp", "build")["status"],
                         "SKIP_NONVISUAL_DESIGN")
        self.assertEqual(orbit_decisions.components(
            "plugin-mcp", [], "Python", "balanced")["new_project_design_order"], [])

    def test_small_icon_change_does_not_trigger_full_redesign(self):
        decision = orbit_specialists.visual_decision(
            "desktop-app", "add-feature", design_approved=True,
            change_scope_clear=True)
        self.assertEqual(decision["status"], "TARGETED_CHANGE_REVIEW")
        self.assertFalse(decision["owner_approval_authenticated"])
        self.assertEqual(orbit_specialists.visual_decision(
            "desktop-app", "redesign", design_approved=True)["status"],
            "ASK_ONE_MATERIAL_SCOPE_QUESTION")

    def test_guide_asks_only_when_material_and_never_learns_globally_from_one_fix(self):
        scoped = orbit_specialists.guide_decision(
            "visual-correction", approved_project_style=True)
        self.assertEqual(scoped["status"], "APPLY_SCOPED_EXISTING_STYLE")
        self.assertTrue(scoped["correction_is_not_global_preference"])
        self.assertFalse(scoped["user_preference_written"])
        self.assertFalse(scoped["native_action_executed"])
        self.assertEqual(orbit_specialists.guide_decision(
            "visual-correction", approved_project_style=False)["status"],
            "OFFER_SCOPED_ALTERNATIVES")
        self.assertEqual(orbit_specialists.guide_decision(
            "redesign", scope_clear=False)["status"],
            "ASK_ONE_MATERIAL_QUESTION")
        self.assertEqual(orbit_specialists.guide_decision(
            "routine", consequential=True)["status"],
            "REQUIRE_OWNER_DECISION")
        self.assertEqual(orbit_specialists.guide_decision(
            "routine", permission_state="DENIED")["status"],
            "HOLD_PERMISSION_DENIED")

    def test_permission_denial_is_not_bypassed(self):
        self.assertEqual(orbit_specialists.visual_decision(
            "web-app", "redesign", permission_state="DENIED")["status"],
            "HOLD_PERMISSION_DENIED")
        with self.assertRaises(ValueError):
            orbit_specialists.visual_decision(
                "web-app", "redesign", permission_state="UNSAFE")

    def test_reuse_first_sources_are_actual_candidates_not_installed(self):
        result = orbit_decisions.components(
            "web-app", ["web"], "React 19 Tailwind", "reuse")
        ids = {x["id"] for x in result["candidates"]}
        self.assertTrue({"vercel-ui-sdk", "lucide", "motion", "shadcn-ui"} <= ids, ids)
        self.assertIn("existing", result["reuse_policy"][0].lower())
        self.assertIn("owner_approval", result["source_review_requirements"])
        self.assertFalse(result["external_sources_installed"])
        vanilla = orbit_decisions.components(
            "website", ["web"], "vanilla html javascript", "reuse")
        self.assertFalse(any(x["id"] == "vercel-ui-sdk" and x["status"] == "REVIEW_MATCH"
                             for x in vanilla["candidates"]))

    def test_design_handoff_requires_complete_dependency_coverage(self):
        plan = orbit_specialists.plan(
            {"product_type": "web-app", "operation": "redesign"}, "Improve layout",
            {"skills": []}, {"shortlist": []}, [], "UNKNOWN")
        design = plan["design_handoff"]
        self.assertIn("component_source_priority", design)
        self.assertIn("new_project_order", design)
        self.assertFalse(design["ui_coverage_review_mcp_exposed"])
        self.assertFalse(design["rendered_visual_qa_verified"])

    def test_coverage_reports_missing_stale_and_failed_without_fake_pass(self):
        expected = {"home": ["default", "loading"], "settings": ["default"]}
        revision = "abc123456789"
        observations = [
            {"screen": "home", "state": "default", "source_revision": revision,
             "status": "PASS", "evidence_ref": "session:home-default"},
            {"screen": "home", "state": "loading", "source_revision": "old456789",
             "status": "PASS", "evidence_ref": "session:home-loading"},
            {"screen": "settings", "state": "default", "source_revision": revision,
             "status": "FAIL", "evidence_ref": "session:settings"},
        ]
        result = orbit_specialists.review_visual_coverage(
            expected, observations, revision)
        self.assertEqual(result["status"], "HOLD_INCOMPLETE_UI_COVERAGE")
        self.assertEqual(result["reported_count"], 1)
        self.assertEqual(result["stale"], [{"screen": "home", "state": "loading"}])
        self.assertEqual(result["blocked"], [{"screen": "settings", "state": "default"}])
        self.assertFalse(result["rendered_visual_qa_passed"])
        self.assertFalse(result["observation_independently_verified"])

    def test_no_observation_or_untrusted_evidence_cannot_pass(self):
        expected = {"home": ["default", "error"]}
        revision = "abc123456789"
        empty = orbit_specialists.review_visual_coverage(expected, [], revision)
        self.assertEqual(empty["status"], "HOLD_INCOMPLETE_UI_COVERAGE")
        self.assertEqual(len(empty["missing"]), 2)
        no_evidence = [{"screen": "home", "state": "default",
                        "source_revision": revision, "status": "PASS",
                        "evidence_ref": "x"}]
        result = orbit_specialists.review_visual_coverage(
            expected, no_evidence, revision)
        self.assertEqual(result["reported_count"], 0)
        with self.assertRaises(ValueError):
            orbit_specialists.review_visual_coverage(
                expected, [dict(no_evidence[0], screen="unknown")], revision)
        with self.assertRaises(ValueError):
            orbit_specialists.review_visual_coverage(
                expected, [no_evidence[0], no_evidence[0]], revision)

    def test_complete_caller_report_still_needs_independent_review(self):
        revision = "abc123456789"
        expected = {"settings": ["default", "error"]}
        checks = [
            {"screen": "settings", "state": name,
             "source_revision": revision, "status": "PASS",
             "evidence_ref": "host-session:" + name} for name in expected["settings"]
        ]
        result = orbit_specialists.review_visual_coverage(expected, checks, revision)
        self.assertEqual(result["status"], "READY_FOR_INDEPENDENT_VISUAL_REVIEW")
        self.assertEqual(result["reported_count"], 2)
        self.assertFalse(result["observation_independently_verified"])
        self.assertFalse(result["rendered_visual_qa_passed"])


if __name__ == "__main__":
    unittest.main()
