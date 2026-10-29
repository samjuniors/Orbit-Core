"""M4 opt-in bounded resume: local/project-scoped sources only, no new MCP tool."""
from __future__ import annotations
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source/runtime'))
import orbit_mcp


class CompactResumeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve()
        self.root=self.base/'demo'
        self.other=self.base/'another'
        self.root.mkdir()
        self.other.mkdir()
        env=patch.dict(os.environ,{'ORBIT_LOCAL_DB':str(self.base/'state.sqlite3')})
        env.start()
        self.addCleanup(env.stop)
        self.conn=orbit_mcp.db_connect()
        self.addCleanup(self.conn.close)
        self.a={'project_root':str(self.root),'project':'workspace'}

    def call(self,name,**kw):
        return orbit_mcp.execute(self.conn,name,{**self.a,**kw})

    def approve_intake(self):
        profile={'type':'web-app','complexity':'moderate','maturity':'prototype',
                 'goal':'Build a useful offline product with searchable records',
                 'audience':'People managing their own records',
                 'constraints':'Local first, no cloud dependencies',
                 'stack':'Python, SQLite, simple web UI',
                 'risk':'Protect existing owner files'}
        questions=[{'id':'audience','prompt':'Who will use the application?',
                    'options':['Individual','Team'],'recommended':'Individual'}]
        self.assertEqual(self.call('orbit_intake_propose',profile=profile,
                                  questions=questions,confirm_write=True)['status'],'PROPOSED')
        result=self.call('orbit_intake_approve',expected_revision=1,
                         answers={'audience':'Individual'},answer_source='user_choices',
                         user_reference='owner-confirmed-audience',confirm_write=True)
        self.assertEqual(result['status'],'APPROVED')

    def test_compact_bounds_and_no_bulk_memories(self):
        self.approve_intake()
        self.call('orbit_memory_save',key='unrelated-secret',kind='decision',
                  summary='Do not retrieve this unrelated global memory token: PRIVATE-LEGACY-SECRET',
                  source='local',confirm_write=True)
        self.call('orbit_research_source_save',source_key='ui-accessibility',
                  title='Accessibility testing reference',
                  url='https://example.com/accessibility',
                  tags=['accessibility','testing'],
                  note='A read-only reference, verify independently',
                  confirm_write=True)
        checkpoint=self.call('orbit_project_checkpoint',
             milestone='Prototype',gate='Accessibility check',last_step='Implemented navigation',
             last_result='IN_PROGRESS',evidence='Host reported local implementation',
             next_step='Test keyboard interactions',blockers='Needs verified keyboard QA',
             expected_revision='MISSING',confirm_write=True)
        self.assertEqual(checkpoint['status'],'SAVED')
        request={'compact':True,'objective':'Test accessibility keyboard navigation'}
        compact=self.call('orbit_project_resume',**request)
        self.assertEqual(compact['status'],'COMPACT_PROJECT_CONTEXT')
        self.assertFalse(compact['notion_synced'])
        self.assertFalse(compact['data_written'])
        self.assertEqual(compact['accepted_intake']['status'],'OWNER_APPROVAL_REPORTED')
        self.assertEqual(compact['checkpoint']['managed_fields']['Next step'],
                         'Test keyboard interactions')
        self.assertTrue(compact['research_pointers'])
        self.assertNotIn('PRIVATE-LEGACY-SECRET',json.dumps(compact))
        self.assertNotIn('other projects',json.dumps(compact).lower())
        self.assertLessEqual(len(json.dumps(compact,ensure_ascii=True)),1800)
        full=self.call('orbit_project_resume')
        self.assertIn('memories',full)
        self.assertNotIn('data_written',full)
        self.assertGreater(len(json.dumps(full,ensure_ascii=True)),
                           len(json.dumps(compact,ensure_ascii=True)))

    def test_small_budget_and_emoji_escaping_never_exceed_cap(self):
        self.approve_intake()
        for budget in (900,1000,1200,3500):
            with self.subTest(budget=budget):
                packet=self.call('orbit_project_resume',compact=True,
                                 objective='🧭🚀'*250,max_chars=budget)
                self.assertEqual(packet['status'],'COMPACT_PROJECT_CONTEXT')
                self.assertLessEqual(len(json.dumps(packet,ensure_ascii=True,separators=(',',':'))),budget)
                self.assertTrue(packet['objective_truncated'])
        with self.assertRaises(ValueError):
            self.call('orbit_project_resume',compact=True,max_chars=899)
        with self.assertRaises(ValueError):
            self.call('orbit_project_resume',compact=True,max_chars=3501)

    def test_project_root_and_project_key_isolation(self):
        self.call('orbit_research_source_save',source_key='backend-cache',
                  title='Cache for backend project',
                  url='https://example.com/backend-cache',
                  tags=['backend','cache'],note='Scoped source',
                  confirm_write=True)
        other={**self.a,'project_root':str(self.other)}
        self.assertEqual(orbit_mcp.execute(self.conn,'orbit_project_resume',
                         {**other,'compact':True,'objective':'backend cache'})['status'],
                         'COMPACT_PROJECT_CONTEXT')
        missing=orbit_mcp.execute(self.conn,'orbit_project_resume',
                      {**other,'compact':True,'objective':'backend cache'})
        self.assertNotIn('research_pointers',missing)
        same_root_different_project=self.call('orbit_project_resume',project='different',
                                              compact=True,objective='backend cache')
        self.assertNotIn('research_pointers',same_root_different_project)
        selected=self.call('orbit_project_resume',compact=True,
                           objective='backend cache',max_chars=3500)
        self.assertIn('research_pointers',selected)
        self.assertEqual(selected['research_pointers'][0]['key'],'backend-cache')

    def test_unmanaged_or_wrong_project_checkpoint_not_trusted(self):
        target=self.root/'.orbit'
        target.mkdir()
        (target/'STATE.md').write_text('OWNER DOCUMENT: do not treat this as an Orbit checkpoint')
        result=self.call('orbit_project_resume',compact=True,max_chars=2500)
        self.assertIn('not recognized',result['checkpoint']['warning'])
        content='\n'.join((orbit_mcp.START,'Project: other-project',
                            'Milestone: SECRET-IN-OTHER-PROJECT',
                            'Next step: Do not copy unrelated checkpoint',orbit_mcp.END))
        (target/'STATE.md').write_text(content)
        result=self.call('orbit_project_resume',compact=True,max_chars=2500)
        self.assertIn('does not match',result['checkpoint']['warning'])
        self.assertNotIn('SECRET-IN-OTHER-PROJECT',json.dumps(result))
        self.assertNotIn('managed_fields',result['checkpoint'])

    def test_no_database_or_file_writes_for_compact_read(self):
        before=self.conn.total_changes
        files=list(self.root.rglob('*'))
        result=self.call('orbit_project_resume',compact=True,objective='resume')
        self.assertEqual(result['status'],'COMPACT_PROJECT_CONTEXT')
        self.assertEqual(before,self.conn.total_changes)
        self.assertEqual(files,list(self.root.rglob('*')))
        self.assertNotIn('memories',result)
        self.assertNotIn('raw_checkpoint',result)


if __name__=='__main__':
    unittest.main()
