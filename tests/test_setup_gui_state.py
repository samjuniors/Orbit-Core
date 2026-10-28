"""Headless tests of GUI callbacks; no desktop window or real home writes."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import os
import sys
import tempfile

GUI=Path(__file__).resolve().parents[1]/'install_orbit_gui.pyw'

class SetupGuiStateTests(unittest.TestCase):
    def setUp(self):
        tree=ast.parse(GUI.read_text())
        functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'installation_action','refresh_action','go'}]
        self.ns={}
        exec(compile(ast.Module(body=functions,type_ignores=[]),str(GUI),'exec'),self.ns)

    def change(self,action,exists=False):
        return SimpleNamespace(action=action,target=SimpleNamespace(exists=lambda:exists),data=b'x')

    def test_action_states(self):
        action=self.ns['installation_action']
        self.assertEqual(action([self.change('CREATE')]),'install')
        self.assertEqual(action([self.change('SKIP',True)]),'current')
        self.assertEqual(action([self.change('PRESERVE',True)]),'current')
        self.assertEqual(action([self.change('UPGRADE',True)]),'update')
        self.assertEqual(action([self.change('MERGE',True)]),'update')
        self.assertEqual(action([self.change('APPEND',True)]),'update')
        self.assertEqual(action([self.change('SKIP',True),self.change('CREATE')]),'repair')

    def setup_callback(self,changes):
        self.ns.update(state={'busy':False},operation_buttons=[Mock()],args=lambda:(None,['codex'],'machine'),
                       make_preview=Mock(return_value=changes),plan=Mock(return_value=changes),
                       install=Mock(),status=Mock(),r=Mock(),messagebox=Mock(),
                       SetupError=RuntimeError,refresh_action=Mock())

    def test_real_install_repeat_and_missing_file_repair(self):
        sys.path.insert(0,str(GUI.parent))
        import installer
        with tempfile.TemporaryDirectory() as folder:
            home=Path(folder)/'home'
            project=Path(folder)/'project'
            project.mkdir()
            with patch.dict(os.environ,{'ORBIT_SETUP_HOME':str(home),'ORBIT_UNIVERSAL_HOME':str(home/'.orbit-universal')}):
                changes=installer.plan(str(project),['codex'],'project')
                self.assertEqual(self.ns['installation_action'](changes),'install')
                installer.install(changes)
                self.assertEqual(self.ns['installation_action'](installer.plan(str(project),['codex'],'project')),'current')
                (home/'.orbit-universal/orbit_cli.py').unlink()
                self.assertEqual(self.ns['installation_action'](installer.plan(str(project),['codex'],'project')),'repair')

    def test_refresh_disables_current_and_conflicting_installs(self):
        self.setup_callback([self.change('SKIP',True)])
        self.ns['primary']=Mock()
        # Use the actual refresh callback rather than the callback fixture mock.
        tree=ast.parse(GUI.read_text())
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='refresh_action')
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(GUI),'exec'),self.ns)
        self.ns['refresh_action']()
        self.ns['primary'].config.assert_called_with(text='Orbit is up to date',state='disabled')
        self.ns['plan'].side_effect=RuntimeError('customized file')
        self.ns['refresh_action']()
        self.ns['primary'].config.assert_called_with(text='Review required',state='disabled')

    def test_current_does_not_prompt_or_write(self):
        self.setup_callback([self.change('SKIP',True)])
        self.ns['go']()
        self.ns['install'].assert_not_called()
        self.ns['messagebox'].askyesno.assert_not_called()
        self.ns['messagebox'].showinfo.assert_called_once()

    def test_busy_reentry_does_nothing(self):
        self.setup_callback([])
        self.ns['state']['busy']=True
        self.ns['go']()
        self.ns['make_preview'].assert_not_called()

    def test_success_verifies_and_refreshes(self):
        changes=[self.change('CREATE')]
        self.setup_callback(changes)
        self.ns['plan'].side_effect=[changes,[self.change('SKIP',True)]]
        self.ns['go']()
        self.ns['install'].assert_called_once_with(changes)
        self.assertIn('installed successfully',self.ns['messagebox'].showinfo.call_args.args[0])
        self.ns['refresh_action'].assert_called_once()
        self.assertFalse(self.ns['state']['busy'])

    def test_failure_never_reports_success(self):
        changes=[self.change('CREATE')]
        self.setup_callback(changes)
        self.ns['install'].side_effect=OSError('write failed')
        self.ns['go']()
        self.ns['messagebox'].showinfo.assert_not_called()
        self.ns['messagebox'].showerror.assert_called_once()
        self.assertFalse(self.ns['state']['busy'])

    def test_cancel_never_writes(self):
        self.setup_callback([self.change('CREATE')])
        self.ns['messagebox'].askyesno.return_value=False
        self.ns['go']()
        self.ns['install'].assert_not_called()
        self.ns['messagebox'].showinfo.assert_not_called()

if __name__=='__main__':
    unittest.main()
