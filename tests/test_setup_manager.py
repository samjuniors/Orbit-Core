"""Unified Orbit Setup regression tests: consent, isolation, safe uninstallation."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import installer
import orbit_setup


class SetupManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.home = self.base / "home"
        self.project = self.base / "demo"
        self.project.mkdir()
        before = {k: os.getenv(k) for k in ("ORBIT_SETUP_HOME", "ORBIT_UNIVERSAL_HOME")}
        os.environ["ORBIT_SETUP_HOME"] = str(self.home)
        os.environ["ORBIT_UNIVERSAL_HOME"] = str(self.home / ".orbit-universal")
        def restore():
            for key, value in before.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        self.addCleanup(restore)

    def install(self, hosts=None, scope="project"):
        changes = installer.plan(str(self.project) if scope == "project" else None,
                                 hosts or ["antigravity","codex"], scope)
        installer.install(changes)
        return changes

    def test_install_update_preview_and_repeat(self):
        self.assertEqual(orbit_setup.run_action(
            "install", "project", str(self.project), ["antigravity","codex"], False), 0)
        self.assertEqual(list(self.project.iterdir()), [])
        self.install()
        self.assertEqual(orbit_setup.run_action(
            "update", "project", str(self.project), ["antigravity","codex"], False), 0)
        self.assertEqual(orbit_setup.run_action(
            "update", "project", str(self.project), ["antigravity","codex"], True), 0)

    def test_unified_install_includes_skill_plan_runtime(self):
        """Installed Orbit must ship every imported v0.29 runtime dependency."""
        changes = installer.plan(str(self.project), ["antigravity", "codex"])
        planned = [c.target for c in changes]
        runtime = installer.runtime_folder()
        expected_modules = {p.name for p in (ROOT / "source/runtime").glob("*.py")}
        planned_modules = {p.name for p in planned if p.parent == runtime}
        self.assertEqual(planned_modules, expected_modules)
        target = runtime / "orbit_skill_plan.py"
        self.assertIn(target, planned)
        # Install only inside the disposable home configured in setUp.
        installer.install(changes)
        self.assertTrue(target.is_file())
        self.assertEqual(
            target.read_bytes(),
            (ROOT / "source/runtime/orbit_skill_plan.py").read_bytes()
        )

    def test_uninstall_preserves_memory_owner_docs_and_unrelated_mcp(self):
        config = self.project / ".agents/mcp_config.json"
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps({"mcpServers":{"other-mcp":{"command":"other"}}}))
        self.install()
        memory = self.home / "AppData/Local/OrbitCore/memory.sqlite3"
        memory.parent.mkdir(parents=True, exist_ok=True)
        memory.write_bytes(b"owner-memory-preserved")
        owner = self.project / "AGENTS.md"
        self.assertTrue(owner.exists())
        prior = owner.read_bytes()
        changes, warnings = orbit_setup.plan_uninstall(
            str(self.project), ["antigravity","codex"])
        self.assertGreater(len(changes), 10)
        self.assertTrue(any("PRESERVE" in w for w in warnings))
        self.assertIn("orbit-core-native", config.read_text())
        backup = orbit_setup.apply_uninstall(changes)
        self.assertTrue(backup.joinpath("manifest.json").is_file())
        self.assertEqual(owner.read_bytes(), prior)
        self.assertEqual(memory.read_bytes(), b"owner-memory-preserved")
        self.assertTrue((self.home / ".orbit-universal" / installer.VERSION / "orbit_mcp.py").exists())
        remaining = json.loads(config.read_text())["mcpServers"]
        self.assertNotIn("orbit-core-native", remaining)
        self.assertEqual(remaining["other-mcp"], {"command":"other"})
        self.assertFalse((self.project / ".agents/agents/orbit-frontend.md").exists())

    def test_uninstall_preview_does_not_mutate(self):
        self.install()
        path = self.project / ".codex/config.toml"
        old = path.read_bytes()
        changes, _ = orbit_setup.plan_uninstall(str(self.project), ["codex"])
        self.assertTrue(changes)
        self.assertEqual(path.read_bytes(), old)
        self.assertFalse((self.home / ".orbit-uninstall-backups").exists())

    def test_uninstall_codex_only_retains_shared_skill_and_antigravity(self):
        self.install()
        changes, _ = orbit_setup.plan_uninstall(str(self.project), ["codex"])
        self.assertNotIn(self.project / ".agents/skills/orbit/SKILL.md", [c.path for c in changes])
        orbit_setup.apply_uninstall(changes)
        self.assertTrue((self.project / ".agents/skills/orbit/SKILL.md").exists())
        self.assertIn("orbit-core-native",(self.project / ".agents/mcp_config.json").read_text())
        self.assertNotIn('orbit-core-native', (self.project / ".codex/config.toml").read_text())

    def test_modified_agent_preserved_and_reported(self):
        self.install()
        agent = self.project / ".agents/agents/orbit-frontend.md"
        agent.write_text("owner custom edits, do not delete")
        changes, warnings = orbit_setup.plan_uninstall(str(self.project), ["antigravity"])
        self.assertNotIn(agent, [c.path for c in changes])
        self.assertTrue(any('PRESERVE customized/unrecognized file' in w and agent.name in w for w in warnings))
        orbit_setup.apply_uninstall(changes)
        self.assertEqual(agent.read_text(), "owner custom edits, do not delete")

    def test_modified_own_registration_preserved(self):
        self.install(["antigravity"])
        config = self.project / ".agents/mcp_config.json"
        data = json.loads(config.read_text())
        data["mcpServers"]["orbit-core-native"]["env"] = {"TOKEN":"custom"}
        config.write_text(json.dumps(data))
        changes, warnings = orbit_setup.plan_uninstall(str(self.project), ["antigravity"])
        self.assertNotIn(config, [c.path for c in changes])
        self.assertTrue(any("PRESERVE customized Orbit entry" in w for w in warnings))

    def test_stale_uninstall_is_rejected_before_any_modifications(self):
        self.install()
        changes, _ = orbit_setup.plan_uninstall(str(self.project), ["antigravity","codex"])
        target = changes[-1].path
        target.write_bytes(b"changed after preview")
        with self.assertRaises(installer.SetupError):
            orbit_setup.apply_uninstall(changes)
        self.assertTrue((self.project / ".agents/agents/orbit-frontend.md").is_file())

    def test_symlink_managed_file_rejected(self):
        self.install(["antigravity"])
        target = self.project / ".agents/agents/orbit-frontend.md"
        target.unlink()
        external = self.base / "external.md"
        external.write_text("outside")
        try:
            target.symlink_to(external)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink not permitted in test runner")
        with self.assertRaises(installer.SetupError):
            orbit_setup.plan_uninstall(str(self.project), ["antigravity"])
        self.assertEqual(external.read_text(),"outside")

    def test_symlink_parent_refused(self):
        self.install(["antigravity"])
        folder = self.project / ".agents/agents"
        external = self.base / "outside-agents"
        folder.rename(external)
        try:
            folder.symlink_to(external, target_is_directory=True)
        except (OSError, NotImplementedError):
            external.rename(folder)
            self.skipTest("Directory symlink unavailable")
        with self.assertRaises(installer.SetupError):
            orbit_setup.plan_uninstall(str(self.project), ["antigravity"])
        self.assertTrue((external / "orbit-frontend.md").exists())

    def test_uninstall_refuses_symlink_backup_store(self):
        self.install(["antigravity"])
        external = self.base / "external-backup"
        external.mkdir()
        shortcut = self.home / ".orbit-uninstall-backups"
        try:
            shortcut.symlink_to(external, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("Directory symlink unavailable")
        changes, _ = orbit_setup.plan_uninstall(str(self.project), ["antigravity"])
        with self.assertRaises(installer.SetupError):
            orbit_setup.apply_uninstall(changes)
        self.assertTrue((self.project / ".agents/agents/orbit-frontend.md").exists())
        self.assertEqual(list(external.iterdir()), [])

    def test_machine_uninstall_leaves_project_scopes(self):
        self.install(["codex"],scope="machine")
        project = self.project / ".codex/config.toml"
        project.parent.mkdir()
        project.write_text('[mcp_servers."other"]\ncommand = "custom"\n')
        changes, _ = orbit_setup.plan_uninstall(None, ["codex"], "machine")
        self.assertTrue(changes)
        orbit_setup.apply_uninstall(changes)
        self.assertTrue(project.is_file())
        self.assertIn("other", project.read_text())
        self.assertTrue((self.home / ".orbit-universal" / installer.VERSION / "orbit_mcp.py").exists())

    def test_unrecognized_external_path_never_removed(self):
        self.install(["claude-code"])
        p = self.project / ".mcp.json"
        data = json.loads(p.read_text())
        data["mcpServers"]["orbit-core-native"]["args"] = [str(self.base/"external"/"orbit_mcp.py")]
        p.write_text(json.dumps(data))
        changes, warnings = orbit_setup.plan_uninstall(str(self.project), ["claude-code"])
        self.assertNotIn(p, [c.path for c in changes])
        self.assertTrue(any("customized Orbit entry" in x for x in warnings))


if __name__ == "__main__":
    unittest.main()
