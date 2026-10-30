"""One Orbit entry point: safe install, source update and selected-host uninstall.

Installation and update delegate to the existing preview-first installer.
Uninstall preserves shared runtime, project data, SQLite and owner guidance.
Clean reset explicitly includes customized Orbit paths and shared runtime;
memory deletion is optional and requires a typed destructive confirmation.
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


def plan_uninstall(project, hosts, scope="project", *, clean=False):
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
        known = (clean or data == expected or
                 hashlib.sha256(data).hexdigest() in installer.OLD_STOCK_SHA256)
        if known:
            planned[path] = Removal(path, data, None, desc)
        else:
            warnings.append("PRESERVE customized/unrecognized file: " + str(path))

    def skill(folder):
        if clean:
            for target in _tree_files(folder):
                raw = _read_file(target)
                planned[target] = Removal(target, raw, None, "Orbit skill, including customized files")
            return
        managed(folder / "SKILL.md", installer.ORBIT_SKILL.encode(), "Orbit skill")
        for ref in sorted((source / "skills/orbit/references").glob("*.md")):
            managed(folder / "references" / ref.name, ref.read_bytes(), "Orbit skill reference")

    def json_config(path, typed, section="mcpServers"):
        raw = _read_file(path)
        if raw is None:
            return
        try:
            obj = json.loads(raw)
        except (ValueError, UnicodeError):
            if clean:
                raise installer.SetupError("Cannot safely edit invalid shared JSON config: " + str(path))
            warnings.append("PRESERVE invalid/custom JSON config: " + str(path))
            return
        if clean and (not isinstance(obj, dict) or (section in obj and not isinstance(obj[section], dict))):
            raise installer.SetupError("Invalid shared MCP configuration structure: " + str(path))
        entries = obj.get(section) if isinstance(obj, dict) else None
        if not isinstance(entries, dict) or SERVER not in entries:
            return
        if not clean and not _owned_entry(entries[SERVER], home, typed):
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
            if clean:
                raise installer.SetupError("Cannot safely edit non-UTF-8 shared Codex config: " + str(path))
            warnings.append("PRESERVE non-UTF-8 Codex config: " + str(path))
            return
        if clean:
            replacement = _remove_codex_orbit(body).encode("utf-8")
            if replacement != raw:
                planned[path] = Removal(path, raw, replacement, "Orbit Codex section, including custom settings")
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
        json_config(cfg, typed=True, section="servers")

    warnings.append("PRESERVE shared runtime/updater, SQLite, other project registrations and owner docs AGENTS.md/CLAUDE.md.")
    return sorted(planned.values(), key=lambda c: str(c.path)), warnings



def _tree_files(folder):
    """Enumerate exact regular files, refusing links at any depth before mutation."""
    if folder.is_symlink() or any(p.is_symlink() for p in folder.parents):
        raise installer.SetupError("Refusing linked Orbit directory: " + str(folder))
    if not folder.exists():
        return []
    if not folder.is_dir():
        raise installer.SetupError("Expected Orbit directory: " + str(folder))
    files = []
    for child in sorted(folder.iterdir()):
        if child.is_symlink():
            raise installer.SetupError("Refusing linked Orbit target: " + str(child))
        if child.is_dir():
            files.extend(_tree_files(child))
        elif child.is_file():
            files.append(child)
        else:
            raise installer.SetupError("Refusing non-file Orbit target: " + str(child))
    return files


def _remove_codex_orbit(body):
    # Preserve all unrelated text and remove only this exact server namespace.
    # Refuse malformed TOML rather than wiping a shared host configuration.
    try:
        import tomllib
    except ImportError:  # Python 3.10: refuse advanced/ambiguous headers below.
        tomllib = None
    if tomllib:
        try:
            original = tomllib.loads(body)
        except ValueError as exc:
            raise installer.SetupError("Invalid shared Codex TOML; repair it before clean reset") from exc
    if not tomllib and ('\"\"\"' in body or "'" * 3 in body):
        raise installer.SetupError("Multiline TOML requires Python 3.11+ for safe clean reset")
    owned = re.compile(r"^\s*\[mcp_servers\.(?:orbit-core-native|[\"']orbit-core-native[\"'])(?:\.[^\]]+)?\]\s*(?:#.*)?$")
    remaining = []
    dropping = False
    for line in body.splitlines(keepends=True):
        if line.lstrip().startswith('['):
            if not re.fullmatch(r"\s*\[.+\]\s*(?:#.*)?", line.strip()):
                raise installer.SetupError("Unsupported Codex TOML header; manual review required")
            dropping = bool(owned.fullmatch(line.strip()))
        if not dropping:
            remaining.append(line)
    result = ''.join(remaining)
    if tomllib:
        parsed = tomllib.loads(result)
        expected = dict(original)
        if isinstance(original.get('mcp_servers'), dict) and SERVER in original['mcp_servers']:
            expected['mcp_servers'] = {k: v for k, v in original['mcp_servers'].items() if k != SERVER}
            # Implicit parent table disappears if its only child is removed.
            if not expected['mcp_servers'] and 'mcp_servers' not in parsed:
                expected.pop('mcp_servers')
        if parsed != expected or SERVER in parsed.get('mcp_servers', {}):
            raise installer.SetupError("Unsupported Orbit TOML syntax; manual review required")
    elif SERVER in result:
        raise installer.SetupError('Unsupported Orbit TOML syntax; use Python 3.11+ or review manually')
    return result


def plan_clean_reset(project=None, *, erase_memory=False):
    """Explicit destructive reset: all global hosts plus one optional project.

    Never searches arbitrary project directories or deletes shared host configs.
    Unknown/custom Orbit files at named Orbit paths are included with backups.
    """
    root = installer.check_project(project) if project else None
    home = installer.user_home()
    planned = {}
    custom_db = os.getenv('ORBIT_LOCAL_DB')
    protected_db = set()
    if custom_db:
        db = Path(custom_db).expanduser().resolve()
        protected_db = {Path(str(db) + suffix) for suffix in ('', '-wal', '-shm', '-journal')}
    notes = [
        "Close ALL coding hosts and Orbit MCP processes before applying.",
        "Removes Orbit from ALL global hosts, including customized Orbit files.",
        "Removes the shared runtime/updater for ALL projects; reinstall afterward.",
        "Other project-local registrations are not searched. Select each project to clear them.",
        "Unrelated MCPs, project source, AGENTS.md and CLAUDE.md are preserved.",
        "Recovery backups remain in .orbit-uninstall-backups outside the active installation.",
    ]
    for location, scope in [(None, 'machine')] + ([(root, 'project')] if root else []):
        changes, _ = plan_uninstall(location, HOSTS, scope, clean=True)
        planned.update((c.path, c) for c in changes)
    def remove_file(path, desc):
        if path.resolve() in protected_db:
            notes.append('PRESERVE custom database (not automatically erased): ' + str(path))
            return
        raw = _read_file(path)
        if raw is not None:
            planned[path] = Removal(path, raw, None, desc)
    def tree(folder, desc):
        pkg = installer.PACKAGE.resolve()
        f_res = folder.resolve()
        if f_res == pkg or f_res in pkg.parents:
            raise installer.SetupError("Run Setup from a separate checkout, outside the installation being cleared")
        for path in _tree_files(folder):
            remove_file(path, desc)
    # Dedicated installer-owned folder only; never recursively remove host folders.
    tree(home / '.orbit-universal', 'Shared Orbit runtime/updater and caches')
    custom_runtime = installer.runtime_folder()
    if custom_runtime.parent != home / '.orbit-universal':
        # Only the configured version folder, never its possibly shared parent.
        tree(custom_runtime, 'Configured Orbit runtime version')
        notes.append('Other versions in custom runtime locations are not searched.')
    # Remove leftover backups of known Orbit agent/skill files, never shared config backups.
    for location in [None] + ([root] if root else []):
        bases = ([location / '.agents', location / '.claude'] if location else
                 [home / '.gemini/config', home / '.claude'])
        for base in bases:
            agents = base / 'agents'
            if agents.is_symlink():
                raise installer.SetupError('Refusing linked agent directory: ' + str(agents))
            for path in sorted(agents.glob('orbit-*.md*')):
                if re.fullmatch(r'orbit-[a-z0-9-]+\.md(?:\.orbit-(?:backup.*|new))?', path.name):
                    remove_file(path, 'Orbit agent or its installer backup, including customizations')
    if erase_memory:
        # Standard platform locations, isolated under the test home when supplied.
        win = home / 'AppData/Local' if os.getenv('ORBIT_SETUP_HOME') else Path(os.getenv('LOCALAPPDATA') or home / 'AppData/Local')
        unix = home / '.local/share' if os.getenv('ORBIT_SETUP_HOME') else Path(os.getenv('XDG_DATA_HOME') or home / '.local/share')
        for db in [win / 'OrbitCore/memory.sqlite3', unix / 'orbit-core/memory.sqlite3']:
            for suffix in ('', '-wal', '-shm', '-journal'):
                remove_file(Path(str(db) + suffix), 'Saved Orbit memory/tasks/research for ALL projects')
        if root:
            tree(root / '.orbit', 'Selected project Orbit checkpoints and notes')
        notes.append('DELETES saved memory/tasks/research for ALL projects and selected project .orbit notes (backed up).')
        if os.getenv('ORBIT_LOCAL_DB'):
            notes.append('Custom ORBIT_LOCAL_DB is not deleted automatically: ' + os.environ['ORBIT_LOCAL_DB'])
    else:
        notes.append('Saved memory/research/tasks and project .orbit notes are retained (memory deletion is unchecked).')
    if custom_db:
        notes.append('PRESERVE configured custom database and sidecars: ' + str(custom_db))
    return sorted((c for c in planned.values() if c.path.resolve() not in protected_db),
                  key=lambda c: str(c.path)), notes

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
    try:
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
    except (OSError, installer.SetupError) as exc:
        raise installer.SetupError('Removal incomplete; recovery backup: ' + str(backup) + '\n' + str(exc)) from exc
    return backup



def apply_clean_reset(changes, project=None, *, erase_memory=False, confirmation=''):
    if confirmation != 'REMOVE ORBIT':
        raise installer.SetupError('Clean reset requires typing REMOVE ORBIT')
    fresh, _ = plan_clean_reset(project, erase_memory=erase_memory)
    if fresh != changes:
        raise installer.SetupError('Clean reset preview changed; review again')
    backup = apply_uninstall(changes)
    home = installer.user_home()
    folders = [home / '.orbit-universal', home / '.gemini/config/skills/orbit',
               home / '.agents/skills/orbit', home / '.claude/skills/orbit', installer.runtime_folder()]
    if project:
        root = installer.check_project(project)
        folders += [root / '.agents/skills/orbit', root / '.claude/skills/orbit']
        if erase_memory:
            folders.append(root / '.orbit')
    # Only remove empty directories inside dedicated Orbit paths. Never rmtree.
    for folder in folders:
        if folder.is_symlink() or not folder.is_dir():
            continue
        for child in sorted(folder.rglob('*'), key=lambda p: len(p.parts), reverse=True):
            if child.is_dir() and not child.is_symlink():
                try:
                    child.rmdir()
                except OSError:
                    pass
        try:
            folder.rmdir()
        except OSError:
            pass
    return backup

def selected_hosts(project, hosts):
    if hosts:
        return hosts
    found = [item["host"] for item in detect(project) if item["detected"]]
    if not found:
        raise installer.SetupError("No host detected; specify --hosts antigravity codex explicitly")
    return found


def run_action(action, scope, project, hosts, apply=False, *, erase_memory=False, confirmation=''):
    if action == 'clean':
        target = project if scope == 'project' else None
        changes, notes = plan_clean_reset(target, erase_memory=erase_memory)
        for change in changes:
            print(('DELETE' if change.replacement is None else 'EDIT').ljust(7), change.path)
        for note in notes:
            print(note)
        if not apply:
            print('PREVIEW ONLY. Apply requires --apply --confirm-clean "REMOVE ORBIT".')
        else:
            backup = apply_clean_reset(changes, target, erase_memory=erase_memory, confirmation=confirmation)
            print('Orbit cleared. Recovery backup:', backup or 'No files required removal')
            print('Reopen Setup to install fresh; other project folders were not scanned.')
        return 0
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
    print("3) Uninstall Orbit from selected hosts (preserve memory)\n4) Clear Orbit for fresh install\n5) Exit")
    choice = input("Choose 1-5: ").strip()
    if choice == "5":
        return 0
    if choice not in {"1", "2", "3", "4"}:
        print("Invalid choice")
        return 2
    action = {"1": "install", "2": "update", "3": "uninstall", "4": "clean"}[choice]
    scope = "machine" if input("Scope [p]roject (default) / [m]achine: ").strip().lower() == "m" else "project"
    project = input("Absolute existing project folder: ").strip() if scope == "project" else None
    if action == 'clean':
        erase = input('Also delete ALL saved project memory and selected .orbit notes? Type DELETE MEMORY: ').strip() == 'DELETE MEMORY'
        run_action(action, scope, project, HOSTS, False, erase_memory=erase)
        confirmation = input('Type REMOVE ORBIT to delete the previewed files (anything else cancels): ').strip()
        if confirmation != 'REMOVE ORBIT':
            print('Cancelled without changes.')
            return 0
        return run_action(action, scope, project, HOSTS, True, erase_memory=erase, confirmation=confirmation)
    hosts = input("Hosts [antigravity codex claude-code vscode]: ").strip().split()
    hosts = selected_hosts(project, hosts or None)
    run_action(action, scope, project, hosts, False)
    if input("Type YES to apply those changes: ").strip() == "YES":
        return run_action(action, scope, project, hosts, True)
    print("Cancelled without changes.")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Orbit unified installer / updater / safe uninstaller")
    parser.add_argument("action", nargs="?", choices=["install","update","uninstall","clean","status"])
    parser.add_argument("--scope", choices=installer.SCOPES, default="project")
    parser.add_argument("--project", help="Existing absolute project directory")
    parser.add_argument("--hosts", nargs="+", choices=HOSTS)
    parser.add_argument("--apply", action="store_true", help="Explicitly confirm changes")
    parser.add_argument('--erase-memory', action='store_true', help='Clean only: also delete saved memory for ALL projects and selected .orbit notes (backed up)')
    parser.add_argument('--confirm-clean', default='', help='Clean apply requires the exact text REMOVE ORBIT')
    parser.add_argument("--gui", action="store_true", help="Open native setup window (Tkinter)")
    args = parser.parse_args(argv)
    try:
        if args.gui:
            from orbit_compact_gui import launch
            launch()
            return 0
        if args.action == "status":
            from orbit_cli import doctor
            return doctor(args.project)
        if args.action is None:
            if not sys.stdin.isatty():
                parser.error("Choose an action in noninteractive mode")
            return menu()
        if args.action != 'clean' and (args.erase_memory or args.confirm_clean):
            raise installer.SetupError('Memory deletion and clean confirmation apply only to clean')
        return run_action(args.action, args.scope, args.project,
                          HOSTS if args.action == 'clean' else selected_hosts(args.project, args.hosts), args.apply,
                          erase_memory=args.erase_memory, confirmation=args.confirm_clean)
    except (installer.SetupError,OSError,ValueError,EOFError) as exc:
        print("ORBIT SETUP BLOCKED:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
