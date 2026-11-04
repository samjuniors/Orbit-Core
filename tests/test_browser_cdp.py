"""Security and protocol regression coverage for opt-in isolated installed browser QA."""
from pathlib import Path
import json
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'source/runtime'))

import orbit_browser_cdp as native
import orbit_mcp


class NativeBrowserGuards(unittest.TestCase):
    def test_origin_is_exact_and_no_hostname_or_port_substitution(self):
        good = ('http://127.0.0.1:18765/',
                'http://127.0.0.1:18765/login',
                'http://127.0.0.1:18765/api/notes?max=5')
        for url in good:
            with self.subTest(url=url):
                self.assertTrue(native.allowed_http(url, 18765))
        bad = ('http://localhost:18765/', 'http://127.0.0.1:18766/',
               'https://127.0.0.1:18765/', 'http://127.0.0.2:18765/',
               'http://127.0.0.1.evil.test:18765/',
               'http://foo@127.0.0.1:18765/',
               'http://127.0.0.1:18765/#token',
               'http://127.0.0.1:0/', 'http://127.0.0.1:bad/',
               '//127.0.0.1:18765/', 'file:///etc/passwd',
               'javascript:alert(1)', 'ws://127.0.0.1:18765/')
        for url in bad:
            with self.subTest(url=url):
                self.assertFalse(native.allowed_http(url, 18765))

    def test_resources_are_passive_and_external_hosts_denied(self):
        self.assertTrue(native.allowed_resource('about:blank', 18765))
        self.assertTrue(native.allowed_resource('data:image/png;base64,AAAA', 18765))
        self.assertTrue(native.allowed_resource('blob:http://127.0.0.1:18765/x', 18765))
        self.assertFalse(native.allowed_resource('https://example.com/track', 18765))
        self.assertFalse(native.allowed_resource('http://127.0.0.1:8888/secret', 18765))
        self.assertFalse(native.allowed_resource('ws://127.0.0.1:18765/stream', 18765))

    def fake_client(self):
        client = native.CDP.__new__(native.CDP)
        client.app_port = 18765
        client.blocked = []
        client.errors = []
        client.dialogs = []
        client.commands = []
        client._send = lambda method, params: client.commands.append((method, params))
        return client

    def test_devtools_intercepts_redirects_and_external_requests(self):
        c = self.fake_client()
        for i, url in enumerate(('http://127.0.0.1:18765/app.js',
                                 'https://example.com/track',
                                 'http://127.0.0.1:4000/metadata',
                                 'https://example.com/redirected')):
            c._event({'method':'Fetch.requestPaused', 'params':{
                'requestId': str(i), 'request': {'url': url}}})
        self.assertEqual([x[0] for x in c.commands],
                         ['Fetch.continueRequest','Fetch.failRequest',
                          'Fetch.failRequest','Fetch.failRequest'])
        self.assertEqual(c.blocked, ['example.com','127.0.0.1','example.com'])
        self.assertTrue(all(x[1]['errorReason']=='BlockedByClient'
                            for x in c.commands[1:]))

    def test_transport_and_popup_are_rejected_and_logged(self):
        c = self.fake_client()
        c._event({'method':'Network.webSocketCreated','params':{
            'url':'ws://127.0.0.1:18765/ws'}})
        c._event({'method':'Page.javascriptDialogOpening','params':{}})
        c._event({'method':'Runtime.exceptionThrown','params':{}})
        self.assertEqual(c.blocked, ['unsupported-browser-transport-or-popup'])
        self.assertEqual(c.dialogs, ['unhandled-browser-dialog'])
        self.assertIn('uncaught-javascript-exception',c.errors)
        self.assertEqual(c.commands, [('Page.handleJavaScriptDialog',{'accept':False})])
        self.assertIn('serviceWorker', native.BLOCK_UNROUTABLE_JS)
        self.assertIn('WebSocket', native.BLOCK_UNROUTABLE_JS)
        self.assertIn('window.open', native.BLOCK_UNROUTABLE_JS)

    def test_no_explicit_other_engine_without_schema_opt_in(self):
        browser = orbit_mcp.TOOL_MAP['orbit_browser_qa']
        self.assertEqual(browser['properties']['engine']['enum'],
                         ['playwright','isolated-cdp'])
        self.assertEqual(len(orbit_mcp.TOOLS),47)

    def test_avoid_project_local_chrome_executable_in_host_path(self):
        # A browser named chrome.exe in a project-controlled PATH is ignored.
        with patch.dict(native.os.environ, {'PATH':'/malicious/project'},clear=False):
            self.assertIsNone(native.installed_executable('chrome',env={}))
        self.assertNotIn('shutil', native.installed_executable.__code__.co_names)

    def test_installed_browser_selection_is_fail_closed(self):
        self.assertIsNone(native.installed_executable('chromium',env={}))
        self.assertIsNone(native.installed_executable('chrome',env={}))
        self.assertIsNone(native.installed_executable('msedge',env={}))

    def test_selector_and_text_values_are_json_escaped_not_executed(self):
        malicious = "';window.alert('injected'); //"
        expression = native._script({'op':'fill','selector':malicious,
                                     'value':'x\";throw new Error(\"evil\");'})
        self.assertIn(json.dumps(malicious),expression)
        self.assertIn('dispatchEvent(new Event',expression)
        self.assertNotIn("querySelector('';",expression)
        self.assertIn("value",expression)

    def test_mouse_actions_dispatch_real_events(self):
        c = self.fake_client()
        c.evaluate = lambda expr: {'x':25,'y':35,'visible':True}
        c.call = lambda method, args: c.commands.append((method,args))
        native._execute(c, {'op':'click','selector':'#submit'}, 390, 844)
        self.assertEqual([x[1]['type'] for x in c.commands],
                         ['mousePressed','mouseReleased'])
        self.assertTrue(all(x[1]['x']==25 for x in c.commands))

    def test_native_key_list_is_bounded(self):
        c = self.fake_client()
        c.evaluate = lambda expr: True
        c.call = lambda method, args: c.commands.append((method,args))
        native._execute(c, {'op':'press','selector':'#query','value':'Enter'}, 390, 844)
        self.assertEqual([x[1]['type'] for x in c.commands],['keyDown','keyUp'])
        with self.assertRaisesRegex(native.BrowserUnavailable,'only Enter'):
            native._execute(c,{'op':'press','selector':'#query','value':'Control+Shift+P'},
                            390,844)

if __name__=='__main__':
    unittest.main()
