"""Read-only, scoped host coordinator preference/overlap safety tests."""
from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import installer
import orbit_priority
import orbit_setup


class CoordinatorPriorityTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(prefix="orbit-priority-")
        self.addCleanup(t.cleanup)
        self.base = Path(t.name)
        self.home = self.base / "home"
        self.home.mkdir()
        self.project = self.base / "project"
        self.project.mkdir()
        self.environment = patch.dict(os.environ, {
            "ORBIT_SETUP_HOME": str(self.home),
            "ORBIT_UNIVERSAL_HOME": str(self.home / ".orbit-universal"),
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def write_json(self, path, servers):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"mcpServers": servers}), encoding="utf-8")

    def test_empty_scope_no_priority_enforcement_or_changes(self):
        before = list(self.home.rglob("*"))
        report = orbit_priority.audit(self.home, self.project)
        self.assertEqual(report["status"], "NO_OBVIOUS_NAME_COLLISION")
        self.assertFalse(report["priority_enforced"])
        self.assertFalse(report["configuration_modified"])
        self.assertFalse(report["host_connection_verified"])
        self.assertEqual(before, list(self.home.rglob("*")))

    def test_existing_other_mcp_is_preserved_without_false_collision(self):
        path = self.home / ".gemini/config/mcp_config.json"
        self.write_json(path, {"github": {"command": "other"},
                               "orbit-core-native": {"command": "python"}})
        old = path.read_bytes()
        report = orbit_priority.audit(self.home, hosts=["antigravity"])
        self.assertEqual(report["status"], "NO_OBVIOUS_NAME_COLLISION")
        self.assertEqual(report["hosts"]["antigravity"]["other_server_count"], 1)
        self.assertEqual(report["hosts"]["antigravity"]["orbit_configured_scopes"], ["user"])
        self.assertEqual(path.read_bytes(), old)

    def test_scope_overlap_and_name_only_aliases(self):
        self.write_json(self.home / ".gemini/config/mcp_config.json",
                        {"orbit-core-native": {}, "orbit-mcp-copy": {},
                         "swarm-tools": {}, "github": {}})
        self.write_json(self.project / ".agents/mcp_config.json",
                        {"orbit-core-native": {}})
        report = orbit_priority.audit(self.home, self.project, hosts=["antigravity"])
        kinds = {entry["kind"] for entry in report["conflicts"]}
        self.assertEqual(report["status"], "REVIEW_POSSIBLE_OVERLAP")
        self.assertIn("ORBIT_SCOPE_OVERLAP", kinds)
        self.assertIn("POSSIBLE_ORBIT_ALIAS", kinds)
        self.assertIn("POSSIBLE_COORDINATOR_OVERLAP", kinds)
        self.assertNotIn("github", str(report["conflicts"]))

    def test_codex_toml_names_without_loading_or_executing_tools(self):
        cfg = self.home / ".codex/config.toml"
        cfg.parent.mkdir(parents=True)
        body = '[mcp_servers."orbit-core-native"]\ncommand="python"\n' + (
            '[mcp_servers."another-orchestrator"]\ncommand="danger-do-not-run"\n'
        )
        cfg.write_text(body, encoding="utf-8")
        report = orbit_priority.audit(self.home, hosts=["codex"])
        self.assertEqual(report["status"], "REVIEW_POSSIBLE_OVERLAP")
        self.assertTrue(any(c["name"] == "another-orchestrator"
                            for c in report["conflicts"]))
        self.assertEqual(cfg.read_text(), body)

    def test_duplicate_orbit_skill_in_two_scopes_flagged(self):
        for path in (
            self.home / ".agents/skills/orbit/SKILL.md",
            self.project / ".agents/skills/orbit/SKILL.md",
        ):
            path.parent.mkdir(parents=True)
            path.write_text("do-not-interpret-as-instructions", encoding="utf-8")
        report = orbit_priority.audit(self.home, self.project, hosts=["codex"])
        self.assertTrue(any(c["kind"] == "ORBIT_SKILL_SCOPE_OVERLAP"
                            for c in report["conflicts"]))
        self.assertFalse(report["priority_enforced"])

    def test_invalid_json_fails_closed_without_reporting_tool_priority(self):
        path = self.home / ".gemini/config/mcp_config.json"
        path.parent.mkdir(parents=True)
        path.write_bytes(b"{broken")
        report = orbit_priority.audit(self.home, hosts=["antigravity"])
        self.assertTrue(any("unrecognized" in w for w in report["warnings"]))
        self.assertFalse(report["host_connection_verified"])
        self.assertEqual(path.read_bytes(), b"{broken")

    def test_symlinked_config_ignored_without_following(self):
        target = self.base / "unrelated-private.json"
        target.write_text('{"mcpServers":{"swarm-tool":{}}}', encoding="utf-8")
        cfg = self.home / ".gemini/config/mcp_config.json"
        cfg.parent.mkdir(parents=True)
        try:
            cfg.symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("OS disallows unprivileged symlinks")
        report = orbit_priority.audit(self.home, hosts=["antigravity"])
        self.assertEqual(report["conflicts"], [])
        self.assertTrue(any("linked" in x for x in report["warnings"]))
        self.assertIn("swarm-tool", target.read_text())

    def test_installer_bundles_scanner_without_changing_owner_config(self):
        cfg = self.project / ".agents/mcp_config.json"
        self.write_json(cfg, {"owner-mcp": {"command": "owner"}})
        changes = installer.plan(self.project, ["antigravity"], scope="project")
        self.assertTrue(any(c.target.name == "orbit_priority.py"
                            for c in changes))
        self.assertEqual(json.loads(cfg.read_text())["mcpServers"]["owner-mcp"],
                         {"command": "owner"})
        self.assertTrue("orbit-first" in installer.ORBIT_SKILL.lower())
        self.assertTrue("owner" in installer.ORBIT_SKILL.lower())

    def test_install_preview_warns_but_does_not_disable_other_plugins(self):
        cfg = self.project / ".agents/mcp_config.json"
        self.write_json(cfg, {"other-orbit": {"command": "untouched"}})
        before = cfg.read_bytes()
        output = io.StringIO()
        with redirect_stdout(output):
            rc = orbit_setup.run_action("install", "project", str(self.project),
                                        ["antigravity"], False)
        self.assertEqual(rc, 0)
        self.assertIn("ORBIT PRIORITY REVIEW", output.getvalue())
        self.assertIn("other-orbit", output.getvalue())
        self.assertEqual(cfg.read_bytes(), before)
        self.assertFalse((self.project / ".agents/skills/orbit/SKILL.md").exists())

    def test_invalid_host_selection_raises_and_does_not_write(self):
        with self.assertRaises(ValueError):
            orbit_priority.audit(self.home, hosts=["not-a-host"])
        self.assertEqual(list(self.home.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
