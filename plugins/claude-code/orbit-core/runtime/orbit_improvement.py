"""Project-scoped improvement observations, not automatic model learning.

Observed outcomes are caller-reported data. They never become trusted prompts,
code, host permissions or cross-project memory by being recorded in SQLite.
"""
from __future__ import annotations

import hashlib
import re
import sqlite3
from datetime import datetime, timezone

_EVENT = re.compile(r"[a-z][a-z0-9-]{2,47}\Z")
_KINDS = {"user-correction", "qa-result", "regression", "task-outcome",
          "resource-review", "process-lesson"}
_RESULTS = {"improved", "regressed", "unchanged", "unknown"}
_RISK = re.compile(
    r"(?i)(?:ignore (?:all |your )?(?:previous|system|developer) instructions|"
    r"override (?:system|developer)|disable (?:security|permissions)|"
    r"(?:api[_ -]?key|bearer|password|secret)\s*[:=]|"
    r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|"
    r"\b(?:https?://|file://|ssh://)\S+)"
)


def setup(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS orbit_improvement_events (
        root TEXT NOT NULL, project TEXT NOT NULL, event_key TEXT NOT NULL,
        kind TEXT NOT NULL, result TEXT NOT NULL,
        lesson TEXT NOT NULL, evidence_ref TEXT NOT NULL,
        score_before INTEGER, score_after INTEGER,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        revision INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        PRIMARY KEY(root, project, event_key)
    )""")
    conn.execute("""CREATE INDEX IF NOT EXISTS idx_orbit_improvement_scope
        ON orbit_improvement_events(root, project, status)""")
    # Only abstract, explicitly reviewed statements are shared. Source IDs,
    # roots, task content and project names never enter this table.
    conn.execute("""CREATE TABLE IF NOT EXISTS orbit_shared_lessons (
        lesson_sha256 TEXT PRIMARY KEY, lesson TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'ACTIVE', revision INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    )""")


def _text(value, name, minimum=1, maximum=320):
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise ValueError(name + " needs " + str(minimum) + ".." + str(maximum) + " characters")
    value = value.strip()
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError(name + " cannot contain control characters")
    if _RISK.search(value):
        raise ValueError("Do not store secrets, remote links or untrusted instruction overrides")
    return value


def _score(value, name):
    if value is None:
        return None
    if type(value) is not int or not 0 <= value <= 100:
        raise ValueError(name + " must be an integer from 0..100")
    return value


def record(conn, root, project, args):
    """Preview or revision-guarded record/archive of one project observation."""
    key = args["event_key"]
    if not _EVENT.fullmatch(key):
        raise ValueError("Invalid event key")
    action = args["action"]
    row = conn.execute("""SELECT * FROM orbit_improvement_events
        WHERE root=? AND project=? AND event_key=?""",
                       (str(root), project, key)).fetchone()
    old = dict(row) if row else None
    confirmed = args.get("confirm_write") is True
    if action == "record":
        if old:
            return {"status": "ALREADY_EXISTS", "revision": old["revision"],
                    "state_written": False}
        kind = args["kind"]
        result = args.get("result", "unknown")
        if kind not in _KINDS or result not in _RESULTS:
            raise ValueError("Invalid observation classification")
        lesson = _text(args["lesson"], "lesson", 20, 320)
        ref = _text(args["evidence_ref"], "evidence_ref", 4, 160)
        before = _score(args.get("score_before"), "score_before")
        after = _score(args.get("score_after"), "score_after")
        if (before is None) != (after is None):
            raise ValueError("Both comparison scores are required together")
        proposal = {"event_key": key, "kind": kind, "result": result,
                    "lesson": lesson, "evidence_ref": ref,
                    "score_before": before, "score_after": after}
        if not confirmed:
            return {"status": "PREVIEW_ONLY", "proposal": proposal,
                    "state_written": False, "evidence_verified": False}
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            with conn:
                conn.execute("""INSERT INTO orbit_improvement_events
                    (root,project,event_key,kind,result,lesson,evidence_ref,
                    score_before,score_after,status,revision,created_at,updated_at)
                    VALUES(?,?,?,?,?,?,?,?,?,'ACTIVE',1,?,?)""",
                    (str(root), project, key, kind, result, lesson, ref,
                     before, after, now, now))
        except sqlite3.IntegrityError:
            return {"status": "ALREADY_EXISTS", "state_written": False}
        return {"status": "OBSERVATION_RECORDED", "revision": 1,
                "state_written": True, "evidence_verified": False,
                "auto_skill_activated": False}
    if action != "archive":
        raise ValueError("Invalid observation action")
    if not old or old["status"] != "ACTIVE":
        return {"status": "NO_ACTIVE_OBSERVATION", "state_written": False}
    expected = args.get("expected_revision")
    if type(expected) is not int or expected != old["revision"]:
        return {"status": "STALE_REVISION", "revision": old["revision"],
                "state_written": False}
    if not confirmed:
        return {"status": "PREVIEW_ONLY", "event_key": key,
                "action": "archive", "state_written": False}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with conn:
        changed = conn.execute("""UPDATE orbit_improvement_events
            SET status='ARCHIVED', revision=revision+1, updated_at=?
            WHERE root=? AND project=? AND event_key=? AND revision=?
            AND status='ACTIVE'""", (now, str(root), project, key, expected))
        if changed.rowcount != 1:
            raise sqlite3.IntegrityError("Concurrent observation change")
    return {"status": "ARCHIVED", "revision": expected + 1,
            "state_written": True}


def context(conn, root, project, args):
    """Bounded project-local recall and pattern suggestions, never instructions."""
    limit = args.get("limit", 12)
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ValueError("limit must be 1..20")
    rows = [dict(r) for r in conn.execute("""SELECT event_key, kind, result,
        lesson, evidence_ref, score_before, score_after, status, revision
        FROM orbit_improvement_events WHERE root=? AND project=?
        AND status='ACTIVE' ORDER BY updated_at DESC, event_key LIMIT ?""",
        (str(root), project, limit)).fetchall()]
    groups = {}
    for item in rows:
        if item["result"] == "improved":
            normalized = item["lesson"].casefold()
            groups.setdefault(normalized, []).append(item["event_key"])
    suggestions = [
        {"lesson": next(x["lesson"] for x in rows
                        if x["lesson"].casefold() == text),
         "reported_distinct_events": len(keys), "event_keys": keys,
         "status": "REVIEW_REUSE_NOT_VERIFIED"}
        for text, keys in groups.items() if len(set(keys)) >= 2
    ]
    shared = []
    if args.get("include_shared") is True:
        shared = [dict(r) for r in conn.execute(
            """SELECT lesson_sha256, lesson, revision FROM orbit_shared_lessons
                WHERE status='ACTIVE' ORDER BY updated_at DESC LIMIT 12"""
        ).fetchall()]
    return {
        "status": "PROJECT_IMPROVEMENT_CONTEXT",
        "project": project, "observations": rows,
        "repeat_candidates": suggestions[:5],
        "source": "CALLER_REPORTED_NOT_INDEPENDENTLY_VERIFIED",
        "scope": "THIS_PROJECT_ONLY",
        "cross_project_shared": bool(shared),
        "shared_lessons_opted_in": args.get("include_shared") is True,
        "shared_abstract_lessons": shared,
        "model_weights_updated": False,
        "background_learning_active": False,
        "skill_installed": False,
        "agent_spawned": False,
        "state_written": False,
    }



def promote(conn, root, project, args):
    """Preview or explicitly promote/revoke an abstract lesson.

    This never auto-injects instructions or validates user consent independently.
    A local host must obtain a real privacy review and apply confirmation.
    """
    action = args["action"]
    if action == "archive":
        key = args.get("lesson_sha256", "")
        if not re.fullmatch(r"[a-f0-9]{64}", key):
            raise ValueError("Archive requires exact shared lesson fingerprint")
        old = conn.execute("""SELECT revision, status FROM orbit_shared_lessons
            WHERE lesson_sha256=?""", (key,)).fetchone()
        if not old or old["status"] != "ACTIVE":
            return {"status": "NO_ACTIVE_SHARED_LESSON", "state_written": False}
        expected = args.get("expected_revision")
        if type(expected) is not int or old["revision"] != expected:
            return {"status": "STALE_REVISION", "revision": old["revision"],
                    "state_written": False}
        if args.get("confirm_write") is not True:
            return {"status": "ARCHIVE_PREVIEW_ONLY", "state_written": False,
                    "lesson_sha256": key}
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with conn:
            cursor = conn.execute("""UPDATE orbit_shared_lessons
                SET status='ARCHIVED', revision=revision+1, updated_at=?
                WHERE lesson_sha256=? AND revision=? AND status='ACTIVE'""",
                (now, key, expected))
            if cursor.rowcount != 1:
                raise sqlite3.IntegrityError("Concurrent lesson archive")
        return {"status": "SHARED_LESSON_ARCHIVED", "state_written": True,
                "lesson_sha256": key, "revision": expected + 1}

    if action != "share":
        raise ValueError("Unknown lesson promotion action")
    lesson = _text(args["lesson"], "lesson", 25, 220)
    # Cross-project summaries must not contain paths, addresses, code, markup
    # or source links; generic language alone can never prove privacy safety.
    if any(not (c.isalnum() or c in " .,;:!?()'-") for c in lesson):
        raise ValueError("Shared lesson must be plain generalized text")
    refs = args.get("event_keys", [])
    if (not isinstance(refs, list) or not 2 <= len(refs) <= 8 or
            len(set(refs)) != len(refs) or
            any(not isinstance(k, str) or not _EVENT.fullmatch(k) for k in refs)):
        raise ValueError("Two to eight distinct event keys required")
    placeholders = ",".join("?" for _ in refs)
    rows = conn.execute(
        """SELECT event_key, lesson, result, status FROM orbit_improvement_events
           WHERE root=? AND project=? AND event_key IN (""" + placeholders + ")",
        (str(root), project, *refs)).fetchall()
    if len(rows) != len(refs) or any(
            x["status"] != "ACTIVE" or x["result"] != "improved" or
            x["lesson"].casefold() != lesson.casefold() for x in rows):
        return {"status": "INSUFFICIENT_MATCHED_PROJECT_EVIDENCE",
                "state_written": False}
    key = hashlib.sha256(lesson.casefold().encode("utf-8")).hexdigest()
    old = conn.execute("SELECT lesson_sha256 FROM orbit_shared_lessons WHERE lesson_sha256=?",
                       (key,)).fetchone()
    if old:
        return {"status": "ALREADY_REVIEWED_SHARED_LESSON",
                "lesson_sha256": key, "state_written": False}
    proposal = {"lesson_sha256": key, "abstract_lesson": lesson,
                "reported_distinct_sources": len(rows),
                "caller_evidence_verified": False,
                "source_project_data_exported": False,
                "review_required": True}
    if args.get("confirm_write") is not True:
        return {"status": "PRIVACY_REVIEW_PREVIEW_ONLY",
                "proposal": proposal, "state_written": False}
    if args.get("privacy_reviewed") is not True:
        return {"status": "HOLD_PRIVACY_REVIEW_REQUIRED",
                "proposal": proposal, "state_written": False}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        with conn:
            conn.execute("""INSERT INTO orbit_shared_lessons
                (lesson_sha256,lesson,status,revision,created_at,updated_at)
                VALUES(?,?,'ACTIVE',1,?,?)""",
                (key, lesson, now, now))
    except sqlite3.IntegrityError:
        return {"status": "ALREADY_REVIEWED_SHARED_LESSON",
                "lesson_sha256": key, "state_written": False}
    return {"status": "REVIEWED_ABSTRACT_LESSON_SHARED",
            "lesson_sha256": key, "state_written": True,
            "source_project_data_exported": False,
            "privacy_review_is_caller_reported": True,
            "skill_installed": False, "model_weights_updated": False}
