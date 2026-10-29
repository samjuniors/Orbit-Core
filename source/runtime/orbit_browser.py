"""Approved local browser verification using an already installed Playwright.

No downloads, no non-loopback page traffic and no arbitrary JavaScript execution.
Screenshots/reports are private local artifacts outside the user's repository.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
from pathlib import Path
from urllib.parse import urlparse

SIZES = {'desktop': (1280, 800), 'mobile': (390, 844)}
ACTIONS = {'click', 'fill', 'press', 'expect_text', 'expect_visible', 'expect_count'}
BROWSERS = ('auto', 'msedge', 'chrome', 'chromium')



def installed_channel(channel, *, windows=None, env=None):
    """Recognize installed branded browsers; never download or execute discovery commands.

    Check common Windows install locations because msedge.exe/chrome.exe are not
    typically on PATH. An explicit channel is still checked by Playwright itself.
    """
    if channel not in {'msedge', 'chrome'}:
        return False
    binary = 'msedge' if channel == 'msedge' else 'chrome'
    if shutil.which(binary) or shutil.which(binary + '.exe'):
        return True
    if windows is None:
        windows = os.name == 'nt'
    if not windows:
        return False
    if env is None:
        env = os.environ
    suffix = ('Microsoft/Edge/Application/msedge.exe' if channel == 'msedge'
              else 'Google/Chrome/Application/chrome.exe')
    for key in ('PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA'):
        base = env.get(key)
        if base and (Path(base) / suffix).is_file():
            return True
    return False


def browser_launch(browser='auto'):
    """Resolve a transparent, local-only browser choice for Playwright.

    On Windows, prefer already-installed Edge/Chrome over downloading Playwright
    Chromium. Explicit selections never silently switch to another engine.
    """
    if browser not in BROWSERS:
        raise ValueError('browser must be auto, msedge, chrome, or chromium')
    if browser in {'msedge', 'chrome'}:
        return {'headless': True, 'channel': browser}, browser
    if browser == 'auto':
        for channel in ('msedge', 'chrome'):
            if installed_channel(channel):
                return {'headless': True, 'channel': channel}, channel
    executable = (shutil.which('chromium') or shutil.which('chromium-browser')
                  or shutil.which('google-chrome'))
    if executable:
        return {'headless': True, 'executable_path': executable}, 'local-chromium'
    return {'headless': True}, 'playwright-chromium'

def artifact_folder(root):
    base = Path(os.getenv('ORBIT_QA_HOME') or Path.home() / '.orbit-universal' / 'qa-artifacts').expanduser().resolve()
    dest = base / hashlib.sha256(str(root).encode()).hexdigest()[:20]
    if dest.is_symlink():
        raise ValueError('Symlink QA folder forbidden')
    dest.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != 'nt':
        dest.chmod(0o700)
    return dest


def validate_actions(actions):
    if not isinstance(actions, list) or len(actions) > 20:
        raise ValueError('actions must be a list of 0–20 operations')
    for a in actions:
        if not isinstance(a, dict) or a.get('op') not in ACTIONS or set(a) - {'op','selector','value'}:
            raise ValueError('Invalid browser QA action')
        if not isinstance(a.get('selector'), str) or not 1 <= len(a['selector']) <= 180:
            raise ValueError('Browser selector must be 1–180 characters')
        value = a.get('value')
        if a['op'] in {'fill','press','expect_text'} and (not isinstance(value, str) or len(value)>300):
            raise ValueError('Browser action requires bounded string value')
        if a['op']=='expect_count' and (type(value) is not int or not 0<=value<=50):
            raise ValueError('expect_count needs an integer from 0 to 50')
    return actions


def approved_preview_origin(target_url, port, *, websocket=False):
    """Allow network traffic only to the exact Orbit-owned preview origin.

    'localhost', IPv6 loopback, alternate ports, HTTPS and DNS rebinding
    hosts are intentionally NOT interchangeable with 127.0.0.1:<port>.
    Use a different reviewed adapter for multi-server application flows.
    """
    try:
        target=urlparse(target_url)
        return (target.scheme == ('ws' if websocket else 'http')
                and target.hostname == '127.0.0.1'
                and target.port == port
                and target.username is None and target.password is None)
    except (ValueError, TypeError):
        return False


def route_preview_request(route, port, blocked):
    """Intercept HTTP(S) requests; never follow redirects to another origin."""
    uri=route.request.url
    try:
        parsed=urlparse(uri)
        kind=parsed.scheme
        permitted=approved_preview_origin(uri,port) or kind in {'data','blob','about'}
        label=parsed.hostname or kind
    except ValueError:
        permitted=False
        label='malformed-url'
    if permitted:
        route.continue_()
    else:
        blocked.append(label)
        route.abort()


def route_preview_socket(ws_route, port, blocked):
    """Playwright 1.48+ intercepts websockets before their first connection."""
    uri=ws_route.url
    if approved_preview_origin(uri, port, websocket=True):
        ws_route.connect_to_server()
    else:
        try:
            target=urlparse(uri)
            label=target.hostname or target.scheme
        except ValueError:
            label='malformed-url'
        blocked.append(label)
        ws_route.close(code=1008, reason='Orbit QA: non-preview WebSocket denied')


def verify_request(root, a, preview):
    if a.get('viewport', 'desktop') not in SIZES:
        raise ValueError('viewport must be desktop or mobile')
    actions=validate_actions(a.get('actions', []))
    session=preview.SESSIONS.get(preview.preview_key(root,a['preview_id']))
    if not session or session['proc'].poll() is not None:
        return None, actions
    health = preview.http_probe(session['port'],session['health_path'])
    if not health['healthy']:
        return None, actions
    return session, actions


def run(root, a, preview):
    launch_options, browser_label = browser_launch(a.get('browser', 'auto'))
    session, actions = verify_request(root,a,preview)
    if session is None:
        return {'status':'PREVIEW_NOT_READY', 'notice':'Start an Orbit-owned preview in this MCP session, then verify readiness.'}
    url = f"http://127.0.0.1:{session['port']}/"
    if a.get('confirm_run') is not True:
        return {'status':'PREVIEW_ONLY','url':url,'viewport':a.get('viewport','desktop'),
                'actions':actions,'browser':browser_label,'notice':'Browser automation may read visible app data and change local app state. Host approval required.'}
    if actions and a.get('confirm_interactions') is not True:
        return {'status':'INTERACTIONS_NEED_APPROVAL','url':url,'actions_count':len(actions)}
    # Snapshot exact local source before browser work, not an LLM-supplied hash.
    import orbit_build
    source_before=orbit_build.code_fingerprint(root)
    if source_before is None:
        return {'status':'SOURCE_SNAPSHOT_UNAVAILABLE',
                'notice':'Code/source snapshot is unsafe, empty or exceeds bounded limits; review scope before trusting browser QA.'}
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {'status':'DEPENDENCY_MISSING','browser':browser_label,'notice':'Install the trusted Python playwright package into the same interpreter as Orbit with approval. If Edge/Chrome is already installed, no browser download is needed; otherwise Chromium is a separate approved install.'}
    viewport_name = a.get('viewport','desktop')
    width,height=SIZES[viewport_name]
    errors=[]
    blocked=[]
    results=[]
    failures=[]
    title=''
    screenshot=None
    started=time.monotonic()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(**launch_options)
            try:
                context=browser.new_context(viewport={'width':width,'height':height}, service_workers='block')
                # Routing HTTP requests is not sufficient: Playwright before 1.48
                # cannot route WebSockets, which can otherwise reach other local
                # services. Fail closed rather than certify isolated browser QA.
                if not callable(getattr(context,'route_web_socket',None)):
                    context.close()
                    return {'status':'DEPENDENCY_TOO_OLD',
                            'notice':'Browser QA requires Playwright >=1.48 for WebSocket origin control. Review an approved dependency update; no remote browser or install attempted.'}
                context.route('**/*',lambda route: route_preview_request(route,session['port'],blocked))
                context.route_web_socket('**/*',lambda ws: route_preview_socket(ws,session['port'],blocked))
                page=context.new_page()
                page.on('pageerror', lambda error: errors.append(str(error)[:240]))
                page.on('console', lambda msg: errors.append(msg.text[:240]) if msg.type=='error' else None)
                page.goto(url, wait_until='domcontentloaded', timeout=12000)
                title=page.title()[:180]
                for i,action in enumerate(actions):
                    name=action['op']
                    try:
                        locator=page.locator(action['selector'])
                        if name=='click': locator.first.click(timeout=4000)
                        elif name=='fill': locator.first.fill(action['value'], timeout=4000)
                        elif name=='press': locator.first.press(action['value'], timeout=4000)
                        elif name=='expect_text':
                            text=locator.first.inner_text(timeout=4000)
                            if action['value'] not in text: raise AssertionError('Expected text not found')
                        elif name=='expect_visible':
                            if not locator.first.is_visible(timeout=4000): raise AssertionError('Element not visible')
                        elif name=='expect_count':
                            if locator.count()!=action['value']: raise AssertionError('Element count mismatch')
                        results.append({'step':i+1,'op':name,'status':'PASS'})
                    except Exception as exc:
                        failures.append({'step':i+1,'op':name,'message':str(exc).splitlines()[0][:160]})
                        results.append({'step':i+1,'op':name,'status':'FAIL'})
                        break
                artifact=artifact_folder(root)
                slug=a['preview_id']
                nonce=f"{int(time.time()*1000)}-{os.getpid()}"
                screenshot_path=artifact/f'{slug}-{viewport_name}-{nonce}.png'
                page.screenshot(path=str(screenshot_path),full_page=True,timeout=10000)
                if os.name!='nt': screenshot_path.chmod(0o600)
                screenshot=str(screenshot_path)
                context.close()
            finally:
                browser.close()
    except Exception as exc:
        failures.append({'step':0,'op':'browser','message':str(exc).splitlines()[0][:240]})
    # A source edit while Playwright was running invalidates the observed result.
    source_after=orbit_build.code_fingerprint(root)
    if source_after!=source_before:
        failures.append({'step':0,'op':'source_revision','message':'Project source changed during browser QA'})
    if blocked:
        failures.append({'step':0,'op':'network_origin',
                         'message':'App attempted requests outside its authorized preview origin; review blocked hostnames.'})
    passed=not errors and not failures and not blocked
    # Bounded reporting; never treat console or screenshot as proof of security compliance.
    result={'status':'PASS' if passed else 'FAIL','url':url,'viewport':viewport_name,
            'title':title,'browser':browser_label,'actions':results,'errors':errors[:10],'failures':failures[:10],
            'blocked_remote_hosts':sorted(set(blocked))[:10],
            'screenshot':screenshot,'elapsed_ms':round((time.monotonic()-started)*1000),
            'source_fingerprint':source_before,'preview_id':a['preview_id'],
            'preview_started_at':session['started_at'],
            'verified_by':'local Playwright (' + browser_label + ')','notice':'Browser functionality tested only as specified with HTTP and WebSocket requests restricted to the approved preview origin; not a network sandbox, deployment or security audit.'}
    return result
