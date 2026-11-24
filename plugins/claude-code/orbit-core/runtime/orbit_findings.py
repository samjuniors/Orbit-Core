"""Persistent, revision-aware reconciliation for structural and source review findings.

The ledger stores bounded Orbit-generated evidence and review dispositions. It does
not certify defects, execute project code, or create tasks.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone

DISPOSITIONS = {"UNREVIEWED", "ACCEPTED", "FALSE_POSITIVE", "RISK_ACCEPTED", "NOT_APPLICABLE"}
ACTIVE_STATUSES = {"NEW", "OPEN", "RECURRING", "STALE"}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def setup(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS orbit_project_findings (
        project TEXT NOT NULL,
        project_root TEXT NOT NULL,
        finding_id TEXT NOT NULL,
        category TEXT NOT NULL,
        severity TEXT NOT NULL,
        confidence TEXT NOT NULL,
        summary TEXT NOT NULL,
        evidence TEXT NOT NULL,
        recommendation TEXT NOT NULL,
        lifecycle TEXT NOT NULL,
        disposition TEXT NOT NULL DEFAULT 'UNREVIEWED',
        first_seen TEXT NOT NULL,
        last_seen TEXT NOT NULL,
        last_snapshot TEXT NOT NULL,
        evidence_sha256 TEXT NOT NULL,
        occurrence_count INTEGER NOT NULL DEFAULT 1,
        revision INTEGER NOT NULL DEFAULT 1,
        linked_task_ids TEXT NOT NULL DEFAULT '[]',
        audit_scope TEXT NOT NULL DEFAULT 'STRUCTURAL',
        PRIMARY KEY(project, project_root, finding_id)
    )""")
    # Additive migration for databases created before scoped audits.
    columns = {row[1] for row in conn.execute('PRAGMA table_info(orbit_project_findings)')}
    if 'audit_scope' not in columns:
        conn.execute("ALTER TABLE orbit_project_findings ADD COLUMN audit_scope TEXT NOT NULL DEFAULT 'STRUCTURAL'")
    conn.execute('DROP INDEX IF EXISTS idx_orbit_findings_scope')
    conn.execute("""CREATE INDEX IF NOT EXISTS idx_orbit_findings_scope
                    ON orbit_project_findings(project, project_root, audit_scope, lifecycle)""")
    conn.commit()


def _public(row):
    result = dict(row)
    result["evidence"] = json.loads(result["evidence"])
    result["linked_task_ids"] = json.loads(result["linked_task_ids"])
    result["is_confirmed_defect"] = False
    result["review_required"] = result["disposition"] == "UNREVIEWED"
    return result


def _validate_finding(item):
    if not isinstance(item, dict):
        raise ValueError("Audit finding must be an object")
    fid = item.get("id")
    if not isinstance(fid, str) or not re.fullmatch(r"[A-Z0-9][A-Z0-9_.-]{0,79}", fid):
        raise ValueError("Audit finding has an invalid stable id")
    category = item.get("category")
    severity = item.get("severity")
    confidence = item.get("confidence")
    summary = item.get("summary")
    recommendation = item.get("recommendation")
    evidence = item.get("evidence", [])
    if category not in {"documentation", "testing", "architecture", "dependencies", "security", "verification"}:
        raise ValueError("Audit finding category is not recognized")
    if severity not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        raise ValueError("Audit finding severity is not recognized")
    if confidence not in {"LOW", "MEDIUM", "HIGH"}:
        raise ValueError("Audit finding confidence is not recognized")
    if not isinstance(summary, str) or len(summary) > 1000:
        raise ValueError("Audit finding summary is invalid")
    if not isinstance(recommendation, str) or len(recommendation) > 1500:
        raise ValueError("Audit finding recommendation is invalid")
    if not isinstance(evidence, list) or len(evidence) > 30 or any(
        not isinstance(path, str) or not path or len(path) > 240
        or path.startswith("/") or "\\" in path or ":" in path or "\x00" in path
        or any(segment in {"", ".", ".."} for segment in path.split("/"))
        for path in evidence
    ):
        raise ValueError("Audit finding evidence paths must be bounded repository-relative POSIX paths")
    payload = {"category": category, "severity": severity, "confidence": confidence,
               "summary": summary, "evidence": evidence, "recommendation": recommendation}
    digest = hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()
    return fid, payload, digest


def reconcile(conn, project, root, audit, audit_scope="STRUCTURAL"):
    """Persist one complete or incomplete scan without cross-scope resolution."""
    if not isinstance(project, str) or not project or len(project) > 80:
        raise ValueError("Invalid project key")
    if audit_scope not in {"STRUCTURAL", "SOURCE"}:
        raise ValueError("Unknown audit scope")
    if not isinstance(audit, dict) or audit.get("status") not in {"SCANNED", "INCOMPLETE"}:
        raise ValueError("A valid structural project audit is required")
    snapshot = audit.get("inventory_snapshot_sha256")
    if not isinstance(snapshot, str) or not re.fullmatch(r"[a-f0-9]{64}", snapshot):
        raise ValueError("Audit snapshot is invalid")
    items = audit.get("findings")
    if not isinstance(items, list) or len(items) > 100:
        raise ValueError("Audit findings must be a bounded array")
    validated = [_validate_finding(item) for item in items]
    if len({item[0] for item in validated}) != len(validated):
        raise ValueError("Audit contains duplicate finding identities")

    now = _now()
    path = str(root)
    with conn:
        if audit["status"] == "INCOMPLETE":
            # An incomplete scan cannot prove absence. Preserve prior evidence and
            # mark active rows stale so callers do not interpret them as current.
            conn.execute(
                """UPDATE orbit_project_findings SET lifecycle='STALE', revision=revision+1
                   WHERE project=? AND project_root=? AND audit_scope=? AND lifecycle IN ('NEW','OPEN','RECURRING')""",
                (project, path, audit_scope),
            )
            rows = conn.execute(
                "SELECT * FROM orbit_project_findings WHERE project=? AND project_root=? AND audit_scope=? ORDER BY finding_id",
                (project, path, audit_scope),
            ).fetchall()
            return {
                "status": "RECONCILED_INCOMPLETE",
                "audit_scope": audit_scope,
                "complete_scan": False,
                "resolved_count": 0,
                "stale_count": sum(1 for row in rows if row["lifecycle"] == "STALE"),
                "findings": [_public(row) for row in rows],
                "warning": "Incomplete scan cannot resolve absent findings; previous evidence is retained as stale.",
                "data_written": True,
            }

        current_ids = {item[0] for item in validated}
        previous = {
            row["finding_id"]: dict(row)
            for row in conn.execute(
                "SELECT * FROM orbit_project_findings WHERE project=? AND project_root=? AND audit_scope=?",
                (project, path, audit_scope),
            ).fetchall()
        }
        for fid, payload, evidence_digest in validated:
            old = previous.get(fid)
            if old is None:
                lifecycle, disposition, first_seen, count, revision, links = (
                    "NEW", "UNREVIEWED", now, 1, 1, "[]"
                )
            else:
                changed_evidence = old["evidence_sha256"] != evidence_digest
                lifecycle = "RECURRING" if old["lifecycle"] == "RESOLVED" else "OPEN"
                disposition = old["disposition"] if not changed_evidence and lifecycle != "RECURRING" else "UNREVIEWED"
                first_seen = old["first_seen"]
                count = old["occurrence_count"] + (1 if lifecycle == "RECURRING" else 0)
                revision = old["revision"] + 1
                links = old["linked_task_ids"]
            conn.execute(
                """INSERT INTO orbit_project_findings
                   (project,project_root,finding_id,category,severity,confidence,summary,evidence,
                    recommendation,lifecycle,disposition,first_seen,last_seen,last_snapshot,
                    evidence_sha256,occurrence_count,revision,linked_task_ids,audit_scope)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(project,project_root,finding_id) DO UPDATE SET
                    category=excluded.category,severity=excluded.severity,confidence=excluded.confidence,
                    summary=excluded.summary,evidence=excluded.evidence,recommendation=excluded.recommendation,
                    lifecycle=excluded.lifecycle,disposition=excluded.disposition,last_seen=excluded.last_seen,
                    last_snapshot=excluded.last_snapshot,evidence_sha256=excluded.evidence_sha256,
                    occurrence_count=excluded.occurrence_count,revision=excluded.revision,
                    audit_scope=excluded.audit_scope""",
                (project, path, fid, payload["category"], payload["severity"], payload["confidence"],
                 payload["summary"], _json(payload["evidence"]), payload["recommendation"], lifecycle,
                 disposition, first_seen, now, snapshot, evidence_digest, count, revision, links, audit_scope),
            )

        resolved_count = 0
        for fid, old in previous.items():
            if fid not in current_ids and old["lifecycle"] != "RESOLVED":
                conn.execute(
                    """UPDATE orbit_project_findings SET lifecycle='RESOLVED',last_snapshot=?,
                       revision=revision+1 WHERE project=? AND project_root=? AND finding_id=? AND audit_scope=?""",
                    (snapshot, project, path, fid, audit_scope),
                )
                resolved_count += 1
        rows = conn.execute(
            "SELECT * FROM orbit_project_findings WHERE project=? AND project_root=? AND audit_scope=? ORDER BY finding_id",
            (project, path, audit_scope),
        ).fetchall()
    return {
        "status": "RECONCILED",
        "audit_scope": audit_scope,
        "complete_scan": True,
        "snapshot": snapshot,
        "new_count": sum(1 for row in rows if row["lifecycle"] == "NEW" and row["last_snapshot"] == snapshot),
        "resolved_count": resolved_count,
        "open_count": sum(1 for row in rows if row["lifecycle"] in ACTIVE_STATUSES),
        "findings": [_public(row) for row in rows],
        "data_written": True,
        "tasks_created": False,
    }


def list_findings(conn, project, root, limit=100, audit_scope=None):
    if type(limit) is not int or not 1 <= limit <= 200:
        raise ValueError("limit must be 1..200")
    if audit_scope is not None and audit_scope not in {"STRUCTURAL", "SOURCE"}:
        raise ValueError("Unknown audit scope")
    sql = "SELECT * FROM orbit_project_findings WHERE project=? AND project_root=?"
    params = [project, str(root)]
    if audit_scope is not None:
        sql += " AND audit_scope=?"
        params.append(audit_scope)
    sql += """ ORDER BY CASE lifecycle WHEN 'NEW' THEN 0 WHEN 'RECURRING' THEN 1
               WHEN 'OPEN' THEN 2 WHEN 'STALE' THEN 3 ELSE 4 END, finding_id LIMIT ?"""
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    return {"status": "FOUND" if rows else "EMPTY", "findings": [_public(row) for row in rows],
            "count": len(rows), "audit_scope": audit_scope or "ALL", "tasks_created": False}


def set_disposition(conn, project, root, finding_id, disposition, expected_revision):
    if disposition not in DISPOSITIONS:
        raise ValueError("Unknown finding disposition")
    if not isinstance(finding_id, str) or not re.fullmatch(r"[A-Z0-9][A-Z0-9_.-]{0,79}", finding_id):
        raise ValueError("Invalid finding id")
    if type(expected_revision) is not int or expected_revision < 1:
        raise ValueError("expected_revision must be a positive integer")
    with conn:
        row = conn.execute(
            """SELECT * FROM orbit_project_findings
               WHERE project=? AND project_root=? AND finding_id=?""",
            (project, str(root), finding_id),
        ).fetchone()
        if row is None:
            raise ValueError("Finding not found in selected project")
        if row["revision"] != expected_revision:
            return {"status": "STALE_REVISION", "finding": _public(row)}
        conn.execute(
            """UPDATE orbit_project_findings SET disposition=?,revision=revision+1
               WHERE project=? AND project_root=? AND finding_id=? AND revision=?""",
            (disposition, project, str(root), finding_id, expected_revision),
        )
        updated = conn.execute(
            """SELECT * FROM orbit_project_findings
               WHERE project=? AND project_root=? AND finding_id=?""",
            (project, str(root), finding_id),
        ).fetchone()
    return {"status": "UPDATED", "finding": _public(updated),
            "defect_confirmed": False, "task_created": False}



def task_preview(conn, project, root, finding_id, expected_revision):
    """Build a no-write task preview from an explicitly accepted, current finding."""
    if not isinstance(finding_id, str) or not re.fullmatch(r"[A-Z0-9][A-Z0-9_.-]{0,79}", finding_id):
        raise ValueError("Invalid finding id")
    if type(expected_revision) is not int or expected_revision < 1:
        raise ValueError("expected_revision must be a positive integer")
    row = conn.execute(
        """SELECT * FROM orbit_project_findings
           WHERE project=? AND project_root=? AND finding_id=?""",
        (project, str(root), finding_id),
    ).fetchone()
    if row is None:
        raise ValueError("Finding not found in selected project")
    if row["revision"] != expected_revision:
        return {"status": "STALE_REVISION", "finding": _public(row), "task_created": False}
    if row["disposition"] != "ACCEPTED":
        return {"status": "REVIEW_REQUIRED", "message": "Only owner-accepted findings can produce task previews.",
                "finding": _public(row), "task_created": False}
    if row["lifecycle"] in {"STALE", "RESOLVED"}:
        return {"status": "FINDING_NOT_CURRENT", "message": "Refresh and review this finding before planning remediation.",
                "finding": _public(row), "task_created": False}
    evidence = json.loads(row["evidence"])
    task_key = "finding-" + finding_id.lower().replace("_", "-").replace(".", "-")
    goal = (f"Review and address structural finding {finding_id}: {row['summary']} "
            f"Recommendation: {row['recommendation']}")[:1500]
    reason = (f"Owner accepted {finding_id}; inspect evidence paths {', '.join(evidence) or '(none)'}. "
              "Confirm the actual source condition and tests before editing.")[:500]
    return {
        "status": "TASK_SPEC_READY",
        "finding_id": finding_id,
        "finding_revision": row["revision"],
        "task_spec": {
            "project": project, "task_key": task_key, "step": "audit-remediation",
            "role": "software-engineer", "goal": goal, "reason": reason,
            "write_paths": [], "depends_on": [],
        },
        "task_created": False,
        "write_scope_assigned": False,
        "note": "This is a preview only. It does not register a task, assign write paths, invoke a host agent, or confirm a defect.",
    }


def link_task(conn, project, root, finding_id, task_key, expected_revision, confirm_write=False):
    """Link an already registered task to an accepted finding after explicit confirmation."""
    if not isinstance(finding_id, str) or not re.fullmatch(r"[A-Z0-9][A-Z0-9_.-]{0,79}", finding_id):
        raise ValueError("Invalid finding id")
    if not isinstance(task_key, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", task_key):
        raise ValueError("Invalid task key")
    if type(expected_revision) is not int or expected_revision < 1:
        raise ValueError("expected_revision must be a positive integer")
    row = conn.execute(
        """SELECT * FROM orbit_project_findings
           WHERE project=? AND project_root=? AND finding_id=?""",
        (project, str(root), finding_id),
    ).fetchone()
    if row is None:
        raise ValueError("Finding not found in selected project")
    if row["revision"] != expected_revision:
        return {"status": "STALE_REVISION", "finding": _public(row), "linked": False}
    if row["disposition"] != "ACCEPTED" or row["lifecycle"] in {"STALE", "RESOLVED"}:
        return {"status": "FINDING_NOT_ELIGIBLE", "finding": _public(row), "linked": False}
    task_table = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='orbit_agent_tasks'"
    ).fetchone()
    if not task_table:
        raise ValueError("Existing Orbit task ledger is unavailable")
    task = conn.execute(
        """SELECT status FROM orbit_agent_tasks
           WHERE project=? AND project_root=? AND task_key=?""",
        (project, str(root), task_key),
    ).fetchone()
    if task is None:
        raise ValueError("Task must already exist in the same project and root before linking")
    linked = json.loads(row["linked_task_ids"])
    if task_key in linked:
        return {"status": "ALREADY_LINKED", "finding": _public(row), "linked": True}
    if confirm_write is not True:
        return {"status": "PREVIEW_ONLY", "finding": _public(row),
                "task_key": task_key, "task_status": task["status"], "linked": False}
    linked.append(task_key)
    with conn:
        updated = conn.execute(
            """UPDATE orbit_project_findings
               SET linked_task_ids=?, revision=revision+1
               WHERE project=? AND project_root=? AND finding_id=? AND revision=?""",
            (_json(linked), project, str(root), finding_id, expected_revision),
        )
        if updated.rowcount != 1:
            raise ValueError("Finding revision conflict: refresh and retry")
        current = conn.execute(
            """SELECT * FROM orbit_project_findings
               WHERE project=? AND project_root=? AND finding_id=?""",
            (project, str(root), finding_id),
        ).fetchone()
    return {"status": "LINKED", "finding": _public(current),
            "task_key": task_key, "linked": True}
