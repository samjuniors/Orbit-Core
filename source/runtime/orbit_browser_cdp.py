"""Opt-in dependency-free QA in a NEW isolated installed Chrome/Edge process.

This is NOT an attachment to the user's browser/profile, a native IDE tool
attestation, a generic DevTools connection or an OS network sandbox. It is
Orbit-owned, scoped local UI automation with independent tool observations.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import struct
import subprocess
import tempfile
import time
import urllib.request
from urllib.parse import urlsplit

MAX_WS_BYTES = 16 * 1024 * 1024
CDP_TIMEOUT = 12
MAX_ERRORS = 10


class BrowserUnavailable(RuntimeError):
    pass


def installed_executable(label, *, env=None):
    """Windows-only opt-in: known system Chrome/Edge locations, never PATH.

    The project (or its dependencies) could place a malicious chrome.exe on
    PATH; executing that as a QA browser would violate the host boundary.
    Other OSes continue using the existing reviewed Playwright browser engine
    until their native browser paths have an independent security review.
    """
    if label not in ('chrome', 'msedge') or os.name != 'nt':
        return None
    if env is None:
        env = os.environ
    suffix = ('Google/Chrome/Application/chrome.exe' if label == 'chrome'
              else 'Microsoft/Edge/Application/msedge.exe')
    for key in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA'):
        base = env.get(key)
        if not base:
            continue
        path = Path(base) / suffix
        if (path.is_file() and not path.is_symlink()
                and path.resolve() == path.absolute()):
            return str(path.resolve())
    return None


def allowed_http(url, port):
    try:
        u = urlsplit(url)
        return (u.scheme == 'http' and u.hostname == '127.0.0.1' and u.port == port
                and u.username is None and u.password is None and not u.fragment)
    except (ValueError, TypeError):
        return False


def allowed_resource(url, port):
    if allowed_http(url, port):
        return True
    try:
        return urlsplit(url).scheme in {'data', 'blob', 'about'}
    except (ValueError, TypeError):
        return False


def _read_exact(sock, n):
    result = bytearray()
    while len(result) < n:
        part = sock.recv(n - len(result))
        if not part:
            raise BrowserUnavailable('Isolated browser DevTools socket closed')
        result.extend(part)
    return bytes(result)


class CDP:
    """Minimal bounded RFC6455 client. DevTools socket must be loopback + new profile."""

    def __init__(self, port, target):
        u = urlsplit(target)
        if (u.scheme != 'ws' or u.hostname != '127.0.0.1' or u.port != port
                or not u.path.startswith('/devtools/page/') or u.username or u.password):
            raise BrowserUnavailable('Unexpected DevTools target address')
        self.sock = socket.create_connection(('127.0.0.1', port), timeout=5)
        self.sock.settimeout(CDP_TIMEOUT)
        key = base64.b64encode(secrets.token_bytes(16)).decode('ascii')
        request = (
            f'GET {u.path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\n'
            'Upgrade: websocket\r\nConnection: Upgrade\r\n'
            'Origin: http://127.0.0.1\r\n'
            f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n'
        )
        self.sock.sendall(request.encode('ascii'))
        header = bytearray()
        while b'\r\n\r\n' not in header:
            if len(header) > 4096:
                raise BrowserUnavailable('Oversized DevTools handshake')
            header.extend(_read_exact(self.sock, 1))
        status, *lines = bytes(header).split(b'\r\n')
        expected = base64.b64encode(hashlib.sha1(
            (key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode('ascii')
        ).digest()).decode('ascii')
        lower = bytes(header).lower()
        if (b' 101 ' not in status or b'upgrade: websocket' not in lower
                or b'sec-websocket-accept: ' + expected.lower().encode('ascii') not in lower):
            raise BrowserUnavailable('DevTools handshake refused or untrusted')
        self.seq = 0
        self.blocked = []
        self.errors = []
        self.dialogs = []
        self.app_port = None
        self.frames = 0

    def close(self):
        self.sock.close()

    def _send_frame(self, opcode, payload=b''):
        if len(payload) > MAX_WS_BYTES:
            raise BrowserUnavailable('DevTools message exceeds bounded size')
        mask = secrets.token_bytes(4)
        header = bytes([0x80 | opcode, 0x80 | len(payload)]) if len(payload) < 126 else (
            bytes([0x80 | opcode, 0x80 | 126]) + struct.pack('!H', len(payload))
            if len(payload) <= 65535 else
            bytes([0x80 | opcode, 0x80 | 127]) + struct.pack('!Q', len(payload)))
        self.sock.sendall(header + mask + bytes(c ^ mask[i % 4] for i, c in enumerate(payload)))

    def _send(self, method, params=None):
        self.seq += 1
        message = json.dumps({'id': self.seq, 'method': method, 'params': params or {}},
                             separators=(',', ':'), ensure_ascii=True).encode('utf-8')
        self._send_frame(1, message)
        return self.seq

    def _message(self):
        while True:
            header = _read_exact(self.sock, 2)
            fin, opcode, masked = header[0] & 0x80, header[0] & 15, header[1] & 0x80
            size = header[1] & 127
            if size == 126:
                size = struct.unpack('!H', _read_exact(self.sock, 2))[0]
            elif size == 127:
                size = struct.unpack('!Q', _read_exact(self.sock, 8))[0]
            if size > MAX_WS_BYTES or masked or not fin:
                raise BrowserUnavailable('Unsupported/oversized DevTools websocket frame')
            body = _read_exact(self.sock, size)
            if opcode == 8:
                raise BrowserUnavailable('Browser closed DevTools connection')
            if opcode == 9:
                self._send_frame(10, body)
                continue
            if opcode == 10:
                continue
            if opcode != 1:
                raise BrowserUnavailable('Unexpected DevTools frame type')
            return json.loads(body)

    def _event(self, msg):
        method = msg.get('method')
        params = msg.get('params') or {}
        if method == 'Fetch.requestPaused':
            url = (params.get('request') or {}).get('url', '')
            request_id = params.get('requestId')
            if not request_id:
                raise BrowserUnavailable('Missing paused request identity')
            if allowed_resource(url, self.app_port):
                self._send('Fetch.continueRequest', {'requestId': request_id})
            else:
                if len(self.blocked) < 20:
                    self.blocked.append((urlsplit(url).hostname or 'nonlocal-resource')[:100])
                self._send('Fetch.failRequest', {'requestId': request_id, 'errorReason': 'BlockedByClient'})
        elif method == 'Network.requestWillBeSent':
            # Backstop: a request not caught by Fetch must still invalidate QA.
            url = (params.get('request') or {}).get('url','')
            if not allowed_resource(url, self.app_port) and len(self.blocked) < 20:
                self.blocked.append((urlsplit(url).hostname or 'unrouted-resource')[:100])
        elif method == 'Page.frameNavigated':
            url = (params.get('frame') or {}).get('url','')
            if not allowed_resource(url, self.app_port) and len(self.blocked) < 20:
                self.blocked.append('non-preview-navigation')
        elif method in {'Network.webSocketCreated', 'Network.webTransportCreated', 'Page.windowOpen'}:
            if len(self.blocked) < 20:
                self.blocked.append('unsupported-browser-transport-or-popup')
        elif method == 'Page.javascriptDialogOpening':
            if len(self.dialogs) < 10:
                self.dialogs.append('unhandled-browser-dialog')
            self._send('Page.handleJavaScriptDialog', {'accept': False})
        elif method == 'Runtime.exceptionThrown':
            if len(self.errors) < 10:
                self.errors.append('uncaught-javascript-exception')
        elif method == 'Log.entryAdded' and (params.get('entry') or {}).get('level') == 'error':
            entry = params.get('entry') or {}
            if len(self.errors) < 10:
                self.errors.append('browser-log-error: ' + str(entry.get('text',''))[:160])
        elif method == 'Runtime.consoleAPICalled' and params.get('type') == 'error':
            if len(self.errors) < 10:
                self.errors.append('console-error: ' + str((params.get('args') or [{}])[0].get('value',''))[:160])

    def call(self, method, params=None, timeout=CDP_TIMEOUT):
        ident = self._send(method, params)
        expires = time.monotonic() + timeout
        while time.monotonic() < expires:
            try:
                msg = self._message()
            except socket.timeout:
                raise BrowserUnavailable('Browser DevTools response timeout') from None
            if 'method' in msg:
                self._event(msg)
                continue
            if msg.get('id') == ident:
                if 'error' in msg:
                    raise BrowserUnavailable('Browser DevTools rejected ' + method)
                return msg.get('result') or {}
        raise BrowserUnavailable('Timed out waiting for DevTools reply')

    def evaluate(self, expression):
        result = self.call('Runtime.evaluate', {
            'expression': expression, 'returnByValue': True, 'awaitPromise': True})
        if result.get('exceptionDetails'):
            raise BrowserUnavailable('Browser page action raised a JavaScript exception')
        return (result.get('result') or {}).get('value')


# Browser pages can execute arbitrary JavaScript; abort browser-dependent
# transports before page scripts run. A Chrome DevTools request interceptor also
# enforces the exact Orbit preview origin on HTTP requests/redirects.
BLOCK_UNROUTABLE_JS = r"""(() => {
  for (const name of ['WebSocket', 'EventSource', 'Worker', 'SharedWorker']) {
    Object.defineProperty(window, name, {configurable:false, writable:false,
      value: class { constructor(){throw new Error('Orbit QA: unsupported browser transport');} }});
  }
  if (navigator.serviceWorker) {
    try {navigator.serviceWorker.register = () => Promise.reject(new Error('Orbit QA: service worker disabled'));} catch (_) {}
  }
  try {navigator.sendBeacon = () => false;} catch (_) {}
  try {window.open = () => {throw new Error('Orbit QA: popups disabled');};} catch (_) {}
  document.addEventListener('click', e => {
    const link = e.target && e.target.closest && e.target.closest('a[target="_blank"]');
    if(link) e.preventDefault();
  }, true);
})()"""


def _script(action, query=False):
    selector = json.dumps(action['selector'], ensure_ascii=True)
    common = ('const e=document.querySelector(' + selector +
              '); if(!e) return {error:"selector-not-found"};')
    if query:
        return '(function(){' + common + (
            'const r=e.getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2,'
            'visible:r.width>0&&r.height>0&&getComputedStyle(e).visibility!=="hidden"'
            '&&getComputedStyle(e).display!=="none"};})()')
    op = action['op']
    if op == 'expect_count':
        return ('document.querySelectorAll(' + selector + ').length')
    if op == 'expect_text':
        return '(function(){' + common + 'return e.textContent || "";})()'
    if op == 'expect_visible':
        return '(function(){' + common + (
            'const r=e.getBoundingClientRect();return r.width>0&&r.height>0'
            '&&getComputedStyle(e).visibility!=="hidden"'
            '&&getComputedStyle(e).display!=="none";})()')
    if op == 'fill':
        value = json.dumps(action['value'], ensure_ascii=True)
        return '(function(){' + common + (
            'if(!("value" in e))return {error:"not-an-input"};e.focus();'
            'const proto=e instanceof HTMLTextAreaElement?HTMLTextAreaElement.prototype:'
            'e instanceof HTMLInputElement?HTMLInputElement.prototype:null;'
            'const setter=proto&&Object.getOwnPropertyDescriptor(proto,"value").set;'
            'if(setter)setter.call(e,' + value + ');else e.value=' + value + ';'
            'e.dispatchEvent(new Event("input",{bubbles:true}));'
            'e.dispatchEvent(new Event("change",{bubbles:true}));return true;})()')
    if op == 'press':
        return '(function(){' + common + 'e.focus();return true;})()'
    raise ValueError('Unsupported isolated browser QA action')


def _execute(cdp, action, width, height):
    op = action['op']
    if op in ('click', 'press'):
        coords = cdp.evaluate(_script(action, query=(op == 'click')))
        if op == 'click':
            if not isinstance(coords, dict) or not coords.get('visible'):
                raise BrowserUnavailable('Click target not visible')
            x, y = coords['x'], coords['y']
            if not (0 <= x < width and 0 <= y < height):
                raise BrowserUnavailable('Click target outside viewport')
            cdp.call('Input.dispatchMouseEvent',
                     {'type': 'mousePressed', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1})
            cdp.call('Input.dispatchMouseEvent',
                     {'type': 'mouseReleased', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1})
        else:
            if coords is not True:
                raise BrowserUnavailable('Cannot focus requested key target')
            key = action['value']
            keys = {'Enter': (13, '\r'), 'Tab': (9, '\t'), 'Escape': (27, '')}
            if key not in keys:
                raise BrowserUnavailable('Isolated browser supports only Enter, Tab and Escape')
            num, text = keys[key]
            for kind in ('keyDown', 'keyUp'):
                cdp.call('Input.dispatchKeyEvent', {
                    'type': kind, 'key': key, 'code': key,
                    'windowsVirtualKeyCode': num, 'nativeVirtualKeyCode': num,
                    'text': text if kind == 'keyDown' else ''})
        return
    result = cdp.evaluate(_script(action))
    if op == 'expect_count' and result != action['value']:
        raise BrowserUnavailable('Element count mismatch')
    if op == 'expect_text' and (not isinstance(result, str) or action['value'] not in result):
        raise BrowserUnavailable('Expected text not found')
    if op == 'expect_visible' and result is not True:
        raise BrowserUnavailable('Element not visible')
    if op == 'fill' and result is not True:
        raise BrowserUnavailable('Cannot fill input')


def _open_browser(executable, profile):
    args = [executable, '--headless=new', '--remote-debugging-port=0',
            '--remote-allow-origins=http://127.0.0.1',
            '--no-first-run', '--no-default-browser-check', '--disable-extensions',
            '--disable-sync', '--disable-background-networking',
            '--disable-component-extensions-with-background-pages',
            '--no-proxy-server',
            '--user-data-dir=' + str(profile), 'about:blank']
    proc = subprocess.Popen(args, stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        marker = profile / 'DevToolsActivePort'
        deadline = time.monotonic() + 7
        while time.monotonic() < deadline and proc.poll() is None:
            if marker.is_file():
                # Windows may expose DevToolsActivePort before Chrome releases
                # its exclusive writer handle. Retry reads, not permissions.
                try:
                    rows = marker.read_text(encoding='ascii').splitlines()
                    port = int(rows[0])
                except (OSError, ValueError, IndexError, UnicodeError):
                    time.sleep(.1)
                    continue
                if not 1024 <= port <= 65535:
                    raise BrowserUnavailable('Invalid local debugging port')
                req = urllib.request.Request(f'http://127.0.0.1:{port}/json')
                try:
                    with urllib.request.urlopen(req, timeout=3) as response:
                        targets = json.load(response)
                except (OSError, ValueError):
                    time.sleep(.1)
                    continue
                urls = [t.get('webSocketDebuggerUrl') for t in targets
                        if t.get('type') == 'page']
                if len(urls) != 1 or not urls[0]:
                    raise BrowserUnavailable('Isolated browser target count unexpected')
                return proc, port, urls[0]
            time.sleep(.1)
        raise BrowserUnavailable('Isolated browser failed to start')
    except Exception:
        proc.terminate()
        try: proc.wait(timeout=5)
        except subprocess.TimeoutExpired: proc.kill()
        raise


def run(root, a, session, actions, source_before, browser_label, artifact_folder):
    """Return PASS only for genuine isolated browser actions from this process."""
    executable = installed_executable(browser_label)
    if not executable:
        return {'status': 'BROWSER_UNAVAILABLE',
                'notice': 'Isolated CDP requires an already-installed Edge or Chrome; no download performed'}
    viewport = a.get('viewport', 'desktop')
    width, height = {'desktop': (1280, 800), 'mobile': (390, 844)}[viewport]
    url = f"http://127.0.0.1:{session['port']}/"
    started = time.monotonic()
    results, errors, failures, blocked = [], [], [], []
    screenshot, title = None, ''
    try:
        import orbit_build
        with tempfile.TemporaryDirectory(prefix='orbit-isolated-cdp-') as temp:
            proc = None
            cdp = None
            try:
                proc, port, target = _open_browser(executable, Path(temp) / 'profile')
                cdp = CDP(port, target)
                cdp.app_port = session['port']
                cdp.call('Page.enable')
                cdp.call('Runtime.enable')
                cdp.call('Network.enable')
                cdp.call('Log.enable')
                cdp.call('Page.addScriptToEvaluateOnNewDocument', {'source': BLOCK_UNROUTABLE_JS})
                cdp.call('Fetch.enable', {'patterns': [{'urlPattern': '*', 'requestStage': 'Request'}]})
                cdp.call('Emulation.setDeviceMetricsOverride', {
                    'width': width, 'height': height, 'deviceScaleFactor': 1, 'mobile': viewport == 'mobile'})
                cdp.call('Page.navigate', {'url': url})
                # Actual page load in this same browser instance (not a caller claim).
                ready = cdp.evaluate('new Promise(resolve => {'
                    'if(document.readyState==="complete")resolve(true);'
                    'else {window.addEventListener("load",()=>resolve(true),{once:true});'
                    'setTimeout(()=>resolve(false),6000);}})')
                if ready is not True:
                    raise BrowserUnavailable('Page did not load')
                title = str(cdp.evaluate('document.title') or '')[:180]
                for i, action in enumerate(actions):
                    try:
                        # Match Playwright's bounded waiting for asynchronous
                        # DOM updates without converting real errors to PASS.
                        stop_waiting = time.monotonic() + 4
                        while True:
                            try:
                                _execute(cdp, action, width, height)
                                break
                            except BrowserUnavailable as exc:
                                transient = str(exc) in {
                                    'Element not visible', 'Click target not visible',
                                    'Element count mismatch', 'Expected text not found',
                                    'Cannot focus requested key target', 'Cannot fill input'}
                                if not transient or time.monotonic() >= stop_waiting:
                                    raise
                                cdp.evaluate('new Promise(resolve=>setTimeout(()=>resolve(true),180))')
                        # Drain asynchronous requests and console errors between steps.
                        cdp.evaluate('new Promise(resolve=>setTimeout(()=>resolve(true),180))')
                        results.append({'step': i + 1, 'op': action['op'], 'status': 'PASS'})
                    except (BrowserUnavailable, ValueError, TypeError) as exc:
                        results.append({'step': i + 1, 'op': action['op'], 'status': 'FAIL'})
                        failures.append({'step': i + 1, 'op': action['op'],
                                         'message': str(exc).splitlines()[0][:160]})
                        break
                if not failures:
                    screenshot_data = cdp.call('Page.captureScreenshot', {
                        'format': 'png', 'captureBeyondViewport': True}, timeout=15).get('data')
                    if not screenshot_data:
                        raise BrowserUnavailable('Browser screenshot missing')
                    screenshot_bytes = base64.b64decode(screenshot_data, validate=True)
                    if not screenshot_bytes.startswith(b'\x89PNG\r\n\x1a\n') or len(screenshot_bytes) > 12*1024*1024:
                        raise BrowserUnavailable('Invalid screenshot content')
                    artifact = artifact_folder(root)
                    screenshot_path = artifact / (
                        a['preview_id'] + '-' + viewport + '-cdp-' + secrets.token_hex(8) + '.png')
                    with screenshot_path.open('xb') as img:
                        img.write(screenshot_bytes)
                    if os.name != 'nt':
                        screenshot_path.chmod(0o600)
                    screenshot = str(screenshot_path)
                errors.extend(cdp.errors[:MAX_ERRORS])
                failures.extend({'step': 0, 'op': 'browser_dialog', 'message': msg}
                                for msg in cdp.dialogs[:MAX_ERRORS])
                blocked.extend(cdp.blocked)
            finally:
                if cdp:
                    try: cdp.call('Browser.close', timeout=2)
                    except (BrowserUnavailable, OSError, socket.timeout): pass
                    cdp.close()
                if proc and proc.poll() is None:
                    proc.terminate()
                    try: proc.wait(timeout=5)
                    except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=5)
    except (BrowserUnavailable, ValueError, TypeError, OSError, KeyError, json.JSONDecodeError) as exc:
        failures.append({'step': 0, 'op': 'isolated_browser',
                         'message': str(exc).splitlines()[0][:240]})
    source_after = orbit_build.code_fingerprint(root)
    if source_after != source_before:
        failures.append({'step': 0, 'op': 'source_revision',
                         'message': 'Project source changed during browser QA'})
    if blocked:
        failures.append({'step': 0, 'op': 'network_origin',
                         'message': 'Browser attempted forbidden network/transport'})
    passed = not errors and not failures and not blocked and bool(actions) and len(results) == len(actions)
    return {
        'status': 'PASS' if passed else 'FAIL',
        'url': url, 'viewport': viewport, 'title': title,
        'browser': browser_label, 'engine': 'isolated-cdp',
        'actions': results, 'errors': errors[:10], 'failures': failures[:10],
        'blocked_remote_hosts': sorted(set(blocked))[:10],
        'screenshot': screenshot, 'elapsed_ms': round((time.monotonic()-started)*1000),
        'source_fingerprint': source_before, 'preview_id': a['preview_id'],
        'preview_started_at': session['started_at'],
        'verified_by': 'local isolated Chrome DevTools (' + browser_label + ')',
        'notice': 'Actual isolated Chrome/Edge actions with DevTools request interception. '
                  'No package download, existing browser profile, IDE/browser CUA attestation, '
                  'OS network sandbox, or remote deployment.'
    }
