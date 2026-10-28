"""One Orbit entry point: safe install, source update and selected-host uninstall.

Installation and update delegate to the existing preview-first installer.
Uninstall preserves shared runtime, project data, SQLite and owner guidance.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import installer
from orbit_cli import detect

HOSTS = installer.HOSTS
SERVER = installer.SERVER


@dataclass(frozen=True)
class Removal:
    path: Path
    original: bytes
    replacement: bytes | None
    description: str


def _owned_runtime(value, home):
    if not isinstance(value, str):
        return False
    try:
        p = Path(value)
        return (p.is_absolute() and p.name == "orbit_mcp.py"
                and re.fullmatch(r"\d+\.\d+\.\d+", p.parent.name) is not None
                and p.parent.parent.resolve() == (home / ".orbit-universal").resolve()
                and not p.is_symlink() and not p.parent.is_symlink())
    except (OSError, ValueError):
        return False


def _owned_entry(value, home, typed=None):
    if not isinstance(value, dict) or set(value) not in (
            {"command", "args"}, {"type", "command", "args"}):
        return False
    if typed is True and value.get("type") != "stdio":
        return False
    if typed is False and "type" in value:
        return False
    return (isinstance(value.get("command"), str)
            and isinstance(value.get("args"), list)
            and len(value["args"]) == 1
            and _owned_runtime(value["args"][0], home))


def _read_file(path):
    if not path.exists() and not path.is_symlink():
        return None
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents) or not path.is_file():
        raise installer.SetupError("Refusing symlink or non-file Orbit target: " + str(path))
    return path.read_bytes()


def plan_uninstall(project, hosts, scope="project"):
    """Read-only removal plan, based on bundled content or exact recognized stock hash."""
    if scope not in installer.SCOPES or not hosts or set(hosts) - set(HOSTS):
        raise installer.SetupError("Invalid scope or host selection")
    root = installer.check_project(project) if scope == "project" else None
    home = installer.user_home()
    source = installer.PACKAGE / "source"
    planned = {}
    warnings = []

    def managed(path, expected, desc):
        data = _read_file(path)
        if data is None:
            return
        known = (data == expected or
                 hashlib.sha256(data).hexdigest() in installer.OLD_STOCK_SHA256)
        if known:
            planned[path] = Removal(path, data, None, desc)
        else:
            warnings.append("PRESERVE customized/unrecognized file: " + str(path))

    def skill(folder):
        managed(folder / "SKILL.md", installer.ORBIT_SKILL.encode(), "Orbit skill")
        for ref in sorted((source / "skills/orbit/references").glob("*.md")):
            managed(folder / "references" / ref.name, ref.read_bytes(), "Orbit skill reference")

    def json_config(path, typed):
        raw = _read_file(path)
        if raw is None:
            return
        try:
            obj = json.loads(raw)
        except (ValueError, UnicodeError):
            warnings.append("PRESERVE invalid/custom JSON config: " + str(path))
            return
        section = "servers" if path.name == "mcp.json" and path.parent.name == ".vscode" else "mcpServers"
        entries = obj.get(section) if isinstance(obj, dict) else None
        if not isinstance(entries, dict) or SERVER not in entries:
            return
        if not _owned_entry(entries[SERVER], home, typed):
            warnings.append("PRESERVE customized Orbit entry: " + str(path))
            return
        updated = {**obj, section: {k: v for k, v in entries.items() if k != SERVER}}
        replacement = (json.dumps(updated, indent=2, ensure_ascii=False) + "\n").encode()
        planned[path] = Removal(path, raw, replacement, "Orbit MCP registration only")

    def codex_config(path):
        raw = _read_file(path)
        if raw is None:
            return
        try:
            body = raw.decode("utf-8")
        except UnicodeError:
            warnings.append("PRESERVE non-UTF-8 Codex config: " + str(path))
            return
        match = re.search(r'(?m)^\s*\[mcp_servers\.([\'"]?)orbit-core-native\1\]\s*\r?\n', body)
        if not match:
            return
        next_table = re.search(r"(?m)^\s*\[", body[match.end():])
        end = match.end() + next_table.start() if next_table else len(body)
        table = body[match.end():end].strip()
        fields = re.fullmatch(
            r'command\s*=\s*("(?:\\.|[^"\\])*")\s*\nargs\s*=\s*\[\s*("(?:\\.|[^"\\])*")\s*\]',
            table)
        if fields:
            try:
                command = json.loads(fields.group(1))
                runtime = json.loads(fields.group(2))
            except ValueError:
                command, runtime = None, None
        else:
            command, runtime = None, None
        if not isinstance(command, str) or not _owned_runtime(runtime, home):
            warnings.append("PRESERVE customized Codex Orbit section: " + str(path))
            return
        replacement = ((body[:match.start()] + body[end:]).strip() + "\n").encode()
        planned[path] = Removal(path, raw, replacement, "Stock Codex Orbit MCP section only")

    if "antigravity" in hosts:
        base = root / ".agents" if root else home / ".gemini/config"
        for file in sorted((source / "agents").glob("*.md")):
            managed(base / "agents" / file.name, file.read_bytes(), "Orbit Antigravity agent")
        if not root or "codex" in hosts:
            skill(base / "skills/orbit")
        else:
            warnings.append("PRESERVE shared .agents/skills/orbit (Codex may use it)")
        json_config(base / "mcp_config.json", typed=False)

    if "codex" in hosts:
        if not root or "antigravity" in hosts:
            skill((root / ".agents/skills/orbit") if root else (home / ".agents/skills/orbit"))
        else:
            warnings.append("PRESERVE shared .agents/skills/orbit (Antigravity may use it)")
        codex_config((root / ".codex/config.toml") if root else (home / ".codex/config.toml"))

    if "claude-code" in hosts:
        base = root / ".claude" if root else home / ".claude"
        skill(base / "skills/orbit")
        managed(base / "agents/orbit-lead.md", installer.ORBIT_LEAD_CLAUDE.encode(),
                "Orbit Claude lead agent")
        for file in sorted((source / "agents").glob("orbit-*.md")):
            managed(base / "agents" / file.name,
                    installer.agent_claude(file.read_text(encoding="utf-8")).encode(),
                    "Orbit Claude agent")
        json_config((root / ".mcp.json") if root else home / ".claude.json", typed=True)

    if "vscode" in hosts:
        if root:
            cfg = root / ".vscode/mcp.json"
        elif os.name == "nt":
            roaming = (home / "AppData/Roaming" if os.getenv("ORBIT_SETUP_HOME") else
                       Path(os.getenv("APPDATA", home / "AppData/Roaming")))
            cfg = roaming / "Code/User/mcp.json"
        elif sys.platform == "darwin":
            cfg = home / "Library/Application Support/Code/User/mcp.json"
        else:
            cfg = home / ".config/Code/User/mcp.json"
        json_config(cfg, typed=True)

    warnings.append("PRESERVE shared runtime/updater, SQLite, other project registrations and owner docs AGENTS.md/CLAUDE.md.")
    return sorted(planned.values(), key=lambda c: str(c.path)), warnings


def apply_uninstall(changes):
    """Backup all originals before mutation; reject changed/symlink targets."""
    if not changes:
        return None
    if len(set(c.path for c in changes)) != len(changes):
        raise installer.SetupError("Duplicate uninstall path")
    for c in changes:
        if _read_file(c.path) != c.original:
            raise installer.SetupError("Uninstall plan stale: " + str(c.path))
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    backup_root = installer.user_home() / ".orbit-uninstall-backups"
    if backup_root.is_symlink():
        raise installer.SetupError("Refusing symlink uninstall backup root")
    backup = backup_root / stamp
    backup.mkdir(parents=True, exist_ok=False, mode=0o700)
    if os.name != "nt":
        backup.chmod(0o700)
    manifest = []
    for i, c in enumerate(changes):
        dest = backup / f"{i:03d}.bak"
        with dest.open("xb") as file:
            file.write(c.original)
        if os.name != "nt":
            dest.chmod(0o600)
        manifest.append({"original_path": str(c.path), "backup_name": dest.name,
                         "action": "REMOVE" if c.replacement is None else "EDIT"})
    index = backup / "manifest.json"
    index.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if os.name != "nt":
        index.chmod(0o600)
    for c in changes:
        if _read_file(c.path) != c.original:
            raise installer.SetupError("Partial uninstall: file changed; see backup " + str(backup))
        if c.replacement is None:
            c.path.unlink()
        else:
            temp = c.path.with_name(c.path.name + ".orbit-uninstall-tmp")
            with temp.open("xb") as file:
                file.write(c.replacement)
            temp.replace(c.path)
    return backup


def selected_hosts(project, hosts):
    if hosts:
        return hosts
    found = [item["host"] for item in detect(project) if item["detected"]]
    if not found:
        raise installer.SetupError("No host detected; specify --hosts antigravity codex explicitly")
    return found


def run_action(action, scope, project, hosts, apply=False):
    if action == "uninstall":
        changes, notes = plan_uninstall(project, hosts, scope)
        for c in changes:
            print(("REMOVE" if c.replacement is None else "EDIT").ljust(7), c.path)
        for note in notes:
            print(note)
        if not apply:
            print(f"PREVIEW ONLY: {len(changes)} planned changes. Use --apply to authorize.")
        elif changes:
            backup = apply_uninstall(changes)
            print(f"Uninstalled {len(changes)} targets; backup at {backup}")
            print("Restart hosts. Shared runtime and project memories preserved.")
        else:
            print("No verified Orbit-managed host files to remove.")
        return 0
    if action == "update":
        print("UPDATE uses the local checked-out source; review/pull Git separately. Not a published release updater.")
    changes = installer.plan(project, hosts, scope)
    for change in changes:
        print(f"{change.action:8} {change.target}")
    if not apply:
        print("PREVIEW ONLY: use --apply to authorize installation/update.")
    else:
        paths = installer.install(changes)
        print(f"Applied {len(paths)} file changes/backups. Restart IDE and verify MCP.")
    return 0


def menu():
    print("\nORBIT SETUP — Install / Update / Uninstall")
    print("1) Install from checked-out source\n2) Update installed files from source")
    print("3) Uninstall Orbit from selected hosts (preserve memory)\n4) Exit")
    choice = input("Choose 1-4: ").strip()
    if choice == "4":
        return 0
    if choice not in {"1", "2", "3"}:
        print("Invalid choice")
        return 2
    action = {"1": "install", "2": "update", "3": "uninstall"}[choice]
    scope = "machine" if input("Scope [p]roject (default) / [m]achine: ").strip().lower() == "m" else "project"
    project = input("Absolute existing project folder: ").strip() if scope == "project" else None
    hosts = input("Hosts [antigravity codex claude-code vscode]: ").strip().split()
    hosts = selected_hosts(project, hosts or None)
    run_action(action, scope, project, hosts, False)
    if input("Type YES to apply those changes: ").strip() == "YES":
        return run_action(action, scope, project, hosts, True)
    print("Cancelled without changes.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Orbit unified installer / updater / safe uninstaller")
    parser.add_argument("action", nargs="?", choices=["install","update","uninstall","status"])
    parser.add_argument("--scope", choices=installer.SCOPES, default="project")
    parser.add_argument("--project", help="Existing absolute project directory")
    parser.add_argument("--hosts", nargs="+", choices=HOSTS)
    parser.add_argument("--apply", action="store_true", help="Explicitly confirm changes")
    parser.add_argument("--gui", action="store_true", help="Open native setup window (Tkinter)")
    args = parser.parse_args(argv)
    try:
        if args.gui:
            import runpy
            runpy.run_path(str(installer.PACKAGE / 'install_orbit_gui.pyw'), run_name='__main__')
            return 0
        if args.action == "status":
            from orbit_cli import doctor
            return doctor(args.project)
        if args.action is None:
            if not sys.stdin.isatty():
                parser.error("Choose an action in noninteractive mode")
            return menu()
        return run_action(args.action, args.scope, args.project,
                          selected_hosts(args.project, args.hosts), args.apply)
    except (installer.SetupError,OSError,ValueError,EOFError) as exc:
        print("ORBIT SETUP BLOCKED:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
