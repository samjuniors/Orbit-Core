"""Durable product feedback and host artifact review experience."""
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source/runtime'))
import orbit_build, orbit_mcp, orbit_intake


class ProductFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name,'project')
        self.root.mkdir()
        self.root=self.root.resolve()
        self.db=sqlite3.connect(':memory:')
        self.db.row_factory=sqlite3.Row
        self.addCleanup(self.db.close)
        orbit_build.setup(self.db)
        orbit_intake.setup(self.db)
        self.db.execute("""CREATE TABLE memories (
            project TEXT, key TEXT, kind TEXT, summary TEXT, evidence TEXT,
            importance INTEGER, updated_at TEXT, status TEXT)""")
        self.db.commit()
        self.a={'project_root':str(self.root),'project':'product',
                'build_id':'app-1'}
        orbit_build.begin(self.db,self.root,{'project':'product','build_id':'app-1',
                         'objective':'Build reviewed product','confirm_write':True})

    def call(self,name,**options):
        args={**self.a,**options}
        if name=='orbit_project_resume':
            args.pop('build_id',None)
        return orbit_mcp.execute(self.db,name,args)

    def revision(self):
        return self.call('orbit_build_status')['run']['revision']

    def feedback(self,**options):
        return self.call('orbit_build_feedback',**options)

    def test_feedback_is_read_only_without_confirmation(self):
        original=self.revision()
        draft=self.feedback(action='request',expected_revision=original,
              source='plan',note='Please support offline use',
              user_reference='owner-comment-443')
        self.assertEqual(draft['status'],'PREVIEW_ONLY')
        self.assertEqual(original,self.revision())
        self.assertEqual(self.call('orbit_build_status')['experience']['open_feedback'],0)

    def test_requested_changes_block_stage_and_survive_resume(self):
        pending=self.feedback(action='request',expected_revision=self.revision(),
            source='plan',note='I want a custom calendar component',
            user_reference='antigravity-comment-17',confirm_write=True)
        self.assertEqual(pending['status'],'FEEDBACK_RECORDED')
        self.assertEqual(pending['open_feedback'],1)
        experience=self.call('orbit_build_status')['experience']
        self.assertEqual(experience['phase'],'CHANGES_REQUESTED')
        self.assertEqual(experience['open_feedback'],1)
        self.assertIn('custom calendar',experience['feedback'][0]['note'])
        self.assertEqual(self.call('orbit_project_resume')['experience']['phase'],'CHANGES_REQUESTED')
        evidence=json.dumps({'task':'Research UI','candidates':['native web APIs'],
            'decision':'Use native components','sources':['README.md'],
            'risks':['date boundaries']})
        blocked=self.call('orbit_build_advance',expected_revision=self.revision(),
                    outcome='PASS',evidence=evidence,confirm_write=True)
        self.assertEqual(blocked['status'],'HOLD')
        self.assertEqual(self.call('orbit_build_status')['run']['stage'],'RESEARCH')
        resolved=self.feedback(action='resolve',expected_revision=self.revision(),
            feedback_id='f1',resolution_evidence='Updated reviewed UI proposal and acceptance cases',
            confirm_write=True)
        self.assertEqual(resolved['status'],'FEEDBACK_RESOLVED')
        self.assertEqual(resolved['open_feedback'],0)
        self.assertEqual(self.call('orbit_build_status')['experience']['phase'],'BUILDING')
        done=self.call('orbit_build_advance',expected_revision=self.revision(),
                    outcome='PASS',evidence=evidence,confirm_write=True)
        self.assertEqual(done['status'],'ADVANCED')
        self.assertEqual(done['run']['stage'],'PLAN')
        history=done['run']['evidence']['__orbit_feedback']
        self.assertEqual(history[0]['status'],'RESOLVED')


    def test_comment_deduplication_does_not_advance_revision(self):
        version=self.revision()
        kwargs={'action':'request','source':'plan','note':'Add a keyboard accessible filter',
                'user_reference':'antigravity-comment-77','confirm_write':True}
        self.assertEqual(self.feedback(expected_revision=version,**kwargs)['status'],
                         'FEEDBACK_RECORDED')
        fresh=self.revision()
        dupe=self.feedback(expected_revision=fresh,**kwargs)
        self.assertEqual(dupe['status'],'ALREADY_RECORDED')
        self.assertEqual(self.revision(),fresh)
        self.assertEqual(self.call('orbit_build_status')['experience']['open_feedback'],1)

    def test_explicit_build_selection_does_not_ask_again(self):
        orbit_build.begin(self.db,self.root,{'project':'product','build_id':'second',
                          'objective':'Another parallel product','confirm_write':True})
        unresolved=self.call('orbit_project_resume')['experience']
        self.assertEqual(unresolved['phase'],'CHOOSE_BUILD')
        selected=self.call('orbit_build_status')['experience']
        self.assertEqual(selected['phase'],'BUILDING')
        self.assertEqual(selected['progress']['build_id'],'app-1')
        self.assertEqual(selected['progress']['stage'],'RESEARCH')
        self.assertFalse(selected['approval_required'])
        self.assertIn('Research',selected['next_action']['label'])

    def test_stale_revision_and_unknown_feedback_never_overwrite(self):
        prior=self.revision()
        first=self.feedback(action='request',expected_revision=prior,note='Change input behavior',
            user_reference='owner-review-comment-21',confirm_write=True)
        self.assertEqual(first['status'],'FEEDBACK_RECORDED')
        stale=self.feedback(action='request',expected_revision=prior,note='Change typography',
            user_reference='owner-review-comment-22',confirm_write=True)
        self.assertEqual(stale['status'],'STALE_REVISION')
        invalid=self.feedback(action='resolve',expected_revision=self.revision(),
            feedback_id='not-found',resolution_evidence='Updated and tested behavior',
            confirm_write=True)
        self.assertEqual(invalid['status'],'HOLD')
        self.assertEqual(self.call('orbit_build_status')['experience']['open_feedback'],1)

    def test_plan_feedback_requires_resolve_and_real_plan_approval(self):
        evidence=json.dumps({'task':'Build app UI','candidates':['native web APIs'],
            'decision':'Use trusted existing components','sources':['README.md'],
            'risks':['persisting data']})
        self.call('orbit_build_advance',expected_revision=1,outcome='PASS',
                  evidence=evidence,confirm_write=True)
        self.assertEqual(self.call('orbit_build_status')['run']['stage'],'PLAN')
        note=self.feedback(action='request',expected_revision=self.revision(),
            source='plan',note='Add a search filter to the plan',
            user_reference='antigravity-artifact-comment-11',confirm_write=True)
        self.assertEqual(note['status'],'FEEDBACK_RECORDED')
        plan=json.dumps({'title':'Approved product application',
            'summary':'An application with searchable user content',
            'tasks':['Build search UI','Add filters and regression tests'],
            'approval_method':'user_approved_plan','approval_reference':'owner-clicked-proceed-17'})
        self.assertEqual(self.call('orbit_build_advance',expected_revision=self.revision(),
                         outcome='PASS',evidence=plan,confirm_write=True)['status'],'HOLD')
        self.assertEqual(self.feedback(action='resolve',expected_revision=self.revision(),
            feedback_id='f1',resolution_evidence='Updated native plan artifact revision 2',
            confirm_write=True)['status'],'FEEDBACK_RESOLVED')
        wrong=self.call('orbit_build_advance',expected_revision=self.revision(),
                  outcome='PASS',evidence='The plan looks good',confirm_write=True)
        self.assertEqual(wrong['status'],'HOLD')
        accepted=self.call('orbit_build_advance',expected_revision=self.revision(),
                  outcome='PASS',evidence=plan,confirm_write=True)
        self.assertEqual(accepted['status'],'ADVANCED')
        self.assertEqual(self.call('orbit_build_status')['experience']['plan']['title'],
                         'Approved product application')


if __name__=='__main__':
    unittest.main()
