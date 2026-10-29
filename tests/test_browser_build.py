"""Durable build state and real (if present) headless browser QA tests."""
from __future__ import annotations
import os
import importlib.util
import shutil
import socket
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source/runtime'))
import orbit_build,orbit_browser,orbit_preview,orbit_mcp

TODO_PAGE='''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Orbit Todo Lab</title></head>
<body><h1>Todo Lab</h1><label>New task<input id="todo" aria-label="New task"></label><button id="add">Add</button>
<ul id="items"></ul><script>
const tasks=[]; document.querySelector('#add').onclick=()=>{const name=document.querySelector('#todo').value.trim();if(!name)return;
tasks.push(name); let li=document.createElement('li');li.textContent=name;document.querySelector('#items').append(li);
document.querySelector('#todo').value='';};
</script></body></html>'''

class BuildBrowserTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'todo';self.root.mkdir()
        (self.root/'index.html').write_text(TODO_PAGE)
        self.db=sqlite3.connect(str(Path(self.temp.name)/'state.sqlite'))
        self.db.row_factory=sqlite3.Row
        self.addCleanup(self.db.close)
        orbit_build.setup(self.db);orbit_build.setup_browser(self.db)
        self.meta={'project':'todo-test','build_id':'test-app'}
        self.env=os.environ.get('ORBIT_QA_HOME')
        os.environ['ORBIT_QA_HOME']=str(Path(self.temp.name)/'qa')
        self.addCleanup(lambda:os.environ.pop('ORBIT_QA_HOME',None) if self.env is None else os.environ.__setitem__('ORBIT_QA_HOME',self.env))
        with socket.socket() as s:
            s.bind(('127.0.0.1',0));self.port=s.getsockname()[1]
        self.pa={'preview_id':'browser-test','port':self.port,'command':[sys.executable,'-m','http.server',str(self.port),'--bind','127.0.0.1']}
        self.addCleanup(lambda:orbit_preview.stop(self.root,{'preview_id':'browser-test','confirm_stop':True}))

    def stage_evidence(self,stage):
        if stage=='RESEARCH':
            return '{"task":"Build tested todo product","candidates":["native HTML UI","existing SQLite"],"decision":"Reuse native tools and test existing code", "sources":["README.md"],"risks":["bad user data"]}'
        if stage=='PLAN':
            return '{"title":"Build Todo application","summary":"Single-user accessible todo CRUD with local testing","tasks":["Implement a local task model","Create semantic accessible task UI","Run acceptance and regression checks"],"approval_method":"user_approved_plan","approval_reference":"user-confirmed-plan-message"}'
        if stage=='VERIFY':
            return '{"commands":[{"command":"python -m unittest discover","exit_code":0}],"edge_cases":["empty todo items"],"security":["untrusted input escaped"]}'
        return 'Verified by test run'

    def advance(self,outcome='PASS'):
        status=orbit_build.current(self.db,self.root,self.meta)['run']
        return orbit_build.advance(self.db,self.root,{**self.meta,'expected_revision':status['revision'],'outcome':outcome,'evidence':self.stage_evidence(status['stage']),'preview_id':'browser-test','confirm_write':True})

    def test_product_kit_style_recovery_is_read_only_and_bounded(self):
        project={**self.meta,'objective':'Build tested Todo','confirm_write':True}
        self.assertEqual(orbit_build.recovery_brief(self.db,self.root,self.meta['project'])['status'],'NO_BUILD')
        orbit_build.begin(self.db,self.root,project)
        first=orbit_build.recovery_brief(self.db,self.root,self.meta['project'])
        self.assertEqual(first['status'],'RESUME')
        self.assertEqual(first['stage'],'RESEARCH')
        self.assertEqual(first['revision'],1)
        self.assertEqual(first['task_progress']['registered'],0)
        self.assertIn('research',first['next'].lower())
        self.assertEqual(orbit_build.current(self.db,self.root,self.meta)['run']['revision'],1)
        # Distinct unfinished builds require explicit selection, not guessed work.
        second={**project,'build_id':'parallel'}
        orbit_build.begin(self.db,self.root,second)
        competing=orbit_build.recovery_brief(self.db,self.root,self.meta['project'])
        self.assertEqual(competing['status'],'NEEDS_BUILD_SELECTION')
        self.assertEqual(len(competing['builds']),2)

    def test_new_research_stage_requires_structured_evidence(self):
        a={**self.meta,'objective':'Create a Todo web app','confirm_write':True}
        orbit_build.begin(self.db,self.root,a)
        status=orbit_build.current(self.db,self.root,self.meta)['run']
        result=orbit_build.advance(self.db,self.root,{**self.meta,'expected_revision':status['revision'],
            'outcome':'PASS','evidence':'researched', 'confirm_write':True})
        self.assertEqual(result['status'],'HOLD')
        self.assertEqual(orbit_build.current(self.db,self.root,self.meta)['run']['stage'],'RESEARCH')

    def test_new_build_requires_real_approval_reference_before_implement(self):
        a={**self.meta,'objective':'Create Todo app','confirm_write':True}
        orbit_build.begin(self.db,self.root,a)
        self.advance() # RESEARCH -> PLAN
        state=orbit_build.current(self.db,self.root,self.meta)
        self.assertEqual(state['run']['stage'],'PLAN')
        self.assertEqual(state['task_progress']['registered'],0)
        attempt=orbit_build.advance(self.db,self.root,{**self.meta,
            'expected_revision':state['run']['revision'],'outcome':'PASS',
            'evidence':'Looks good to me','confirm_write':True})
        self.assertEqual(attempt['status'],'HOLD')
        self.assertEqual(orbit_build.current(self.db,self.root,self.meta)['run']['stage'],'PLAN')
        self.assertEqual(self.advance()['run']['stage'],'IMPLEMENT')

    def test_existing_plan_stage_is_compatible(self):
        with self.db:
            self.db.execute('INSERT INTO build_runs VALUES (?,?,?,?,?,?,?,?)',
                (self.meta['project'],str(self.root),self.meta['build_id'],'PLAN',1,'prior version','{}','now'))
        self.assertEqual(self.advance()['run']['stage'],'IMPLEMENT')

    def test_durable_build_revision_and_qa_gate(self):
        a={**self.meta,'objective':'Create a Todo web app','confirm_write':True}
        self.assertEqual(orbit_build.begin(self.db,self.root,a)['status'],'CREATED')
        self.assertEqual(orbit_build.begin(self.db,self.root,a)['status'],'EXISTS')
        self.assertEqual(self.advance()['run']['stage'],'PLAN')
        self.assertEqual(self.advance()['run']['stage'],'IMPLEMENT')
        self.assertEqual(self.advance()['run']['stage'],'VERIFY')
        self.assertEqual(self.advance()['run']['stage'],'PREVIEW')
        self.assertEqual(self.advance()['status'],'HOLD')
        self.assertEqual(orbit_preview.start(self.root,{**self.pa,'confirm_run':True})['status'],'READY')
        self.assertEqual(self.advance()['run']['stage'],'BROWSER_QA')
        self.assertEqual(self.advance()['status'],'HOLD')
        con2=sqlite3.connect(str(Path(self.temp.name)/'state.sqlite'))
        con2.row_factory=sqlite3.Row
        try:
            self.assertEqual(orbit_build.current(con2,self.root,self.meta)['run']['stage'],'BROWSER_QA')
        finally: con2.close()
        # Legacy rows without code/preview revision are not sufficient to pass M3 QA.
        with self.db:
            self.db.execute('INSERT INTO browser_results(project,root,build_id,status,summary,created_at) VALUES (?,?,?,?,?,?)',
                            ('todo-test',str(self.root),'test-app','PASS','{"actions":[{"status":"PASS"}]}','now'))
        self.assertEqual(self.advance()['status'],'HOLD')
        session=orbit_preview.SESSIONS[orbit_preview.preview_key(self.root,'browser-test')]
        orbit_build.save_browser(self.db,self.root,{**self.meta,'preview_id':'browser-test'},{
            'status':'PASS','actions':[{'status':'PASS','op':'expect_visible'}],
            'source_fingerprint':orbit_build.code_fingerprint(self.root),
            'preview_id':'browser-test','preview_started_at':session['started_at']})
        self.assertEqual(self.advance()['run']['stage'],'REVIEW')
        self.assertEqual(self.advance()['run']['stage'],'CHECKPOINT')
        self.assertEqual(self.advance()['status'],'HOLD')
        cp=self.root/'.orbit'/'STATE.md';cp.parent.mkdir()
        cp.write_text('<!-- ORBIT_NATIVE_CHECKPOINT_START -->\nVerified via tests\n<!-- ORBIT_NATIVE_CHECKPOINT_END -->\n')
        self.assertEqual(self.advance()['run']['stage'],'DONE')
        self.assertEqual(self.advance()['status'],'ALREADY_DONE')

    def make_browser_gate(self):
        orbit_build.begin(self.db,self.root,{**self.meta,'objective':'Todo QA','confirm_write':True})
        for _ in range(4):
            self.advance()
        self.assertEqual(orbit_preview.start(self.root,{**self.pa,'confirm_run':True})['status'],'READY')
        self.assertEqual(self.advance()['run']['stage'],'BROWSER_QA')
        return orbit_preview.SESSIONS[orbit_preview.preview_key(self.root,'browser-test')]

    def save_test_pass(self, session, actions=None):
        # Unit-only synthetic result; production results come from local Playwright.
        result={'status':'PASS','actions':actions or [{'status':'PASS','op':'expect_visible'}],
                'source_fingerprint':orbit_build.code_fingerprint(self.root),
                'preview_id':'browser-test','preview_started_at':session['started_at']}
        return orbit_build.save_browser(self.db,self.root,{**self.meta,'preview_id':'browser-test'},result)

    def test_m3_browser_qa_blocks_stale_source_even_if_build_revision_unchanged(self):
        session=self.make_browser_gate()
        original=(self.root/'index.html').read_text()
        self.save_test_pass(session)
        (self.root/'index.html').write_text(original+'\n<!-- changed after QA -->')
        stale=self.advance()
        self.assertEqual(stale['status'],'HOLD')
        self.assertIn('stale',stale['reason'].lower())
        self.assertEqual(orbit_build.current(self.db,self.root,self.meta)['run']['stage'],'BROWSER_QA')
        # Rerunning QA at the new source snapshot releases the gate.
        self.save_test_pass(session)
        self.assertEqual(self.advance()['run']['stage'],'REVIEW')

    def test_m3_qa_rejects_changed_preview_generation(self):
        session=self.make_browser_gate()
        self.save_test_pass(session)
        original=session['started_at']
        session['started_at']=original+1
        try:
            self.assertEqual(self.advance()['status'],'HOLD')
            self.assertIn('generation',self.advance()['reason'].lower())
            self.save_test_pass(session)
            self.assertEqual(self.advance()['run']['stage'],'REVIEW')
        finally:
            session['started_at']=original

    def test_m3_failed_steps_and_missing_snapshot_cannot_claim_pass(self):
        session=self.make_browser_gate()
        self.assertEqual(self.advance()['status'],'HOLD')
        with self.assertRaises(ValueError):
            orbit_build.save_browser(self.db,self.root,{**self.meta,'preview_id':'browser-test'},{
                'status':'PASS','actions':[{'status':'PASS'}],'preview_id':'browser-test',
                'preview_started_at':session['started_at']})
        self.save_test_pass(session,[{'status':'FAIL','op':'expect_visible'}])
        self.assertEqual(self.advance()['status'],'HOLD')
        self.save_test_pass(session)
        self.assertEqual(self.advance()['run']['stage'],'REVIEW')

    def test_m3_source_fingerprint_rejects_symlinked_code(self):
        first=orbit_build.code_fingerprint(self.root)
        self.assertEqual(len(first),64)
        (self.root/'.orbit').mkdir()
        (self.root/'.orbit'/'STATE.md').write_text('checkpoint updated')
        self.assertEqual(first,orbit_build.code_fingerprint(self.root))
        (self.root/'new.js').write_text('console.log(1)')
        self.assertNotEqual(first,orbit_build.code_fingerprint(self.root))
        link=self.root/'linked.css'
        try:
            link.symlink_to(self.root/'new.js')
        except (OSError,NotImplementedError):
            self.skipTest('Symlinks unavailable on this host')
        self.assertIsNone(orbit_build.code_fingerprint(self.root))

    def test_branded_browser_choices_and_no_download(self):
        from unittest.mock import patch
        edge = Path(self.temp.name) / 'program-files' / 'Microsoft' / 'Edge' / 'Application' / 'msedge.exe'
        edge.parent.mkdir(parents=True)
        edge.write_bytes(b'fake edge binary for discovery only; never execute')
        env={'PROGRAMFILES': str(Path(self.temp.name) / 'program-files')}
        with patch('orbit_browser.shutil.which', return_value=None):
            self.assertTrue(orbit_browser.installed_channel('msedge', windows=True, env=env))
            self.assertFalse(orbit_browser.installed_channel('chrome', windows=True, env=env))
            self.assertFalse(orbit_browser.installed_channel('chrome', windows=False, env=env))
            self.assertEqual(orbit_browser.browser_launch('msedge'),
                             ({'headless':True, 'channel':'msedge'},'msedge'))
            self.assertEqual(orbit_browser.browser_launch('chrome'),
                             ({'headless':True, 'channel':'chrome'},'chrome'))
            with self.assertRaises(ValueError): orbit_browser.browser_launch('javascript://remote')
            with patch('orbit_browser.installed_channel', side_effect=lambda channel: channel=='msedge'):
                self.assertEqual(orbit_browser.browser_launch('auto')[1],'msedge')
            with patch('orbit_browser.installed_channel', return_value=False):
                self.assertEqual(orbit_browser.browser_launch('auto')[1],'playwright-chromium')
        schema=orbit_mcp.TOOL_MAP['orbit_browser_qa']
        self.assertIn('browser', schema['properties'])
        self.assertEqual(schema['properties']['browser']['enum'], ['auto','msedge','chrome','chromium'])

    def test_m34_preview_network_origin_is_exact(self):
        allowed=orbit_browser.approved_preview_origin
        for url in ('http://127.0.0.1:49152/','http://127.0.0.1:49152/api?x=1',
                    'http://127.0.0.1:49152/#dashboard'):
            self.assertTrue(allowed(url,49152),url)
        for url in ('http://127.0.0.1:49153/',
                    'http://127.0.0.1:80/',
                    'http://localhost:49152/',
                    'http://[::1]:49152/',
                    'https://127.0.0.1:49152/',
                    'http://127.0.0.2:49152/',
                    'http://127.0.0.1.evil.example:49152/',
                    'http://user:password@127.0.0.1:49152/',
                    'file:///etc/passwd',
                    'http://[::1'):
            with self.subTest(url=url):
                self.assertFalse(allowed(url,49152))
        self.assertTrue(allowed('ws://127.0.0.1:49152/notifications',49152,websocket=True))
        for url in ('wss://127.0.0.1:49152/ws','ws://127.0.0.1:49153/ws',
                    'ws://localhost:49152/ws','ws://remote.example/ws'):
            with self.subTest(url=url):
                self.assertFalse(allowed(url,49152,websocket=True))

    def test_m34_http_routes_allow_only_preview_and_inline_resources(self):
        class FakeRoute:
            def __init__(self,url):
                self.request=type('Request',(),{'url':url})()
                self.action=None
            def continue_(self): self.action='continue'
            def abort(self): self.action='abort'
        blocked=[]
        for url in ('http://127.0.0.1:49152/styles.css','data:text/plain,hello',
                    'blob:http://127.0.0.1:49152/object','about:blank'):
            route=FakeRoute(url)
            orbit_browser.route_preview_request(route,49152,blocked)
            self.assertEqual(route.action,'continue',url)
        for url in ('http://127.0.0.1:49153/secret','http://localhost:49152/',
                    'https://127.0.0.1:49152/','https://public.example/script.js',
                    'file:///etc/passwd'):
            route=FakeRoute(url)
            orbit_browser.route_preview_request(route,49152,blocked)
            self.assertEqual(route.action,'abort',url)
        self.assertEqual(len(blocked),5)
        self.assertIn('127.0.0.1',blocked)
        self.assertIn('public.example',blocked)

    def test_m34_websocket_route_never_connects_to_other_services(self):
        class FakeSocket:
            def __init__(self,url):
                self.url=url;self.connected=False;self.closed=None
            def connect_to_server(self): self.connected=True
            def close(self,**kwargs): self.closed=kwargs
        blocked=[]
        good=FakeSocket('ws://127.0.0.1:49152/updates')
        orbit_browser.route_preview_socket(good,49152,blocked)
        self.assertTrue(good.connected)
        self.assertIsNone(good.closed)
        for url in ('ws://127.0.0.1:49153/admin','ws://localhost:49152/',
                    'wss://remote.example/socket'):
            route=FakeSocket(url)
            orbit_browser.route_preview_socket(route,49152,blocked)
            self.assertFalse(route.connected)
            self.assertEqual(route.closed['code'],1008)
        self.assertEqual(len(blocked),3)

    def test_browser_input_validation(self):
        with self.assertRaises(ValueError):orbit_browser.validate_actions([{'op':'evaluate','selector':'body','value':'fetch()'}])
        with self.assertRaises(ValueError):orbit_browser.validate_actions([{'op':'click','selector':''}])
        self.assertEqual(orbit_build.begin(self.db,self.root,{**self.meta,'objective':'Todo','confirm_write':False})['status'],'PREVIEW_ONLY')
        self.assertEqual(orbit_build.current(self.db,self.root,self.meta)['status'],'NOT_FOUND')

    @unittest.skipUnless(importlib.util.find_spec('playwright') and (shutil.which('chromium') or shutil.which('google-chrome')), 'Playwright and system Chromium both required for optional browser test')
    def test_real_browser_dom_without_network(self):
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            binary=shutil.which('chromium') or shutil.which('google-chrome')
            browser=p.chromium.launch(executable_path=binary,headless=True)
            try:
                page=browser.new_page()
                page.set_content(TODO_PAGE)
                page.locator('#todo').fill('Real DOM interaction')
                page.locator('#add').click()
                self.assertEqual(page.locator('#items li').inner_text(),'Real DOM interaction')
            finally: browser.close()

    @unittest.skipUnless(importlib.util.find_spec('playwright') and (shutil.which('chromium') or shutil.which('google-chrome')), 'Playwright and system Chromium both required for optional browser test')
    def test_real_chromium_todo_interaction_and_screenshot(self):
        orbit_build.begin(self.db,self.root,{**self.meta,'objective':'Todo','confirm_write':True})
        for _ in range(4): self.advance()
        self.assertEqual(orbit_preview.start(self.root,{**self.pa,'confirm_run':True})['status'],'READY')
        self.advance()
        inputs={**self.meta,'preview_id':'browser-test','viewport':'mobile',
                'actions':[{'op':'fill','selector':'#todo','value':'Finish browser QA'},
                           {'op':'click','selector':'#add'},
                           {'op':'expect_text','selector':'#items li','value':'Finish browser QA'},
                           {'op':'expect_count','selector':'#items li','value':1}]}
        self.assertEqual(orbit_browser.run(self.root,inputs,orbit_preview)['status'],'PREVIEW_ONLY')
        self.assertEqual(orbit_browser.run(self.root,{**inputs,'confirm_run':True},orbit_preview)['status'],'INTERACTIONS_NEED_APPROVAL')
        result=orbit_browser.run(self.root,{**inputs,'confirm_run':True,'confirm_interactions':True},orbit_preview)
        if result['status']=='FAIL' and any('ERR_BLOCKED_BY_ADMINISTRATOR' in x.get('message','') for x in result['failures']):
            self.skipTest('Managed Chromium blocks localhost in this runner; verify in native IDE')
        self.assertEqual(result['status'],'PASS',result)
        self.assertTrue(Path(result['screenshot']).is_file())
        self.assertEqual(len(result['actions']),4)
        orbit_build.save_browser(self.db,self.root,self.meta,result)
        self.assertEqual(self.advance()['run']['stage'],'REVIEW')

if __name__=='__main__':unittest.main()
