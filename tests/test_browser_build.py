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

    def advance(self,outcome='PASS'):
        status=orbit_build.current(self.db,self.root,self.meta)['run']
        return orbit_build.advance(self.db,self.root,{**self.meta,'expected_revision':status['revision'],'outcome':outcome,'evidence':'Verified by test run','preview_id':'browser-test','confirm_write':True})

    def test_durable_build_revision_and_qa_gate(self):
        a={**self.meta,'objective':'Create a Todo web app','confirm_write':True}
        self.assertEqual(orbit_build.begin(self.db,self.root,a)['status'],'CREATED')
        self.assertEqual(orbit_build.begin(self.db,self.root,a)['status'],'EXISTS')
        self.assertEqual(self.advance()['run']['stage'],'IMPLEMENT')
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
        with self.db:
            self.db.execute('INSERT INTO browser_results(project,root,build_id,status,summary,created_at) VALUES (?,?,?,?,?,?)',
                            ('todo-test',str(self.root),'test-app','PASS','{"actions":[{"status":"PASS"}]}','now'))
        self.assertEqual(self.advance()['run']['stage'],'REVIEW')
        self.assertEqual(self.advance()['run']['stage'],'CHECKPOINT')
        self.assertEqual(self.advance()['status'],'HOLD')
        cp=self.root/'.orbit'/'STATE.md';cp.parent.mkdir()
        cp.write_text('<!-- ORBIT_NATIVE_CHECKPOINT_START -->\nVerified via tests\n<!-- ORBIT_NATIVE_CHECKPOINT_END -->\n')
        self.assertEqual(self.advance()['run']['stage'],'DONE')
        self.assertEqual(self.advance()['status'],'ALREADY_DONE')

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
        for _ in range(2): self.advance()
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
