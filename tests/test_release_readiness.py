"""Regression tests for public release notes and packaging readiness."""
from pathlib import Path
import json
import tempfile
import unittest
import zipfile

from scripts.check_release_readiness import check_release


class PublicReleaseQualityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir()
        (self.root / "VERSION").write_text("0.27.0\n")
        (self.root / "CHANGELOG.md").write_text(
            "# Changelog\n\n## [Unreleased]\n\n## [0.27.0] — Prerelease\n"
            "### Highlights\n- Useful capability.\n"
            "### Install and upgrade\n- Use published ZIP and checksum.\n"
            "### Compatibility\n- Preserve SQLite backups.\n"
            "### Known limitations\n- Host UI approval remains unverified.\n")
        for path in (self.root / "README.md",
                     self.root / "docs" / "RELEASE-QUICKSTART.md",
                     self.root / "docs" / "RELEASE-PROCESS.md"):
            path.write_text("See https://github.com/samjuniors/Orbit-Core-MCP/releases\n")
        self.bundle = self.root / "ORBIT-Claude-Desktop-v0.27.0.mcpb"
        self.manifest = {
            "version": "0.27.0",
            "name": "orbit-core-native",
            "display_name": "Orbit Core - Memory & Agent Tasks",
            "long_description": "Orbit works with supported coding hosts."
        }
        self.write_manifest()

    def write_manifest(self):
        with zipfile.ZipFile(self.bundle, "w") as z:
            z.writestr("manifest.json", json.dumps(self.manifest))

    def test_valid_future_release_notes_and_metadata_pass(self):
        self.assertEqual(check_release(self.root), [])

    def test_missing_user_facing_changelog_section_blocks(self):
        p = self.root / "CHANGELOG.md"
        p.write_text(p.read_text().replace("### Install and upgrade", "### Engineering updates"))
        self.assertTrue(any("Install and upgrade" in s for s in check_release(self.root)))

    def test_stale_public_latest_version_claim_blocks(self):
        p = self.root / "README.md"
        p.write_text(p.read_text() + "Latest published release is v0.25.1\n")
        self.assertTrue(any("hard-coded latest" in s for s in check_release(self.root)))

    def test_corrupted_desktop_title_blocks(self):
        self.manifest["display_name"] = "Orbit Core Local Ã¢ÂÂ Memory & Agent Tasks"
        self.write_manifest()
        self.assertTrue(any("display_name" in s for s in check_release(self.root)))

    def test_prepublishing_claim_in_future_notes_blocks(self):
        p = self.root / "CHANGELOG.md"
        p.write_text(p.read_text() + "\nNot yet published.\n")
        self.assertTrue(any("not-published" in s for s in check_release(self.root)))


if __name__ == "__main__":
    unittest.main()
