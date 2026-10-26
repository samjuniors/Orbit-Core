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

 def test_incremental_question_tracks_prior_answer_and_requires_real_branch(self):
  x=self.do('orbit_intake_propose',profile=P,questions=Q,confirm_write=True)
  self.assertEqual(x['status'],'PROPOSED')
  second={'id':'storage','prompt':'Where should the personal data live?',
          'options':['Local only','Cloud sync'],'recommended':'Local only'}
  base={'question':second,'based_on_id':'target','based_on_choice':'Personal',
        'rationale':'Personal use permits offline storage without team accounts'}
  self.assertEqual(self.do('orbit_intake_followup',expected_revision=1,**base,confirm_write=True)['status'],'HOLD')
  a=self.do('orbit_intake_answer',expected_revision=1,question_id='target',choice='Personal',
            user_reference='user-answered-personal',confirm_write=True)
  self.assertEqual(a['status'],'ANSWER_RECORDED')
  self.assertEqual(self.do('orbit_intake_followup',expected_revision=1,**base,confirm_write=True)['status'],'STALE_REVISION')
  self.assertEqual(self.do('orbit_intake_followup',expected_revision=2,
            **{**base,'based_on_choice':'Team'},confirm_write=True)['status'],'HOLD')
  b=self.do('orbit_intake_followup',expected_revision=2,**base,confirm_write=True)
  self.assertEqual(b['status'],'FOLLOWUP_PROPOSED')
  self.assertEqual(b['intake']['questions'][-1]['based_on'],'target')
  with self.assertRaises(ValueError):
   self.do('orbit_intake_approve',expected_revision=3,answers={'target':'Team','storage':'Local only'},
           answer_source='user_choices',user_reference='user-approved-full-brief',confirm_write=True)
  self.assertEqual(self.do('orbit_intake_approve',expected_revision=3,
            answers={'target':'Personal','storage':'Local only'},answer_source='user_choices',
            user_reference='user-approved-full-brief',confirm_write=True)['status'],'APPROVED')
  self.assertEqual(self.do('orbit_build_begin',build_id='adaptive',objective='Habit',confirm_write=True)['status'],'CREATED')
 def test_freeform_answer_and_dependent_custom_question(self):
  x=self.do('orbit_intake_propose',profile=P,questions=Q,confirm_write=True)
  self.assertEqual(x['status'],'PROPOSED')
  self.assertEqual(self.do('orbit_intake_answer',expected_revision=1,question_id='target',
     choice='Custom',user_reference='user-wants-custom',confirm_write=True)['status'],'HOLD')
  custom='Offline Android and iOS app with voice-only interaction and our own habit card'
  a=self.do('orbit_intake_answer',expected_revision=1,question_id='target',
     choice=custom,user_reference='user-specified-custom-goal',confirm_write=True)
  self.assertEqual(a['status'],'ANSWER_RECORDED')
  self.assertEqual(a['choice_type'],'CUSTOM')
  self.assertEqual(a['intake']['answers']['target'],custom)
  follow={'id':'voice_access','prompt':'Should voice input work entirely offline?',
     'options':['Yes offline','Online acceptable'],'recommended':'Yes offline'}
  result=self.do('orbit_intake_followup',expected_revision=2,based_on_id='target',
     based_on_choice=custom,question=follow,rationale='An offline voice-only native app needs local speech APIs.',
     confirm_write=True)
  self.assertEqual(result['status'],'FOLLOWUP_PROPOSED')
  self.assertEqual(self.do('orbit_intake_approve',expected_revision=3,
     answers={'target':custom,'voice_access':'Yes offline'},answer_source='user_choices',
     user_reference='user-accepted-custom-voice-scope',confirm_write=True)['status'],'APPROVED')
  self.assertEqual(self.do('orbit_intake_status')['answers']['target'],custom)

 def test_custom_answers_cannot_be_silently_substituted_for_delegated_defaults(self):
  self.do('orbit_intake_propose',profile=P,questions=Q,confirm_write=True)
  with self.assertRaises(ValueError):
   self.do('orbit_intake_approve',expected_revision=1,answers={'target':'iOS custom native'},
      answer_source='user_delegated_defaults',user_reference='user-approved-defaults',confirm_write=True)

 def test_platform_router_custom_components_and_model_limits(self):
  self.assertEqual(self.do('orbit_decision_route')['status'],'NEEDS_PROJECT_CLASSIFICATION')
  self.do('orbit_intake_propose',profile=P,questions=Q,confirm_write=True)
  self.do('orbit_intake_approve',expected_revision=1,answers={'target':'Personal'},answer_source='user_choices',user_reference='user-picked-personal',confirm_write=True)
  web=self.do('orbit_decision_route',product_type='web-app',platforms=['web'],
              existing_stack='React 19 StyleX',component_preference='custom')
  self.assertEqual(web['status'],'RECOMMENDATION_ONLY')
  self.assertEqual(web['workflow_profile'],'web')
  self.assertTrue(web['custom_component_allowed'])
  self.assertEqual(next(x for x in web['candidates'] if x['id']=='astryx')['status'],'REVIEW_MATCH')
  android=self.do('orbit_decision_route',product_type='mobile-app',platforms=['android'],
                  existing_stack='Kotlin',component_preference='reuse')
  self.assertEqual(android['workflow_profile'],'native')
  self.assertIn('NATIVE_QA',android['recommended_stages'])
  self.assertNotIn('BROWSER_QA',android['recommended_stages'])
  self.assertEqual(next(x for x in android['candidates'] if x['id']=='jetpack-compose')['status'],'REVIEW_MATCH')
  sdk=self.do('orbit_decision_route',product_type='sdk-library')
  self.assertNotIn('PREVIEW',sdk['recommended_stages'])
  self.assertNotIn('BROWSER_QA',sdk['recommended_stages'])
  self.assertFalse(any(x['id']=='astryx' for x in sdk['candidates']))
  easy=self.do('orbit_model_route',role='orbit-writer',task='documentation',host='claude-code',
              available_models=['Claude Opus 5.5','Claude Haiku 5.5','Claude Sonnet 5.5'],budget='economy')
  self.assertEqual(easy['recommended_model'],'Claude Haiku 5.5')
  self.assertTrue(easy['no_switch_executed'])
  deep=self.do('orbit_model_route',role='orbit-security',task='security',host='codex',
              available_models=['fast-small','deep-reasoning'],complexity='high-assurance',budget='quality')
  self.assertEqual(deep['desired_tier'],'deep')
  self.assertEqual(deep['recommended_model'],'deep-reasoning')
  unknown=self.do('orbit_model_route',role='orbit-frontend',task='implementation',host='antigravity')
  self.assertIsNone(unknown['recommended_model'])
  self.assertEqual(unknown['selection_status'],'INHERIT_HOST_MODEL')

 def test_native_mobile_build_skips_browser_only_gates(self):
  mobile={**P,'type':'mobile-app','stack':'Kotlin native Android'}
  self.do('orbit_intake_propose',profile=mobile,questions=Q,confirm_write=True)
  self.do('orbit_intake_approve',expected_revision=1,answers={'target':'Personal'},answer_source='user_choices',user_reference='approved-android-native',confirm_write=True)
  start=self.do('orbit_build_begin',build_id='android-app',objective='Android native UI',confirm_write=True)
  self.assertEqual(start['status'],'CREATED')
  flow=self.do('orbit_build_status',build_id='android-app')['stages']
  self.assertIn('NATIVE_QA',flow)
  self.assertNotIn('BROWSER_QA',flow)
  self.assertNotIn('PREVIEW',flow)

 def test_sdk_build_skips_ui_preview_and_qa_but_retains_verify(self):
  sdk={**P,'type':'sdk-library','stack':'Python 3.11 SDK'}
  self.do('orbit_intake_propose',profile=sdk,questions=Q,confirm_write=True)
  self.do('orbit_intake_approve',expected_revision=1,answers={'target':'Personal'},answer_source='user_choices',user_reference='approved-sdk-contract',confirm_write=True)
  self.do('orbit_build_begin',build_id='sdk',objective='Python SDK',confirm_write=True)
  flow=self.do('orbit_build_status',build_id='sdk')['stages']
  self.assertIn('VERIFY',flow)
  self.assertNotIn('PREVIEW',flow)
  self.assertNotIn('BROWSER_QA',flow)
  self.assertNotIn('NATIVE_QA',flow)

if __name__=='__main__':unittest.main()
