"""ORBIT Antigravity native local MCP (stdio); no AI model runtime or agent spawner.

Standalone, dependency-free local project memory/checkpoint tools. Uses the
existing Orbit Core SQLite table shape and OS default database path.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import sqlite3
import sys
import orbit_tasks
import orbit_capabilities
import orbit_preview
import orbit_browser
import orbit_build
import orbit_intake
from datetime import datetime, timezone
from pathlib import Path

VERSION = '0.24.0'
MAX_REQUEST_BYTES = 128 * 1024
MAX_STATE_BYTES = 24000
KINDS = {'semantic', 'episodic', 'decision', 'procedural', 'checkpoint'}
START = '<!-- ORBIT_NATIVE_CHECKPOINT_START -->'
END = '<!-- ORBIT_NATIVE_CHECKPOINT_END -->'


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def db_path():
    configured = os.environ.get('ORBIT_LOCAL_DB')
    if configured:
        return Path(configured).expanduser().resolve()
    if os.name == 'nt':
        return Path(os.getenv('LOCALAPPDATA') or Path.home() / 'AppData' / 'Local') / 'OrbitCore' / 'memory.sqlite3'
    return Path(os.getenv('XDG_DATA_HOME') or (Path.home() / '.local' / 'share')) / 'orbit-core' / 'memory.sqlite3'


def require_string(obj, name, max_len=4000):
    s = obj.get(name)
    if not isinstance(s, str) or not s.strip() or len(s) > max_len:
        raise ValueError(f'{name} must be non-empty text of at most {max_len} characters')
    return s.strip()


def project_root(obj):
    raw = require_string(obj, 'project_root', 2000)
    p = Path(raw).expanduser()
    if not p.is_absolute() or p.is_symlink():
        raise ValueError('project_root must be an absolute, non-symlink directory')
    p = p.resolve(strict=True)
    if not p.is_dir() or p == Path(p.anchor) or p == Path.home().resolve():
        raise ValueError('Select a specific existing project directory')
    return p


def project_key(obj):
    s = require_string(obj, 'project', 80)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}', s):
        raise ValueError('project must be a project slug')
    return s


def safe_checkpoint_path(root):
    orbit = root / '.orbit'
    path = orbit / 'STATE.md'
    if orbit.is_symlink() or path.is_symlink():
        raise ValueError('Symlink checkpoint path forbidden')
    return path


def snapshot(root):
    path = safe_checkpoint_path(root)
    if not path.exists():
        return {'revision': 'MISSING', 'content': '', 'exists': False}
    if not path.is_file() or path.stat().st_size > MAX_STATE_BYTES:
        raise ValueError('Existing checkpoint is not a bounded regular file')
    body = path.read_text(encoding='utf-8')
    return {'revision': hashlib.sha256(body.encode('utf-8')).hexdigest(), 'content': body[:6000], 'exists': True}


def db_connect():
    path = db_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name != 'nt':
        try: path.parent.chmod(0o700)
        except OSError: pass
    conn = sqlite3.connect(str(path), timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA busy_timeout=15000')
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('''CREATE TABLE IF NOT EXISTS memories (
        project TEXT NOT NULL, key TEXT NOT NULL, kind TEXT NOT NULL,
        summary TEXT NOT NULL, source TEXT NOT NULL, importance INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'ACTIVE', evidence TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        archived_at TEXT, archive_reason TEXT,
        PRIMARY KEY (project, key))''')
    conn.commit()
    orbit_tasks.setup(conn)
    orbit_build.setup(conn)
    orbit_intake.setup(conn)
    orbit_build.setup_browser(conn)
    if os.name != 'nt':
        try: path.chmod(0o600)
        except OSError: pass
    return conn


def get_one(conn, project, key):
    row = conn.execute('SELECT * FROM memories WHERE project=? AND key=?', (project, key)).fetchone()
    return dict(row) if row else None


def memory_save(conn, a):
    project = project_key(a)
    key = require_string(a, 'key', 160)
    kind = require_string(a, 'kind', 32)
    summary = require_string(a, 'summary', 4000)
    source = require_string(a, 'source', 1000)
    evidence = a.get('evidence', '')
    importance = a.get('importance', 3)
    if kind not in KINDS or type(importance) is not int or not 1 <= importance <= 5:
        raise ValueError('Invalid kind or importance')
    if not isinstance(evidence, str) or len(evidence) > 4000:
        raise ValueError('Invalid evidence')
    if a.get('confirm_write') is not True:
        return {'status': 'PREVIEW_ONLY', 'project': project, 'key': key, 'kind': kind, 'summary': summary}
    t = timestamp()
    with conn:
        conn.execute('''INSERT INTO memories(project,key,kind,summary,source,importance,evidence,created_at,updated_at)
          VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(project,key) DO UPDATE SET
          kind=excluded.kind,summary=excluded.summary,source=excluded.source,
          importance=excluded.importance,evidence=excluded.evidence,updated_at=excluded.updated_at,
          status='ACTIVE',archived_at=NULL,archive_reason=NULL''',
          (project, key, kind, summary, source, importance, evidence, t, t))
    return {'status': 'SAVED', 'memory': get_one(conn, project, key)}


def memory_recall(conn, a):
    project = project_key(a)
    query = a.get('query', '')
    limit = a.get('limit', 5)
    if not isinstance(query, str) or len(query) > 300 or type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError('Invalid query/limit')
    include_archived = a.get('include_archived', False)
    if type(include_archived) is not bool:
        raise ValueError('Invalid include_archived')
    rows = [dict(r) for r in conn.execute('SELECT * FROM memories WHERE project=? AND (?=1 OR status=\'ACTIVE\') ORDER BY updated_at DESC LIMIT 500', (project, int(include_archived)))]
    terms = [s.lower() for s in re.findall('[a-zA-Z0-9_-]+', query) if len(s) > 1]
    matches = []
    for r in rows:
        content = ' '.join(str(r[k]) for k in ('key','kind','summary','evidence')).lower()
        score = sum(10 for term in terms if term in content) + 2*r['importance'] + (3 if r['kind']=='decision' else 0)
        if not terms or any(term in content for term in terms):
            matches.append((score, r['updated_at'], r))
    matches.sort(key=lambda x: (x[0],x[1]), reverse=True)
    return matches[:0] if not matches else [x[2] for x in matches[:limit]]


def memory_archive(conn, a):
    project = project_key(a)
    key = require_string(a, 'key', 160)
    reason = require_string(a, 'reason', 500)
    if not get_one(conn, project, key):
        raise ValueError('Record not found in specified project')
    if a.get('confirm_write') is not True:
        return {'status': 'PREVIEW_ONLY', 'project': project, 'key': key}
    t = timestamp()
    with conn:
        conn.execute('UPDATE memories SET status=\'ARCHIVED\',archived_at=?,archive_reason=?,updated_at=? WHERE project=? AND key=?', (t,reason,t,project,key))
    return {'status': 'ARCHIVED', 'memory': get_one(conn, project, key)}


def checkpoint(conn, a):
    root, project = project_root(a), project_key(a)
    milestone = require_string(a, 'milestone', 250)
    gate = require_string(a, 'gate', 250)
    result = require_string(a, 'last_result', 40)
    last_step = require_string(a, 'last_step', 350)
    next_step = require_string(a, 'next_step', 350)
    evidence = require_string(a, 'evidence', 1400)
    blockers = a.get('blockers', 'None')
    if result not in {'PASS','FAIL','NOT_RUN','IN_PROGRESS','BLOCKED'} or not isinstance(blockers,str) or len(blockers)>1000:
        raise ValueError('Invalid result/blockers')
    prior = snapshot(root)
    header = '\n'.join([START, f'Project: {project}', f'Milestone: {milestone}', f'Gate: {gate}', f'Last step: {last_step}', f'Last result: {result}', f'Evidence (caller-provided, unverified): {evidence}', f'Blockers: {blockers}', f'Next step: {next_step}', f'Updated UTC: {timestamp()}', END])+'\n'
    if prior['exists']:
        full = safe_checkpoint_path(root).read_text(encoding='utf-8')
        if START not in full or END not in full or full.index(START)>full.index(END):
            return {'status':'EXISTING_UNMANAGED_STATE', 'message':'Will not overwrite .orbit/STATE.md owned by another workflow', 'revision':prior['revision']}
        prefix = full[:full.index(START)]
        suffix = full[full.index(END)+len(END):]
        new_body = prefix + header + suffix.lstrip('\n')
    else:
        new_body = '# Orbit session checkpoint\n\n'+header
    if len(new_body.encode('utf-8'))>MAX_STATE_BYTES:
        raise ValueError('Checkpoint is too large')
    if a.get('confirm_write') is not True:
        return {'status':'PREVIEW_ONLY', 'revision':prior['revision'], 'proposed':header}
    if a.get('expected_revision') != prior['revision']:
        return {'status':'STALE_REVISION', 'revision':prior['revision']}
    path = safe_checkpoint_path(root)
    path.parent.mkdir(exist_ok=True)
    # Existing symlinks remain prohibited. This is a single-user local test, not a
    # cross-process file-locking service: refresh revision and serialize writes.
    if path.exists() and path.is_symlink():
        raise ValueError('Symlink checkpoint forbidden')
    path.write_text(new_body, encoding='utf-8')
    return {'status':'SAVED', 'revision':hashlib.sha256(new_body.encode('utf-8')).hexdigest()}


def scan(a):
    root, project = project_root(a), project_key(a)
    candidates = ('README.md','docs/README.md','docs/ARCHITECTURE.md','ARCHITECTURE.md','PRD.md','REQUIREMENTS.md','ROADMAP.md','.orbit/STATE.md','.orbit/PROJECT.md')
    existing = [x for x in candidates if not (root / x).is_symlink() and (root/x).is_file()]
    return {'project': project, 'root': str(root), 'docs_found': existing, 'checkpoint': snapshot(root), 'notice':'Metadata only; not a full semantic document audit'}


def gate(a):
    checks = a.get('checks')
    if not isinstance(checks,list) or not checks:
        raise ValueError('checks must be nonempty list')
    missing = 0
    failed = 0
    for x in checks:
        if not isinstance(x,dict) or not x.get('id') or x.get('status') not in {'PASS','FAIL','NOT_RUN'}:
            raise ValueError('Invalid gate check')
        if x['status']=='PASS' and not str(x.get('evidence','')).strip():
            raise ValueError('PASS requires supplied evidence')
        missing += (x['status']=='NOT_RUN')
        failed += (x['status']=='FAIL')
    return {'gate':'REWORK' if failed else 'HOLD' if missing else 'GO', 'criterion_count':len(checks), 'evidence_is_unverified':True}


def schema(fields, required):
    return {'type':'object','properties':fields,'required':required,'additionalProperties':False}


def string(n=4000):
    return {'type':'string','minLength':1,'maxLength':n}

TOOLS = [
    {'name':'orbit_project_scan','description':'Read-only bounded project checkpoint and document metadata.', 'inputSchema':schema({'project_root':string(2000),'project':string(80)},['project_root','project'])},
    {'name':'orbit_project_resume','description':'Load current project state and project-scoped SQLite memories. Caller checks Git/tests separately.', 'inputSchema':schema({'project_root':string(2000),'project':string(80)},['project_root','project'])},
    {'name':'orbit_memory_save','description':'Preview/save one approved project-scoped memory; explicit confirm_write for persistence.', 'inputSchema':schema({'project':string(80),'key':string(160),'kind':{'type':'string','enum':sorted(KINDS)},'summary':string(4000),'source':string(1000),'evidence':{'type':'string','maxLength':4000},'importance':{'type':'integer','minimum':1,'maximum':5},'confirm_write':{'type':'boolean'}},['project','key','kind','summary','source'])},
    {'name':'orbit_memory_recall','description':'Read project-scoped SQLite memories, no cross-project recall.', 'inputSchema':schema({'project':string(80),'query':{'type':'string','maxLength':300},'limit':{'type':'integer','minimum':1,'maximum':20},'include_archived':{'type':'boolean'}},['project'])},
    {'name':'orbit_memory_archive','description':'Non-destructively archive a record on explicit approval.', 'inputSchema':schema({'project':string(80),'key':string(160),'reason':string(500),'confirm_write':{'type':'boolean'}},['project','key','reason'])},
    {'name':'orbit_project_checkpoint','description':'Preview or revision-guarded checkpoint update, without overwriting non-Orbit state.', 'inputSchema':schema({'project_root':string(2000),'project':string(80),'milestone':string(250),'gate':string(250),'last_step':string(350),'last_result':{'type':'string','enum':['PASS','FAIL','NOT_RUN','IN_PROGRESS','BLOCKED']},'evidence':string(1400),'next_step':string(350),'blockers':string(1000),'expected_revision':{'type':'string','maxLength':64},'confirm_write':{'type':'boolean'}},['project_root','project','milestone','gate','last_step','last_result','evidence','next_step'])},
    {'name':'orbit_gate_evaluate','description':'Evaluate caller-supplied criteria (not independent test verification).','inputSchema':schema({'checks':{'type':'array','minItems':1,'items':{'type':'object'}}},['checks'])},
    # Product Kit-inspired native task ledger; no Git actions, model spawning or implicit approvals.
    {'name':'orbit_task_plan','description':'Preview/register one scoped specialist task. Does NOT launch agents.','inputSchema':schema({'project_root':string(2000),'project':string(80),'task_key':string(80),'step':string(100),'role':{'type':'string','enum':sorted(orbit_tasks.ROLES)},'goal':string(1500),'reason':string(500),'write_paths':{'type':'array','maxItems':24,'items':{'type':'string'}},'depends_on':{'type':'array','maxItems':8,'items':{'type':'string'}},'confirm_write':{'type':'boolean'}},['project_root','project','task_key','step','role','goal','reason'])},
    {'name':'orbit_task_list','description':'List scoped task registry (read-only).','inputSchema':schema({'project_root':string(2000),'project':string(80),'limit':{'type':'integer','minimum':1,'maximum':40},'status':string(25)},['project_root','project'])},
    {'name':'orbit_task_reserve','description':'After actual host/user approval, reserve one native subagent slot. NO agent is spawned. Advisory caller approval reference; independent host permission still required.','inputSchema':schema({'project_root':string(2000),'project':string(80),'task_key':string(80),'expected_revision':{'type':'integer','minimum':1},'approval_reference':string(240),'confirm_write':{'type':'boolean'}},['project_root','project','task_key','expected_revision','approval_reference'])},
    {'name':'orbit_task_started','description':'Mark RESERVED task RUNNING only AFTER Antigravity confirms actual invoke_subagent and returns its reference. Does not invoke host.','inputSchema':schema({'project_root':string(2000),'project':string(80),'task_key':string(80),'expected_revision':{'type':'integer','minimum':1},'host_session':string(240),'confirm_write':{'type':'boolean'}},['project_root','project','task_key','expected_revision','host_session'])},
    {'name':'orbit_task_release','description':'Cancel a reservation only when native invocation did NOT start; cannot terminate a running agent.','inputSchema':schema({'project_root':string(2000),'project':string(80),'task_key':string(80),'expected_revision':{'type':'integer','minimum':1},'reason':string(500),'confirm_write':{'type':'boolean'}},['project_root','project','task_key','expected_revision','reason'])},
    {'name':'orbit_task_scope_check','description':'Check caller-supplied changed file paths against registered writable scope; independently inspect Git diff.','inputSchema':schema({'project_root':string(2000),'project':string(80),'task_key':string(80),'changed_paths':{'type':'array','maxItems':60,'items':{'type':'string'}}},['project_root','project','task_key','changed_paths'])},
    {'name':'orbit_task_report','description':'Record result reported by a native subagent; do NOT assume test evidence is verified.','inputSchema':schema({'project_root':string(2000),'project':string(80),'task_key':string(80),'expected_revision':{'type':'integer','minimum':1},'outcome':{'type':'string','enum':['REPORTED_DONE','FAILED','BLOCKED','CANCELLED']},'evidence':string(1600),'changed_paths':{'type':'array','maxItems':60,'items':{'type':'string'}},'confirm_write':{'type':'boolean'}},['project_root','project','task_key','expected_revision','outcome','evidence'])},
    {'name':'orbit_task_review','description':'Record separately inspected review result; never merge Git or independently attest evidence.','inputSchema':schema({'project_root':string(2000),'project':string(80),'task_key':string(80),'expected_revision':{'type':'integer','minimum':1},'verdict':{'type':'string','enum':['ACCEPT','REWORK']},'review_evidence':string(1600),'confirm_write':{'type':'boolean'}},['project_root','project','task_key','expected_revision','verdict','review_evidence'])},
]
TOOLS += [
    {'name':'orbit_capability_discover','description':'Read-only local skill and MCP config metadata inventory; never downloads, installs or executes anything.','inputSchema':schema({'project_root':string(2000)},['project_root'])},
    {'name':'orbit_capability_select','description':'Suggest reusable installed skill/tool matches and official research candidates for a task; external installs require owner review/approval.','inputSchema':schema({'project_root':string(2000),'objective':string(1500),'host_tools':{'type':'array','maxItems':80,'items':{'type':'string'}}},['project_root','objective'])},
    {'name':'orbit_preview_start','description':'PREVIEW or explicitly run a localhost dev server in this project; executes the supplied project command only with confirm_run. No public tunnel or deployment.','inputSchema':schema({'project_root':string(2000),'preview_id':string(40),'command':{'type':'array','minItems':1,'maxItems':20,'items':{'type':'string'}},'port':{'type':'integer','minimum':1024,'maximum':65535},'health_path':string(100),'confirm_run':{'type':'boolean'}},['project_root','preview_id','command','port'])},
    {'name':'orbit_preview_status','description':'Check running local preview readiness and bounded log tail for this MCP session. No browser simulation.','inputSchema':schema({'project_root':string(2000),'preview_id':string(40)},['project_root','preview_id'])},
    {'name':'orbit_preview_stop','description':'Stop only the locally spawned preview tracked by this MCP session, with explicit confirm_stop.','inputSchema':schema({'project_root':string(2000),'preview_id':string(40),'confirm_stop':{'type':'boolean'}},['project_root','preview_id'])},
    {'name':'orbit_browser_qa','description':'Perform approved loopback-only Playwright browser QA with installed Edge/Chrome or Chromium; bounded DOM actions, private screenshots and build gate results. Requires Python playwright; never downloads software.', 'inputSchema':schema({'project_root':string(2000),'project':string(80),'build_id':string(40),'preview_id':string(40),'viewport':{'type':'string','enum':['desktop','mobile']},'browser':{'type':'string','enum':['auto','msedge','chrome','chromium']},'actions':{'type':'array','maxItems':20,'items':{'type':'object'}},'confirm_run':{'type':'boolean'},'confirm_interactions':{'type':'boolean'}},['project_root','project','build_id','preview_id'])},
    {'name':'orbit_build_begin','description':'Preview or create durable app-building gates (PLAN, IMPLEMENT, PREVIEW, BROWSER_QA, REVIEW, CHECKPOINT, DONE). Does not start AI agents.', 'inputSchema':schema({'project_root':string(2000),'project':string(80),'build_id':string(40),'objective':string(1500),'confirm_write':{'type':'boolean'}},['project_root','project','build_id','objective'])},
    {'name':'orbit_build_status','description':'Read persistent app build stage and evidence, across host/MCP restarts.', 'inputSchema':schema({'project_root':string(2000),'project':string(80),'build_id':string(40)},['project_root','project','build_id'])},
    {'name':'orbit_build_advance','description':'Revision-guarded explicit stage advance; browser QA PASS requires a real Orbit-recorded Playwright PASS.', 'inputSchema':schema({'project_root':string(2000),'project':string(80),'build_id':string(40),'expected_revision':{'type':'integer','minimum':1},'outcome':{'type':'string','enum':['PASS','FAIL','BLOCKED']},'evidence':string(1600),'preview_id':string(40),'confirm_write':{'type':'boolean'}},['project_root','project','build_id','expected_revision','outcome','evidence'])}
]
TOOLS += [
 {'name':'orbit_intake_status','description':'Read guided product intake and progressive autonomy.', 'inputSchema':schema({'project_root':string(2000),'project':string(80)},['project_root','project'])},
 {'name':'orbit_intake_propose','description':'Save proposed product classification and interview questions, not user acceptance.', 'inputSchema':schema({'project_root':string(2000),'project':string(80),'profile':{'type':'object'},'questions':{'type':'array','maxItems':6},'expected_revision':{'type':'integer','minimum':1},'confirm_write':{'type':'boolean'}},['project_root','project','profile','questions'])},
 {'name':'orbit_intake_approve','description':'Record selected options or explicitly delegated recommended defaults; user consent is host-attested.', 'inputSchema':schema({'project_root':string(2000),'project':string(80),'expected_revision':{'type':'integer','minimum':1},'answers':{'type':'object'},'answer_source':{'type':'string','enum':['user_choices','user_delegated_defaults']},'user_reference':string(240),'confirm_write':{'type':'boolean'}},['project_root','project','expected_revision','answers','answer_source','user_reference'])},
 {'name':'orbit_autonomy_review','description':'Recommend maturity-based guided/assisted/trusted mode; no automatic promotion.', 'inputSchema':schema({'project_root':string(2000),'project':string(80),'level':{'type':'string','enum':['guided','assisted','trusted']},'expected_revision':{'type':'integer','minimum':1},'user_reference':string(240),'confirm_write':{'type':'boolean'}},['project_root','project'])},
 {'name':'orbit_docs_audit','description':'Read-only, repeatable project documentation inventory and growth signals.', 'inputSchema':schema({'project_root':string(2000),'project':string(80),'signals':{'type':'array','maxItems':8,'items':{'type':'string'}}},['project_root','project'])},
]
TOOL_MAP = {x['name']:x['inputSchema'] for x in TOOLS}


def validate_value(value, spec, path='arguments'):
    """Validate the schema subset used by TOOLS; domain checks stay in handlers."""
    typ = spec.get('type')
    expected = {'string': str, 'integer': int, 'boolean': bool,
                'array': list, 'object': dict}
    if typ in expected and type(value) is not expected[typ]:
        raise ValueError(f'Invalid {path}: expected {typ}')
    if 'enum' in spec and value not in spec['enum']:
        raise ValueError(f'Invalid {path}: unsupported value')
    if typ == 'string':
        if len(value) < spec.get('minLength', 0) or ('maxLength' in spec and len(value) > spec['maxLength']):
            raise ValueError(f'Invalid {path}: text length')
    elif typ == 'integer':
        if ('minimum' in spec and value < spec['minimum']) or ('maximum' in spec and value > spec['maximum']):
            raise ValueError(f'Invalid {path}: integer range')
    elif typ == 'array':
        if len(value) < spec.get('minItems', 0) or ('maxItems' in spec and len(value) > spec['maxItems']):
            raise ValueError(f'Invalid {path}: array length')
        if 'items' in spec:
            for index, item in enumerate(value):
                validate_value(item, spec['items'], f'{path}[{index}]')
    elif typ == 'object':
        properties = spec.get('properties', {})
        if spec.get('additionalProperties') is False and set(value) - set(properties):
            raise ValueError(f'Unexpected properties in {path}')
        for key in spec.get('required', []):
            if key not in value:
                raise ValueError(f'Missing {path}.{key}')
        for key, item in value.items():
            if key in properties:
                validate_value(item, properties[key], f'{path}.{key}')


def validate(name, args):
    if not isinstance(name, str) or name not in TOOL_MAP:
        raise ValueError('Unknown tool')
    validate_value(args, TOOL_MAP[name])


def execute(conn, name, a):
    validate(name,a)
    if name in {'orbit_intake_status','orbit_intake_propose','orbit_intake_approve','orbit_autonomy_review','orbit_docs_audit'}:
        a={**a,'project':project_key(a)}
        root=project_root(a)
        handlers={'orbit_intake_status':orbit_intake.status,
                  'orbit_intake_propose':orbit_intake.propose,
                  'orbit_intake_approve':orbit_intake.approve,
                  'orbit_autonomy_review':orbit_intake.autonomy,
                  'orbit_docs_audit':orbit_intake.docs_audit}
        return handlers[name](conn,root,a)
    if name=='orbit_build_begin':
        a={**a,'project':project_key(a)}
        root=project_root(a)
        if not orbit_build.get(conn,root,a) and orbit_intake.status(conn,root,a)['status']!='APPROVED':
            return {'status':'HOLD','reason':'Fresh project requires a completed interview before build planning',
                    'next':['orbit_intake_propose','ask the user or obtain explicit delegation of defaults','orbit_intake_approve']}
        return orbit_build.begin(conn,root,a)
    if name=='orbit_build_status':
        a={**a,'project':project_key(a)}
        return orbit_build.current(conn,project_root(a),a)
    if name=='orbit_build_advance':
        a={**a,'project':project_key(a)}
        return orbit_build.advance(conn,project_root(a),a)
    if name=='orbit_browser_qa':
        a={**a,'project':project_key(a)}
        root=project_root(a)
        orbit_build.validate_key(a['build_id'])
        run=orbit_build.get(conn,root,a)
        if not run or run['stage']!='BROWSER_QA':
            return {'status':'HOLD','reason':'Create the build and reach BROWSER_QA stage before automated verification.'}
        result=orbit_browser.run(root,a,orbit_preview)
        if result['status'] in {'PASS','FAIL'}:
            orbit_build.save_browser(conn,root,a,result)
        return result
    if name=='orbit_preview_start': return orbit_preview.start(project_root(a), a)
    if name=='orbit_preview_status': return orbit_preview.status(project_root(a), a)
    if name=='orbit_preview_stop': return orbit_preview.stop(project_root(a), a)
    if name=='orbit_capability_discover': return orbit_capabilities.discover(project_root(a))
    if name=='orbit_capability_select': return orbit_capabilities.select(project_root(a),a['objective'],a.get('host_tools',[]))
    if name=='orbit_project_scan': return scan(a)
    if name=='orbit_project_resume':
        status=scan(a)
        status['memories']=memory_recall(conn,{'project':status['project'],'limit':5})
        status['intake']=orbit_intake.status(conn,project_root(a),a)
        return status
    if name=='orbit_memory_save': return memory_save(conn,a)
    if name=='orbit_memory_recall': return memory_recall(conn,a)
    if name=='orbit_memory_archive': return memory_archive(conn,a)
    if name=='orbit_project_checkpoint': return checkpoint(conn,a)
    if name=='orbit_gate_evaluate': return gate(a)
    if name.startswith('orbit_task_'):
        root = project_root(a)
        a = {**a, 'project': project_key(a)}
        handlers = {'orbit_task_plan':orbit_tasks.plan,'orbit_task_list':orbit_tasks.read_tasks,
                    'orbit_task_reserve':orbit_tasks.reserve,'orbit_task_started':orbit_tasks.started,
                    'orbit_task_release':orbit_tasks.release,'orbit_task_scope_check':orbit_tasks.scope_check,
                    'orbit_task_report':orbit_tasks.reported,'orbit_task_review':orbit_tasks.review}
        if name in handlers: return handlers[name](conn,a,root)
    raise ValueError('Unsupported tool')


def handle(conn, message):
    if not isinstance(message, dict):
        return {'jsonrpc':'2.0','id':None,'error':{'code':-32600,'message':'Expected object'}}
    mid=message.get('id')
    if message.get('jsonrpc') != '2.0' or not isinstance(message.get('method'),str):
        return {'jsonrpc':'2.0','id':mid,'error':{'code':-32600,'message':'Invalid request'}}
    if mid is None: return None
    method=message['method']
    try:
        if method=='initialize':
            params=message.get('params',{})
            if not isinstance(params, dict):
                raise ValueError('Expected params object')
            ver=params.get('protocolVersion','2025-11-25')
            if not isinstance(ver, str) or ver not in {'2025-11-25','2025-06-18','2025-03-26'}:
                raise ValueError('Unsupported protocol version')
            return {'jsonrpc':'2.0','id':mid,'result':{'protocolVersion':ver,'capabilities':{'tools':{'listChanged':False}},'serverInfo':{'name':'orbit-native-local','version':VERSION}}}
        if method=='ping': return {'jsonrpc':'2.0','id':mid,'result':{}}
        if method=='tools/list': return {'jsonrpc':'2.0','id':mid,'result':{'tools':TOOLS}}
        if method=='tools/call':
            p=message.get('params')
            if not isinstance(p,dict): raise ValueError('Expected params object')
            try:
                out=execute(conn,p.get('name'),p.get('arguments',{}))
                return {'jsonrpc':'2.0','id':mid,'result':{'content':[{'type':'text','text':json.dumps(out,ensure_ascii=False)}],'isError':False}}
            except (ValueError,TypeError,KeyError,OSError,UnicodeError) as exc:
                return {'jsonrpc':'2.0','id':mid,'result':{'content':[{'type':'text','text':str(exc)}],'isError':True}}
        return {'jsonrpc':'2.0','id':mid,'error':{'code':-32601,'message':'Method not found'}}
    except (ValueError,TypeError) as exc:
        return {'jsonrpc':'2.0','id':mid,'error':{'code':-32602,'message':str(exc)}}


def main():
    conn=db_connect()
    try:
        while True:
            raw = sys.stdin.buffer.readline(MAX_REQUEST_BYTES + 1)
            if not raw:
                break
            if len(raw)>MAX_REQUEST_BYTES:
                # Drain this frame in bounded chunks so the next request stays aligned.
                while raw and not raw.endswith(b'\n'):
                    raw = sys.stdin.buffer.readline(MAX_REQUEST_BYTES + 1)
                response={'jsonrpc':'2.0','id':None,'error':{'code':-32600,'message':'Request too large'}}
            else:
                try:
                    message=json.loads(raw)
                    response=handle(conn,message) if isinstance(message,dict) else {'jsonrpc':'2.0','id':None,'error':{'code':-32600,'message':'Expected object'}}
                except (UnicodeError,ValueError,RecursionError):
                    response={'jsonrpc':'2.0','id':None,'error':{'code':-32700,'message':'Parse error'}}
            if response is not None:
                sys.stdout.write(json.dumps(response,ensure_ascii=False,separators=(',',':'))+'\n')
                sys.stdout.flush()
    finally:
        conn.close()

if __name__=='__main__':
    main()
