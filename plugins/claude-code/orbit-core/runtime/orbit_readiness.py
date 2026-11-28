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
        source_status TEXT NOT NULL DEFAULT 'SCAN_REQUIRED',
        source_audit_version TEXT NOT NULL DEFAULT 'source-static-v1',
        source_scan_started_at TEXT,
        source_scan_completed_at TEXT,
        source_snapshot_sha256 TEXT,
        source_scan_complete INTEGER NOT NULL DEFAULT 0,
        source_last_error TEXT,
        source_file_count INTEGER NOT NULL DEFAULT 0,
        source_bytes_read INTEGER NOT NULL DEFAULT 0,
        source_finding_count INTEGER NOT NULL DEFAULT 0,
        source_scan_count INTEGER NOT NULL DEFAULT 0,
        source_revision INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY(project, project_root)
    )""")
    columns = {row[1] for row in conn.execute("PRAGMA table_info(orbit_project_readiness)")}
    migrations = {
        "source_status": "TEXT NOT NULL DEFAULT 'SCAN_REQUIRED'",
        "source_audit_version": "TEXT NOT NULL DEFAULT 'source-static-v1'",
        "source_scan_started_at": "TEXT",
        "source_scan_completed_at": "TEXT",
        "source_snapshot_sha256": "TEXT",
        "source_scan_complete": "INTEGER NOT NULL DEFAULT 0",
        "source_last_error": "TEXT",
        "source_file_count": "INTEGER NOT NULL DEFAULT 0",
        "source_bytes_read": "INTEGER NOT NULL DEFAULT 0",
        "source_finding_count": "INTEGER NOT NULL DEFAULT 0",
        "source_scan_count": "INTEGER NOT NULL DEFAULT 0",
        "source_revision": "INTEGER NOT NULL DEFAULT 0",
    }
    for name, declaration in migrations.items():
        if name not in columns:
            conn.execute(f"ALTER TABLE orbit_project_readiness ADD COLUMN {name} {declaration}")
    conn.commit()


def _validate_scope(project, root):
    if not isinstance(project, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", project):
        raise ValueError("Invalid project key")
    if not isinstance(root, str) or not root or len(root) > 2000:
        raise ValueError("Invalid project root")


def _public(row):
    result = dict(row)
    result["last_scan_complete"] = bool(result["last_scan_complete"])
    result["source_scan_complete"] = bool(result["source_scan_complete"])
    result["snapshot_semantics"] = (
        "Bounded path/size/mtime metadata digest; not a content hash or Git revision."
        if result["last_scan_complete"] else
        "Latest scan attempt was incomplete; any stored digest is not a complete current inventory snapshot."
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
    blocked = audit.get("scan_block_reason") == "WINDOWS_REPARSE_POINT_SAFE_RELATIVE_OPEN_UNAVAILABLE"
    if blocked:
        if audit.get("status") != "INCOMPLETE" or snapshot is not None:
            raise ValueError("Invalid blocked project audit result")
    elif not isinstance(snapshot, str) or not SNAPSHOT_RE.fullmatch(snapshot):
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
        changed = (
            None if blocked or previous_snapshot is None
            else previous_snapshot != snapshot
        )
        stored_snapshot = previous_snapshot if blocked else snapshot
        stored_counts = (
            [prior["file_count"], prior["directory_count"], prior["finding_count"]]
            if blocked else counts
        )
        status = "SCANNED" if complete else "INCOMPLETE"
        update = conn.execute(
            """UPDATE orbit_project_readiness SET
                 status=?,scan_completed_at=?,last_snapshot_sha256=?,
                 last_scan_complete=?,last_error=NULL,file_count=?,directory_count=?,
                 finding_count=?,scan_count=scan_count+1,revision=revision+1
               WHERE project=? AND project_root=? AND revision=? AND status='SCANNING'""",
            (status, completed, stored_snapshot, int(complete),
             stored_counts[0], stored_counts[1], stored_counts[2],
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


def begin_source_scan(conn, project, root):
    """Persist an explicit source scan start and return a revision token."""
    _validate_scope(project, str(root))
    started = _now()
    with conn:
        prior = conn.execute(
            "SELECT source_status, source_revision FROM orbit_project_readiness WHERE project=? AND project_root=?",
            (project, str(root)),
        ).fetchone()
        interrupted = bool(prior and prior["source_status"] == "SCANNING")
        revision = (prior["source_revision"] + 1) if prior else 1
        conn.execute(
            """INSERT INTO orbit_project_readiness
               (project,project_root,status,audit_version,scan_started_at,revision,
                source_status,source_audit_version,source_scan_started_at,source_revision)
               VALUES(?,?,'SCAN_REQUIRED',?,?,1,'SCANNING','source-static-v1',?,?)
               ON CONFLICT(project,project_root) DO UPDATE SET
                 source_status='SCANNING',source_audit_version='source-static-v1',
                 source_scan_started_at=excluded.source_scan_started_at,
                 source_last_error=NULL,source_revision=excluded.source_revision""",
            (project, str(root), AUDIT_VERSION, started, started, revision),
        )
    return {
        "project": project, "project_root": str(root), "revision": revision,
        "scan_started_at": started, "recovered_interrupted_scan": interrupted,
    }


def complete_source_scan(conn, project, root, token, audit):
    """Persist source-scan metadata only; never persist source file contents."""
    _validate_scope(project, str(root))
    if not isinstance(token, dict) or token.get("project") != project or token.get("project_root") != str(root):
        raise ValueError("Source scan token does not match project scope")
    if type(token.get("revision")) is not int or token["revision"] < 1:
        raise ValueError("Invalid source scan revision")
    if not isinstance(audit, dict) or audit.get("status") not in {"SCANNED", "INCOMPLETE"}:
        raise ValueError("Invalid source audit result")
    snapshot = audit.get("inventory_snapshot_sha256")
    if not isinstance(snapshot, str) or not SNAPSHOT_RE.fullmatch(snapshot):
        raise ValueError("Invalid source snapshot digest")
    summary = audit.get("summary")
    if not isinstance(summary, dict):
        raise ValueError("Invalid source audit summary")
    counts = [summary.get("source_files"), summary.get("source_bytes_read"), audit.get("findings_count")]
    if any(type(value) is not int or value < 0 for value in counts):
        raise ValueError("Invalid source audit counts")
    complete = audit["status"] == "SCANNED"
    completed = _now()
    with conn:
        prior = conn.execute(
            "SELECT * FROM orbit_project_readiness WHERE project=? AND project_root=?",
            (project, str(root)),
        ).fetchone()
        if prior is None or prior["source_revision"] != token["revision"] or prior["source_status"] != "SCANNING":
            return {"status": "STALE_SOURCE_SCAN_RESULT", "data_written": False}
        previous_snapshot = prior["source_snapshot_sha256"]
        changed = None if previous_snapshot is None else previous_snapshot != snapshot
        status = "SCANNED" if complete else "INCOMPLETE"
        update = conn.execute(
            """UPDATE orbit_project_readiness SET
                 source_status=?,source_scan_completed_at=?,source_snapshot_sha256=?,
                 source_scan_complete=?,source_last_error=NULL,source_file_count=?,
                 source_bytes_read=?,source_finding_count=?,source_scan_count=source_scan_count+1,
                 source_revision=source_revision+1
               WHERE project=? AND project_root=? AND source_revision=? AND source_status='SCANNING'""",
            (status, completed, snapshot, int(complete), counts[0], counts[1], counts[2],
             project, str(root), token["revision"]),
        )
        if update.rowcount != 1:
            return {"status": "STALE_SOURCE_SCAN_RESULT", "data_written": False}
    current = get_status(conn, project, root)
    return {
        "status": current["source_status"],
        "source_status": current["source_status"],
        "source_scan_completed_at": current["source_scan_completed_at"],
        "source_snapshot_sha256": current["source_snapshot_sha256"],
        "source_scan_complete": current["source_scan_complete"],
        "source_file_count": current["source_file_count"],
        "source_bytes_read": current["source_bytes_read"],
        "source_finding_count": current["source_finding_count"],
        "source_scan_count": current["source_scan_count"],
        "source_revision": current["source_revision"],
        "changed_since_previous_source_scan": changed,
        "data_written": True,
    }


def fail_source_scan(conn, project, root, token, error_type):
    """Mark a failed source scan while preserving the previous source snapshot."""
    _validate_scope(project, str(root))
    if not isinstance(token, dict) or token.get("project") != project or token.get("project_root") != str(root):
        raise ValueError("Source scan token does not match project scope")
    if type(token.get("revision")) is not int or token["revision"] < 1:
        raise ValueError("Invalid source scan revision")
    safe_error = error_type if isinstance(error_type, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,79}", error_type) else "SourceScanError"
    with conn:
        update = conn.execute(
            """UPDATE orbit_project_readiness SET source_status='FAILED',
               source_scan_complete=0,source_last_error=?,source_revision=source_revision+1
               WHERE project=? AND project_root=? AND source_revision=? AND source_status='SCANNING'""",
            (safe_error, project, str(root), token["revision"]),
        )
    if update.rowcount != 1:
        return {"status": "STALE_SOURCE_SCAN_RESULT", "data_written": False}
    current = get_status(conn, project, root)
    return {
        "status": current["source_status"],
        "source_status": current["source_status"],
        "source_last_error": current["source_last_error"],
        "source_snapshot_sha256": current["source_snapshot_sha256"],
        "source_scan_complete": current["source_scan_complete"],
        "data_written": True,
    }
