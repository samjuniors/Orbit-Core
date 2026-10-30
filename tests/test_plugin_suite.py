"""Verify Orbit Core's single ZIP with host-specific plugin formats."""
import unittest
from pathlib import Path
from scripts.build_plugin_suite import entries

ROOT = Path(__file__).resolve().parents[1]

class SuiteTests(unittest.TestCase):
    def test_host_layout(self):
        files = entries(ROOT)
        for host, manifest in [('antigravity','mcp_config.json'), ('codex','mcp.json'), ('claude-code','.mcp.json')]:
            prefix = f'orbit-core-suite/{host}/orbit-core/'
            self.assertIn(prefix + manifest, files)
            self.assertIn(prefix + 'runtime/orbit_mcp.py', files)
            self.assertIn(prefix + 'skills/orbit-workflow-skill/SKILL.md', files)
        self.assertNotIn('orbit-core-suite/deepseek-harness', files)

if __name__ == '__main__':
    unittest.main()
