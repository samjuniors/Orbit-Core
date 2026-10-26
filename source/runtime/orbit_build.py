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


def feedback(conn,root,a):
    """Persist user feedback separately from stage PASS/FAIL.

    Native IDE artifacts remain the editable source of truth. A host-reported
    feedback reference records only the request and its acknowledged resolution.
    """
    row=get(conn,root,a)
    if not row:raise ValueError('Build not found')
    if row['revision']!=a['expected_revision']:
        return {'status':'STALE_REVISION','revision':row['revision'],'stage':row['stage']}
    if row['stage']=='DONE':
        return {'status':'HOLD','reason':'Completed builds need a new approved change request, not a retroactive mutation'}
    action=a['action']
    if action not in {'request','resolve'}:raise ValueError('Invalid feedback action')
    evidence=json.loads(row['evidence_json'])
    items=evidence.get('__orbit_feedback',[])
    if not isinstance(items,list):raise ValueError('Invalid persisted feedback')
    if action=='request':
        note=a.get('note','')
        ref=a.get('user_reference','')
        if not isinstance(note,str) or not 5<=len(note.strip())<=600:
            raise ValueError('Feedback requires 5–600 characters of text')
        if not isinstance(ref,str) or not 8<=len(ref)<=200:
            raise ValueError('Real user artifact/comment reference required')
        if sum(item['status']=='OPEN' for item in items)>=8:
            return {'status':'HOLD','reason':'Resolve existing feedback before adding more requests'}
        item={'id':'f'+str(evidence.get('__orbit_feedback_seq',0)+1),
              'status':'OPEN','stage':row['stage'],'source':a.get('source','plan'),
              'note':note.strip(),'reference':ref,'created_at':now()}
        updated=[x for x in items if x['status']=='OPEN']+[
            x for x in items if x['status']=='RESOLVED'][-8:]
        updated.append(item)
        result='FEEDBACK_RECORDED'
    else:
        fid=a.get('feedback_id','')
        matches=[x for x in items if x['id']==fid and x['status']=='OPEN']
        if len(matches)!=1:return {'status':'HOLD','reason':'Feedback id is missing or already resolved'}
        resolution=a.get('resolution_evidence','')
        if not isinstance(resolution,str) or not 8<=len(resolution.strip())<=600:
            raise ValueError('Resolution needs actual changed artifact/test evidence')
        updated=[{**x,'status':'RESOLVED','resolution':resolution.strip(),
                  'resolved_at':now()} if x['id']==fid else x for x in items]
        result='FEEDBACK_RESOLVED'
    if a.get('confirm_write') is not True:
        return {'status':'PREVIEW_ONLY','action':action,'build_id':row['build_id'],
                'note':'No feedback state was written'}
    evidence['__orbit_feedback']=updated
    if action=='request':evidence['__orbit_feedback_seq']=int(item['id'][1:])
    with conn:
        cur=conn.execute('''UPDATE build_runs SET revision=revision+1,
              evidence_json=?,updated_at=? WHERE project=? AND root=? AND build_id=? AND revision=?''',
              (json.dumps(evidence),now(),a['project'],str(root),row['build_id'],row['revision']))
    if cur.rowcount!=1:return {'status':'STALE_REVISION'}
    return {'status':result,'run':public(get(conn,root,a)),
            'open_feedback':sum(x['status']=='OPEN' for x in updated),
            'note':'Host must re-check the actual artifact/changes and obtain owner approval when required.'}


def experience_view(intake, recovery, run=None):
    """Host-renderable, read-only summary of *existing* persisted facts.

    This does not make LLM calls, approve decisions, advance a stage or claim an
    IDE panel is installed. All host actions still need permission and evidence.
    """
    state=intake.get('status','NOT_STARTED')
    result={'version':1,'mode':'guided','phase':'DISCOVERY',
            'headline':'Tell Orbit what you want to build',
            'summary':'Choose how much guidance you want; Orbit will not choose consequential requirements silently.',
            'next_action':{'label':'Choose scope-first or approved defaults','tool':'orbit_intake_propose'},
            'decision':None,'plan':None,'progress':None,'task_cards':[],
            'feedback':[],'open_feedback':0,
            'attention':[],'approval_required':False,
            'evidence_note':'Display data is derived from persisted host-reported state; no model or user approval is inferred.'}
    if intake.get('autonomy') in {'guided','assisted','trusted'}:
        result['mode']=intake['autonomy']
    if state=='PROPOSED':
        questions=intake.get('questions',[])
        answers=intake.get('answers',{})
        pending=next((q for q in questions if q.get('id') not in answers),None)
        result['phase']='DISCOVERY'
        result['headline']='A decision is needed' if pending else 'Review your project decisions'
        result['summary']='Answers are remembered; ask a follow-up only if the previous answer makes it necessary.'
        result['approval_required']=True
        if pending:
            result['decision']={'id':pending['id'],'prompt':pending['prompt'],
                'options':pending['options'][:5], 'recommended':pending['recommended'],
                'custom_allowed':True,'based_on':pending.get('based_on'),
                'reason':pending.get('rationale')}
            result['next_action']={'label':'Answer or type your own choice','tool':'orbit_intake_answer'}
        else:
            result['next_action']={'label':'Confirm the agreed brief','tool':'orbit_intake_approve'}
    elif state=='APPROVED':
        profile=intake.get('profile',{})
        result['summary']=str(profile.get('goal','Approved product decisions'))[:240]
        result['headline']='Decisions recorded'
        result['phase']='READY'
        result['next_action']={'label':'Research or resume the agreed build','tool':'orbit_build_begin'}

    status=recovery.get('status','NO_BUILD')
    result['task_cards']=[{'task_key':t['task_key'],'status':t['status'],
                           'goal':t.get('goal','')[:120]}
                          for t in recovery.get('pending_tasks',[])[:5]]
    if status=='NEEDS_BUILD_SELECTION':
        result.update(phase='CHOOSE_BUILD',headline='Which unfinished build should Orbit continue?',
                      approval_required=True,
                      next_action={'label':'Select a build before continuing','tool':'orbit_build_status'})
        result['decision']={'prompt':'Select an existing build','options':[
            x['build_id'] for x in recovery.get('builds',[])[:8]],
            'recommended':None,'custom_allowed':False}
        return result
    if status=='ALL_DONE':
        result.update(phase='COMPLETED',headline='No unfinished builds',
                      next_action={'label':'Review the result or request a new change','tool':'orbit_project_resume'})
        result['summary']='Latest completed build: '+str(recovery.get('last_completed_build',''))
        return result
    if status!='RESUME':
        return result
    if not run:
        result.update(phase='RESUME',headline='Resume saved work',
                      next_action={'label':str(recovery.get('next','Resume current build'))[:160],
                                   'tool':'orbit_build_status'})
        return result
    stages=flow_for({'evidence_json':json.dumps(run.get('evidence',{})),
                     'stage':run['stage']})
    stage=run['stage']
    count=stages.index(stage) if stage in stages else 0
    result['progress']={'build_id':run['build_id'],'stage':stage,
                       'completed_stages':count,'total_stages':len(stages)-1,
                       'revision':run['revision'],'kind':'recorded-stage-not-quality-percentage'}
    result['phase']='PLAN_REVIEW' if stage=='PLAN' else ('BUILDING' if stage in {'IMPLEMENT','RESEARCH'}
                        else 'CHECKING' if stage in {'VERIFY','PREVIEW','BROWSER_QA','NATIVE_QA','REVIEW','CHECKPOINT'}
                        else 'COMPLETED')
    result['headline']={'RESEARCH':'Researching the best approach',
       'PLAN':'Review the plan before building','IMPLEMENT':'Building the agreed product',
       'VERIFY':'Checking behavior and edge cases','PREVIEW':'Preparing local preview',
       'BROWSER_QA':'Testing real browser interactions',
       'NATIVE_QA':'Testing the native experience','REVIEW':'Reviewing the work',
       'CHECKPOINT':'Saving progress','DONE':'Build completed'}.get(stage,'Continue Orbit build')
    result['next_action']={'label':str(recovery.get('next','Continue the current stage'))[:160],
                           'tool':'orbit_build_status' if stage=='PLAN' else 'orbit_build_advance'}
    if stage=='PLAN':
        result['approval_required']=True
        result['attention'].append('Present an editable plan and get real owner approval; approval cannot be inferred from this status.')
    record=run.get('evidence',{}).get('PLAN',{})
    if isinstance(record,dict) and record.get('outcome')=='PASS':
        try:
            plan=json.loads(record['evidence'])
            if valid_approved_plan(record['evidence']):
                result['plan']={'title':plan['title'],
                                'summary':plan['summary'],
                                'tasks':plan['tasks'][:12],
                                'approval_method':plan['approval_method'],
                                'approval_reported_by_host':True}
        except (TypeError,ValueError,KeyError):
            pass
    comments=run.get('evidence',{}).get('__orbit_feedback',[])
    if isinstance(comments,list):
        pending=[x for x in comments if isinstance(x,dict) and x.get('status')=='OPEN']
        result['open_feedback']=len(pending)
        result['feedback']=[{'id':x['id'],'source':x.get('source'),
             'note':x.get('note','')[:240],'stage':x.get('stage')}
            for x in pending[-4:]]
        if pending:
            result['attention'].insert(0,str(len(pending))+' user change request(s) need action.')
            result['next_action']={'label':'Revise the existing Antigravity artifact and address requested changes',
                                   'tool':'orbit_build_feedback'}
            result['phase']='CHANGES_REQUESTED'
    result['attention'] += [
        'Recorded '+str(x.get('stage',''))+': '+str(x.get('outcome',''))+
        '. Review actual evidence before retrying.'
        for x in recovery.get('blockers',[])[:3]]
    result['attention']=result['attention'][:4]
    return result


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
    if outcome=='PASS' and any(x.get('status')=='OPEN' for x in evidence_map.get('__orbit_feedback',[])
                               if isinstance(x,dict)):
        return {'status':'HOLD','reason':'Open user feedback must be addressed and recorded as resolved before advancing this stage'}
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
    new_stage=flow[flow.index(row['stage'])+1] if outcome=='PASS' else row['stage']
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
