"""ORBIT native-agent task ledger. Pure bookkeeping; never spawns or merges.

SQLite coordination for host-native subagents (any MCP-capable host). All approval/session,
changed-file, and test evidence is CALLER-REPORTED; MCP does not authenticate the
human principal, inspect Git, or enforce the host's sandbox. Permission remains
with the host, and review requires separate actual source/test inspection.
"""
from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROLES = {'frontend','backend','architect','data','devops','qa','security','ux',
         'research','reviewer','writer','integrator'}
ACTIVE = ('RESERVED','RUNNING')
RETRYABLE = ('PLANNED','REWORK','FAILED','BLOCKED')
# Agent/host control files are persistence vectors for prompt injection; humans edit them directly.
PROTECTED_SEGMENTS = {'.git','.orbit','.agents','.env','id_rsa','id_ed25519','credentials.json',
                      '.claude','.codex','.gemini','.cursor','.vscode','.mcp.json',
                      'claude.md','agents.md','gemini.md'}
MAX_CONCURRENT = 2
MAX_PER_STEP = 3
MAX_PER_DAY = 12


def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def setup(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS orbit_agent_tasks (
        project TEXT NOT NULL, project_root TEXT NOT NULL, task_key TEXT NOT NULL,
        step TEXT NOT NULL, role TEXT NOT NULL, goal TEXT NOT NULL, reason TEXT NOT NULL,
        write_paths TEXT NOT NULL, depends_on TEXT NOT NULL,
        status TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
        approval_reference TEXT NOT NULL DEFAULT '', reserved_at TEXT NOT NULL DEFAULT '', host_session TEXT NOT NULL DEFAULT '',
        evidence TEXT NOT NULL DEFAULT '', review_evidence TEXT NOT NULL DEFAULT '',
        changed_paths TEXT NOT NULL DEFAULT '[]', note TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
        PRIMARY KEY(project,project_root,task_key))''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_orbit_agent_tasks_scope ON orbit_agent_tasks(project_root,status)')
    # Append-only attempt identity, separate from the current mutable task state.
    # Never replace or backfill historical task rows. Old untracked rows are
    # counted conservatively as a single attempt (see _attempt_usage).
    conn.execute('''CREATE TABLE IF NOT EXISTS orbit_task_attempts (
        project TEXT NOT NULL, project_root TEXT NOT NULL, task_key TEXT NOT NULL,
        attempt_number INTEGER NOT NULL, step TEXT NOT NULL,
        reserved_at TEXT NOT NULL, disposition TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        PRIMARY KEY(project,project_root,task_key,attempt_number))''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_orbit_attempt_step ON orbit_task_attempts(project,project_root,step,disposition)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_orbit_attempt_day ON orbit_task_attempts(project_root,reserved_at,disposition)')
    conn.commit()


def text(a, field, limit=1000, minimum=1):
    value=a.get(field)
    if not isinstance(value,str) or len(value)>limit or len(value.strip())<minimum:
        raise ValueError(f'{field} must be text of {minimum}..{limit} characters')
    return value.strip()


def key(a):
    v=text(a,'task_key',80)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}',v):
        raise ValueError('task_key must be a stable slug')
    return v


def _norm(path):
    return unicodedata.normalize('NFC',path).casefold()


def _scopes(items, *, limit=24, allow_protected=False):
    if not isinstance(items,list) or len(items)>limit:
        raise ValueError('Paths must be a bounded array')
    result=[]
    for item in items:
        if not isinstance(item,str) or not 1<=len(item)<=240 or '\\' in item or '\x00' in item:
            raise ValueError('Paths must be repository-relative forward-slash paths')
        directory=item.endswith('/')
        bare=item.rstrip('/')
        segments=bare.split('/')
        if any(s in ('','.','..') for s in segments) or bare.startswith('/') or ':' in bare:
            raise ValueError('Absolute, traversal and empty path segments are forbidden')
        # Windows ignores trailing dots/spaces, so '.git ' addresses '.git'.
        guarded=[unicodedata.normalize('NFC',s).rstrip(' .').casefold() for s in segments]
        if not allow_protected and any(g in PROTECTED_SEGMENTS or g.startswith('.env.') for g in guarded):
            raise ValueError('Cannot assign protected repository/control/credential paths')
        canonical='/'.join(segments) + ('/' if directory else '')
        if canonical not in result: result.append(canonical)
    return sorted(result)


def _overlaps(x,y):
    x,y=_norm(x),_norm(y)
    if x==y: return True
    xdir=x.endswith('/'); ydir=y.endswith('/')
    return (xdir and y.startswith(x)) or (ydir and x.startswith(y))


def _collisions(a,b):
    return [(x,y) for x in a for y in b if _overlaps(x,y)]


def _row(conn, a, root):
    r=conn.execute('SELECT * FROM orbit_agent_tasks WHERE project=? AND project_root=? AND task_key=?',
                   (a['project'],str(root),key(a))).fetchone()
    if r is None: raise ValueError('Task not found in selected project')
    return dict(r)


def public(row):
    d=dict(row)
    for field in ('write_paths','depends_on','changed_paths'):
        d[field]=json.loads(d[field])
    d['host_evidence_unverified']=True
    if d.get('note','').startswith('IMPORTED_HISTORY_UNVERIFIED;'):
        d['imported_history_unverified']=True
        d['host_session_is_historical']=True
    return d


def spec(a):
    project=text(a,'project',80)
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}',project):
        raise ValueError('Invalid project slug')
    step=text(a,'step',100)
    role=text(a,'role',40)
    if role not in ROLES: raise ValueError('Unknown specialist role')
    goal=text(a,'goal',1500,20)
    reason=text(a,'reason',500,20)
    paths=_scopes(a.get('write_paths',[]))
    deps=a.get('depends_on',[])
    if not isinstance(deps,list) or len(deps)>8 or any(not isinstance(v,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}',v) for v in deps):
        raise ValueError('Invalid dependency task keys')
    deps=list(dict.fromkeys(deps))
    if key(a) in deps: raise ValueError('Task cannot depend on itself')
    return project,step,role,goal,reason,paths,deps


def _creates_cycle(conn,project,root,task,deps):
    """True when any dependency already (transitively) depends on this task."""
    seen=set(); stack=list(deps)
    while stack:
        cur=stack.pop()
        if cur==task: return True
        if cur in seen: continue
        seen.add(cur)
        row=conn.execute('SELECT depends_on FROM orbit_agent_tasks WHERE project=? AND project_root=? AND task_key=?',
                         (project,str(root),cur)).fetchone()
        if row: stack.extend(json.loads(row['depends_on']))
    return False


def _serialize(x):
    return json.dumps(x,sort_keys=True,separators=(',',':'))


def plan(conn,a,root):
    project,step,role,goal,reason,paths,deps=spec(a)
    current=conn.execute('SELECT * FROM orbit_agent_tasks WHERE project=? AND project_root=? AND task_key=?',
                         (project,str(root),key(a))).fetchone()
    payload={'project':project,'project_root':str(root),'task_key':key(a),'step':step,'role':role,
             'goal':goal,'reason':reason,'write_paths':paths,'depends_on':deps}
    if current:
        old=public(current)
        if all(payload[k]==old[k] for k in payload):
            return {'status':'ALREADY_REGISTERED','task':old}
        return {'status':'CONFLICT','message':'Existing task key has a different specification; never overwrite it','task':old}
    if _creates_cycle(conn,project,root,key(a),deps):
        raise ValueError('Dependency cycle: a listed dependency already depends on this task')
    if a.get('confirm_write') is not True:
        return {'status':'PREVIEW_ONLY','proposed_task':payload,'agent_spawned':False}
    t=utc_now()
    with conn:
        conn.execute('''INSERT INTO orbit_agent_tasks(project,project_root,task_key,step,role,goal,reason,
                       write_paths,depends_on,status,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)''',
                     (project,str(root),key(a),step,role,goal,reason,_serialize(paths),_serialize(deps),'PLANNED',t,t))
    return {'status':'PLANNED','task':public(_row(conn,a,root)),'agent_spawned':False}


def read_tasks(conn,a,root):
    max_results=a.get('limit',20)
    if type(max_results) is not int or not 1<=max_results<=40:
        raise ValueError('limit must be 1..40')
    status=a.get('status','ALL')
    if status not in ('ALL','PLANNED','RESERVED','RUNNING','REPORTED_DONE','REVIEW_ACCEPTED','REWORK','FAILED','BLOCKED','CANCELLED'):
        raise ValueError('Unknown status filter')
    q='SELECT * FROM orbit_agent_tasks WHERE project=? AND project_root=?'
    params=[a['project'],str(root)]
    if status!='ALL': q+=' AND status=?';params.append(status)
    q+=' ORDER BY created_at DESC,task_key LIMIT ?';params.append(max_results)
    rows=[public(r) for r in conn.execute(q,params)]
    return {'tasks':rows,'count':len(rows),'project':a['project'],'no_host_execution':True}


def _revision(a,old):
    rev=a.get('expected_revision')
    if type(rev) is not int or rev != old['revision']:
        return {'status':'STALE_REVISION','task':public(old)}
    return None


def _update(conn, old, status, **fields):
    sets=['status=?','revision=revision+1','updated_at=?']
    vals=[status,utc_now()]
    for k,v in fields.items():
        sets.append(k+'=?'); vals.append(v)
    vals.extend([old['project'],old['project_root'],old['task_key'],old['revision']])
    result=conn.execute('UPDATE orbit_agent_tasks SET '+', '.join(sets)+' WHERE project=? AND project_root=? AND task_key=? AND revision=?',vals)
    if result.rowcount!=1: raise ValueError('Task revision conflict: refresh')
    return dict(conn.execute('SELECT * FROM orbit_agent_tasks WHERE project=? AND project_root=? AND task_key=?',
                             (old['project'],old['project_root'],old['task_key'])).fetchone())


def _attempt_usage(conn, project, root, step, day):
    """Count reservations per attempt, not merely per task key.

    Unstarted slots released without host execution are refunded. Existing
    tasks from before this table have no reconstructible attempt history: count
    each still-relevant task once until it has a first tracked reservation.
    This is a local advisory budget, not cross-PC or host quota enforcement.
    """
    path=str(root)
    consuming="disposition<>'RELEASED_UNUSED'"
    n_step=conn.execute(
        "SELECT COUNT(*) FROM orbit_task_attempts WHERE project=? AND project_root=? AND step=? AND "+consuming,
        (project,path,step)).fetchone()[0]
    n_day=conn.execute(
        "SELECT COUNT(*) FROM orbit_task_attempts WHERE project_root=? AND substr(reserved_at,1,10)=? AND "+consuming,
        (path,day)).fetchone()[0]
    legacy="""t.status<>'PLANNED'
              AND NOT (t.status IN ('CANCELLED','BLOCKED') AND t.host_session='')
              AND NOT EXISTS (
                SELECT 1 FROM orbit_task_attempts a
                WHERE a.project=t.project AND a.project_root=t.project_root
                  AND a.task_key=t.task_key)"""
    n_step+=conn.execute(
        "SELECT COUNT(*) FROM orbit_agent_tasks t WHERE t.project=? AND t.project_root=? AND t.step=? AND "+legacy,
        (project,path,step)).fetchone()[0]
    n_day+=conn.execute(
        "SELECT COUNT(*) FROM orbit_agent_tasks t WHERE t.project_root=? AND substr(t.reserved_at,1,10)=? AND "+legacy,
        (path,day)).fetchone()[0]
    return n_step,n_day


def _record_reservation(conn, old, when):
    """Record each approved reservation atomically under reserve's IMMEDIATE lock."""
    params=(old['project'],old['project_root'],old['task_key'])
    number=conn.execute(
        '''SELECT COALESCE(MAX(attempt_number),0) FROM orbit_task_attempts
           WHERE project=? AND project_root=? AND task_key=?''',params).fetchone()[0]
    if number==0 and old['status']!='PLANNED' and not (
            old['status'] in ('CANCELLED','BLOCKED') and not old['host_session']):
        # We cannot reconstruct past tries: preserve one unverified legacy
        # observation instead of pretending a long-lived task was never run.
        timestamp=old['reserved_at'] or when
        conn.execute('''INSERT INTO orbit_task_attempts
            (project,project_root,task_key,attempt_number,step,reserved_at,disposition,updated_at)
            VALUES(?,?,?,?,?,?,?,?)''',
            (*params,1,old['step'],timestamp,'LEGACY_UNVERIFIED',when))
        number=1
    next_number=number+1
    conn.execute('''INSERT INTO orbit_task_attempts
        (project,project_root,task_key,attempt_number,step,reserved_at,disposition,updated_at)
        VALUES(?,?,?,?,?,?,?,?)''',
        (*params,next_number,old['step'],when,'RESERVED',when))
    return next_number


def _mark_latest_attempt(conn, old, disposition):
    """Move only the most recent recorded attempt to a terminal observation."""
    conn.execute('''UPDATE orbit_task_attempts SET disposition=?, updated_at=?
        WHERE project=? AND project_root=? AND task_key=?
          AND attempt_number=(SELECT MAX(attempt_number) FROM orbit_task_attempts
            WHERE project=? AND project_root=? AND task_key=?)''',
        (disposition,utc_now(),old['project'],old['project_root'],old['task_key'],
         old['project'],old['project_root'],old['task_key']))


def reserve(conn,a,root):
    if a.get('confirm_write') is not True:
        return {'status':'PREVIEW_ONLY','message':'Reservation requires explicit approved write, no native agent is launched'}
    approval=text(a,'approval_reference',240,8)
    conn.execute('BEGIN IMMEDIATE')
    try:
        old=_row(conn,a,root)
        conflict=_revision(a,old)
        if conflict: conn.rollback();return conflict
        if old['status'] not in RETRYABLE: raise ValueError('Only PLANNED, REWORK, FAILED or BLOCKED tasks can reserve')
        for dep in json.loads(old['depends_on']):
            item=conn.execute('SELECT status FROM orbit_agent_tasks WHERE project=? AND project_root=? AND task_key=?',
                              (old['project'],old['project_root'],dep)).fetchone()
            if not item or item['status']!='REVIEW_ACCEPTED':
                raise ValueError('Dependency is not review-accepted: '+dep)
        active=[dict(x) for x in conn.execute('SELECT * FROM orbit_agent_tasks WHERE project_root=? AND status IN (\'RESERVED\',\'RUNNING\')',(str(root),))]
        if len(active)>=MAX_CONCURRENT: raise ValueError('Active native-agent reservations reached the cap of 2')
        for other in active:
            conflicts=_collisions(json.loads(old['write_paths']),json.loads(other['write_paths']))
            if conflicts: raise ValueError(f'Overlapping writable scopes with {other["task_key"]}: {conflicts}')
        today=utc_now()
        stepcount,daycount=_attempt_usage(conn,old['project'],root,old['step'],today[:10])
        if stepcount>=MAX_PER_STEP: raise ValueError('Per-step agent budget exhausted (3 attempts)')
        if daycount>=MAX_PER_DAY: raise ValueError('Daily agent budget exhausted (12 attempts)')
        attempt=_record_reservation(conn,old,today)
        out=_update(conn,old,'RESERVED',approval_reference=approval,reserved_at=today)
        conn.commit()
        return {'status':'RESERVED','task':public(out),'agent_spawned':False,
                'attempt_number':attempt,
                'attempt_budget':{'step_used':stepcount+1,'step_limit':MAX_PER_STEP,
                                  'day_used':daycount+1,'day_limit':MAX_PER_DAY,
                                  'legacy_history_may_be_incomplete':True},
                'next':'Invoke the native subagent through the host native subagent tools, then mark_started using the real host session reference. Release this reservation if invocation fails.',
                'permission_note':'approval_reference is caller-supplied, not cryptographically authenticated by MCP.'}
    except Exception:
        conn.rollback();raise


def started(conn,a,root):
    if a.get('confirm_write') is not True: return {'status':'PREVIEW_ONLY'}
    ref=text(a,'host_session',240,8)
    with conn:
        old=_row(conn,a,root)
        conflict=_revision(a,old)
        if conflict:return conflict
        if old['status']!='RESERVED': raise ValueError('Task must be RESERVED before host confirms execution')
        out=_update(conn,old,'RUNNING',host_session=ref)
        _mark_latest_attempt(conn,old,'HOST_REPORTED_STARTED')
    return {'status':'RUNNING_REPORTED','task':public(out),'host_session_verified':False}


def release(conn,a,root):
    if a.get('confirm_write') is not True:return {'status':'PREVIEW_ONLY'}
    why=text(a,'reason',500,10)
    with conn:
        old=_row(conn,a,root)
        conflict=_revision(a,old)
        if conflict:return conflict
        if old['status'] not in ('PLANNED','RESERVED'): raise ValueError('Only unused PLANNED or RESERVED tasks can release; running tasks must be stopped in the host')
        out=_update(conn,old,'CANCELLED',note=why)
        if old['status']=='RESERVED' and not old['host_session']:
            _mark_latest_attempt(conn,old,'RELEASED_UNUSED')
    return {'status':'CANCELLED','task':public(out),'agent_stopped_by_mcp':False}


def scope_report(assigned,changed):
    changes=_scopes(changed,limit=60,allow_protected=True)
    violation=[p for p in changes if not any(_norm(p)==_norm(s) or (s.endswith('/') and _norm(p).startswith(_norm(s))) for s in assigned)]
    return {'allowed':not violation,'changed_paths':changes,'outside_scope':violation,
            'note':'Caller-supplied changed_paths; inspect the actual Git diff independently.'}


def scope_check(conn,a,root):
    old=_row(conn,a,root)
    return {'task_key':old['task_key'],**scope_report(json.loads(old['write_paths']),a.get('changed_paths',[]))}


def reported(conn,a,root):
    if a.get('confirm_write') is not True: return {'status':'PREVIEW_ONLY'}
    outcome=text(a,'outcome',40)
    if outcome not in ('REPORTED_DONE','FAILED','BLOCKED','CANCELLED'):
        raise ValueError('Outcome must be REPORTED_DONE, FAILED, BLOCKED or CANCELLED')
    evidence=text(a,'evidence',1600,12)
    paths=_scopes(a.get('changed_paths',[]),limit=60,allow_protected=True)
    with conn:
        old=_row(conn,a,root)
        conflict=_revision(a,old)
        if conflict: return conflict
        if old['status']!='RUNNING': raise ValueError('Only RUNNING tasks can report an outcome')
        out=_update(conn,old,outcome,evidence=evidence,changed_paths=_serialize(paths))
        _mark_latest_attempt(conn,old,'HOST_REPORTED_'+outcome)
    check=scope_report(json.loads(old['write_paths']),paths)
    return {'status':outcome,'task':public(out),'scope_report':check,
            'verification':'NOT_VERIFIED_BY_MCP','next':'Inspect actual Git diff/tests; review separately before accepting dependencies or merging.'}


def review(conn,a,root):
    if a.get('confirm_write') is not True: return {'status':'PREVIEW_ONLY'}
    verdict=text(a,'verdict',20)
    if verdict not in ('ACCEPT','REWORK'):raise ValueError('Invalid review verdict')
    evidence=text(a,'review_evidence',1600,20)
    with conn:
        old=_row(conn,a,root)
        conflict=_revision(a,old)
        if conflict:return conflict
        if old['status']!='REPORTED_DONE': raise ValueError('Only reported completed work may be reviewed')
        scope=scope_report(json.loads(old['write_paths']),json.loads(old['changed_paths']))
        if verdict=='ACCEPT' and not scope['allowed']:
            raise ValueError('Cannot accept scope violations; inspect, revert or explicitly re-plan first')
        out=_update(conn,old,'REVIEW_ACCEPTED' if verdict=='ACCEPT' else 'REWORK',review_evidence=evidence)
    return {'status':out['status'],'task':public(out),'verification':'REVIEWER_REPORTED_ONLY',
            'git_merge_performed':False,'warning':'Human/host confirmation and real diff/test inspection are required; the MCP does not attest to evidence.'}
