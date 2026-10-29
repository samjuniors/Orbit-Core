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
        base=Path(self.temp.name).resolve()
        self.a=base/'old'; self.b=base/'new'
        self.a.mkdir(); self.b.mkdir()
        self.a=self.a.resolve(); self.b=self.b.resolve()
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
        row=self.db.execute('SELECT * FROM orbit_agent_tasks WHERE project_root=?',(str(self.b.resolve()),)).fetchone()
        self.assertEqual(row['approval_reference'],'')
        self.assertIn('IMPORTED_HISTORY',row['note'])
    def test_active_session_is_historical_and_blocked(self):
        self.db.execute("UPDATE orbit_agent_tasks SET status='RUNNING',host_session='old-session',approval_reference='old-approval'")
        raw=self.export()['bundle']; p=self.imp(raw)
        self.imp(raw,confirm_write=True,expected_revision=p['bundle_revision'])
        row=self.db.execute('SELECT * FROM orbit_agent_tasks WHERE project_root=?',(str(self.b.resolve()),)).fetchone()
        self.assertEqual(row['status'],'BLOCKED'); self.assertEqual(row['host_session'],'old-session')
        self.assertEqual(row['approval_reference'],'')
    def test_imported_unknown_attempt_date_never_counts_as_todays_host_execution(self):
        import orbit_tasks
        reserve=m.execute(self.db,'orbit_task_reserve',{
            **self.base,'task_key':'todo','expected_revision':1,
            'approval_reference':'approved-source-host-12345','confirm_write':True})
        self.assertEqual(reserve['status'],'RESERVED')
        m.execute(self.db,'orbit_task_started',{
            **self.base,'task_key':'todo','expected_revision':2,
            'host_session':'historical-source-session-12345','confirm_write':True})
        exported=self.export()
        packet=self.imp(exported['bundle'])
        self.assertEqual(self.imp(exported['bundle'],
            expected_revision=packet['bundle_revision'],confirm_write=True)['status'],'IMPORTED')
        current=self.db.execute("SELECT status,host_session,reserved_at,revision FROM orbit_agent_tasks WHERE project_root=?",
            (str(self.b),)).fetchone()
        self.assertEqual(current['status'],'BLOCKED')
        self.assertEqual(current['reserved_at'],'')
        self.assertEqual(current['host_session'],'historical-source-session-12345')
        retry=m.execute(self.db,'orbit_task_reserve',{
            'project_root':str(self.b),'project':'lab','task_key':'todo',
            'expected_revision':current['revision'],
            'approval_reference':'approved-destination-host-12345','confirm_write':True})
        self.assertEqual(retry['status'],'RESERVED')
        self.assertEqual(retry['attempt_number'],2)
        self.assertEqual(retry['attempt_budget']['step_used'],2)
        self.assertEqual(retry['attempt_budget']['day_used'],1)
        past=self.db.execute("""SELECT reserved_at,disposition,host_session FROM orbit_task_attempts
             WHERE project_root=? AND task_key='todo' AND attempt_number=1""",(str(self.b),)).fetchone()
        self.assertEqual(past['reserved_at'],'')
        self.assertEqual(past['disposition'],'LEGACY_UNVERIFIED')
        self.assertEqual(past['host_session'],'historical-source-session-12345')
        self.assertEqual(orbit_tasks._attempt_usage(self.db,'lab',self.b,'Build',
            orbit_tasks.utc_now()[:10]),(2,1))
        self.assertEqual(retry['task']['host_session'],'')

    def test_reject_project_and_malicious_scopes_without_writes(self):
        packet=json.loads(self.export()['bundle'])
        packet['project']='other'
        with self.assertRaises(ValueError): self.imp(json.dumps(packet))
        packet['project']='lab';packet['tasks'][0]['write_paths']='["../secret"]'
        with self.assertRaises(ValueError): self.imp(json.dumps(packet),confirm_write=True)
        self.assertEqual(self.db.execute('SELECT count(*) FROM orbit_agent_tasks WHERE project_root=?',(str(self.b.resolve()),)).fetchone()[0],0)
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

    def test_partial_database_counts_do_not_swallow_unrelated_sqlite_errors(self):
        import orbit_portable
        partial=sqlite3.connect(':memory:')
        self.addCleanup(partial.close)
        self.assertEqual(orbit_portable.counts(partial,self.b,'lab'),
                         {'tasks':0,'research':0})
        self.assertEqual(partial.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0],0)
        # Only a truly missing table is treated as absent. A corrupt or older
        # incompatible schema must be diagnosed, not reported as zero records.
        partial.execute('CREATE TABLE orbit_agent_tasks(project_root TEXT)')
        with self.assertRaises(sqlite3.OperationalError):
            orbit_portable.counts(partial,self.b,'lab')

    def test_uninitialized_database_counts_and_transfer(self):
        import orbit_portable
        empty_db=sqlite3.connect(':memory:')
        self.addCleanup(empty_db.close)
        self.assertEqual(orbit_portable.counts(empty_db,self.a,'lab'),{'tasks':0,'research':0})
        packet=m.execute(empty_db,'orbit_project_transfer',{**self.base,'action':'export'})
        self.assertEqual(packet['status'],'EXPORT_READY')
