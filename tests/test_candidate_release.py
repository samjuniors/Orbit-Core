"""Release-candidate artifacts must be verifiable without publishing or mutating old bundles."""
import json
import tempfile
import unittest
import zipfile
from hashlib import sha256
from pathlib import Path

from scripts.prepare_release_candidate import prepare, source_parity


class CandidatePackageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "VERSION").write_text("0.25.0\n", encoding="utf-8")
        source = self.root / "source/runtime"
        source.mkdir(parents=True)
        (source / "orbit_mcp.py").write_bytes(b"VERSION = '0.25.0'\n")
        (source / "orbit_tasks.py").write_bytes(b"# source-tasks\n")
        self.prior = self.root / "ORBIT-Claude-Desktop-v0.24.1.mcpb"
        with zipfile.ZipFile(self.prior, "w") as bundle:
            bundle.writestr("manifest.json", json.dumps({"name": "orbit-core", "version": "0.24.1"}))
            bundle.writestr("server/orbit_mcp.py", "VERSION = '0.24.1'\n")
            bundle.writestr("icon.png", b"unchanged-icon")
        self.prior_digest = sha256(self.prior.read_bytes()).hexdigest()

    def test_prepare_generated_bundle_with_exact_inventory_and_preserves_prior(self):
        first = prepare(self.root)
        self.assertTrue(first["generated"])
        self.assertEqual(first["version"], "0.25.0")
        artifact = self.root / "ORBIT-Claude-Desktop-v0.25.0.mcpb"
        self.assertEqual(first["sha256"], sha256(artifact.read_bytes()).hexdigest())
        self.assertEqual(self.prior_digest, sha256(self.prior.read_bytes()).hexdigest())
        self.assertEqual(first["sha256"], source_parity(self.root, artifact, "0.25.0"))
        with zipfile.ZipFile(artifact) as bundle:
            self.assertEqual(bundle.read("icon.png"), b"unchanged-icon")
            self.assertEqual(json.loads(bundle.read("manifest.json"))["version"], "0.25.0")
        second = prepare(self.root)
        self.assertFalse(second["generated"])
        self.assertEqual(first["sha256"], second["sha256"])

    def test_mutated_candidate_and_missing_modules_fail_closed(self):
        prepare(self.root)
        (self.root / "source/runtime/orbit_tasks.py").write_bytes(b"# changed-after-bundle\n")
        with self.assertRaisesRegex(ValueError, "differs"):
            prepare(self.root)
        with self.assertRaisesRegex(ValueError, "differs"):
            source_parity(self.root, self.root / "ORBIT-Claude-Desktop-v0.25.0.mcpb", "0.25.0")

    def test_missing_prior_fails_without_generating_new_bundle(self):
        self.prior.unlink()
        with self.assertRaisesRegex(ValueError, "prior immutable"):
            prepare(self.root)
        self.assertFalse((self.root / "ORBIT-Claude-Desktop-v0.25.0.mcpb").exists())

    def test_invalid_version_never_generates_bundle(self):
        (self.root / "VERSION").write_text("0.25.0-rc1\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Invalid"):
            prepare(self.root)
        self.assertFalse((self.root / "ORBIT-Claude-Desktop-v0.25.0.mcpb").exists())


if __name__ == "__main__":
    unittest.main()
