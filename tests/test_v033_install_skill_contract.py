"""Regression: published-style host installation must ship v0.33 runtime guidance.

The universal installer embeds a compact skill independently of the repository
source skill. Its safety/feature contract must not silently lag new MCP APIs.
No real user home, host permissions, model calls, or plugins are used.
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import installer


class V033InstallerSkillContractTests(unittest.TestCase):
    TERMS = (
        "include_ui_inventory",
        "include_visual_review",
        "visual_contract",
        "ui_coverage_packet",
        "expected_resume_digest",
        "reported_branch",
        "specialist_return_mode",
        "specialist_return_to_lead",
        "expected_output_kind",
        "include_team_events",
        "not",
    )

    def test_compact_installed_skill_matches_new_safety_contract(self):
        self.assertEqual(installer.VERSION, "0.33.0")
        s = installer.ORBIT_SKILL
        for term in self.TERMS:
            with self.subTest(term=term):
                self.assertIn(term, s)
        self.assertIn("authenticated owner consent", s)
        self.assertIn("must HOLD", s)
        self.assertIn("host-native", s)

    def test_disposable_install_preview_exposes_current_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp).resolve()
            root = base / "disposable-orbit-project"
            root.mkdir()
            env = {"ORBIT_SETUP_HOME": str(base / "home"),
                   "ORBIT_UNIVERSAL_HOME": str(base / "runtime")}
            with patch.dict(os.environ, env):
                changes = installer.plan(root, ("antigravity", "codex"), "project")
                skill = root / ".agents/skills/orbit/SKILL.md"
                matches = [c for c in changes if c.target == skill]
                self.assertEqual(len(matches), 1)
                self.assertEqual(matches[0].action, "CREATE")
                text = matches[0].data.decode("utf-8")
                for term in self.TERMS:
                    self.assertIn(term, text)
                self.assertFalse(skill.exists(), "Preview must not write")
                installer.install(changes)
                self.assertEqual(skill.read_text(encoding="utf-8"), text)
                after = installer.plan(root, ("antigravity", "codex"), "project")
                self.assertEqual({c.action for c in after}, {"SKIP"})

    def test_source_skill_and_embedded_contract_have_same_key_gates(self):
        source = (ROOT / "source/skills/orbit/SKILL.md").read_text(encoding="utf-8")
        for term in ("include_visual_review", "include_ui_inventory",
                     "expected_resume_digest", "specialist_return_to_lead",
                     "include_team_events"):
            self.assertIn(term, source)
            self.assertIn(term, installer.ORBIT_SKILL)


if __name__ == "__main__":
    unittest.main()
