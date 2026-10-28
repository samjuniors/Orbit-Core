"""Regression for the official intermediate template reported by Windows setup."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import installer


class StockAgentUpgradeTests(unittest.TestCase):
    def test_intermediate_official_agent_upgrades_with_backup(self):
        stock = (Path(__file__).parent / 'fixtures/orbit-architect-7e1372f.md').read_bytes()
        for windows in (False, True):
            for host in ('antigravity', 'claude-code'):
                with self.subTest(windows=windows, host=host), tempfile.TemporaryDirectory() as folder:
                    home = Path(folder)
                    if host == 'antigravity':
                        target = home / '.gemini/config/agents/orbit-architect.md'
                        data = stock
                    else:
                        target = home / '.claude/agents/orbit-architect.md'
                        data = installer.agent_claude(stock.decode()).encode()
                    if windows:
                        data = data.replace(b'\n', b'\r\n')
                    target.parent.mkdir(parents=True)
                    target.write_bytes(data)
                    env = {'ORBIT_SETUP_HOME': folder, 'ORBIT_UNIVERSAL_HOME': str(home / '.orbit-universal')}
                    with patch.dict(os.environ, env):
                        changes = installer.plan(None, [host], 'machine')
                        change = next(c for c in changes if c.target == target)
                        self.assertEqual(change.action, 'UPGRADE')
                        self.assertEqual(target.read_bytes(), data, 'Preview must not write')
                        installer.install(changes)
                        self.assertEqual(target.with_name(target.name + '.orbit-backup').read_bytes(), data)
                        self.assertEqual(target.read_bytes(), change.data)
                        self.assertTrue(all(c.action in {'SKIP', 'PRESERVE'} for c in installer.plan(None, [host], 'machine')))

    def test_owner_edit_remains_blocked_without_writes(self):
        stock = (Path(__file__).parent / 'fixtures/orbit-architect-7e1372f.md').read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            home = Path(folder)
            target = home / '.gemini/config/agents/orbit-architect.md'
            target.parent.mkdir(parents=True)
            data = stock + b'\nOwner customization\n'
            target.write_bytes(data)
            with patch.dict(os.environ, {'ORBIT_SETUP_HOME': folder, 'ORBIT_UNIVERSAL_HOME': str(home / '.orbit-universal')}):
                with self.assertRaisesRegex(installer.SetupError, 'no overwrite'):
                    installer.plan(None, ['antigravity'], 'machine')
                self.assertEqual(target.read_bytes(), data)
                self.assertFalse((home / '.orbit-universal').exists())
