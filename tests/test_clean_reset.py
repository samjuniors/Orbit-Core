"""Destructive reset runs only against disposable homes and explicit project paths."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import installer
import orbit_setup


class CleanResetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.home = self.base / 'home'
        self.project = self.base / 'project'
        self.project.mkdir()
        env = patch.dict(os.environ, {'ORBIT_SETUP_HOME': str(self.home),
                                     'ORBIT_UNIVERSAL_HOME': str(self.home / '.orbit-universal')})
        env.start()
        self.addCleanup(env.stop)
        installer.install(installer.plan(None, installer.HOSTS, 'machine'))
        installer.install(installer.plan(self.project, installer.HOSTS, 'project'))
        self.memory = self.home / 'AppData/Local/OrbitCore/memory.sqlite3'
        self.write(self.memory, b'saved research')
        self.write(self.project / '.orbit/STATE.md', b'checkpoint')
        self.write(self.project / 'app.js', b'product source')
        self.agent = self.home / '.gemini/config/agents/orbit-architect.md'
        self.agent.write_bytes(b'customized conflicting Orbit agent')
        self.write(self.home / '.orbit-universal/old-version/custom.py', b'old runtime')
        self.write(self.home / '.gemini/config/skills/orbit/custom.md', b'custom Orbit skill')
        self.write(self.home / '.gemini/config/agents/other-agent.md', b'unrelated agent')
        cfg = self.home / '.gemini/config/mcp_config.json'
        cfg.write_text(json.dumps({'theme': 'dark', 'mcpServers': {
            'other': {'command': 'other'}, installer.SERVER: {'command': 'custom', 'env': {'X': 'Y'}}}}))
        self.codex = self.home / '.codex/config.toml'
        self.codex.write_text('# owner config\nmodel = "owner"\n[mcp_servers."orbit-core-native"]\ncommand="custom"\n[mcp_servers."orbit-core-native".env]\nX="Y"\n[mcp_servers.other]\ncommand="other"\n')

    def write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def plan(self, erase=False):
        return orbit_setup.plan_clean_reset(self.project, erase_memory=erase)[0]

    def apply(self, changes, erase=False, confirmation='REMOVE ORBIT'):
        return orbit_setup.apply_clean_reset(changes, self.project, erase_memory=erase, confirmation=confirmation)

    def test_preview_is_read_only_and_confirmation_is_required(self):
        changes = self.plan(True)
        self.assertTrue(self.agent.exists())
        self.assertTrue(self.memory.exists())
        self.assertFalse((self.home / '.orbit-uninstall-backups').exists())
        with self.assertRaisesRegex(installer.SetupError, 'requires typing'):
            self.apply(changes, True, '')
        self.assertTrue(self.agent.exists())
        self.assertFalse((self.home / '.orbit-uninstall-backups').exists())

    def test_clean_conflicts_then_install_fresh_preserving_other_tools_and_memory(self):
        backup = self.apply(self.plan())
        self.assertFalse(self.agent.exists())
        self.assertFalse((self.home / '.orbit-universal').exists())
        self.assertFalse((self.home / '.gemini/config/skills/orbit').exists())
        self.assertEqual(self.memory.read_bytes(), b'saved research')
        self.assertEqual((self.project / '.orbit/STATE.md').read_bytes(), b'checkpoint')
        self.assertEqual((self.project / 'app.js').read_bytes(), b'product source')
        cfg = json.loads((self.home / '.gemini/config/mcp_config.json').read_text())
        self.assertEqual(cfg, {'theme': 'dark', 'mcpServers': {'other': {'command': 'other'}}})
        self.assertIn('model = "owner"', self.codex.read_text())
        self.assertIn('[mcp_servers.other]', self.codex.read_text())
        self.assertNotIn(installer.SERVER, self.codex.read_text())
        self.assertEqual((self.home / '.gemini/config/agents/other-agent.md').read_bytes(), b'unrelated agent')
        manifest = json.loads((backup / 'manifest.json').read_text())
        entry = next(x for x in manifest if x['original_path'] == str(self.agent))
        self.assertEqual((backup / entry['backup_name']).read_bytes(), b'customized conflicting Orbit agent')
        for project, scope in [(None, 'machine'), (self.project, 'project')]:
            installer.install(installer.plan(project, installer.HOSTS, scope))
            self.assertTrue(all(c.action in {'SKIP', 'PRESERVE'} for c in installer.plan(project, installer.HOSTS, scope)))

    def test_explicit_memory_reset_removes_database_sidecars_and_project_notes(self):
        self.write(Path(str(self.memory) + '-wal'), b'wal')
        backup = self.apply(self.plan(True), True)
        self.assertFalse(self.memory.exists())
        self.assertFalse(Path(str(self.memory) + '-wal').exists())
        self.assertFalse((self.project / '.orbit').exists())
        self.assertTrue((self.project / 'app.js').exists())
        self.assertTrue((backup / 'manifest.json').exists())

    def test_stale_content_or_added_file_blocks_before_deletion(self):
        for drift in ('changed', 'new'):
            with self.subTest(drift=drift):
                changes = self.plan()
                if drift == 'changed':
                    self.agent.write_bytes(b'different now')
                else:
                    self.write(self.home / '.orbit-universal/new.py', b'new file')
                with self.assertRaisesRegex(installer.SetupError, 'preview changed'):
                    self.apply(changes)
                self.assertTrue(self.agent.exists())
                self.assertTrue(self.memory.exists())

    def test_symlink_inside_runtime_or_skill_blocks_all_deletion(self):
        outside = self.base / 'outside'
        outside.write_bytes(b'keep')
        for folder in [self.home / '.orbit-universal', self.home / '.gemini/config/skills/orbit']:
            link = folder / 'link'
            try:
                link.symlink_to(outside)
            except OSError:
                self.skipTest("Symlink creation unavailable on this host")
            try:
                with self.assertRaisesRegex(installer.SetupError, 'linked'):
                    self.plan()
                self.assertTrue(self.agent.exists())
                self.assertEqual(outside.read_bytes(), b'keep')
            finally:
                link.unlink()

    def test_invalid_shared_config_blocks_instead_of_deleting_other_settings(self):
        cfg = self.home / '.gemini/config/mcp_config.json'
        cfg.write_bytes(b'{broken config')
        with self.assertRaisesRegex(installer.SetupError, 'invalid shared JSON'):
            self.plan()
        self.assertEqual(cfg.read_bytes(), b'{broken config')
        self.assertTrue(self.agent.exists())

    def test_global_vscode_servers_removed_without_touching_other_entries(self):
        cfg = (self.home / 'AppData/Roaming/Code/User/mcp.json' if os.name == 'nt' else
               self.home / ('Library/Application Support/Code/User/mcp.json' if os.sys.platform == 'darwin' else '.config/Code/User/mcp.json'))
        self.write(cfg, json.dumps({'servers': {installer.SERVER: {'command': 'custom'}, 'other': {'command': 'keep'}}}).encode())
        self.apply(self.plan())
        self.assertEqual(json.loads(cfg.read_text()), {'servers': {'other': {'command': 'keep'}}})

    def test_unselected_project_is_never_scanned(self):
        other = self.base / 'other-project/.orbit/STATE.md'
        self.write(other, b'other project')
        self.apply(self.plan(True), True)
        self.assertEqual(other.read_bytes(), b'other project')

    def test_custom_database_inside_runtime_is_not_deleted_implicitly(self):
        custom = self.home / '.orbit-universal/custom.sqlite3'
        self.write(custom, b'custom database')
        with patch.dict(os.environ, {'ORBIT_LOCAL_DB': str(custom)}):
            self.apply(self.plan(True), True)
        self.assertEqual(custom.read_bytes(), b'custom database')

    def test_backup_write_failure_prevents_any_deletion(self):
        changes = self.plan()
        original_open = Path.open
        def fail_backup(path, *args, **kwargs):
            if path.suffix == '.bak':
                raise PermissionError('backup denied')
            return original_open(path, *args, **kwargs)
        with patch.object(Path, 'open', fail_backup):
            with self.assertRaises(PermissionError):
                self.apply(changes)
        self.assertTrue(self.agent.exists())
        self.assertTrue((self.home / '.orbit-universal').exists())

    def test_locked_target_reports_recovery_location(self):
        changes = self.plan()
        original_unlink = Path.unlink
        def fail_target(path, *args, **kwargs):
            if path == self.agent:
                raise PermissionError('target in use')
            return original_unlink(path, *args, **kwargs)
        with patch.object(Path, 'unlink', fail_target):
            with self.assertRaisesRegex(installer.SetupError, 'recovery backup:'):
                self.apply(changes)
        backups = list((self.home / '.orbit-uninstall-backups').glob('*/manifest.json'))
        self.assertEqual(len(backups), 1)
        self.assertTrue(self.agent.exists())

    def test_cli_requires_explicit_confirmation_and_does_not_use_host_detection(self):
        from contextlib import redirect_stdout, redirect_stderr
        import io
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(orbit_setup.main(['clean', '--scope', 'machine']), 0)
            self.assertEqual(orbit_setup.main(['clean', '--scope', 'machine', '--apply']), 1)
        self.assertTrue(self.agent.exists())
        self.assertFalse((self.home / '.orbit-uninstall-backups').exists())

    def test_cannot_delete_current_setup_source(self):
        real_plan = orbit_setup.plan_uninstall
        # Point the active package at a child of the runtime after global planning.
        original = installer.PACKAGE
        def move_package(*args, **kwargs):
            result = real_plan(*args, **kwargs)
            installer.PACKAGE = self.home / '.orbit-universal/active-setup'
            return result
        try:
            with patch.object(orbit_setup, 'plan_uninstall', side_effect=move_package):
                with self.assertRaisesRegex(installer.SetupError, 'separate checkout'):
                    orbit_setup.plan_clean_reset()
        finally:
            installer.PACKAGE = original
        self.assertTrue(self.agent.exists())

    def test_toml_with_ambiguous_multiline_header_is_not_corrupted(self):
        body = 'notes = """\n[mcp_servers.orbit-core-native]\n"""\n[mcp_servers.orbit-core-native]\ncommand="old"\n'
        with self.assertRaises((installer.SetupError, ValueError)):
            orbit_setup._remove_codex_orbit(body)
