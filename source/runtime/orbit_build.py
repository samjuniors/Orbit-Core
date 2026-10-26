"""Durable, version-checked app build gate ledger (no AI agent executor).

Host coding agents do work; this ledger records evidence and required next gates
across MCP restarts. A reported code/test result is not independently verified.
"""
from __future__ import annotations
import json
import sqlite3
import orbit_decisions
from datetime import datetime,timezone

STAGES=('RESEARCH','PLAN','IMPLEMENT','VERIFY','PREVIEW','BROWSER_QA','REVIEW','CHECKPOINT','DONE')
# Old build rows retain STAGES exactly. New approved product types persist an
# explicit frozen per-build flow so later interview edits cannot rewrite history.
FLOWS=orbit_decisions.FLOWS

def flow_for(row):
    if row is None:return STAGES
    try:
        value=json.loads(row['evidence_json']).get('__orbit_flow')
    except (KeyError,TypeError,ValueError):
        return STAGES
    if isinstance(value,list) and tuple(value) in FLOWS.values() and row['stage'] in value:
        return tuple(value)
    return STAGES

def flow_for_project(conn,root,a):
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='orbit_project_intake'").fetchone():
        return STAGES
    r=conn.execute("SELECT status,profile_json FROM orbit_project_intake WHERE project=? AND root=?",
                   (a['project'],str(root))).fetchone()
    if not r or r['status']!='APPROVED':return STAGES
    try:kind=json.loads(r['profile_json'])['type']
    except (KeyError,ValueError,TypeError):return STAGES
    category=('native' if kind in {'mobile-app','desktop-app'} else
              'library' if kind in {'cli','sdk-library','plugin-mcp','api-service','data-automation'} else
              'platform' if kind=='os-platform' else 'web')
    return FLOWS[category]


def now(): return datetime.now(timezone.utc).isoformat(timespec='seconds')

def setup(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS build_runs(
        project TEXT NOT NULL, root TEXT NOT NULL, build_id TEXT NOT NULL,
        stage TEXT NOT NULL, revision INTEGER NOT NULL, objective TEXT NOT NULL,
        evidence_json TEXT NOT NULL, updated_at TEXT NOT NULL,
        PRIMARY KEY(project,root,build_id))''')
    conn.commit()

def validate_key(s):
    import re
    if not isinstance(s,str) or not re.fullmatch(r'[a-z][a-z0-9-]{0,39}',s):
        raise ValueError('build_id must be a lowercase slug')
    return s

def get(conn,root,a):
    key=validate_key(a['build_id'])
    row=conn.execute('SELECT * FROM build_runs WHERE project=? AND root=? AND build_id=?',
                    (a['project'],str(root),key)).fetchone()
    return dict(row) if row else None

def valid_approved_plan(evidence):
    """Host-reported approval + bounded task breakdown, not authenticated user consent."""
    try:
        doc=json.loads(evidence)
    except (ValueError,TypeError):
        return False
    if not isinstance(doc,dict) or set(doc)!={'title','summary','tasks','approval_method','approval_reference'}:
        return False
    if any(not isinstance(doc.get(k),str) or not 8<=len(doc[k].strip())<=350
           for k in ('title','summary')):
        return False
    if doc.get('approval_method') not in ('user_approved_plan','user_delegated_build'):
        return False
    if not isinstance(doc.get('approval_reference'),str) or not 8<=len(doc['approval_reference'])<=240:
        return False
    tasks=doc.get('tasks')
    return isinstance(tasks,list) and 1<=len(tasks)<=12 and all(
        isinstance(t,str) and 5<=len(t)<=140 for t in tasks)


def task_progress(conn,project,root):
    """Summary of persisted task ledger; never imply a host agent executed anything."""
    counts={}
    # The build ledger can be used stand-alone by test harnesses and earlier
    # installs before the specialist task table has been initialized.
    if not conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='orbit_agent_tasks'").fetchone():
        return {'registered':0,'finished':0,'counts':{},'completion_percent':None}
    for row in conn.execute(
        'SELECT status,COUNT(*) AS n FROM orbit_agent_tasks WHERE project=? AND project_root=? GROUP BY status',
        (project,str(root))):
        counts[row['status']]=row['n']
    if not counts:
        return {'registered':0,'finished':0,'counts':{},'completion_percent':None}
    total=sum(counts.values())
    finished=counts.get('REVIEW_ACCEPTED',0)
    return {'registered':total,'finished':finished,'counts':counts,
            'completion_percent':round(finished*100/total)}


def recovery_brief(conn, root, project):
    """Small, read-only recover/continue view derived from actual local records."""
    rows=conn.execute(
        '''SELECT build_id,stage,revision,objective,updated_at,evidence_json
           FROM build_runs WHERE project=? AND root=?
           ORDER BY updated_at DESC,build_id LIMIT 12''',
        (project,str(root))).fetchall()
    all_builds=[dict(x) for x in rows]
    active=[x for x in all_builds if x['stage']!='DONE']
    progress=task_progress(conn,project,root)
    tasks=[]
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='orbit_agent_tasks'").fetchone():
        tasks=[{'task_key':x['task_key'],'status':x['status'],
                'step':x['step'],'role':x['role'],'goal':x['goal'][:180]}
               for x in conn.execute(
                   '''SELECT task_key,status,step,role,goal FROM orbit_agent_tasks
                      WHERE project=? AND project_root=? AND status<>'REVIEW_ACCEPTED'
                      ORDER BY updated_at DESC LIMIT 6''',(project,str(root)))]
    if len(active)>1:
        return {'status':'NEEDS_BUILD_SELECTION',
                'builds':[{'build_id':x['build_id'],'stage':x['stage'],'revision':x['revision']}
                          for x in active[:8]],
                'next':'Select a build ID; do not guess which parallel build to resume.',
                'task_progress':progress,'pending_tasks':tasks,
                'evidence_source':'persisted_local_sqlite'}
    if not active:
        return {'status':'ALL_DONE' if all_builds else 'NO_BUILD',
                'last_completed_build':all_builds[0]['build_id'] if all_builds else None,
                'next':'For a new objective, inspect existing project/intake and start an approved new build; never replay finished work.',
                'task_progress':progress,'pending_tasks':tasks,
                'evidence_source':'persisted_local_sqlite'}
    selected=active[0]
    next_by_stage={
        'RESEARCH':'Inspect only relevant code/docs, compare reuse candidates, record sources and risks; never re-run old research.',
        'PLAN':'Present a concise editable task plan and ask for actual approval or explicit build delegation.',
        'IMPLEMENT':'Resume authorized scoped tasks; inspect only changed files and run targeted checks.',
        'VERIFY':'Run real tests/security and business-rule edge cases; record actual commands and exit codes.',
        'PREVIEW':'Confirm permission and start a managed loopback preview; HTTP readiness is not QA.',
        'BROWSER_QA':'Run approved real browser interactions and capture failures/screenshots.',
        'REVIEW':'Independently inspect changes, test evidence, open findings and any user-only milestone tests.',
        'CHECKPOINT':'Save the next step, blockers and verified result in Orbit-managed .orbit/STATE.md.',
    }
    ev=json.loads(selected['evidence_json'])
    blockers=[{'stage':stage,'outcome':v.get('outcome'),
               'evidence':str(v.get('evidence',''))[:200]}
              for stage,v in ev.items() if isinstance(v,dict) and
              v.get('outcome') in ('FAIL','BLOCKED')][:4]
    return {'status':'RESUME','build_id':selected['build_id'],'stage':selected['stage'],
            'revision':selected['revision'],'next':next_by_stage.get(selected['stage'],'Inspect current persisted stage before acting.'),
            'blockers':blockers,'task_progress':progress,'pending_tasks':tasks,
            'evidence_source':'persisted_local_sqlite',
            'note':'Never treat saved caller-reported evidence as an independently executed check.'}


def public(row):
    return {**{k:v for k,v in row.items() if k!='evidence_json'},'evidence':json.loads(row['evidence_json'])}

def begin(conn,root,a):
    key=validate_key(a['build_id'])
    objective=a['objective']
    if not isinstance(objective,str) or not 1<=len(objective)<=1500:
        raise ValueError('objective must be bounded text')
    row=get(conn,root,a)
    if row:return {'status':'EXISTS','run':public(row)}
    flow=flow_for_project(conn,root,a)
    if a.get('confirm_write') is not True:
        return {'status':'PREVIEW_ONLY','project':a['project'],'root':str(root),'build_id':key,
                'stage':'RESEARCH','stages':list(flow),
                'next':'Research domain rules and reusable components before making the plan.'}
    with conn:
        conn.execute('INSERT INTO build_runs VALUES (?,?,?,?,?,?,?,?)',
                     (a['project'],str(root),key,'RESEARCH',1,objective,json.dumps({'__orbit_policy':'approval-v1','__orbit_flow':list(flow)}),now()))
    return {'status':'CREATED','run':public(get(conn,root,a))}

def current(conn,root,a):
    row=get(conn,root,a)
    return {'status':'FOUND','run':public(row),'stages':list(flow_for(row)),
            'task_progress':task_progress(conn,a['project'],root),
            'evidence_policy':'host-reported-except-recorded-browser-qa'} if row else {'status':'NOT_FOUND'}


def valid_stage_evidence(stage, evidence):
    if stage=='NATIVE_QA':
        try: report=json.loads(evidence)
        except (ValueError,TypeError):return False
        if not isinstance(report,dict) or set(report)!={'platforms','commands','interactions','accessibility'}:
            return False
        platforms=report['platforms']
        if not isinstance(platforms,list) or not 1<=len(platforms)<=3 or any(
            x not in {'android','ios','macos','windows','linux'} for x in platforms):return False
        commands=report['commands']
        if not isinstance(commands,list) or not 1<=len(commands)<=8 or any(
            not isinstance(c,dict) or set(c)!={'command','exit_code'}
            or not isinstance(c['command'],str) or len(c['command'])<3
            or type(c['exit_code']) is not int or c['exit_code']!=0 for c in commands):return False
        return all(isinstance(report[k],list) and 1<=len(report[k])<=8 and
                   all(isinstance(item,str) and 5<=len(item)<=240 for item in report[k])
                   for k in ('interactions','accessibility'))
    if stage not in ('RESEARCH','VERIFY'):
        return True
    try:
        data=json.loads(evidence)
    except (ValueError,TypeError):
        return False
    if not isinstance(data,dict):
        return False
    if stage=='RESEARCH':
        if set(data)!={'task','candidates','decision','sources','risks'}:
            return False
        if any(not isinstance(data[x],str) or len(data[x].strip())<8 for x in ('task','decision')):
            return False
        keys=('candidates','sources','risks')
    else:
        if set(data)!={'commands','edge_cases','security'}:
            return False
        cmds=data['commands']
        if not isinstance(cmds,list) or not 1<=len(cmds)<=8:
            return False
        for c in cmds:
            if (not isinstance(c,dict) or set(c)!={'command','exit_code'} or
                not isinstance(c['command'],str) or len(c['command'])<3 or
                type(c['exit_code']) is not int or c['exit_code']!=0):
                return False
        keys=('edge_cases','security')
    return all(isinstance(data[x],list) and 1<=len(data[x])<=8 and
               all(isinstance(v,str) and 3<=len(v)<=240 for v in data[x])
               for x in keys)

def advance(conn,root,a):
    row=get(conn,root,a)
    if not row: raise ValueError('Build not found')
    if row['revision']!=a['expected_revision']:
        return {'status':'STALE_REVISION','revision':row['revision'],'stage':row['stage']}
    if row['stage']=='DONE': return {'status':'ALREADY_DONE','run':public(row)}
    outcome=a['outcome']
    if outcome not in {'PASS','FAIL','BLOCKED'}: raise ValueError('outcome must be PASS/FAIL/BLOCKED')
    evidence=a['evidence']
    if not isinstance(evidence,str) or not 1<=len(evidence)<=1600:
        raise ValueError('evidence must be bounded text')
    evidence_map=json.loads(row['evidence_json'])
    flow=flow_for(row)
    if row['stage'] not in flow:return {'status':'HOLD','reason':'Persisted build flow is inconsistent; review stored state before continuing'}
    # Only newly created builds carry this marker; legacy PLAN-stage builds
    # must resume without a surprise migration or retroactive approval gate.
    if (row['stage']=='PLAN' and outcome=='PASS'
            and evidence_map.get('__orbit_policy')=='approval-v1'
            and not valid_approved_plan(evidence)):
        return {'status':'HOLD','reason':'Show/edit the plan, list bounded tasks and obtain actual user plan approval or explicit build delegation before implementation.'}
    if outcome=='PASS' and not valid_stage_evidence(row['stage'],evidence):
        return {'status':'HOLD','reason':'RESEARCH/VERIFY PASS needs structured task, reuse, command, edge-case and security evidence.'}
    # A readiness probe is evidence of a live local app server, not a functional pass.
    if row['stage']=='PREVIEW' and outcome=='PASS':
        import orbit_preview
        preview_id=a.get('preview_id')
        if not preview_id or orbit_preview.status(root,{'preview_id':preview_id}).get('status')!='READY':
            return {'status':'HOLD','reason':'A managed local preview must actually be READY in this MCP session'}
    if row['stage']=='CHECKPOINT' and outcome=='PASS':
        checkpoint=root/'.orbit'/'STATE.md'
        if checkpoint.is_symlink() or not checkpoint.is_file() or '<!-- ORBIT_NATIVE_CHECKPOINT_START -->' not in checkpoint.read_text(encoding='utf-8'):
            return {'status':'HOLD','reason':'Write an Orbit-managed .orbit/STATE.md checkpoint with actual evidence first'}
    # Independent browser checks require a pass result stored by Orbit, not caller claims.
    if row['stage']=='BROWSER_QA' and outcome=='PASS':
        rec=conn.execute('SELECT status,summary FROM browser_results WHERE project=? AND root=? AND build_id=? ORDER BY id DESC LIMIT 1',
                         (a['project'],str(root),row['build_id'])).fetchone()
        recorded=json.loads(rec['summary']) if rec else {}
        if not rec or rec['status']!='PASS' or not recorded.get('actions'):
            return {'status':'HOLD','reason':'No recorded passing interactive Playwright browser QA result for this build'}
    if a.get('confirm_write') is not True:
        return {'status':'PREVIEW_ONLY','stage':row['stage'], 'next_stage':flow[flow.index(row['stage'])+1] if outcome=='PASS' else row['stage']}
    evidence_map[row['stage']]={'outcome':outcome,'evidence':evidence,'updated_at':now(),
                                'verification':'browser-tool' if row['stage']=='BROWSER_QA' and outcome=='PASS' else 'caller-reported-not-attested'}
    new_stage=STAGES[STAGES.index(row['stage'])+1] if outcome=='PASS' else row['stage']
    with conn:
        cursor=conn.execute('''UPDATE build_runs SET stage=?,revision=revision+1,evidence_json=?,updated_at=?
             WHERE project=? AND root=? AND build_id=? AND revision=?''',
             (new_stage,json.dumps(evidence_map),now(),a['project'],str(root),row['build_id'],row['revision']))
    if cursor.rowcount!=1:return {'status':'STALE_REVISION'}
    return {'status':'ADVANCED' if outcome=='PASS' else 'RECORDED_'+outcome,'run':public(get(conn,root,a))}

def save_browser(conn,root,a,result):
    with conn:
        conn.execute('INSERT INTO browser_results (project,root,build_id,status,summary,created_at) VALUES (?,?,?,?,?,?)',
                     (a['project'],str(root),a['build_id'],result['status'],json.dumps({k:v for k,v in result.items() if k in {'url','viewport','title','actions','errors','failures','screenshot'}}),now()))
    return result

def setup_browser(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS browser_results(id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL,root TEXT NOT NULL,build_id TEXT NOT NULL,status TEXT NOT NULL,
    summary TEXT NOT NULL, created_at TEXT NOT NULL)''')
    conn.commit()
