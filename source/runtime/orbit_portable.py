"""Explicit, bounded project transfer. Bundles are untrusted data, never permissions."""
import hashlib
import json
import sqlite3
import orbit_evidence
import orbit_tasks

MAX_BYTES = 90000

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def counts(conn, root, project):
    return {label: conn.execute(f'SELECT count(*) FROM {table} WHERE {column}=? AND project=?',
            (str(root), project)).fetchone()[0]
            for label, table, column in [('tasks','orbit_agent_tasks','project_root'),
                                        ('research','orbit_research_sources','root')]}

def transfer(conn, root, project, args, checkpoint):
    if args['action'] == 'export':
        tasks = [dict(r) for r in conn.execute('SELECT * FROM orbit_agent_tasks WHERE project_root=? AND project=? ORDER BY task_key LIMIT 101', (str(root), project))]
        research = [dict(r) for r in conn.execute('SELECT * FROM orbit_research_sources WHERE root=? AND project=? ORDER BY source_key LIMIT 101', (str(root), project))]
        if max(len(tasks), len(research)) > 100:
            raise ValueError('Transfer limit is 100 tasks and 100 research pointers; no partial export')
        for row in tasks:
            row.pop('project_root')
            row['approval_reference'] = ''
        for row in research:
            row.pop('root')
        bundle = {'format':1, 'project':project, 'tasks':tasks, 'research':research,
                  'checkpoint':checkpoint, 'trust':'CALLER_REPORTED_UNVERIFIED'}
        encoded = json.dumps(bundle, sort_keys=True)
        if len(encoded.encode()) > MAX_BYTES:
            raise ValueError('Transfer exceeds 90000 bytes; no partial export')
        return {'status':'EXPORT_READY', 'bundle':encoded, 'bundle_revision':digest(bundle),
                'warning':'Review for sensitive notes/URLs before manually saving outside Git. No files written. No credentials/configuration or other projects collected.'}
    raw = args.get('bundle', '')
    if not isinstance(raw,str) or len(raw.encode()) > MAX_BYTES:
        raise ValueError('Invalid bounded bundle')
    bundle = json.loads(raw)
    if not isinstance(bundle,dict) or bundle.get('format') != 1 or bundle.get('project') != project:
        raise ValueError('Bundle format/project mismatch')
    for field in ('tasks','research'):
        if not isinstance(bundle.get(field),list) or len(bundle[field]) > 100:
            raise ValueError('Invalid bundle records')
    # Validate the entire packet before any writes. Unknown fields never become SQL.
    task_columns = [r[1] for r in conn.execute('PRAGMA table_info(orbit_agent_tasks)')]
    source_columns = [r[1] for r in conn.execute('PRAGMA table_info(orbit_research_sources)')]
    tasks=[]; research=[]
    for row in bundle['tasks']:
        if not isinstance(row,dict) or set(row) != set(task_columns)-{'project_root'}:
            raise ValueError('Invalid task fields')
        if row['project'] != project or any(not isinstance(v,(str,int)) for v in row.values()):
            raise ValueError('Invalid task project/values')
        parsed={**row, **{f:json.loads(row[f]) for f in ('write_paths','depends_on','changed_paths')}}
        orbit_tasks.spec(parsed)
        orbit_tasks._scopes(parsed['changed_paths'])
        if row['status'] not in {'PLANNED','RESERVED','RUNNING','REWORK','FAILED','BLOCKED','REPORTED_DONE','REVIEW_ACCEPTED','CANCELLED'} or type(row['revision']) is not int or row['revision'] < 1:
            raise ValueError('Invalid task state')
        row={**row,'project_root':str(root),'approval_reference':'','reserved_at':'',
             'note':'IMPORTED_HISTORY_UNVERIFIED; host_session is historical; fresh approval required. '+row['note'][:500]}
        if row['status'] in {'RESERVED','RUNNING','REPORTED_DONE'}:
            row['status']='BLOCKED'
        tasks.append(row)
    # Reuse source validation in an isolated database, without touching destination.
    check=sqlite3.connect(':memory:'); check.row_factory=sqlite3.Row
    try:
        orbit_evidence.setup(check)
        for row in bundle['research']:
            if not isinstance(row,dict) or set(row) != set(source_columns)-{'root'} or row['project'] != project:
                raise ValueError('Invalid research fields/project')
            if any(not isinstance(v,(str,int)) for v in row.values()) or type(row['revision']) is not int or row['revision'] < 1 or row['status'] != 'REFERENCE_ONLY':
                raise ValueError('Invalid research state')
            orbit_evidence.save(check,root,project,{**row,'tags':json.loads(row['tags_json'])})
            research.append({**row,'root':str(root)})
    finally:
        check.close()
    for rows, key in ((tasks,'task_key'),(research,'source_key')):
        if len({r[key] for r in rows}) != len(rows): raise ValueError('Duplicate bundle keys')
    revision=digest(bundle)
    conflicts=[]
    for table, column, key, rows in [('orbit_agent_tasks','project_root','task_key',tasks),('orbit_research_sources','root','source_key',research)]:
        for row in rows:
            if conn.execute(f'SELECT 1 FROM {table} WHERE {column}=? AND project=? AND {key}=?',(str(root),project,row[key])).fetchone():
                conflicts.append(row[key])
    result={'status':'CONFLICT' if conflicts else 'PREVIEW_ONLY','bundle_revision':revision,
            'tasks':len(tasks),'research':len(research),'conflicts':conflicts,
            'checkpoint_imported':False,'evidence_unverified':True,
            'warning':'No permissions transferred. Active work becomes BLOCKED. Existing records are never overwritten. Checkpoint remains unchanged.'}
    if conflicts or not args.get('confirm_write'): return result
    if args.get('expected_revision') != revision: return {**result,'status':'STALE_REVISION'}
    try:
        with conn:
            for table, columns, rows in [('orbit_agent_tasks',task_columns,tasks),('orbit_research_sources',source_columns,research)]:
                for row in rows:
                    conn.execute(f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",[row[c] for c in columns])
    except sqlite3.IntegrityError:
        return {**result,'status':'CONFLICT'}
    return {**result,'status':'IMPORTED'}
