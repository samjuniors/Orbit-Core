import sqlite3,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source/runtime'))
import orbit_mcp,orbit_build,orbit_intake
P={'type':'web-app','complexity':'moderate','maturity':'prototype','goal':'Todo app','audience':'Personal','constraints':'Offline','stack':'SQLite','risk':'Normal'}
Q=[{'id':'target','prompt':'Who should use the app?','options':['Personal','Team'],'recommended':'Personal'}]
class TestIntake(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.root=Path(self.temp.name)/'todo';self.root.mkdir()
  self.db=sqlite3.connect(':memory:');self.db.row_factory=sqlite3.Row;self.addCleanup(self.db.close)
  orbit_build.setup(self.db);orbit_intake.setup(self.db)
  self.a={'project_root':str(self.root),'project':'todo'}
 def do(self,n,**kw):return orbit_mcp.execute(self.db,n,{**self.a,**kw})
 def test_new_build_is_blocked_until_accepted_interview(self):
  self.assertEqual(self.do('orbit_build_begin',build_id='first',objective='todo',confirm_write=True)['status'],'HOLD')
  self.assertEqual(self.do('orbit_intake_propose',profile=P,questions=Q)['status'],'PREVIEW_ONLY')
  x=self.do('orbit_intake_propose',profile=P,questions=Q,confirm_write=True)
  self.assertEqual(x['status'],'PROPOSED')
  self.assertEqual(self.do('orbit_build_begin',build_id='first',objective='todo',confirm_write=True)['status'],'HOLD')
  self.assertEqual(self.do('orbit_intake_approve',expected_revision=1,answers={'target':'Personal'},answer_source='user_choices',user_reference='user-chose-personal',confirm_write=True)['status'],'APPROVED')
  self.assertEqual(self.do('orbit_build_begin',build_id='first',objective='todo',confirm_write=True)['status'],'CREATED')
  self.assertEqual(self.do('orbit_build_begin',build_id='first',objective='todo',confirm_write=True)['status'],'EXISTS')
 def test_docs_can_be_created_later_and_autonomy_is_manual(self):
  self.do('orbit_intake_propose',profile=P,questions=Q,confirm_write=True)
  self.do('orbit_intake_approve',expected_revision=1,answers={'target':'Personal'},answer_source='user_delegated_defaults',user_reference='user-delegated-defaults',confirm_write=True)
  self.assertIn('vision',[x['purpose'] for x in self.do('orbit_docs_audit',signals=['api_change'])['gaps']])
  (self.root/'docs').mkdir();(self.root/'docs/VISION.md').write_text('Owner vision')
  self.assertNotIn('vision',[x['purpose'] for x in self.do('orbit_docs_audit')['gaps']])
  self.assertEqual(self.do('orbit_autonomy_review')['current'],'guided')
  self.assertEqual(self.do('orbit_autonomy_review',level='assisted',expected_revision=2,user_reference='owner-approved-assist',confirm_write=False)['status'],'PREVIEW_ONLY')
  self.assertEqual(self.do('orbit_intake_status')['autonomy'],'guided')
 def test_existing_build_not_retroactively_blocked(self):
  orbit_build.begin(self.db,self.root,{**self.a,'build_id':'legacy','objective':'existing','confirm_write':True})
  self.assertEqual(self.do('orbit_build_begin',build_id='legacy',objective='existing',confirm_write=True)['status'],'EXISTS')
if __name__=='__main__':unittest.main()
