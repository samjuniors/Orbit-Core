"""Issue #7: cross-host maturity routing, scoped changes and pause safety."""
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source/runtime'))
import orbit_build
import orbit_mcp
import orbit_intake
import orbit_tasks


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name, 'product')
        self.root.mkdir()
        self.root = self.root.resolve()
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self.addCleanup(self.conn.close)
        orbit_build.setup(self.conn)
        orbit_intake.setup(self.conn)
        orbit_tasks.setup(self.conn)
        self.conn.execute("""CREATE TABLE memories(
          project TEXT, key TEXT, kind TEXT, summary TEXT,
          evidence TEXT, importance INTEGER, updated_at TEXT, status TEXT)""")
        self.conn.commit()
        self.args = {'project_root':str(self.root), 'project':'demo'}

    def call(self, tool, **kw):
        return orbit_mcp.execute(self.conn, tool, {**self.args, **kw})

    def inspect(self, action='status', **kw):
        return self.call('orbit_project_action', action=action, **kw)

    def create(self, bid='base'):
        return orbit_build.begin(self.conn, self.root,
            {'project':'demo','build_id':bid,'objective':'Ship existing application',
             'confirm_write':True})

    def current(self, bid='base'):
        return self.call('orbit_build_status', build_id=bid)['run']

    def test_blank_is_read_only_and_uses_approved_intake(self):
        before = list(self.root.iterdir())
        result = self.inspect('start')
        self.assertEqual(result['maturity'], 'new')
        self.assertEqual(result['status'], 'READY')
        self.assertFalse(result['host_action_executed'])
        self.assertEqual(before, list(self.root.iterdir()))
        self.assertEqual(self.call('orbit_build_begin', build_id='brand-new',
            objective='Make a product', confirm_write=True)['status'], 'HOLD')
        self.assertEqual(self.call('orbit_project_resume')['recovery']['status'], 'NO_BUILD')

    def test_existing_repo_routes_without_reinterview_or_writes(self):
        (self.root/'pyproject.toml').write_text('[project]\nname="product"\n')
        (self.root/'README.md').write_text('Owner docs are canonical.')
        prior = {p.name:p.read_bytes() for p in self.root.iterdir()}
        state = self.call('orbit_project_resume')
        self.assertEqual(state['lifecycle']['maturity'], 'existing')
        self.assertEqual(state['experience']['phase'], 'EXISTING_PROJECT')
        self.assertEqual(state['intake']['status'], 'NOT_STARTED')
        self.assertEqual(prior, {p.name:p.read_bytes() for p in self.root.iterdir()})
        self.assertEqual(self.inspect('debug weird traceback')['action'], 'fix')
        self.assertEqual(self.inspect('add feature user export')['action'], 'feature')
        self.assertEqual(self.inspect('redesign mobile screen')['action'], 'redesign')
        self.assertEqual(self.inspect('refactor auth module')['action'], 'refactor')
        self.assertEqual(self.inspect('test checkout')['action'], 'review')
        custom=self.inspect('Make this integrate with a novel hardware protocol')
        self.assertEqual(custom['action'], 'custom')
        self.assertIn('novel hardware', custom['raw_intent'])

    def test_docs_only_folder_does_not_get_mistaken_for_coded_product(self):
        (self.root/'README.md').write_text('Existing project idea, not implementation')
        (self.root/'AGENTS.md').write_text('Existing owner instructions')
        (self.root/'.git').mkdir()
        before = {p.name: (p.read_bytes() if p.is_file() else None)
                  for p in self.root.iterdir()}
        route=self.inspect('start')
        self.assertEqual(route['maturity'],'new')
        self.assertEqual(route['maturity_evidence'],'no_code_markers')
        self.assertEqual(route['observed_code_signals'],[])
        self.assertIn('README.md',route['observed_docs_signals'])
        self.assertIn('intake',route['next_action'])
        self.assertEqual(before,{p.name: (p.read_bytes() if p.is_file() else None)
                                 for p in self.root.iterdir()})

    def test_existing_static_site_and_partially_built_user_stage(self):
        (self.root/'index.html').write_text('<main>Existing site</main>')
        route=self.inspect('continue',maturity='partially_built')
        self.assertEqual(route['action'],'resume')
        self.assertEqual(route['maturity'],'partially_built_user_reported')
        self.assertFalse(route['maturity_is_inferred'])
        self.assertEqual(route['maturity_evidence'],'code_or_manifest_names')
        self.assertIn('index.html',route['observed_code_signals'])
        self.assertIn('inspect existing code',route['next_action'])

    def test_unverified_finished_or_stalled_project_requires_baseline(self):
        for stage in ('completed','stalled','maintained'):
            with self.subTest(stage=stage):
                result=self.inspect('start',maturity=stage)
                self.assertEqual(result['maturity'],stage+'_user_reported')
                self.assertEqual(result['needs_decision'],
                                 'Locate the reported source folder')
                self.assertIn('Locate and inspect',result['next_action'])
                self.assertEqual(list(self.root.iterdir()),[])

    def test_plain_language_new_project_and_plural_features(self):
        self.assertEqual(self.inspect('build a mobile app')['action'],'new')
        self.assertEqual(self.inspect('create a website')['action'],'new')
        self.assertEqual(self.inspect('add features to the existing app')['action'],
                         'feature')
        self.assertEqual(self.inspect('stop preview')['action'],'preview_stop')

    def test_scoped_fix_skips_new_project_plan_but_requires_tests(self):
        (self.root/'src').mkdir()
        run=self.call('orbit_build_begin', build_id='repair-export',
            objective='Repair CSV quoting regression', change_kind='fix',
            baseline_reference='git:abc12345', confirm_write=True)
        self.assertEqual(run['status'], 'CREATED')
        self.assertEqual(run['run']['stage'], 'IMPLEMENT')
        self.assertEqual(run['run']['evidence']['__orbit_anchor']['host_reported_baseline'],
                         'git:abc12345')
        steps=self.call('orbit_build_status',build_id='repair-export')['stages']
        self.assertEqual(steps, ['IMPLEMENT','VERIFY','REVIEW','CHECKPOINT','DONE'])
        advanced=self.call('orbit_build_advance', build_id='repair-export',
            expected_revision=1, outcome='PASS', evidence='Focused patch ready',
            confirm_write=True)
        self.assertEqual(advanced['run']['stage'], 'VERIFY')
        self.assertEqual(self.call('orbit_build_advance', build_id='repair-export',
            expected_revision=2, outcome='PASS', evidence='Tests passed',
            confirm_write=True)['status'], 'HOLD')

    def test_pausing_and_resuming_requires_revision_and_confirmation(self):
        self.create()
        v=self.current()['revision']
        draft=self.inspect('stop',build_id='base',expected_revision=v)
        self.assertEqual(draft['status'],'PREVIEW_ONLY')
        self.assertEqual(self.current()['revision'],v)
        self.assertEqual(self.inspect('pause',build_id='base',
            expected_revision=v+2,confirm_write=True)['status'],'STALE_REVISION')
        paused=self.inspect('pause',build_id='base',expected_revision=v,
            confirm_write=True,reason='Owner asked to pause after a safe point')
        self.assertEqual(paused['status'],'PAUSED')
        self.assertEqual(self.current()['revision'],v+1)
        self.assertEqual(self.call('orbit_project_resume')['experience']['phase'],'PAUSED')
        blocked=self.call('orbit_build_advance',build_id='base',
             expected_revision=v+1,outcome='PASS',evidence='Not verified',confirm_write=True)
        self.assertEqual(blocked['status'],'HOLD')
        self.assertIn('paused',blocked['reason'])
        self.assertEqual(self.inspect('continue',build_id='base',
            expected_revision=v+1)['status'],'PREVIEW_ONLY')
        self.assertEqual(self.inspect('continue',build_id='base',
            expected_revision=v+1,confirm_write=True)['status'],'RESUMED')
        self.assertEqual(self.current()['stage'],'RESEARCH')
        self.assertFalse(self.current()['evidence']['__orbit_control']['paused'])
        self.assertFalse((self.root/'.orbit').exists())

    def test_finished_build_change_is_new_and_old_done_immutable(self):
        base=self.create()['run']
        self.conn.execute("UPDATE build_runs SET stage='DONE' WHERE project=? AND root=? AND build_id=?",
                          ('demo',str(self.root),'base'))
        self.conn.commit()
        old=self.current()
        self.assertEqual(self.inspect('resume',build_id='base')['status'],'ALREADY_DONE')
        change=self.call('orbit_build_begin',build_id='new-search',
            objective='Add search to the existing completed product',
            change_kind='feature',change_from='base',confirm_write=True)
        self.assertEqual(change['status'],'CREATED')
        self.assertEqual(change['run']['stage'],'PLAN')
        self.assertEqual(change['run']['evidence']['__orbit_anchor']['build_id'],'base')
        self.assertEqual(self.current(),old)
        self.assertEqual(self.call('orbit_build_status',build_id='new-search')['stages'],
                         ['PLAN','IMPLEMENT','VERIFY','REVIEW','CHECKPOINT','DONE'])
        self.assertEqual(self.call('orbit_build_advance',build_id='new-search',
            expected_revision=1,outcome='PASS',evidence='Skip user approval',
            confirm_write=True)['status'],'HOLD')
        self.assertEqual(self.current()['stage'],'DONE')

    def test_scoped_source_restrictions_and_multi_build_selection(self):
        self.create()
        self.create('another')
        selection=self.inspect('resume')
        self.assertEqual(selection['status'],'NEEDS_BUILD_SELECTION')
        self.assertEqual(len(selection['builds']),2)
        bad=self.call('orbit_build_begin',build_id='inappropriate',
            objective='Unauthorized follow-on',change_kind='feature',
            change_from='base',confirm_write=True)
        self.assertEqual(bad['status'],'HOLD')
        self.assertEqual(self.call('orbit_build_status',build_id='inappropriate')['status'],
                         'NOT_FOUND')
        no_signal=self.call('orbit_build_begin',build_id='no-code',
            objective='Feature on blank folder',change_kind='feature',
            baseline_reference='git:abc12345',confirm_write=True)
        self.assertEqual(no_signal['status'],'HOLD')

    def test_stop_preview_never_pauses_a_build_or_kills_a_process(self):
        self.create()
        before=self.current()
        route=self.inspect('stop preview',build_id='base',
                           expected_revision=1,confirm_write=True)
        self.assertEqual(route['action'],'preview_stop')
        self.assertTrue(route['preview_stop_requires_separate_tool'])
        self.assertFalse(route['user_data_modified'])
        self.assertEqual(self.current(),before)
        self.assertIn('orbit_preview_stop',route['next_action'])

    def test_legacy_build_flow_survives_without_schema_migration(self):
        self.create()
        self.conn.execute("UPDATE build_runs SET evidence_json=? WHERE project=? AND root=? AND build_id=?",
                          (json.dumps({'RESEARCH':{'outcome':'PASS'}}),'demo',str(self.root),'base'))
        self.conn.commit()
        self.assertEqual(tuple(self.call('orbit_build_status',build_id='base')['stages']),
                         orbit_build.STAGES)
        self.assertEqual(self.inspect('status')['selected_build']['revision'],1)

    def test_protocol_limits_and_free_form_intent(self):
        for value in ('', 'x'*241):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.call('orbit_project_action',action=value)
        with self.assertRaises(ValueError):
            self.call('orbit_project_action',action='fix',confirm_write='true')
        state=self.inspect('stalled maintenance',maturity='stalled')
        self.assertEqual(state['maturity'],'stalled_user_reported')


if __name__ == '__main__':
    unittest.main()
