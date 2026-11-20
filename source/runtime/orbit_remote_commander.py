#!/usr/bin/env python3
"""Orbit Remote Commander: opt-in project-scoped *local stdio* MCP prototype.

No inbound network listener, remote relay, service install, or implicit permissions.
Works only when an MCP-capable desktop host explicitly launches this program.
This does NOT make a browser-based ChatGPT conversation reach a user's computer.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from typing import Any

MAX_READ_BYTES = 96_000
MAX_WRITE_BYTES = 96_000
MAX_ENTRIES = 120
MAX_JSON_BYTES = 128_000
PROTOCOL = "2025-11-25"

# Refuse sensitive files even inside an approved project root. This is a guardrail;
# use OS identity separation / VM and read-only mounts for actual isolation.
SECRET_NAMES = {".env", ".env.local", ".env.production", "id_rsa", "id_ed25519", ".npmrc", ".pypirc", "credentials", "credentials.json", "secrets.json", "token.json"}
SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".kdbx")
DENIED_COMPONENTS = {".ssh", ".aws", ".gnupg", ".azure", ".kube"}


class Rejected(ValueError):
    pass


class Commander:
    def __init__(self, root: str | Path | None, allow_write: bool = False, allow_checks: bool = False):
        if not root:
            raise Rejected("ORBIT_RC_ROOT must be explicitly configured")
        path = Path(root).expanduser().resolve(strict=True)
        if not path.is_dir() or path == Path(path.anchor) or path == Path.home().resolve():
            raise Rejected("Choose a specific project folder, not a filesystem or home root")
        self.root = path
        self.allow_write = allow_write
        self.allow_checks = allow_checks

    def _path(self, rel: str, require_exists: bool = True) -> Path:
        if not isinstance(rel, str) or not rel or "\x00" in rel or len(rel) > 2048:
            raise Rejected("Path must be a non-empty relative string")
        supplied = Path(rel)
        if supplied.is_absolute() or any(p == ".." for p in supplied.parts):
            raise Rejected("Absolute paths and traversal are not permitted")
        parts = [p.lower() for p in supplied.parts]
        if any(p in DENIED_COMPONENTS for p in parts) or any(p in SECRET_NAMES or p.startswith(".env.") or p.endswith(SECRET_SUFFIXES) for p in parts):
            raise Rejected("Sensitive files are not exposed")
        candidate = (self.root / supplied).resolve(strict=require_exists)
        if not candidate.is_relative_to(self.root):
            raise Rejected("Path escapes the approved root")
        return candidate

    def status(self) -> dict[str, Any]:
        # Avoid returning the absolute path to unrelated clients unnecessarily.
        return {"status": "READY_LOCAL_STDIO", "root_name": self.root.name, "read_only": not self.allow_write, "checks_enabled": self.allow_checks, "remote_relay": "NOT_CONFIGURED", "transport": "stdio"}

    def list_dir(self, path: str = ".") -> dict[str, Any]:
        directory = self._path(path)
        if not directory.is_dir():
            raise Rejected("Not a directory")
        items = []
        for child in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
            try:
                rel = child.relative_to(self.root).as_posix()
                self._path(rel)
                items.append({"name": child.name, "kind": "directory" if child.is_dir() else "file" if child.is_file() else "other"})
            except (Rejected, OSError, ValueError):
                continue
            if len(items) >= MAX_ENTRIES:
                break
        return {"path": path, "entries": items, "limit": MAX_ENTRIES, "possibly_truncated": len(items) == MAX_ENTRIES}

    def read_text(self, path: str) -> dict[str, Any]:
        file = self._path(path)
        if not file.is_file() or file.stat().st_size > MAX_READ_BYTES:
            raise Rejected("File missing, not regular, or exceeds read limit")
        data = file.read_bytes()
        if len(data) > MAX_READ_BYTES:
            raise Rejected("File exceeds read limit")
        try:
            content = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise Rejected("Only UTF-8 text files are supported") from exc
        return {"path": path, "text": content, "sha256": hashlib.sha256(data).hexdigest()}

    def write_text(self, path: str, text: str, expected_sha256: str, confirm_write: bool) -> dict[str, Any]:
        if not self.allow_write:
            raise Rejected("Write mode disabled on this device")
        if confirm_write is not True:
            raise Rejected("Explicit write confirmation required in addition to device write mode")
        if not isinstance(text, str) or len(text.encode("utf-8")) > MAX_WRITE_BYTES:
            raise Rejected("Text must be UTF-8 and within write limit")
        if not isinstance(expected_sha256, str) or len(expected_sha256) != 64 or any(c not in "0123456789abcdef" for c in expected_sha256):
            raise Rejected("Expected SHA-256 from a prior read is required; creation is not supported")
        target = self._path(path)
        if not target.is_file():
            raise Rejected("Only existing regular text files may be modified")
        old = target.read_bytes()
        if hashlib.sha256(old).hexdigest() != expected_sha256:
            raise Rejected("File changed since read; refusing stale overwrite")
        try:
            old.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise Rejected("Only UTF-8 text files may be modified") from exc
        # Atomic replacement in the same directory. Permissions preserved. Does not
        # defeat concurrent malicious symlink mutation; OS-level isolation is required.
        fd, tempname = tempfile.mkstemp(prefix=".orbit-rc-", dir=str(target.parent))
        try:
            with os.fdopen(fd, "wb") as out:
                out.write(text.encode("utf-8"))
                out.flush()
                os.fsync(out.fileno())
            os.chmod(tempname, stat.S_IMODE(target.stat().st_mode))
            if self._path(path) != target or hashlib.sha256(target.read_bytes()).hexdigest() != expected_sha256:
                raise Rejected("File changed during update")
            os.replace(tempname, target)
        finally:
            if os.path.exists(tempname):
                os.unlink(tempname)
        return {"path": path, "written": True, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}

    def run_check(self, check: str) -> dict[str, Any]:
        if not self.allow_checks:
            raise Rejected("Diagnostic subprocesses disabled on this device")
        # Fixed argv, no arbitrary shell, no arbitrary executable arguments.
        checks = {
            "git-status": ["git", "--no-pager", "status", "--short"],
            "git-diff-stat": ["git", "--no-pager", "diff", "--stat"],
            "git-branch": ["git", "branch", "--show-current"],
        }
        if check not in checks:
            raise Rejected("Unsupported diagnostic ID")
        # Minimal environment. Git's external helpers/config are not a security sandbox.
        env = {"PATH": os.environ.get("PATH", ""), "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0", "GIT_PAGER": "cat", "GIT_CONFIG_NOSYSTEM": "1"}
        if os.name == "nt":
            env["SYSTEMROOT"] = os.environ.get("SYSTEMROOT", "C:\\Windows")
        try:
            completed = subprocess.run(checks[check], cwd=self.root, env=env, shell=False,
                                       capture_output=True, text=True, timeout=15, errors="replace")
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            raise Rejected("Diagnostic unavailable or timed out") from exc
        return {"check": check, "exit_code": completed.returncode,
                "stdout": completed.stdout[:16_000], "stderr": completed.stderr[:4_000]}


TOOLS = [
    {"name": "orbit_rc_status", "description": "Show this explicitly connected Orbit local commander's status and scoped capability; no remote connection implied.", "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "orbit_rc_list", "description": "List bounded entries inside the configured project root only.", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "additionalProperties": False}},
    {"name": "orbit_rc_read", "description": "Read one non-sensitive UTF-8 file inside the configured project root; returns a hash for stale-write protection.", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"], "additionalProperties": False}},
    {"name": "orbit_rc_write", "description": "Modify one existing text file only if device write mode is on, user separately approves and the previously-read SHA-256 matches. Not a general authorization mechanism.", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}, "text": {"type": "string"}, "expected_sha256": {"type": "string"}, "confirm_write": {"type": "boolean"}}, "required": ["path", "text", "expected_sha256", "confirm_write"], "additionalProperties": False}},
    {"name": "orbit_rc_check", "description": "Run one fixed git diagnostic on the approved project; disabled by default. This is NOT arbitrary terminal access.", "inputSchema": {"type": "object", "properties": {"check": {"type": "string", "enum": ["git-status", "git-diff-stat", "git-branch"]}}, "required": ["check"], "additionalProperties": False}},
]


def serve(commander: Commander) -> None:
    # MCP stdio uses one JSON-RPC message per line. stdout must contain JSON only.
    for raw in sys.stdin.buffer:
        if len(raw) > MAX_JSON_BYTES:
            continue
        try:
            message = json.loads(raw)
            method = message.get("method")
            msg_id = message.get("id")
            if msg_id is None:
                continue
            params = message.get("params") or {}
            if method == "initialize":
                result = {"protocolVersion": PROTOCOL, "capabilities": {"tools": {}}, "serverInfo": {"name": "orbit-remote-commander-local", "version": "0.1.0"}}
            elif method == "ping":
                result = {}
            elif method == "tools/list":
                result = {"tools": TOOLS}
            elif method == "tools/call":
                name = params.get("name")
                args = params.get("arguments") or {}
                handlers = {"orbit_rc_status": lambda: commander.status(),
                            "orbit_rc_list": lambda: commander.list_dir(args.get("path", ".")),
                            "orbit_rc_read": lambda: commander.read_text(args["path"]),
                            "orbit_rc_write": lambda: commander.write_text(args["path"], args["text"], args["expected_sha256"], args["confirm_write"]),
                            "orbit_rc_check": lambda: commander.run_check(args["check"])}
                if name not in handlers:
                    raise Rejected("Unknown tool")
                try:
                    value = handlers[name]()
                    result = {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}]}
                except (Rejected, KeyError, TypeError, OSError) as exc:
                    result = {"isError": True, "content": [{"type": "text", "text": f"DENIED: {type(exc).__name__}: {str(exc)}"}]}
            else:
                reply = {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": "Method not found"}}
                sys.stdout.write(json.dumps(reply) + "\n"); sys.stdout.flush()
                continue
            reply = {"jsonrpc": "2.0", "id": msg_id, "result": result}
        except (ValueError, TypeError, AttributeError):
            # Ignore unparseable requests. Do not leak device environment in errors.
            continue
        sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def main() -> int:
    try:
        commander = Commander(os.environ.get("ORBIT_RC_ROOT"),
                              allow_write=os.environ.get("ORBIT_RC_ALLOW_WRITE") == "1",
                              allow_checks=os.environ.get("ORBIT_RC_ALLOW_CHECKS") == "1")
    except (OSError, Rejected) as exc:
        print(f"Orbit local commander refused to start: {exc}", file=sys.stderr)
        return 2
    serve(commander)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
