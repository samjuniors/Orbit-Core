import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source/runtime'))
import orbit_mcp as m

class PortableTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.a=Path(self.temp.name)/'old'; self.b=Path(self.temp.name)/'new'
        self.a.mkdir(); self.b.mkdir()
        self.db=sqlite3.connect(':memory:'); self.db.row_factory=sqlite3.Row
        self.addCleanup(self.db.close)
        import orbit_tasks, orbit_evidence
        orbit_tasks.setup(self.db); orbit_evidence.setup(self.db)
        self.base={'project_root':str(self.a),'project':'lab'}
        m.execute(self.db,'orbit_research_source_save',{**self.base,'source_key':'ecc','url':'https://github.com/affaan-m/ECC','title':'Agent memory','tags':['memory'],'note':'Research pointer','confirm_write':True})
        m.execute(self.db,'orbit_task_plan',{**self.base,'task_key':'todo','step':'Build','role':'frontend','goal':'Build a minimal Todo application','reason':'Test portable project continuation','write_paths':['app.js'],'confirm_write':True})
    def export(self):
        return m.execute(self.db,'orbit_project_transfer',{**self.base,'action':'export'})
    def imp(self,bundle,**kw):
        return m.execute(self.db,'orbit_project_transfer',{'project_root':str(self.b),'project':'lab','action':'import','bundle':bundle,**kw})
    def test_roundtrip_preview_conflicts_and_recall(self):
        packet=self.export(); raw=packet['bundle']
        self.assertNotIn(str(self.a),raw)
        preview=self.imp(raw)
        self.assertEqual(preview['status'],'PREVIEW_ONLY')
        self.assertEqual(self.imp(raw,confirm_write=True,expected_revision='0'*64)['status'],'STALE_REVISION')
        self.assertEqual(self.imp(raw,confirm_write=True,expected_revision=preview['bundle_revision'])['status'],'IMPORTED')
        self.assertEqual(self.imp(raw)['status'],'CONFLICT')
        result=m.execute(self.db,'orbit_research_context',{'project_root':str(self.b),'project':'lab','objective':'memory'})
        self.assertEqual(result['status'],'RELEVANT_REFERENCES')
        row=self.db.execute('SELECT * FROM orbit_agent_tasks WHERE project_root=?',(str(self.b),)).fetchone()
        self.assertEqual(row['approval_reference'],'')
        self.assertIn('IMPORTED_HISTORY',row['note'])
    def test_active_session_is_historical_and_blocked(self):
        self.db.execute("UPDATE orbit_agent_tasks SET status='RUNNING',host_session='old-session',approval_reference='old-approval'")
        raw=self.export()['bundle']; p=self.imp(raw)
        self.imp(raw,confirm_write=True,expected_revision=p['bundle_revision'])
        row=self.db.execute('SELECT * FROM orbit_agent_tasks WHERE project_root=?',(str(self.b),)).fetchone()
        self.assertEqual(row['status'],'BLOCKED'); self.assertEqual(row['host_session'],'old-session')
        self.assertEqual(row['approval_reference'],'')
    def test_reject_project_and_malicious_scopes_without_writes(self):
        packet=json.loads(self.export()['bundle'])
        packet['project']='other'
        with self.assertRaises(ValueError): self.imp(json.dumps(packet))
        packet['project']='lab';packet['tasks'][0]['write_paths']='["../secret"]'
        with self.assertRaises(ValueError): self.imp(json.dumps(packet),confirm_write=True)
        self.assertEqual(self.db.execute('SELECT count(*) FROM orbit_agent_tasks WHERE project_root=?',(str(self.b),)).fetchone()[0],0)
    def test_no_cross_project_export(self):
        packet=json.loads(self.export()['bundle'])
        self.assertEqual(len(packet['tasks']),1);self.assertEqual(len(packet['research']),1)
        self.assertFalse((self.a/'.orbit').exists())

    def test_checkpoint_only_resume_on_new_pc(self):
        from unittest.mock import patch
        (self.b/'.orbit').mkdir()
        (self.b/'.orbit'/'STATE.md').write_text('Project: lab\nNext: Continue existing Todo',encoding='utf-8')
        with patch.dict('os.environ',{'ORBIT_LOCAL_DB':str(Path(self.temp.name)/'fresh.sqlite3')}):
            fresh=m.db_connect()
            try:
                with patch.object(m.orbit_updates,'notice',return_value={'status':'CURRENT'}):
                    r=m.execute(fresh,'orbit_project_resume',{'project_root':str(self.b),'project':'lab'})
                self.assertEqual(r['continuity']['status'],'CHECKPOINT_ONLY_LOCAL_CONTEXT_MISSING')
                self.assertEqual(r['continuity']['local_records'],{'tasks':0,'research':0})
                raw=self.export()['bundle']; p=m.execute(fresh,'orbit_project_transfer',{'project_root':str(self.b),'project':'lab','action':'import','bundle':raw})
                r=m.execute(fresh,'orbit_project_transfer',{'project_root':str(self.b),'project':'lab','action':'import','bundle':raw,'confirm_write':True,'expected_revision':p['bundle_revision']})
                self.assertEqual(r['status'],'IMPORTED')
            finally: fresh.close()

    def test_uninitialized_database_counts_and_transfer(self):
        import orbit_portable
        empty_db=sqlite3.connect(':memory:')
        self.addCleanup(empty_db.close)
        self.assertEqual(orbit_portable.counts(empty_db,self.a,'lab'),{'tasks':0,'research':0})
        packet=m.execute(empty_db,'orbit_project_transfer',{**self.base,'action':'export'})
        self.assertEqual(packet['status'],'EXPORT_READY')
