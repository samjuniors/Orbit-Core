"""Fail-open Claude Code hook adapter for the explicitly enabled optional hooks."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import orbit_claude_lifecycle
import orbit_mcp

MAX_INPUT_BYTES = 64 * 1024


def process_payload(payload, conn):
    if not isinstance(payload, dict):
        return {"status": "IGNORED", "reason": "invalid_payload"}
    event_name = payload.get("hook_event_name")
    if event_name not in orbit_claude_lifecycle.ALLOWED_EVENTS:
        return {"status": "IGNORED", "reason": "unsupported_event"}
    cwd = payload.get("cwd")
    if not isinstance(cwd, str) or not cwd:
        return {"status": "IGNORED", "reason": "project_root_missing"}
    # Reuse Orbit's host-side path validation and configured trusted-root policy.
    try:
        root = orbit_mcp.project_root({"project_root": cwd, "project": "claude-code-hook"})
    except OSError as exc:
        raise ValueError("Invalid Claude Code project root") from exc
    session_id = payload.get("session_id")
    return orbit_claude_lifecycle.record_event(
        conn, str(root), event_name, session_id=session_id
    )


def main():
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        return 0
    conn = None
    try:
        payload = json.loads(raw.decode("utf-8"))
        conn = orbit_mcp.db_connect()
        process_payload(payload, conn)
    except Exception:
        # Lifecycle telemetry must never block a Claude Code operation.
        # Do not print exception details: they may contain local paths or payload data.
        return 0
    finally:
        if conn is not None:
            conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
