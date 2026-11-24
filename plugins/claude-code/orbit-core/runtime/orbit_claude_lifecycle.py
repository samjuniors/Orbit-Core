"""Opt-in, privacy-minimal Claude Code lifecycle event ledger.

Only selected lifecycle event names and a digest of the host session ID are
stored. Prompt text, transcripts, tool inputs/results and permission decisions
are deliberately discarded.
"""
from __future__ import annotations

import hashlib
import os
import re
import uuid
from datetime import datetime, timedelta, timezone

HOST = "claude-code"
SCHEMA_VERSION = 1
ALLOWED_EVENTS = {"SessionStart", "PreCompact", "PostCompact", "SessionEnd"}
MAX_EVENTS_PER_ROOT = 500
RETENTION_DAYS = 30


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def setup(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS orbit_host_lifecycle_events (
            event_id TEXT PRIMARY KEY,
            host TEXT NOT NULL,
            project_root TEXT NOT NULL,
            event_name TEXT NOT NULL,
            session_digest TEXT,
            occurred_at TEXT NOT NULL,
            schema_version INTEGER NOT NULL
        )"""
    )
    conn.execute(
        """CREATE INDEX IF NOT EXISTS idx_orbit_host_lifecycle_root_time
           ON orbit_host_lifecycle_events(project_root, occurred_at DESC)"""
    )
    conn.commit()


def record_event(conn, project_root, event_name, session_id=None, occurred_at=None):
    """Persist a minimal event observation, never raw host payload data."""
    if not isinstance(project_root, str) or not project_root or len(project_root) > 2000:
        raise ValueError("Invalid project root")
    if event_name not in ALLOWED_EVENTS:
        raise ValueError("Unsupported Claude Code lifecycle event")
    if session_id is not None and (
        not isinstance(session_id, str) or not session_id or len(session_id) > 256
    ):
        raise ValueError("Invalid session identifier")
    if occurred_at is None:
        occurred_at = _now()
    if not isinstance(occurred_at, str) or len(occurred_at) > 40:
        raise ValueError("Invalid event timestamp")
    try:
        parsed = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("Event timestamp must include timezone")
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid event timestamp") from exc

    session_digest = (
        hashlib.sha256(session_id.encode("utf-8")).hexdigest()
        if session_id is not None else None
    )
    setup(conn)
    event_id = uuid.uuid4().hex
    cutoff = (datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)).isoformat(timespec="seconds")
    with conn:
        conn.execute(
            """INSERT INTO orbit_host_lifecycle_events
               (event_id,host,project_root,event_name,session_digest,occurred_at,schema_version)
               VALUES(?,?,?,?,?,?,?)""",
            (event_id, HOST, project_root, event_name, session_digest, parsed.astimezone(timezone.utc).isoformat(timespec="seconds"), SCHEMA_VERSION),
        )
        conn.execute(
            "DELETE FROM orbit_host_lifecycle_events WHERE project_root=? AND occurred_at<?",
            (project_root, cutoff),
        )
        conn.execute(
            """DELETE FROM orbit_host_lifecycle_events
               WHERE project_root=? AND event_id NOT IN (
                   SELECT event_id FROM orbit_host_lifecycle_events
                   WHERE project_root=? ORDER BY occurred_at DESC,event_id DESC LIMIT ?
               )""",
            (project_root, project_root, MAX_EVENTS_PER_ROOT),
        )
    return {
        "status": "RECORDED",
        "host": HOST,
        "event_name": event_name,
        "project_root": project_root,
        "session_id_stored": False,
        "session_digest_stored": session_digest is not None,
        "raw_hook_payload_stored": False,
        "prompt_or_transcript_stored": False,
        "retention_days": RETENTION_DAYS,
        "max_events_per_project": MAX_EVENTS_PER_ROOT,
    }


def recent_events(conn, project_root, limit=8):
    try:
        project_root = os.fspath(project_root)
    except TypeError as exc:
        raise ValueError("Invalid project root") from exc
    if not isinstance(project_root, str) or not project_root or len(project_root) > 2000:
        raise ValueError("Invalid project root")
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError("limit must be 1..20")
    rows = conn.execute(
        """SELECT host,event_name,occurred_at
           FROM orbit_host_lifecycle_events
           WHERE project_root=?
           ORDER BY occurred_at DESC,event_id DESC LIMIT ?""",
        (project_root, limit),
    ).fetchall()
    events = [dict(row) for row in rows]
    return {
        "status": "EVENTS_AVAILABLE" if events else "NO_EVENTS_RECORDED",
        "events": events,
        "scope": "Exact resolved project root",
        "stored_fields": ["host", "event_name", "project_root", "session_id_sha256", "occurred_at"],
        "excluded_fields": ["prompt_text", "transcript_path", "tool_input", "tool_result", "permission_decision", "model_output"],
        "retention_days": RETENTION_DAYS,
        "max_events_per_project": MAX_EVENTS_PER_ROOT,
        "host_execution_attested": False,
    }
