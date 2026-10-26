"""Persistent product intake, deliberately non-automatic autonomy, evolving doc inventory."""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone

TYPES = {'website','web-app','desktop-app','mobile-app','api-service','cli','sdk-library','plugin-mcp','os-platform','game','data-automation','other'}
COMPLEXITY = {'simple','moderate','complex','high-assurance'}
MATURITY = {'spike','prototype','product','production-critical'}
AUTONOMY = ('guided','assisted','trusted')
DOCS = {'vision':['VISION.md','PRD.md','PRODUCT.md'], 'architecture':['ARCHITECTURE.md','SYSTEM-DESIGN.md'],
        'roadmap':['ROADMAP.md','MILESTONES.md'], 'design':['DESIGN.md','UI.md','UX.md'],
        'requirements':['REQUIREMENTS.md','SPEC.md','PRD.md'],'api':['API.md','API-CONTRACT.md','OPENAPI.md'],
        'security':['SECURITY.md','THREAT-MODEL.md'], 'operations':['OPERATIONS.md','RUNBOOK.md','DEPLOYMENT.md'],
        'testing':['TESTING.md','TEST-PLAN.md'], 'compatibility':['COMPATIBILITY.md','SUPPORT-MATRIX.md'],
        'distribution':['DISTRIBUTION.md','RELEASING.md'], 'hardware':['HARDWARE.md','PLATFORM.md']}

def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')

def setup(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS orbit_project_intake(
      project TEXT NOT NULL, root TEXT NOT NULL, revision INTEGER NOT NULL,
      status TEXT NOT NULL, profile_json TEXT NOT NULL, questions_json TEXT NOT NULL,
      answers_json TEXT NOT NULL, autonomy TEXT NOT NULL, approval_reference TEXT NOT NULL,
      updated_at TEXT NOT NULL, PRIMARY KEY(project,root))''')
    conn.commit()

def row(conn,root,project):
    r=conn.execute('SELECT * FROM orbit_project_intake WHERE project=? AND root=?',(project,str(root))).fetchone()
    return dict(r) if r else None

def public(r):
    if not r:return {'status':'NOT_STARTED','autonomy':'guided'}
    return {**{k:v for k,v in r.items() if not k.endswith('_json')},
            'profile':json.loads(r['profile_json']), 'questions':json.loads(r['questions_json']),
            'answers':json.loads(r['answers_json']), 'consent_is_caller_reported':True}

def status(conn,root,a):return public(row(conn,root,a['project']))

def validate_profile(p):
    if not isinstance(p,dict) or set(p)!={'type','complexity','maturity','goal','audience','constraints','stack','risk'}:
        raise ValueError('Profile requires type, complexity, maturity, goal, audience, constraints, stack, risk')
    if p['type'] not in TYPES or p['complexity'] not in COMPLEXITY or p['maturity'] not in MATURITY:
        raise ValueError('Invalid product classification')
    if any(not isinstance(p[k],str) or not 1<=len(p[k])<=700 for k in ('goal','audience','constraints','stack','risk')):
        raise ValueError('Invalid profile text')

def validate_questions(q):
    if not isinstance(q,list) or not 1<=len(q)<=6:raise ValueError('Need 1–6 questions')
    seen=set()
    for x in q:
        if not isinstance(x,dict) or set(x)!={'id','prompt','options','recommended'}:raise ValueError('Question shape')
        if not isinstance(x['id'],str) or not re.fullmatch('[a-z][a-z0-9_]{1,39}',x['id']) or x['id'] in seen:
            raise ValueError('Question ID')
        seen.add(x['id'])
        if not isinstance(x['prompt'],str) or not 5<=len(x['prompt'])<=250:raise ValueError('Question text')
        o=x['options']
        if not isinstance(o,list) or not 2<=len(o)<=5 or any(not isinstance(s,str) or not 1<=len(s)<=120 for s in o) or len(set(o))!=len(o):raise ValueError('Options')
        if x['recommended'] not in o:raise ValueError('Recommendation must be an option')

def propose(conn,root,a):
    p=a['profile'];q=a['questions'];validate_profile(p);validate_questions(q)
    old=row(conn,root,a['project'])
    if old and old['status']=='APPROVED':return {'status':'ALREADY_APPROVED','intake':public(old)}
    if a.get('confirm_write') is not True:return {'status':'PREVIEW_ONLY','profile':p,'questions':q}
    if old and old['revision']!=a.get('expected_revision'):return {'status':'STALE_REVISION','intake':public(old)}
    with conn:
        conn.execute('''INSERT INTO orbit_project_intake VALUES(?,?,1,'PROPOSED',?,?,?,'guided','',?)
          ON CONFLICT(project,root) DO UPDATE SET revision=revision+1,status='PROPOSED',
          profile_json=excluded.profile_json,questions_json=excluded.questions_json,
          answers_json=excluded.answers_json,updated_at=excluded.updated_at''',
          (a['project'],str(root),json.dumps(p),json.dumps(q),'{}',now()))
    return {'status':'PROPOSED','intake':status(conn,root,a),'next':'Ask the FIRST highest-impact question. After the response, use orbit_intake_answer then conditionally ask another, or obtain explicit defaults.'}

def answer(conn,root,a):
    """Persist one actually supplied user choice; no implicit default acceptance."""
    old=row(conn,root,a['project'])
    if not old or old['status']!='PROPOSED':
        return {'status':'HOLD','reason':'An active proposed interview is required'}
    if old['revision']!=a['expected_revision']:
        return {'status':'STALE_REVISION','intake':public(old)}
    if not isinstance(a.get('user_reference'),str) or not 8<=len(a['user_reference'])<=240:
        raise ValueError('Host must provide a real user answer reference')
    questions=json.loads(old['questions_json'])
    matches=[q for q in questions if q['id']==a['question_id']]
    if len(matches)!=1:
        raise ValueError('Question must match the active interview')
    # Options are suggestions, never a closed vocabulary: product users can
    # describe custom platforms, data rules, UI components and constraints.
    choice=a['choice']
    if not isinstance(choice,str) or not 1<=len(choice.strip())<=500:
        raise ValueError('Custom answer must be 1–500 characters of actual user text')
    if choice.strip().lower() in {'custom','other','type my own answer'}:
        return {'status':'HOLD','reason':'Ask the user to type the custom decision in their own words, then record that text.'}
    choice=choice.strip()
    answers=json.loads(old['answers_json'])
    if a['question_id'] in answers:
        if answers[a['question_id']]!=a['choice']:
            return {'status':'HOLD','reason':'An existing decision cannot be silently changed; use a reviewed new intake'}
        return {'status':'ALREADY_ANSWERED','intake':public(old)}
    if a.get('confirm_write') is not True:
        return {'status':'PREVIEW_ONLY','question_id':a['question_id'],'choice':choice,
                'choice_type':'SUGGESTED' if choice in matches[0]['options'] else 'CUSTOM'}
    answers[a['question_id']]=choice
    with conn:
        update=conn.execute('''UPDATE orbit_project_intake SET answers_json=?,revision=revision+1,
          updated_at=? WHERE project=? AND root=? AND revision=?''',
          (json.dumps(answers),now(),a['project'],str(root),old['revision']))
        if update.rowcount!=1:raise ValueError('Concurrent intake decision conflict')
    return {'status':'ANSWER_RECORDED','intake':status(conn,root,a),
            'choice_type':'SUGGESTED' if choice in matches[0]['options'] else 'CUSTOM',
            'next':'Analyze this specific choice and ask a conditional follow-up only when it changes meaningful product requirements.'}

def followup(conn,root,a):
    """Append exactly one question tied to an already recorded parent answer."""
    old=row(conn,root,a['project'])
    if not old or old['status']!='PROPOSED':
        return {'status':'HOLD','reason':'An active proposed interview is required'}
    if old['revision']!=a['expected_revision']:
        return {'status':'STALE_REVISION','intake':public(old)}
    q=json.loads(old['questions_json'])
    answers=json.loads(old['answers_json'])
    parent=a['based_on_id']
    if parent not in answers or answers[parent]!=a['based_on_choice']:
        return {'status':'HOLD','reason':'Follow-up must depend on an actually recorded answer'}
    if len(q)>=6:return {'status':'HOLD','reason':'Interview question cap reached; choose safe scope or seek explicit exception'}
    if any(item['id']==a['question']['id'] for item in q):
        raise ValueError('Follow-up id already used')
    validate_questions([a['question']])
    if not isinstance(a['rationale'],str) or not 12<=len(a['rationale'])<=500:
        raise ValueError('Describe why the previous choice changes the next decision')
    new_q={**a['question'],'based_on':parent,'because_choice':a['based_on_choice'],
           'rationale':a['rationale']}
    if a.get('confirm_write') is not True:
        return {'status':'PREVIEW_ONLY','question':new_q}
    with conn:
        update=conn.execute('''UPDATE orbit_project_intake SET questions_json=?,revision=revision+1,
           updated_at=? WHERE project=? AND root=? AND revision=?''',
           (json.dumps(q+[new_q]),now(),a['project'],str(root),old['revision']))
        if update.rowcount!=1:raise ValueError('Concurrent interview question conflict')
    return {'status':'FOLLOWUP_PROPOSED','intake':status(conn,root,a),
            'next':'Ask this dependent question; do not pre-fill the answer.'}

def approve(conn,root,a):
    old=row(conn,root,a['project'])
    if not old:return {'status':'HOLD','reason':'Propose an interview first'}
    if old['revision']!=a['expected_revision']:return {'status':'STALE_REVISION','intake':public(old)}
    if old['status']=='APPROVED':return {'status':'ALREADY_APPROVED','intake':public(old)}
    q=json.loads(old['questions_json']);ans=a['answers']
    if not isinstance(ans,dict) or set(ans)!={x['id'] for x in q}:raise ValueError('All questions require answers')
    if any(not isinstance(ans[x['id']],str) or not 1<=len(ans[x['id']].strip())<=500
           or ans[x['id']].strip().lower() in {'custom','other','type my own answer'} for x in q):
        raise ValueError('Every answer must be a bounded actual choice or free-form description')
    recorded=json.loads(old['answers_json'])
    if any(ans[k]!=v for k,v in recorded.items()):
        raise ValueError('Final approval cannot silently override previously recorded choices')
    if a['answer_source'] not in {'user_choices','user_delegated_defaults'}:raise ValueError('Invalid answer source')
    if a['answer_source']=='user_delegated_defaults' and any(ans[x['id']]!=x['recommended'] for x in q):
        raise ValueError('Delegated defaults must be the recommended choices')
    if not isinstance(a['user_reference'],str) or len(a['user_reference'])<8:raise ValueError('Owner choice reference required')
    if a.get('confirm_write') is not True:return {'status':'PREVIEW_ONLY','answers':ans}
    with conn:
        conn.execute('''UPDATE orbit_project_intake SET status='APPROVED',answers_json=?,approval_reference=?,
          revision=revision+1,updated_at=? WHERE project=? AND root=? AND revision=?''',
          (json.dumps(ans),a['user_reference'],now(),a['project'],str(root),old['revision']))
    return {'status':'APPROVED','intake':status(conn,root,a),'warning':'Actual user consent must be verified by host.'}

def autonomy(conn,root,a):
    old=row(conn,root,a['project'])
    if not old or old['status']!='APPROVED':return {'status':'HOLD','reason':'Complete intake first'}
    if 'level' not in a:
        done=conn.execute("SELECT COUNT(*) FROM build_runs WHERE project=? AND root=? AND stage='DONE'",(a['project'],str(root))).fetchone()[0]
        suggestion='trusted' if done>=5 else 'assisted' if done>=2 else 'guided'
        return {'status':'REVIEW','current':old['autonomy'],'recommended':suggestion,'verified_build_count':done,
                'requires_explicit_owner_consent':True}
    if old['revision']!=a.get('expected_revision'):return {'status':'STALE_REVISION','intake':public(old)}
    level=a['level']
    if level not in AUTONOMY:raise ValueError('Unknown autonomy')
    if not isinstance(a.get('user_reference'),str) or len(a['user_reference'])<8:raise ValueError('User approval reference required')
    if a.get('confirm_write') is not True:return {'status':'PREVIEW_ONLY','level':level}
    with conn:
        conn.execute('''UPDATE orbit_project_intake SET autonomy=?,approval_reference=?,revision=revision+1,updated_at=?
            WHERE project=? AND root=? AND revision=?''',(level,a['user_reference'],now(),a['project'],str(root),old['revision']))
    return {'status':'UPDATED','intake':status(conn,root,a),'warning':'Host approvals for destructive, credentials, spending, Git and deployment stay mandatory.'}

def docs_audit(conn,root,a):
    old=row(conn,root,a['project'])
    p=json.loads(old['profile_json']) if old and old['status']=='APPROVED' else {'type':'other','complexity':'moderate'}
    kind=p['type']; need={'vision','architecture','roadmap'}
    if kind in {'web-app','website','desktop-app','mobile-app','game'}:need.add('design')
    if kind in {'cli','sdk-library','plugin-mcp','api-service'}:need.update(('api','compatibility'))
    if kind in {'cli','sdk-library'}:need.add('distribution')
    if kind=='os-platform':need.update(('hardware','security','testing','operations'))
    if p['complexity'] in {'complex','high-assurance'}:need.update(('requirements','security','testing'))
    signals=a.get('signals',[])
    if not isinstance(signals,list) or len(signals)>8 or any(s not in {'new_feature','api_change','data_change','architecture_change','security_change','release','scale'} for s in signals):raise ValueError('Invalid growth signals')
    if 'api_change' in signals:need.add('api')
    if 'security_change' in signals:need.add('security')
    if 'release' in signals:need.add('operations')
    existing={}
    for k, names in DOCS.items():
        found=[]
        for d in (root,root/'docs'):
            if d.is_dir() and not d.is_symlink():
                found.extend(str(f.relative_to(root)) for f in d.iterdir() if f.is_file() and not f.is_symlink() and f.name.lower() in {n.lower() for n in names})
        if found:existing[k]=sorted(set(found))
    return {'project':a['project'],'project_type':kind,'signals':signals,'existing_docs':existing,
            'gaps':[{'purpose':x,'suggested_path':'docs/'+DOCS[x][0],'action':'REVIEW_CONTENT_AND_OWNER_SOURCES_FIRST'} for x in sorted(need) if x not in existing],
            'notice':'Non-destructive filename heuristic, not a semantic doc audit. Rerun as project evolves.'}