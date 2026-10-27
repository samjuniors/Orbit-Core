"""Orbit MVP local-only preview manager.

Explicitly approved commands run in a chosen project directory without a shell.
The manager can stop only processes started by this same running MCP instance.
Persistent cross-session supervision and browser QA are separate milestones.
"""
from __future__ import annotations

import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

MAX_RUNNING = 3
# Interpreter options that run inline code, preload arbitrary code, or open debug ports.
NODE_BLOCKED = re.compile(r'^(?:-e|-p|-r|--eval|--print|--require|--import|--loader|--experimental-loader|--inspect(?:-brk|-wait)?(?:=.*)?|--input-type(?:=.*)?)$')
PYTHON_CLUSTER_C = re.compile(r'^-[A-Za-z]*c[A-Za-z]*$')
PUBLIC_BIND = re.compile(r'(?:^|[=:\s,])(?:0\.0\.0\.0|\[?::\]?)(?:$|[:/\s,])')
SECRET_ENV = re.compile(r'SECRET|TOKEN|PASSW|CREDENTIAL|API_?KEY|ACCESS_?KEY|PRIVATE_?KEY|AUTH|SESSION', re.I)
ALLOWED_EXES = {'python', 'python3', 'python.exe', 'python3.exe', 'node', 'node.exe',
                'npm', 'npm.cmd', 'pnpm', 'pnpm.cmd', 'yarn', 'yarn.cmd', 'bun', 'bun.exe'}
SESSIONS = {}


class RejectRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Preview endpoint redirected; refusing to follow any redirect')


NO_REDIRECT = urllib.request.build_opener(RejectRedirect)


def preview_key(root, preview_id):
    if not isinstance(preview_id, str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,39}', preview_id):
        raise ValueError('preview_id must be a lowercase slug of up to 40 characters')
    return (str(root), preview_id)


def check_port(port):
    if type(port) is not int or not 1024 <= port <= 65535:
        raise ValueError('port must be 1024–65535')
    return port


def check_health(path):
    if not isinstance(path, str) or not path.startswith('/') or path.startswith('//') or len(path) > 100:
        raise ValueError('health_path must be a local absolute URL path')
    if '?' in path or '#' in path or '\\' in path or any(ord(c) < 32 for c in path):
        raise ValueError('health_path cannot contain query, fragment or control characters')
    return path


def check_command(argv):
    if not isinstance(argv, list) or not 1 <= len(argv) <= 20 or any(
        not isinstance(x, str) or not x or len(x) > 320 or any(ord(c) < 32 for c in x)
        for x in argv
    ):
        raise ValueError('command must be a list of 1–20 nonempty arguments')
    if Path(argv[0]).name != argv[0] and not Path(argv[0]).is_absolute():
        raise ValueError('Use a bare runtime name from PATH or an absolute interpreter path, not a relative path')
    binary = Path(argv[0]).name.lower()
    if binary not in ALLOWED_EXES:
        raise ValueError('Only known local development runtimes are allowed; use IDE terminal for others')
    if any(PUBLIC_BIND.search(x) for x in argv[1:]):
        raise ValueError('Preview must bind to loopback only; wildcard addresses are not approved')
    if binary.startswith('python'):
        # Inspect only interpreter options (everything before the script or -m target).
        for item in argv[1:]:
            if item == '-m' or not item.startswith('-'):
                break
            if PYTHON_CLUSTER_C.match(item):
                raise ValueError('python -c is not an approved preview command')
    if binary.startswith('node') or binary.startswith('bun'):
        for item in argv[1:]:
            if not item.startswith('-'):
                break
            if NODE_BLOCKED.match(item):
                raise ValueError('Inline-code, preload and debugger options are not approved preview commands')
    if binary.startswith('npm') or binary.startswith('pnpm') or binary.startswith('yarn'):
        if len(argv) < 3 or argv[1:3] not in (['run', 'dev'], ['run', 'start'], ['run', 'preview']):
            raise ValueError('Package-manager commands must be run dev/start/preview')
        if any(x.startswith(('--script-shell', '--shell', '--prefix', '--userconfig', '--globalconfig')) for x in argv[3:]):
            raise ValueError('Package-manager shell/config overrides are not approved')
    return argv


def occupied(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(('127.0.0.1', port)) == 0


def http_probe(port, path):
    url = f'http://127.0.0.1:{port}{path}'
    req = urllib.request.Request(url, method='GET', headers={'User-Agent':'Orbit-Local-Preview/0.24'})
    try:
        with NO_REDIRECT.open(req, timeout=0.6) as response:
            return {'reachable': True, 'http_status': response.status, 'healthy': 200 <= response.status < 400,
                    'url': url}
    except urllib.error.HTTPError as exc:
        return {'reachable': True, 'http_status': exc.code, 'healthy': False, 'url': url}
    except (OSError, ValueError, TimeoutError) as exc:
        return {'reachable': False, 'healthy': False, 'url':url, 'reason':str(exc)[:160]}


def safe_log_folder(root):
    # Logs never reside under the user's code repository or in memory/SQLite files.
    import hashlib
    base = Path(os.environ.get('ORBIT_PREVIEW_LOG_HOME', Path.home() / '.orbit-universal' / 'preview-logs')).expanduser().resolve()
    directory = base / hashlib.sha256(str(root).encode()).hexdigest()[:20]
    if directory.is_symlink():
        raise ValueError('Refusing symlink log directory')
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name != 'nt':
        try: directory.chmod(0o700)
        except OSError: pass
    return directory


def start(root, a):
    key = preview_key(root, a['preview_id'])
    port = check_port(a['port'])
    path = check_health(a.get('health_path','/'))
    command = check_command(a['command'])
    existing = SESSIONS.get(key)
    if existing and existing['proc'].poll() is None:
        return {'status':'ALREADY_RUNNING', **view(existing)}
    if a.get('confirm_run') is not True:
        return {'status':'PREVIEW_ONLY', 'project_root':str(root), 'preview_id':key[1],
                'command':command, 'url':f'http://127.0.0.1:{port}{path}',
                'notice':'Starting this command executes project code. Review it and explicitly approve first.'}
    resolved = command[0] if Path(command[0]).is_absolute() else shutil.which(command[0])
    if not resolved:
        raise ValueError('Runtime not found on PATH: '+command[0])
    inside = Path(resolved).resolve()
    if inside == Path(root).resolve() or Path(root).resolve() in inside.parents:
        raise ValueError('Runtime resolves inside the project folder; refusing project-local executable')
    if occupied(port):
        return {'status':'PORT_IN_USE', 'port':port, 'notice':'Orbit will not adopt or terminate another process.'}
    active = sum(row['proc'].poll() is None for row in SESSIONS.values())
    if active >= MAX_RUNNING:
        raise ValueError('Maximum active previews reached; stop an Orbit preview first')
    folder = safe_log_folder(root)
    logfile = folder / (key[1]+'.log')
    if logfile.is_symlink():
        raise ValueError('Refusing symlink log file')
    # Preserve log history; the log path is fixed to the project hash and preview slug.
    with logfile.open('ab') as log:
        log.write((f'\n--- Orbit preview {time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())} ---\n').encode())
        log.flush()
        env = {k: v for k, v in os.environ.items()
               if os.environ.get('ORBIT_PREVIEW_INHERIT_ENV') == '1' or not SECRET_ENV.search(k)}
        env.update({'PORT': str(port), 'HOST': '127.0.0.1'})
        kwargs = {'cwd':str(root), 'stdin':subprocess.DEVNULL, 'stdout':log,
                  'stderr':subprocess.STDOUT, 'shell':False, 'env':env}
        if os.name == 'nt':
            kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            kwargs['start_new_session'] = True
        try:
            proc = subprocess.Popen([resolved, *command[1:]], **kwargs)
        except OSError as exc:
            return {'status':'START_FAILED','error':str(exc)[:200]}
    session = {'proc':proc,'root':str(root),'preview_id':key[1], 'port':port,'health_path':path,
               'command':list(command), 'logfile':str(logfile),'started_at':time.time()}
    SESSIONS[key] = session
    for _ in range(16):
        if proc.poll() is not None:
            break
        probe=http_probe(port, path)
        if probe['healthy']:
            return {'status':'READY', **view(session)}
        time.sleep(0.2)
    return {'status':'STARTED_NOT_READY' if proc.poll() is None else 'EXITED',**view(session)}


def log_tail(logfile, max_bytes=3000):
    path=Path(logfile)
    if path.is_symlink() or not path.is_file():
        return ''
    with path.open('rb') as f:
        f.seek(0, 2)
        size=f.tell()
        f.seek(max(0,size-max_bytes))
        return f.read(max_bytes).decode('utf-8','replace')


def view(session):
    proc = session['proc']
    running = proc.poll() is None
    probe = http_probe(session['port'],session['health_path']) if running else {'reachable':False,'healthy':False}
    return {'project_root':session['root'],'preview_id':session['preview_id'],
            'pid':proc.pid, 'running':running, 'exit_code':None if running else proc.returncode,
            'port':session['port'], 'preview_url':f"http://127.0.0.1:{session['port']}/",
            'readiness':probe, 'logs':log_tail(session['logfile']),
            'notice':'Local-only URL. Host browser testing is separate. Process controls require the same MCP session.'}


def status(root, a):
    key=preview_key(root,a['preview_id'])
    session=SESSIONS.get(key)
    if not session:
        return {'status':'NOT_MANAGED_BY_THIS_SESSION', 'project_root':str(root),'preview_id':key[1],
                'notice':'MCP restarted or preview was started outside Orbit. No process adopted or terminated.'}
    return {'status':'READY' if session['proc'].poll() is None and http_probe(session['port'],session['health_path'])['healthy']
            else 'NOT_READY', **view(session)}


def stop(root,a):
    key=preview_key(root,a['preview_id'])
    session=SESSIONS.get(key)
    if not session:
        return {'status':'NOT_MANAGED_BY_THIS_SESSION','notice':'Cannot stop an unverified process.'}
    proc=session['proc']
    if a.get('confirm_stop') is not True:
        return {'status':'PREVIEW_ONLY',**view(session)}
    if proc.poll() is None:
        try:
            if os.name == 'nt':
                proc.terminate()
            else:
                os.killpg(proc.pid,signal.SIGTERM)
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            return {'status':'STOP_TIMEOUT','notice':'Process did not exit. Check it manually.',**view(session)}
        except ProcessLookupError:
            pass
    result={'status':'STOPPED','pid':proc.pid,'exit_code':proc.poll(),'preview_id':key[1]}
    del SESSIONS[key]
    return result


def shutdown_all():
    """Best-effort cleanup of previews owned by this MCP process (called when the session ends).

    Without this, a host that restarts the MCP leaves unmanaged servers holding the port.
    Set ORBIT_PREVIEW_KEEP_ALIVE=1 to keep previews running after the session.
    """
    if os.environ.get('ORBIT_PREVIEW_KEEP_ALIVE') == '1':
        return
    for session in list(SESSIONS.values()):
        proc = session['proc']
        if proc.poll() is not None:
            continue
        try:
            if os.name == 'nt':
                proc.terminate()
            else:
                os.killpg(proc.pid, signal.SIGTERM)
            proc.wait(timeout=3)
        except (OSError, subprocess.TimeoutExpired):
            try: proc.kill()
            except OSError: pass
    SESSIONS.clear()
