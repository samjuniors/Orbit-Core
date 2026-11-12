"""Release communication contract: templates and publishing file list remain consistent."""
from __future__ import annotations
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "docs" / "templates"


class ReleaseCommunicationTests(unittest.TestCase):
    def test_all_reusable_templates_present_and_product_neutral(self):
        for filename, required in {
            "CHANGELOG-ENTRY.md": ("[Unreleased]", "[X.Y.Z]", "Breaking changes"),
            "GITHUB-RELEASE-NOTES.md": ("Highlights", "Before you update", "known limitations"),
            "VERSION-MISSION.md": ("Committed scope", "Feature freeze", "Next action"),
            "RELEASE-READINESS.md": ("NOT RUN", "Owner", "Post-release"),
        }.items():
            with self.subTest(template=filename):
                data = (TEMPLATES / filename).read_text(encoding="utf-8")
                for term in required:
                    self.assertIn(term.lower(), data.lower())
                self.assertTrue(data.startswith("# "))

    def test_release_workflow_uploads_every_verified_zip(self):
        workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        names = [
            "ORBIT-Universal-Setup",
            "Orbit-Antigravity-Plugin",
            "Orbit-Core-Plugin-Suite",
        ]
        check = workflow.partition("- name: Build and verify reproducible release artifacts")[2]
        publish = workflow.partition("- name: Publish GitHub Release with installation assets")[2]
        for name in names:
            with self.subTest(asset=name):
                self.assertIn(name, check)
                self.assertIn(f"dist/{name}-v", publish)
                self.assertIn(f"dist/{name}-v${{ORBIT_RELEASE_VERSION}}.zip.sha256", publish)

    def test_publish_notes_continue_to_use_version_specific_changelog(self):
        workflow = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        self.assertIn("CHANGELOG.md", workflow)
        self.assertIn("re.escape(version)", workflow)
        self.assertIn("--notes-file", workflow)
        self.assertIn("refs/heads/main", workflow)
        self.assertIn("Existing tag", workflow)

    def test_reusable_templates_do_not_claim_a_release_has_shipped(self):
        for name in ("CHANGELOG-ENTRY.md", "RELEASE-READINESS.md"):
            content = (TEMPLATES / name).read_text(encoding="utf-8")
            self.assertTrue("NOT PUBLISHED" in content or "HOLD" in content)


if __name__ == "__main__":
    unittest.main()
