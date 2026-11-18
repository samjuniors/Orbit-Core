"""v0.33 local UI inventory, source-claim evaluation and scoped preference regression."""
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source" / "runtime"))
import orbit_specialists
import orbit_decisions
import orbit_improvement
import orbit_intake
import orbit_mcp


class VisualInventoryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name, "project")
        self.root.mkdir()
        self.root = self.root.resolve()
        for folder in ("src/app/settings", "src/components", "src/styles", "node_modules/hijack"):
            (self.root / folder).mkdir(parents=True, exist_ok=True)
        (self.root / "src/app/page.tsx").write_text(
            'import Button from "../components/Button";\n'
            'export default function Home() { return <Button /> }\n', encoding="utf-8")
        (self.root / "src/app/settings/page.tsx").write_text(
            'export default function Settings() { return <div>Settings</div> }\n',
            encoding="utf-8")
        (self.root / "src/components/Button.tsx").write_text(
            'import { Home } from "lucide-react";\n'
            'export default function Button() { return <Home /> }\n', encoding="utf-8")
        (self.root / "src/styles/tokens.css").write_text(
            ':root { --space-2: 8px; --color-ink: #333; }\n', encoding="utf-8")
        (self.root / "node_modules/hijack/page.tsx").write_text(
            'export default function Evil() {}', encoding="utf-8")
        (self.root / "package.json").write_text(json.dumps({
            "dependencies": {"react": "19.2.0", "lucide-react": "0.4.0",
                             "unrelated-package": "1.0.0"}
        }), encoding="utf-8")
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.addCleanup(self.db.close)
        orbit_intake.setup(self.db)
        orbit_improvement.setup(self.db)

    def test_discovers_routes_components_tokens_consumers_and_icon_families(self):
        result = orbit_specialists.scan_visual_project(self.root)
        self.assertEqual(result["status"], "HEURISTIC_UI_INVENTORY_PARTIAL")
        self.assertEqual([x["path"] for x in result["routes"]], ["/", "/settings"])
        self.assertIn("src/components/Button.tsx", result["component_files"])
        self.assertEqual(result["component_consumers_hint"]["src/components/Button.tsx"],
                         ["src/app/page.tsx"])
        self.assertEqual(result["icon_families_imported_hint"]["lucide"], 1)
        self.assertIn("space-2", result["css_custom_properties_hint"])
        self.assertEqual(result["declared_ui_dependencies_hint"]["react"], "19.2.0")
        self.assertFalse(any("hijack" in x for x in result["component_files"]))
        self.assertFalse(result["project_code_executed"])
        self.assertFalse(result["network_accessed"])
        self.assertFalse(result["screen_inventory_complete"])
        self.assertFalse(result["source_git_revision_verified"])

    def test_snapshot_changes_on_source_edit_not_external_ignored_files(self):
        first = orbit_specialists.scan_visual_project(self.root)["source_snapshot_sha256"]
        (self.root / "node_modules/hijack/page.tsx").write_text("modified", encoding="utf-8")
        self.assertEqual(orbit_specialists.scan_visual_project(self.root)["source_snapshot_sha256"], first)
        (self.root / "src/app/page.tsx").write_text("changed", encoding="utf-8")
        self.assertNotEqual(orbit_specialists.scan_visual_project(self.root)["source_snapshot_sha256"], first)

    def test_symlink_escape_not_read(self):
        outside = self.root.parent / "outside.tsx"
        outside.write_text('export const secret = "outside";', encoding="utf-8")
        link = self.root / "src/components/Outside.tsx"
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("File symlinks unavailable")
        result = orbit_specialists.scan_visual_project(self.root)
        self.assertNotIn("src/components/Outside.tsx", result["component_files"])
        self.assertEqual(result["scanned_file_count"], 5)

    def test_conservative_dynamic_route_and_file_size_limit(self):
        (self.root / "src/app/[slug]").mkdir()
        (self.root / "src/app/[slug]/page.tsx").write_text("dynamic", encoding="utf-8")
        (self.root / "src/components/Huge.tsx").write_bytes(b"x" * (129 * 1024))
        result = orbit_specialists.scan_visual_project(self.root)
        self.assertIn("DYNAMIC_ROUTE_REQUIRES_HOST_INSPECTION", result["partial_reasons"])
        self.assertIn("MAX_FILE_OR_BYTE_LIMIT", result["partial_reasons"])
        self.assertNotIn("src/components/Huge.tsx", result["component_files"])

    def test_empty_or_unrecognized_app_cannot_claim_completeness(self):
        with tempfile.TemporaryDirectory() as td:
            out = orbit_specialists.scan_visual_project(td)
        self.assertEqual(out["routes"], [])
        self.assertIn("NO_STATIC_SCREEN_ROUTE_FOUND", out["partial_reasons"])
        self.assertFalse(out["rendered_visual_qa_verified"])

    def test_source_review_fails_closed_for_unsafe_or_missing_claims(self):
        candidate = {"source_id": "shadcn-ui", "url": "https://ui.shadcn.com/docs",
                     "version_or_commit": "v4.0", "license": "MIT",
                     "compatibility": "compatible",
                     "source_evidence": "official-docs-reviewed-by-host"}
        self.assertEqual(orbit_decisions.review_component_source(candidate)["status"],
                         "REVIEW_SOURCE_CLAIMS")
        self.assertFalse(orbit_decisions.review_component_source(candidate)["registry_fetched_by_orbit"])
        self.assertFalse(orbit_decisions.review_component_source(candidate)["license_independently_verified"])
        self.assertEqual(orbit_decisions.review_component_source(
            dict(candidate, url="https://evil.example.org"))["status"],
            "HOLD_SOURCE_URL_MISMATCH")
        self.assertEqual(orbit_decisions.review_component_source(
            dict(candidate, source_id="unfamiliar-library"))["status"],
            "HOLD_UNCATALOGED_SOURCE")
        self.assertEqual(orbit_decisions.review_component_source(
            dict(candidate, compatibility="incompatible"))["status"],
            "HOLD_INCOMPATIBLE_SOURCE")
        self.assertEqual(orbit_decisions.review_component_source(
            {"source_id": "shadcn-ui", "url": "https://ui.shadcn.com/docs"})["status"],
            "HOLD_MISSING_SOURCE_CLAIMS")

    def test_source_review_requires_pin_license_and_actual_stack_fit(self):
        basic = {"source_id": "shadcn-ui", "url": "https://ui.shadcn.com/docs",
                 "version_or_commit": "4.1.2", "license": "MIT",
                 "compatibility": "compatible",
                 "source_evidence": "reviewed-official-documentation"}
        self.assertEqual(orbit_decisions.review_component_source(
            dict(basic, version_or_commit="latest"))["status"],
            "HOLD_UNPINNED_SOURCE")
        self.assertEqual(orbit_decisions.review_component_source(
            dict(basic, license="unknown"))["status"],
            "HOLD_UNCLEAR_LICENSE")
        res = orbit_mcp.execute(self.db, "orbit_decision_route", {
            "project_root": str(self.root), "project": "sdk",
            "product_type": "sdk-library", "source_snapshot": basic})
        self.assertEqual(res["component_source_review"]["status"],
                         "HOLD_SOURCE_NOT_APPLICABLE_TO_PROJECT")
        wrong = orbit_mcp.execute(self.db, "orbit_decision_route", {
            "project_root": str(self.root), "project": "web",
            "product_type": "web-app", "platforms": ["web"],
            "existing_stack": "Vue 3", "source_snapshot": basic})
        self.assertEqual(wrong["component_source_review"]["status"],
                         "HOLD_PROJECT_STACK_MISMATCH")

    def test_project_style_approval_and_isolation_and_archive(self):
        first = {
            "event_key": "icon-style-project-one", "action": "record",
            "kind": "project-style-preference", "result": "unknown",
            "lesson": "For this project, prefer compact single-weight outline icons.",
            "evidence_ref": "user-message-8431",
        }
        self.assertEqual(orbit_improvement.record(
            self.db, self.root, "app-a", dict(first, confirm_write=True))["status"],
            "HOLD_PROJECT_STYLE_APPROVAL_REFERENCE")
        self.assertEqual(orbit_improvement.context(
            self.db, self.root, "app-a", {})["project_style_preference_claims"], [])
        preview = orbit_improvement.record(
            self.db, self.root, "app-a",
            dict(first, approval_reference="user-message-8431"))
        self.assertEqual(preview["status"], "PREVIEW_ONLY")
        self.assertFalse(preview["state_written"])
        saved = orbit_improvement.record(
            self.db, self.root, "app-a",
            dict(first, approval_reference="user-message-8431", confirm_write=True))
        self.assertTrue(saved["approved_style_preference_claim_recorded"])
        self.assertFalse(saved["approval_authenticated"])
        claims = orbit_improvement.context(
            self.db, self.root, "app-a", {})["project_style_preference_claims"]
        self.assertEqual(len(claims), 1)
        self.assertFalse(claims[0]["approval_independently_verified"])
        self.assertFalse(orbit_improvement.context(
            self.db, self.root, "app-b", {})["project_style_preference_claims"])
        self.assertFalse(orbit_improvement.context(
            self.db, self.root.parent, "app-a", {})["project_style_preference_claims"])
        rev = orbit_improvement.record(
            self.db, self.root, "app-a",
            {"action": "archive", "event_key": first["event_key"],
             "expected_revision": 1, "confirm_write": True})
        self.assertEqual(rev["status"], "ARCHIVED")
        self.assertEqual(orbit_improvement.context(
            self.db, self.root, "app-a", {})["project_style_preference_claims"], [])

    def test_decision_tool_exposes_bounded_audit_and_project_context(self):
        a = {"project_root": str(self.root), "project": "app-a",
             "product_type": "web-app", "platforms": ["web"],
             "existing_stack": "React 19 Tailwind", "include_ui_inventory": True,
             "include_project_style_context": True,
             "source_snapshot": {"source_id": "shadcn-ui",
                                 "url": "https://ui.shadcn.com/docs",
                                 "version_or_commit": "v4.0",
                                 "license": "MIT",
                                 "compatibility": "compatible",
                                 "source_evidence": "official-docs-reviewed-by-host"}}
        res = orbit_mcp.execute(self.db, "orbit_decision_route", a)
        self.assertEqual(res["ui_inventory"]["routes"][0]["path"], "/")
        self.assertEqual(res["component_source_review"]["status"], "REVIEW_SOURCE_CLAIMS")
        self.assertEqual(res["project_style_context"]["claims"], [])
        self.assertFalse(res["selection_applied"])
        self.assertEqual(len(orbit_mcp.TOOLS), 57)

    def test_approved_project_style_is_visible_only_in_same_project_decisions(self):
        entry = {"project_root": str(self.root), "project": "app-a",
                 "action": "record", "event_key": "project-icon-density",
                 "kind": "project-style-preference", "result": "unknown",
                 "lesson": "Use compact monochrome icons for the current project interface.",
                 "evidence_ref": "user-approved-icons-456",
                 "approval_reference": "user-approved-icons-456",
                 "confirm_write": True}
        saved = orbit_mcp.execute(self.db, "orbit_improvement_record", entry)
        self.assertEqual(saved["status"], "OBSERVATION_RECORDED")
        for n in range(24):
            orbit_improvement.record(self.db, self.root, "app-a", {
                "event_key": "later-task-event-%02d" % n, "action": "record",
                "kind": "task-outcome", "result": "unknown",
                "lesson": "A later independent routine task observation %02d." % n,
                "evidence_ref": "test-task-evidence-%02d" % n,
                "confirm_write": True,
            })
        a = {"project_root": str(self.root), "project": "app-a",
             "product_type": "web-app", "include_project_style_context": True}
        matched = orbit_mcp.execute(self.db, "orbit_decision_route", a)
        self.assertEqual(len(matched["project_style_context"]["claims"]), 1)
        self.assertFalse(matched["project_style_context"]["preferences_auto_applied"])
        other = orbit_mcp.execute(self.db, "orbit_decision_route", dict(a, project="app-b"))
        self.assertEqual(other["project_style_context"]["claims"], [])

    def test_nonvisual_decision_does_not_scan_ui(self):
        res = orbit_mcp.execute(self.db, "orbit_decision_route", {
            "project_root": str(self.root), "project": "sdk",
            "product_type": "sdk-library", "include_ui_inventory": True,
        })
        self.assertEqual(res["ui_inventory"]["status"], "NOT_APPLICABLE_NONVISUAL")


if __name__ == "__main__":
    unittest.main()
