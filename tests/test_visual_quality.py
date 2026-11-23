"""Opt-in, source-only design drift and browser QA scope evidence tests."""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source" / "runtime"))
import orbit_specialists
import orbit_mcp
import orbit_intake
import orbit_improvement


class VisualQualityTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name).resolve() / "product"
        (self.root / "src/app/settings").mkdir(parents=True)
        (self.root / "src/components").mkdir()
        (self.root / "src/styles").mkdir()
        (self.root / "src/app/page.tsx").write_text(
            'import { House } from "lucide-react";\n'
            'export default function Home(){ return <div className="gap-[13px] text-[15px]">'
            '<House/></div> }\n', encoding="utf-8")
        (self.root / "src/app/settings/page.tsx").write_text(
            'import { Gear } from "phosphor-react";\n'
            'export default function Settings(){return <Gear/>}\n', encoding="utf-8")
        (self.root / "src/components/Nav.tsx").write_text(
            'export function Nav(){return <button aria-label="Home"/>}\n', encoding="utf-8")
        (self.root / "src/styles/base.css").write_text(
            ':root { --space-md: 16px; }\n'
            '.body { gap: 11px; font-size: 14px; transition-duration: 300ms;'
            ' padding: var(--space-md); margin: var(--not-defined-here); }\n'
            '@media (prefers-reduced-motion: reduce) { * { animation: none; } }\n',
            encoding="utf-8")
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.addCleanup(self.conn.close)
        orbit_intake.setup(self.conn)
        orbit_improvement.setup(self.conn)

    def decision(self, **updates):
        args = {"project_root": str(self.root), "project": "quality-fixture",
                "product_type": "web-app", "existing_stack": "React 19 Tailwind",
                **updates}
        return orbit_mcp.execute(self.conn, "orbit_decision_route", args)

    def test_static_hints_include_spacing_type_motion_and_token_refs(self):
        inv = orbit_specialists.scan_visual_project(self.root)
        self.assertEqual(inv["status"], "HEURISTIC_UI_INVENTORY_PARTIAL")
        cats = {hint["area"] for hint in inv["style_literal_review_hints"]}
        self.assertTrue({"spacing", "typography", "motion"} <= cats, cats)
        self.assertEqual(set(inv["icon_families_imported_hint"]),
                         {"lucide", "phosphor"})
        self.assertIn("space-md", inv["css_custom_properties_hint"])
        self.assertIn("not-defined-here", inv["css_variable_references_hint"])
        self.assertIn("src/styles/base.css", inv["reduced_motion_source_hints"])
        self.assertFalse(inv["rendered_visual_qa_verified"])
        self.assertFalse(inv["source_git_revision_verified"])

    def test_no_design_contract_never_claims_consistency(self):
        inv = orbit_specialists.scan_visual_project(self.root)
        audit = orbit_specialists.audit_visual_contract(inv, None)
        self.assertEqual(audit["status"], "NEEDS_PROJECT_DESIGN_CONTRACT")
        self.assertFalse(audit["style_rules_applied"])
        self.assertFalse(audit["approved_contract_authenticated"])

    def test_approved_style_claim_detects_mixed_icons_and_spacing_drift(self):
        inv = orbit_specialists.scan_visual_project(self.root)
        audit = orbit_specialists.audit_visual_contract(inv, {
            "icon_family": "lucide", "spacing_policy": "token-first",
            "typography_policy": "token-first", "motion_policy": "token-first"})
        rules = {f["rule"] for f in audit["findings"]}
        self.assertEqual(audit["status"], "STYLE_DRIFT_REVIEW_REQUIRED")
        self.assertIn("MIXED_ICON_FAMILIES", rules)
        self.assertIn("ICON_FAMILY_MISMATCH", rules)
        self.assertIn("POTENTIAL_TOKEN_DRIFT_RAW_CSS_LITERAL", rules)
        self.assertIn("POTENTIAL_TOKEN_DRIFT_ARBITRARY_UTILITY_LITERAL", rules)
        self.assertIn("UNRESOLVED_TOKEN_REFERENCE_HINT", rules)
        self.assertFalse(audit["visual_qa_verified"])
        self.assertFalse(audit["approved_contract_authenticated"])
        self.assertTrue(all("value" not in x for x in audit["findings"]))

    def test_contract_rejects_unexpected_rule_or_invalid_mode(self):
        inv = orbit_specialists.scan_visual_project(self.root)
        with self.assertRaises(ValueError):
            orbit_specialists.audit_visual_contract(inv, {"new_agent": "yes"})
        with self.assertRaises(ValueError):
            orbit_specialists.audit_visual_contract(inv, {"spacing_policy": "ignore-all"})
        with self.assertRaises(ValueError):
            orbit_specialists.audit_visual_contract(inv, {"icon_family": "rogue"})

    def test_no_hints_is_still_not_rendered_qa_pass(self):
        (self.root / "src/app/settings/page.tsx").write_text(
            'export default function Settings(){return <div/>}\n', encoding="utf-8")
        (self.root / "src/app/page.tsx").write_text(
            'export default function Home(){return <div/>}\n', encoding="utf-8")
        (self.root / "src/styles/base.css").write_text(":root { --space-md: 16px; }\n",
                                                        encoding="utf-8")
        inv = orbit_specialists.scan_visual_project(self.root)
        audit = orbit_specialists.audit_visual_contract(
            inv, {"icon_family": "lucide", "spacing_policy": "token-first"})
        self.assertEqual(audit["status"], "NO_STATIC_DRIFT_HINTS")
        self.assertFalse(audit["visual_qa_verified"])

    def test_qa_plan_never_claims_full_runtime_route_discovery(self):
        inv = orbit_specialists.scan_visual_project(self.root)
        plan = orbit_specialists.plan_visual_qa(inv, scope="full-product")
        self.assertEqual(plan["route_candidates"], ["/", "/settings"])
        self.assertIn("focus", plan["candidate_required_states"])
        self.assertEqual(plan["status"], "NEEDS_RUNTIME_ROUTE_AND_STATE_RECONCILIATION")
        self.assertFalse(plan["all_runtime_routes_discovered"])
        self.assertFalse(plan["rendered_visual_qa_verified"])
        self.assertEqual(orbit_specialists.plan_visual_qa(
            inv, scope="changed-slice")["status"], "HOLD_TARGET_UI_SCOPE_REQUIRED")
        self.assertEqual(orbit_specialists.plan_visual_qa(
            inv, scope="changed-slice", target_routes=["/settings"])["route_candidates"],
            ["/settings"])

    def test_review_only_bundle_exposed_using_existing_decision_tool(self):
        result = self.decision(include_visual_review=True,
                               visual_contract={"icon_family": "lucide",
                                                "spacing_policy": "token-first"},
                               qa_plan_scope="changed-slice",
                               qa_target_routes=["/settings"])
        quality = result["ui_quality_review"]
        self.assertEqual(quality["status"], "SOURCE_REVIEW_ONLY")
        self.assertEqual(quality["qa_plan"]["route_candidates"], ["/settings"])
        self.assertEqual(quality["visual_contract"]["status"], "STYLE_DRIFT_REVIEW_REQUIRED")
        self.assertEqual(len(orbit_mcp.TOOLS), 57)
        self.assertFalse(result["selection_applied"])

    def test_full_product_coverage_rejects_missing_static_routes(self):
        packet = {"source_revision": "rev1234567",
                  "source_snapshot_sha256": orbit_specialists.scan_visual_project(
                      self.root)["source_snapshot_sha256"], "scope": "full-product",
                  "runtime_routes_reviewed": True,
                  "expected": {"/": ["default"]},
                  "observations": [{"screen": "/", "state": "default",
                                    "source_revision": "rev1234567",
                                    "evidence_ref": "host-browser:home",
                                    "status": "PASS"}]}
        quality = self.decision(ui_coverage_packet=packet)["ui_quality_review"]
        report = quality["coverage_review"]
        self.assertEqual(report["status"], "HOLD_UNMAPPED_STATIC_ROUTES")
        self.assertEqual(report["unmapped_static_route_hints"], ["/settings"])
        self.assertFalse(report["runtime_route_review_independently_verified"])

    def test_complete_report_without_runtime_review_stays_hold(self):
        packet = {"source_revision": "rev1234567",
                  "source_snapshot_sha256": orbit_specialists.scan_visual_project(
                      self.root)["source_snapshot_sha256"], "scope": "full-product",
                  "expected": {"/": ["default"], "/settings": ["default"]},
                  "observations": [{"screen": route, "state": "default",
                                    "source_revision": "rev1234567",
                                    "evidence_ref": "host-browser:" + route,
                                    "status": "PASS"} for route in ("/", "/settings")]}
        r = self.decision(ui_coverage_packet=packet)["ui_quality_review"]["coverage_review"]
        self.assertEqual(r["status"], "HOLD_RUNTIME_SCOPE_NOT_REVIEWED")
        packet["runtime_routes_reviewed"] = True
        r = self.decision(ui_coverage_packet=packet)["ui_quality_review"]["coverage_review"]
        self.assertEqual(r["status"], "READY_FOR_INDEPENDENT_VISUAL_REVIEW")
        self.assertFalse(r["rendered_visual_qa_passed"])
        self.assertFalse(r["runtime_route_review_independently_verified"])

    def test_stale_evidence_never_passes(self):
        packet = {"source_revision": "rev1234567",
                  "source_snapshot_sha256": orbit_specialists.scan_visual_project(
                      self.root)["source_snapshot_sha256"], "scope": "changed-slice",
                  "runtime_routes_reviewed": True,
                  "expected": {"/settings": ["default"]},
                  "observations": [{"screen": "/settings", "state": "default",
                                    "source_revision": "stale0000",
                                    "evidence_ref": "host-browser:settings",
                                    "status": "PASS"}]}
        r = self.decision(ui_coverage_packet=packet)["ui_quality_review"]["coverage_review"]
        self.assertEqual(r["status"], "HOLD_INCOMPLETE_UI_COVERAGE")
        self.assertEqual(len(r["stale"]), 1)

    def test_file_change_invalidates_reported_ui_coverage_snapshot(self):
        inventory = orbit_specialists.scan_visual_project(self.root)
        packet = {
            "source_revision": "rev1234567", "scope": "changed-slice",
            "source_snapshot_sha256": inventory["source_snapshot_sha256"],
            "runtime_routes_reviewed": True,
            "expected": {"/settings": ["default"]},
            "observations": [{"screen": "/settings", "state": "default",
                              "source_revision": "rev1234567",
                              "evidence_ref": "host-session:settings-screenshot",
                              "status": "PASS"}],
        }
        clean = self.decision(ui_coverage_packet=packet)["ui_quality_review"]["coverage_review"]
        self.assertEqual(clean["status"], "READY_FOR_INDEPENDENT_VISUAL_REVIEW")
        self.assertTrue(clean["source_snapshot_matches_inspected_files"])
        (self.root / "src/styles/base.css").write_text(
            ".body { gap: 19px; }", encoding="utf-8")
        drift = self.decision(ui_coverage_packet=packet)["ui_quality_review"]["coverage_review"]
        self.assertEqual(drift["status"], "HOLD_SOURCE_SNAPSHOT_MISMATCH")
        self.assertFalse(drift["source_snapshot_matches_inspected_files"])
        self.assertFalse(drift["rendered_visual_qa_passed"])

    def test_nonvisual_does_not_trigger_static_ui_audit(self):
        result = orbit_mcp.execute(self.conn, "orbit_decision_route", {
            "project_root": str(self.root), "project": "sdk-only",
            "product_type": "sdk-library", "include_visual_review": True})
        self.assertEqual(result["ui_quality_review"]["status"],
                         "NOT_APPLICABLE_NONVISUAL")


if __name__ == "__main__":
    unittest.main()
