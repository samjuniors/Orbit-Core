"""Durable, version-checked app build gate ledger (no AI agent executor).

Host coding agents do work; this ledger records evidence and required next gates
across MCP restarts. A reported code/test result is not independently verified.
"""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime,timezone

STAGES=('PLAN','IMPLEMENT','PREVIEW','BROWSER_QA','REVIEW','CHECKPOINT','DONE')

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

def public(row):
    return {**{k:v for k,v in row.items() if k!='evidence_json'},'evidence':json.loads(row['evidence_json'])}

def begin(conn,root,a):
    key=validate_key(a['build_id'])
    objective=a['objective']
    if not isinstance(objective,str) or not 1<=len(objective)<=1500:
        raise ValueError('objective must be bounded text')
    row=get(conn,root,a)
    if row:return {'status':'EXISTS','run':public(row)}
    if a.get('confirm_write') is not True:
        return {'status':'PREVIEW_ONLY','project':a['project'],'root':str(root),'build_id':key,
                'stage':'PLAN','next':'Create a scoped plan; host model and tools perform real work.'}
    with conn:
        conn.execute('INSERT INTO build_runs VALUES (?,?,?,?,?,?,?,?)',
                     (a['project'],str(root),key,'PLAN',1,objective,'{}',now()))
    return {'status':'CREATED','run':public(get(conn,root,a))}

def current(conn,root,a):
    row=get(conn,root,a)
    return {'status':'FOUND','run':public(row),'stages':list(STAGES)} if row else {'status':'NOT_FOUND'}

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
        return {'status':'PREVIEW_ONLY','stage':row['stage'], 'next_stage':STAGES[STAGES.index(row['stage'])+1] if outcome=='PASS' else row['stage']}
    evidence_map[row['stage']]={'outcome':outcome,'evidence':evidence,'updated_at':now(),
                                'verification':'browser-tool' if row['stage']=='BROWSER_QA' and outcome=='PASS' else 'caller-reported'}
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
