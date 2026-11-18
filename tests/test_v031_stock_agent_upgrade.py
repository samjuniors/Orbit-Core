"""Official v0.31.0 Antigravity stock agent -> newer Orbit upgrade regression.

Frozen fixture bytes came from the immutable public GitHub v0.31.0 tag.
Unknown/customized files must still block and never be overwritten.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import installer

PREVIOUS = {
    "orbit.md": (
        "orbit-v031-agent.md",
        "7ffa5061f3192ee8156ef4bee44ed65bbf72e5219363034b4338816216bb59e4",
    ),
    "orbit-creative-director.md": (
        "orbit-creative-director-v031.md",
        "cb22cb9021995e7814fdf82da38539065b759ec885c21ffb0e392d3dd4bbe600",
    ),
}


class OfficialV031AgentUpgradeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        self.runtime = self.home / ".orbit-universal"
        self.locations = {}
        for name, (fixture, digest) in PREVIOUS.items():
            source = (ROOT / "tests/fixtures" / fixture).read_bytes()
            self.assertEqual(hashlib.sha256(source).hexdigest(), digest)
            self.assertIn(digest, installer.OLD_STOCK_SHA256)
            path = self.home / ".gemini" / "config" / "agents" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(source)
            self.locations[name] = (path, source)

    def _environment(self):
        return patch.dict(os.environ, {
            "ORBIT_SETUP_HOME": str(self.home),
            "ORBIT_UNIVERSAL_HOME": str(self.runtime),
        })

    def test_unmodified_published_v031_agents_upgrade_backup_first(self):
        with self._environment():
            preview = installer.plan(None, ["antigravity", "codex"], "machine")
            for name, (path, original) in self.locations.items():
                matches = [c for c in preview if c.target == path]
                self.assertEqual(len(matches), 1, name)
                self.assertEqual(matches[0].action, "UPGRADE", name)
                self.assertEqual(path.read_bytes(), original)
                self.assertFalse(path.with_name(path.name + ".orbit-backup").exists())
            self.assertFalse(self.runtime.exists(), "Preview must be read-only")
            installer.install(preview)
            for name, (path, original) in self.locations.items():
                self.assertEqual(
                    path.with_name(path.name + ".orbit-backup").read_bytes(),
                    original, name,
                )
                self.assertEqual(
                    path.read_bytes(),
                    (ROOT / "source/agents" / name).read_bytes(), name,
                )
            remaining = installer.plan(None, ["antigravity", "codex"], "machine")
            self.assertEqual({c.action for c in remaining}, {"SKIP"})

    def test_customized_agent_stays_blocked_and_no_files_are_changed(self):
        for name in PREVIOUS:
            with self.subTest(name=name):
                with self._environment():
                    path, raw = self.locations[name]
                    modified = raw + b"\n# deliberate owner's customization\n"
                    path.write_bytes(modified)
                    with self.assertRaisesRegex(installer.SetupError, "no overwrite"):
                        installer.plan(None, ["antigravity", "codex"], "machine")
                    self.assertEqual(path.read_bytes(), modified)
                    self.assertFalse(self.runtime.exists())
                    self.assertFalse(path.with_name(path.name + ".orbit-backup").exists())
                    path.write_bytes(raw)

    def test_unknown_stock_digest_not_broadly_accepted(self):
        with self._environment():
            path, raw = self.locations["orbit.md"]
            path.write_bytes(b"unrecognized agent template from an unknown source\n")
            with self.assertRaises(installer.SetupError):
                installer.plan(None, ["antigravity", "codex"], "machine")
            self.assertFalse(path.with_name(path.name + ".orbit-backup").exists())
            self.assertFalse(self.runtime.exists())
            path.write_bytes(raw)


if __name__ == "__main__":
    unittest.main()
