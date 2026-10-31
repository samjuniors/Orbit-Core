"""Release workflow must publish all tested user-facing host archives.

This checks static configuration only. It does not tag, publish, or approve a release.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ReleaseAssetManifestTests(unittest.TestCase):
    def test_built_plugin_suite_is_in_release_upload_inventory(self):
        workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
        build_step = workflow.split("Build and verify reproducible release artifacts", 1)[1]
        self.assertIn('Orbit-Core-Plugin-Suite-v${ORBIT_RELEASE_VERSION}.zip.sha256', build_step)
        self.assertIn('sha256sum --check "Orbit-Core-Plugin-Suite-v${ORBIT_RELEASE_VERSION}.zip.sha256"', build_step)
        self.assertIn('gh release create "$ORBIT_RELEASE_TAG"', workflow)
        release_command = workflow.split('gh release create "$ORBIT_RELEASE_TAG"', 1)[1].split('--repo "$GITHUB_REPOSITORY"', 1)[0]
        for path in (
            'ORBIT-Universal-Setup-v${ORBIT_RELEASE_VERSION}.zip',
            'Orbit-Antigravity-Plugin-v${ORBIT_RELEASE_VERSION}.zip',
            'Orbit-Core-Plugin-Suite-v${ORBIT_RELEASE_VERSION}.zip',
            'ORBIT-Claude-Desktop-v${ORBIT_RELEASE_VERSION}.mcpb',
        ):
            with self.subTest(asset=path):
                self.assertIn(path, release_command)
                self.assertIn(path + '.sha256', release_command)


if __name__ == "__main__":
    unittest.main()
