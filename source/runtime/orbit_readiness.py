"""Persistent project scan/readiness state for one project root.

This ledger records when Orbit's bounded metadata inventory ran and whether it
completed. It is not a Git revision, content hash, continuous watcher, or proof
that the project has not changed since the recorded scan.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

AUDIT_VERSION = "metadata-inventory-v1"
SNAPSHOT_RE = re.compile(r"[a-f0-9]{64}")


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def setup(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS orbit_project_readiness (
        project TEXT NOT NULL,
        project_root TEXT NOT NULL,
        status TEXT NOT NULL,
        audit_version TEXT NOT NULL,
        scan_started_at TEXT NOT NULL,
        scan_completed_at TEXT,
        last_snapshot_sha256 TEXT,
        last_scan_complete INTEGER NOT NULL DEFAULT 0,
        last_error TEXT,
        file_count INTEGER NOT NULL DEFAULT 0,
        directory_count INTEGER NOT NULL DEFAULT 0,
        finding_count INTEGER NOT NULL DEFAULT 0,
        scan_count INTEGER NOT NULL DEFAULT 0,
        revision INTEGER NOT NULL DEFAULT 1,
        PRIMARY KEY(project, project_root)
    )""")
    conn.commit()


def _validate_scope(project, root):
    if not isinstance(project, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", project):
        raise ValueError("Invalid project key")
    if not isinstance(root, str) or not root or len(root) > 2000:
        raise ValueError("Invalid project root")


def _public(row):
    result = dict(row)
    result["last_scan_complete"] = bool(result["last_scan_complete"])
    result["snapshot_semantics"] = (
        "Bounded path/size/mtime metadata digest; not a content hash or Git revision."
    )
    result["freshness_semantics"] = (
        "Valid as of scan_completed_at only; no filesystem watcher monitors later changes."
    )
    result["scan_required_to_revalidate"] = True
    return result


def get_status(conn, project, root):
    _validate_scope(project, str(root))
    row = conn.execute(
        "SELECT * FROM orbit_project_readiness WHERE project=? AND project_root=?",
        (project, str(root)),
    ).fetchone()
    if row is None:
        return {
            "status": "SCAN_REQUIRED",
            "project": project,
            "project_root": str(root),
            "revision": 0,
            "scan_count": 0,
            "scan_required_to_revalidate": True,
            "freshness_semantics": "No persisted scan exists for this exact project/root.",
        }
    return _public(row)


def begin_scan(conn, project, root):
    """Persist SCANNING and return a revision token for completion/failure."""
    _validate_scope(project, str(root))
    started = _now()
    with conn:
        prior = conn.execute(
            "SELECT status, revision FROM orbit_project_readiness WHERE project=? AND project_root=?",
            (project, str(root)),
        ).fetchone()
        interrupted = bool(prior and prior["status"] == "SCANNING")
        revision = (prior["revision"] + 1) if prior else 1
        conn.execute(
            """INSERT INTO orbit_project_readiness
               (project,project_root,status,audit_version,scan_started_at,revision)
               VALUES(?,?,'SCANNING',?,?,?)
               ON CONFLICT(project,project_root) DO UPDATE SET
                 status='SCANNING',audit_version=excluded.audit_version,
                 scan_started_at=excluded.scan_started_at,last_error=NULL,
                 revision=excluded.revision""",
            (project, str(root), AUDIT_VERSION, started, revision),
        )
    return {
        "project": project,
        "project_root": str(root),
        "revision": revision,
        "scan_started_at": started,
        "recovered_interrupted_scan": interrupted,
    }


def complete_scan(conn, project, root, token, audit):
    """Record only a well-formed scan result from the active scan revision."""
    _validate_scope(project, str(root))
    if not isinstance(token, dict) or token.get("project") != project or token.get("project_root") != str(root):
        raise ValueError("Scan token does not match project scope")
    if type(token.get("revision")) is not int or token["revision"] < 1:
        raise ValueError("Invalid scan revision")
    if not isinstance(audit, dict) or audit.get("status") not in {"SCANNED", "INCOMPLETE"}:
        raise ValueError("Invalid project audit result")
    snapshot = audit.get("inventory_snapshot_sha256")
    if not isinstance(snapshot, str) or not SNAPSHOT_RE.fullmatch(snapshot):
        raise ValueError("Invalid inventory snapshot digest")
    summary = audit.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("Invalid project audit summary")
    counts = [summary.get("files"), summary.get("directories"), audit.get("findings_count")]
    if any(type(value) is not int or value < 0 for value in counts):
        raise ValueError("Invalid project audit counts")
    complete = audit["status"] == "SCANNED"
    completed = _now()
    with conn:
        prior = conn.execute(
            "SELECT * FROM orbit_project_readiness WHERE project=? AND project_root=?",
            (project, str(root)),
        ).fetchone()
        if prior is None or prior["revision"] != token["revision"] or prior["status"] != "SCANNING":
            return {"status": "STALE_SCAN_RESULT", "data_written": False}
        previous_snapshot = prior["last_snapshot_sha256"]
        changed = None if previous_snapshot is None else previous_snapshot != snapshot
        status = "SCANNED" if complete else "INCOMPLETE"
        update = conn.execute(
            """UPDATE orbit_project_readiness SET
                 status=?,scan_completed_at=?,last_snapshot_sha256=?,
                 last_scan_complete=?,last_error=NULL,file_count=?,directory_count=?,
                 finding_count=?,scan_count=scan_count+1,revision=revision+1
               WHERE project=? AND project_root=? AND revision=? AND status='SCANNING'""",
            (status, completed, snapshot, int(complete), counts[0], counts[1], counts[2],
             project, str(root), token["revision"]),
        )
        if update.rowcount != 1:
            return {"status": "STALE_SCAN_RESULT", "data_written": False}
    current = get_status(conn, project, root)
    return {
        **current,
        "changed_since_previous_scan": changed,
        "data_written": True,
        "scan_result": audit["status"],
    }


def fail_scan(conn, project, root, token, error_type):
    """Mark an interrupted scan failed without discarding the last good snapshot."""
    _validate_scope(project, str(root))
    if not isinstance(token, dict) or token.get("project") != project or token.get("project_root") != str(root):
        raise ValueError("Scan token does not match project scope")
    if type(token.get("revision")) is not int or token["revision"] < 1:
        raise ValueError("Invalid scan revision")
    safe_error = error_type if isinstance(error_type, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,79}", error_type) else "ScanError"
    with conn:
        update = conn.execute(
            """UPDATE orbit_project_readiness SET status='FAILED',last_scan_complete=0,
               last_error=?,revision=revision+1
               WHERE project=? AND project_root=? AND revision=? AND status='SCANNING'""",
            (safe_error, project, str(root), token["revision"]),
        )
    if update.rowcount != 1:
        return {"status": "STALE_SCAN_RESULT", "data_written": False}
    return {**get_status(conn, project, root), "data_written": True}
