"""Persistent, revision-aware reconciliation for structural project findings.

The ledger stores only Orbit-generated structural signals and review dispositions.
It does not certify defects, read source contents, execute project code, or create tasks.
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
        PRIMARY KEY(project, project_root, finding_id)
    )""")
    conn.execute("""CREATE INDEX IF NOT EXISTS idx_orbit_findings_scope
                    ON orbit_project_findings(project, project_root, lifecycle)""")
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
        not isinstance(path, str) or len(path) > 240 or path.startswith("/") or ".." in path.split("/")
        for path in evidence
    ):
        raise ValueError("Audit finding evidence paths are invalid")
    payload = {"category": category, "severity": severity, "confidence": confidence,
               "summary": summary, "evidence": evidence, "recommendation": recommendation}
    digest = hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()
    return fid, payload, digest


def reconcile(conn, project, root, audit):
    """Persist one complete or incomplete scan without false resolution."""
    if not isinstance(project, str) or not project or len(project) > 80:
        raise ValueError("Invalid project key")
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
                   WHERE project=? AND project_root=? AND lifecycle IN ('NEW','OPEN','RECURRING')""",
                (project, path),
            )
            rows = conn.execute(
                "SELECT * FROM orbit_project_findings WHERE project=? AND project_root=? ORDER BY finding_id",
                (project, path),
            ).fetchall()
            return {
                "status": "RECONCILED_INCOMPLETE",
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
                "SELECT * FROM orbit_project_findings WHERE project=? AND project_root=?",
                (project, path),
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
                    evidence_sha256,occurrence_count,revision,linked_task_ids)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(project,project_root,finding_id) DO UPDATE SET
                    category=excluded.category,severity=excluded.severity,confidence=excluded.confidence,
                    summary=excluded.summary,evidence=excluded.evidence,recommendation=excluded.recommendation,
                    lifecycle=excluded.lifecycle,disposition=excluded.disposition,last_seen=excluded.last_seen,
                    last_snapshot=excluded.last_snapshot,evidence_sha256=excluded.evidence_sha256,
                    occurrence_count=excluded.occurrence_count,revision=excluded.revision""",
                (project, path, fid, payload["category"], payload["severity"], payload["confidence"],
                 payload["summary"], _json(payload["evidence"]), payload["recommendation"], lifecycle,
                 disposition, first_seen, now, snapshot, evidence_digest, count, revision, links),
            )

        resolved_count = 0
        for fid, old in previous.items():
            if fid not in current_ids and old["lifecycle"] != "RESOLVED":
                conn.execute(
                    """UPDATE orbit_project_findings SET lifecycle='RESOLVED',last_snapshot=?,
                       revision=revision+1 WHERE project=? AND project_root=? AND finding_id=?""",
                    (snapshot, project, path, fid),
                )
                resolved_count += 1
        rows = conn.execute(
            "SELECT * FROM orbit_project_findings WHERE project=? AND project_root=? ORDER BY finding_id",
            (project, path),
        ).fetchall()
    return {
        "status": "RECONCILED",
        "complete_scan": True,
        "snapshot": snapshot,
        "new_count": sum(1 for row in rows if row["lifecycle"] == "NEW" and row["last_snapshot"] == snapshot),
        "resolved_count": resolved_count,
        "open_count": sum(1 for row in rows if row["lifecycle"] in ACTIVE_STATUSES),
        "findings": [_public(row) for row in rows],
        "data_written": True,
        "tasks_created": False,
    }


def list_findings(conn, project, root, limit=100):
    if type(limit) is not int or not 1 <= limit <= 200:
        raise ValueError("limit must be 1..200")
    rows = conn.execute(
        """SELECT * FROM orbit_project_findings
           WHERE project=? AND project_root=?
           ORDER BY CASE lifecycle WHEN 'NEW' THEN 0 WHEN 'RECURRING' THEN 1
                    WHEN 'OPEN' THEN 2 WHEN 'STALE' THEN 3 ELSE 4 END, finding_id
           LIMIT ?""",
        (project, str(root), limit),
    ).fetchall()
    return {"status": "FOUND" if rows else "EMPTY", "findings": [_public(row) for row in rows],
            "count": len(rows), "tasks_created": False}


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
