"""Opt-in Orbit Autopilot local runner command — DEVELOPMENT, not installed.

This tool is not an MCP server command or background service. It executes
one reviewed task per invocation, ONLY on an isolated Git clone. The user
must be physically present at the local terminal to confirm each invocation.
Such confirmation is not cryptographic authentication of the founder.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source" / "runtime"))

import orbit_autopilot
import orbit_autopilot_runner
import orbit_mcp


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Unreleased Orbit Autopilot local one-task supervisor")
    parser.add_argument("action", choices=("preview", "run", "stop", "status"))
    parser.add_argument("--project-root", required=True,
                        help="Exact existing clean feature-branch Git project root")
    parser.add_argument("--project", required=True)
    parser.add_argument("--mission-id", required=True)
    parser.add_argument("--revision", type=int, default=1)
    parser.add_argument("--local-db",
                        help="Optional project-scoped SQLite path; defaults to Orbit's configured DB")
    args = parser.parse_args(argv)

    # A caller cannot override the host binary, sandbox, approval policy,
    # write scope, model, runner capacity, or machine permissions.
    root = orbit_mcp.project_root({"project_root": args.project_root})
    project = orbit_mcp.project_key({"project": args.project})
    mission = orbit_autopilot._mission_id({"mission_id": args.mission_id})
    if args.local_db:
        target = Path(args.local_db).expanduser().resolve()
        if target.is_dir():
            parser.error("--local-db must point to a SQLite file, not directory")
        os.environ["ORBIT_LOCAL_DB"] = str(target)
    conn = orbit_mcp.db_connect()
    orbit_autopilot_runner.setup(conn)
    try:
        if args.action == "status":
            result = orbit_autopilot_runner._public(
                orbit_autopilot_runner._job(conn, root, project, mission))
        elif args.action == "preview":
            result = orbit_autopilot_runner.preview(
                conn, root, project, mission, args.revision)
        elif args.action == "stop":
            result = orbit_autopilot_runner.stop(conn, root, project, mission)
        else:
            plan = orbit_autopilot_runner.preview(
                conn, root, project, mission, args.revision)
            if plan["status"] != "READY_FOR_LOCAL_OPERATOR_REVIEW":
                print(json.dumps(plan, indent=2), flush=True)
                return 2
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                print("BLOCKED: --run requires an interactive local terminal; "
                      "no stdin pipe, redirected output or headless bypass is permitted", file=sys.stderr)
                return 2
            print(json.dumps(plan, indent=2), flush=True)
            challenge = "RUN " + mission + " " + plan["task_key"]
            print("One locally sandboxed Codex task only. This will consume host "
                  "quota, may edit an isolated temporary clone and will stop "
                  "for independent review. No merge, publish or deploy.")
            try:
                response = input("Type " + repr(challenge) + " to approve: ")
            except (EOFError, KeyboardInterrupt):
                print("BLOCKED: local operator input unavailable or cancelled",
                      file=sys.stderr)
                return 2
            if response != challenge:
                print("BLOCKED: approval not supplied", file=sys.stderr)
                return 2
            result = orbit_autopilot_runner.run_once(
                conn, root, project, mission, args.revision,
                operator_confirmed=True)
        print(json.dumps(result, indent=2), flush=True)
        return 0 if result["status"] in {
            "READY_FOR_LOCAL_OPERATOR_REVIEW", "REVIEW_REQUIRED",
            "STOP_REQUESTED", "STOPPED", "NO_RUN"} else 2
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
