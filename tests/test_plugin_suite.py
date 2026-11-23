"""Verify Orbit Core's single ZIP with host-specific plugin formats."""
import json
import unittest
from pathlib import Path
from scripts.build_plugin_suite import CLAUDE_CODE_PLUGIN_DIR, claude_code_files, entries

ROOT = Path(__file__).resolve().parents[1]

class SuiteTests(unittest.TestCase):
    def test_host_layout(self):
        files = entries(ROOT)
        self.assertIn('orbit-core-suite/Orbit Setup.cmd', files)
        for host, manifest in [('antigravity','mcp_config.json'), ('codex','mcp.json'), ('claude-code','.mcp.json')]:
            prefix = f'orbit-core-suite/{host}/orbit-core/'
            self.assertIn(prefix + manifest, files)
            self.assertIn(prefix + 'runtime/orbit_mcp.py', files)
            self.assertIn(prefix + 'skills/orbit-workflow-skill/SKILL.md', files)
        self.assertNotIn('orbit-core-suite/deepseek-harness', files)

    def test_committed_claude_code_plugin_matches_source(self):
        # Regenerate with: python scripts/build_plugin_suite.py --sync-claude-code
        target = ROOT / CLAUDE_CODE_PLUGIN_DIR
        desired = claude_code_files(ROOT)
        committed = {p.relative_to(target).as_posix(): p.read_bytes()
                     for p in target.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
        self.assertEqual(sorted(committed), sorted(desired))
        for name, blob in desired.items():
            self.assertEqual(committed[name], blob, name)

    def test_marketplace_points_at_committed_plugin(self):
        market = json.loads((ROOT / '.claude-plugin/marketplace.json').read_text(encoding='utf-8'))
        self.assertEqual(market['name'], 'orbit-core')
        self.assertEqual(market['owner']['name'], 'Samjuniors')
        self.assertEqual(market['owner']['url'], 'https://github.com/samjuniors')
        [entry] = market['plugins']
        self.assertEqual(entry['displayName'], 'Orbit Core')
        self.assertEqual(entry['author'], {
            'name': 'Samjuniors', 'url': 'https://github.com/samjuniors'})
        self.assertEqual(entry['homepage'], 'https://github.com/samjuniors/Orbit-Core')
        self.assertEqual(entry['repository'], 'https://github.com/samjuniors/Orbit-Core')
        self.assertEqual(entry['license'], 'MIT')
        self.assertEqual(entry['source'], './' + CLAUDE_CODE_PLUGIN_DIR.as_posix())
        plugin = json.loads((ROOT / CLAUDE_CODE_PLUGIN_DIR / '.claude-plugin/plugin.json')
                            .read_text(encoding='utf-8'))
        self.assertEqual(plugin['name'], entry['name'])
        self.assertEqual(plugin['displayName'], 'Orbit Core')
        self.assertEqual(plugin['author'], {
            'name': 'Samjuniors', 'url': 'https://github.com/samjuniors'})
        self.assertEqual(plugin['version'], (ROOT / 'VERSION').read_text().strip())
        # Windows Store `python` alias closes stdio before the server starts; ORBIT_PYTHON overrides it.
        mcp = json.loads((ROOT / CLAUDE_CODE_PLUGIN_DIR / '.mcp.json').read_text(encoding='utf-8'))
        self.assertEqual(mcp['mcpServers']['orbit-core-mcp']['command'], '${ORBIT_PYTHON:-python}')

    def test_claude_code_agents_keep_tool_allowlists_and_canonical_mcp_names(self):
        agents = {n: b.decode('utf-8') for n, b in claude_code_files(ROOT).items()
                  if n.startswith('agents/')}
        self.assertTrue(agents)
        for name, text in agents.items():
            header = text.split('\n---\n', 1)[0]
            tools = [line for line in header.splitlines() if line.startswith('tools: ')]
            self.assertEqual(len(tools), 1, name)
            self.assertNotIn('orbit-lead-agent_', text, name)
        for role in ('orbit-research-agent', 'orbit-reviewer-agent', 'orbit-security-agent'):
            self.assertIn('\ntools: Read, Grep, Glob\n', agents[f'agents/{role}.md'])
        self.assertIn('`orbit_capability_select`', agents['agents/orbit-architect-agent.md'])

if __name__ == '__main__':
    unittest.main()
