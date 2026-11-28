#!/usr/bin/env python3
"""Repeat the MCP shared-SQLite subprocess test with updater checks on/off.

Each iteration gets a fresh updater cache. Full child stdout/stderr, including
faulthandler output and the unittest assertion containing the child exit code,
is retained under artifacts/mcp-stress for CI artifact upload.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEST = [
    sys.executable, "-X", "faulthandler", "-m", "unittest", "discover",
    "-s", "tests", "-p", "test_universal.py",
    "-k", "test_mcp_process_and_shared_db", "-v",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--modes", nargs="+", choices=("enabled", "disabled"),
                        default=("enabled", "disabled"))
    parser.add_argument("--log-dir", type=Path,
                        default=ROOT / "artifacts" / "mcp-stress")
    args = parser.parse_args()
    if args.iterations < 1 or args.iterations > 100:
        parser.error("--iterations must be between 1 and 100")

    args.log_dir.mkdir(parents=True, exist_ok=True)
    failures: list[str] = []
    total = 0

    for mode in args.modes:
        for iteration in range(1, args.iterations + 1):
            total += 1
            with tempfile.TemporaryDirectory(prefix="orbit-mcp-stress-") as temp:
                cache = Path(temp) / "update-home"
                cache.mkdir()
                env = os.environ.copy()
                env.update({
                    "ORBIT_UPDATE_CHECK": "1" if mode == "enabled" else "0",
                    "ORBIT_UPDATE_HOME": str(cache),
                    "PYTHONFAULTHANDLER": "1",
                    "PYTHONUNBUFFERED": "1",
                })
                started = time.monotonic()
                try:
                    result = subprocess.run(
                        TEST, cwd=ROOT, env=env, text=True,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        timeout=90, check=False,
                    )
                    code = result.returncode
                    stdout, stderr = result.stdout, result.stderr
                except subprocess.TimeoutExpired as exc:
                    code = 124
                    stdout = exc.stdout or ""
                    stderr = exc.stderr or ""
                    if isinstance(stdout, bytes):
                        stdout = stdout.decode("utf-8", errors="replace")
                    if isinstance(stderr, bytes):
                        stderr = stderr.decode("utf-8", errors="replace")
                    stderr += "\nSTRESS_HARNESS_TIMEOUT: unittest exceeded 90 seconds\n"

                elapsed = time.monotonic() - started
                log = (
                    f"mode={mode} iteration={iteration}/{args.iterations} "
                    f"returncode={code} elapsed_seconds={elapsed:.3f}\n"
                    f"--- stdout ---\n{stdout}\n"
                    f"--- stderr (includes child stderr on assertion failure) ---\n{stderr}\n"
                )
                log_path = args.log_dir / f"{mode}-{iteration:02d}.log"
                log_path.write_text(log, encoding="utf-8")
                if code:
                    failures.append(f"{mode} iteration {iteration}: exit {code}")
                    print(f"FAIL {mode} {iteration}/{args.iterations} "
                          f"(exit={code}, {elapsed:.1f}s; {log_path})", flush=True)
                else:
                    print(f"PASS {mode} {iteration}/{args.iterations} "
                          f"({elapsed:.1f}s)", flush=True)

    print(f"SUMMARY: {total - len(failures)}/{total} passed; "
          f"{len(failures)} failed; logs={args.log_dir}", flush=True)
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
