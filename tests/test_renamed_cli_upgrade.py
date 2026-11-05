"""Regression for exact historical Windows CLI repository rename migration."""

from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

import installer

RENAMED_V0251_CRLF_SHA256 = "a0c7748caa60b49c5af99ace391011798a3c64c7d7b851d8aaa1bf63516d984c"

V0251_HOST_AGENT_HASHES = {
    "orbit-architect.md": "eecf1296589f28bbe760f604d8a13fdb63edb53175825232698e768627e60883",
    "orbit-backend.md": "f89ada629e70e5faef0e4b4c3be2d2fb9b08293f924a3930137c8997f92d6e5a",
    "orbit-data.md": "c8e228b918063e16d0234086a0a784bf9e5d8f776cb494fcf824796cefd82f36",
    "orbit-devops.md": "1f053826ef91a896af356a019ebf3a37e6cd0e41a73ac6c01f45504f5b43f241",
    "orbit-frontend.md": "86483bedaeeafe01ad00f504c3717b986a9c20635108db12575ac41f145774e9",
    "orbit-integrator.md": "2c2708932582b658b9a81aa39f3aee600e3e359a359395648ab474b3fb20d8b9",
    "orbit-qa.md": "5e281544c7bcd1a6ae5aa2d606e4be380fe63df8a77fb7bd9385827d8d9f70a5",
    "orbit-research.md": "cca00c050ede41d92b6ac9ce15c4db749d57b8081a92025414621b46bca530be",
    "orbit-reviewer.md": "6d1ffd5da18d6a896d4a4bd9afcb7397d639b370544e369faa63e639b353661d",
    "orbit-security.md": "67c46598dd13a0c4a522365fd9729bc2558778ecba75865f29b9fcd7366630eb",
    "orbit-ux.md": "aeb948fbef1da6c9beb64a8d9328c444b9f8212505c238ca1b16cc7e2aea086f",
    "orbit-writer.md": "937ba9abd1e042640d5694748a2222edbc8436443ac79288f5d2030f2a83f8a4",
    "orbit.md": "93850f3fc0a5bb5067cd00a68da5c7bfaa6b8dd3b1078d30046ab1b62643349e",
}


class RenamedCliUpgradeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.dest = Path(temporary.name) / "orbit_cli.py"
        root = Path(__file__).resolve().parents[1]
        self.current = (root / "orbit_cli.py").read_bytes()
        # Frozen, hash-checked v0.25.1 Windows CLI migration bytes.
        # Never derive a historical fingerprint from an actively edited CLI.
        self.old = (root / "tests/fixtures/v0251-renamed-orbit-cli-crlf.bin").read_bytes()

    def test_exact_renamed_v0251_windows_cli_is_recognized(self):
        self.assertIn(b"samjuniors/Orbit-Core", self.current)
        self.assertNotIn(b"samjuniors/Orbit-Core-MCP", self.current)
        self.assertEqual(hashlib.sha256(self.old).hexdigest(), RENAMED_V0251_CRLF_SHA256)
        self.assertIn(RENAMED_V0251_CRLF_SHA256, installer.OLD_STOCK_SHA256)

    def test_exact_v0251_agent_inventory_is_recognized(self):
        self.assertEqual(len(V0251_HOST_AGENT_HASHES), 13)
        self.assertEqual(len(set(V0251_HOST_AGENT_HASHES.values())), 13)
        for name, digest in V0251_HOST_AGENT_HASHES.items():
            with self.subTest(name=name):
                self.assertIn(digest, installer.OLD_STOCK_SHA256)

    def test_preview_and_backup_first_install(self):
        self.dest.write_bytes(self.old)
        changes = []
        installer.same_or_create(changes, self.dest, self.current, None, "CLI migration")
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].action, "UPGRADE")
        self.assertEqual(self.dest.read_bytes(), self.old)
        written = installer.install(changes)
        backup = self.dest.with_name(self.dest.name + ".orbit-backup")
        self.assertTrue(backup.is_file())
        self.assertEqual(backup.read_bytes(), self.old)
        self.assertEqual(self.dest.read_bytes(), self.current)
        self.assertIn(str(backup), written)

    def test_real_customization_still_blocks_upgrade(self):
        modified = self.old + b"# owner custom line\r\n"
        self.dest.write_bytes(modified)
        with self.assertRaisesRegex(installer.SetupError, "no overwrite"):
            installer.same_or_create([], self.dest, self.current, None, "CLI migration")
        self.assertEqual(self.dest.read_bytes(), modified)
        self.assertFalse(self.dest.with_name(self.dest.name + ".orbit-backup").exists())


if __name__ == "__main__":
    unittest.main()


class CodexLiteralFormTests(unittest.TestCase):
    def setUp(self):
        import sys
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        self.file = self.base / ".codex" / "config.toml"
        self.file.parent.mkdir(parents=True)
        self.old = self.base / ".orbit-universal" / "0.25.1" / "orbit_mcp.py"
        self.new = self.base / ".orbit-universal" / "0.29.0" / "orbit_mcp.py"
        self.old.parent.mkdir(parents=True)
        self.old.write_text("# verified test fixture", encoding="utf-8")
        self.command = str(Path(sys.executable).resolve())
        self.body = ("command = '" + self.command + "'\n" +
                     "args = ['" + str(self.old) + "']\n")

    def test_literal_quoted_stock_codex_migrates_backup_first(self):
        import json
        original = ("[mcp_servers.'orbit-core-native']\n" + self.body +
                    "\n[mcp_servers.other]\ncommand = 'other'\n")
        self.file.write_text(original, encoding="utf-8")
        self.assertTrue(installer.stock_codex_body(self.body, self.command, self.new))
        changes = []
        installer.merge_toml(changes, self.file, self.command, self.new, self.base)
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].action, "APPEND")
        self.assertEqual(self.file.read_text(encoding="utf-8"), original)
        installer.install(changes)
        backup = self.file.with_name("config.toml.orbit-backup")
        self.assertEqual(backup.read_text(encoding="utf-8"), original)
        updated = self.file.read_text(encoding="utf-8")
        self.assertIn("[mcp_servers.other]", updated)
        self.assertIn(json.dumps(str(self.new)), updated)
        self.assertNotIn("0.25.1", updated)

    def test_user_custom_codex_fields_are_still_refused(self):
        body = self.body + "env = { CUSTOM_FIELD = 'do-not-overwrite' }\n"
        self.assertFalse(installer.stock_codex_body(body, self.command, self.new))
        self.file.write_text("[mcp_servers.'orbit-core-native']\n" + body, encoding="utf-8")
        with self.assertRaises(installer.SetupError):
            installer.merge_toml([], self.file, self.command, self.new, self.base)
