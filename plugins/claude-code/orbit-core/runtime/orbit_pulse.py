"""Read-only, project-scoped one-glance task pulse.

Counts represent local task records; they do not attest real host execution.
"""
from __future__ import annotations


def summarize(conn, root, project, checkpoint):
    available=conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='orbit_agent_tasks'"
    ).fetchone()
    statuses={}
    if available:
        rows=conn.execute(
            "SELECT status, COUNT(*) FROM orbit_agent_tasks "
            "WHERE project=? AND project_root=? GROUP BY status",
            (project,str(root)))
        statuses={status:count for status,count in rows}
    total=sum(statuses.values())
    active=statuses.get('RESERVED',0)+statuses.get('RUNNING',0)
    blocked=sum(statuses.get(name,0) for name in ('BLOCKED','FAILED','REWORK'))
    review=statuses.get('REPORTED_DONE',0)
    if active:
        code='VERIFY_HOST_SESSIONS'
        hint='Inspect actual host sessions before retrying task reservations.'
    elif blocked:
        code='REVIEW_BLOCKED_TASKS'
        hint='Review blocked task evidence before attempting repairs.'
    elif review:
        code='REVIEW_REPORTED_TASKS'
        hint='Inspect actual evidence before accepting reported results.'
    elif checkpoint.get('managed_fields',{}).get('Next step'):
        code='REVIEW_CHECKPOINT_NEXT'
        hint='Review the local checkpoint next step against current source.'
    elif total:
        code='INSPECT_TASK_LEDGER'
        hint='Review existing task records and decide the next action.'
    else:
        code='INSPECT_PROJECT'
        hint='Inspect current source and tests before planning.'
    return {
        'source':'local_sqlite_project_tasks',
        'task_counts':{
            'total':total,'active':active,'blocked_or_rework':blocked,
            'awaiting_review':review,'review_accepted':statuses.get('REVIEW_ACCEPTED',0),
        },
        'next_action':{'code':code,'hint':hint},
        'record_trust':'CALLER_REPORTED_UNVERIFIED',
        'host_liveness_verified':False,
        'tests_verified':False,
    }
