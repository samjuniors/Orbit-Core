"""A new release bundle is created without editing a published older .mcpb."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from scripts.build_desktop_extension import build


class VersionPreparationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "VERSION").write_text("0.25.0\n")
        source = self.root / "source" / "runtime"
        source.mkdir(parents=True)
        (source / "orbit_mcp.py").write_text("VERSION = '0.25.0'\n")
        self.old = self.root / "ORBIT-Claude-Desktop-v0.24.1.mcpb"
        with zipfile.ZipFile(self.old, "w") as bundle:
            bundle.writestr("manifest.json", json.dumps({"name": "Orbit", "version": "0.24.1"}))
            bundle.writestr("server/orbit_mcp.py", "VERSION = '0.24.1'\n")
            bundle.writestr("icon.png", b"illustrative-image-bytes")
        self.previous_bytes = self.old.read_bytes()

    def test_prepare_next_version_preserves_old_bundle_and_extras(self):
        target = build(self.root, "0.24.1")
        self.assertEqual(target.name, "ORBIT-Claude-Desktop-v0.25.0.mcpb")
        self.assertEqual(self.old.read_bytes(), self.previous_bytes)
        with zipfile.ZipFile(target) as bundle:
            manifest = json.loads(bundle.read("manifest.json"))
            self.assertEqual(manifest["version"], "0.25.0")
            self.assertEqual(manifest["display_name"], "Orbit Core - Memory & Agent Tasks")
            self.assertIn("host controls", manifest["long_description"].lower().replace("the host controls", "host controls"))
            self.assertNotIn("switching..", manifest["long_description"])
            self.assertNotIn("Ã", manifest["display_name"])
            self.assertEqual(bundle.read("server/orbit_mcp.py").decode().splitlines(), ["VERSION = '0.25.0'"])
            self.assertEqual(bundle.read("icon.png"), b"illustrative-image-bytes")
        before = target.read_bytes()
        build(self.root)
        self.assertEqual(target.read_bytes(), before)

    def test_new_version_cannot_use_newer_or_missing_template(self):
        with self.assertRaises(ValueError):
            build(self.root)
        with self.assertRaises(ValueError):
            build(self.root, "0.25.0")
        with self.assertRaises(FileNotFoundError):
            build(self.root, "0.24.9")
        self.assertFalse((self.root / "ORBIT-Claude-Desktop-v0.25.0.mcpb").exists())


if __name__ == "__main__":
    unittest.main()
