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
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise installer.SetupError("Refusing symlink Orbit target: " + str(path))
    if not path.exists():
        return None
    if not path.is_file():
        raise installer.SetupError("Refusing non-file Orbit target: " + str(path))
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

_UNINSTALL_MANIFEST = "orbit-uninstall-v2"


def _write_uninstall_manifest(backup, record):
    """Atomically checkpoint a backup's state before/after each mutation."""
    path = backup / "manifest.json"
    import uuid
    temp = backup / ("manifest.json.tmp-" + uuid.uuid4().hex)
    with temp.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    try:
        temp.replace(path)
    finally:
        if temp.exists():
            temp.unlink()


def _preflight_sqlite_removal(changes):
    """Reject a busy SQLite database before touching any host registration.

    This is a best-effort liveness check, not a substitute for rollback: a host
    can reopen the database after preflight.
    """
    import sqlite3
    for change in changes:
        if change.replacement is not None or not change.path.name.endswith(".sqlite3"):
            continue
        if not change.original.startswith(b"SQLite format 3\x00"):
            continue
        connection = None
        try:
            connection = sqlite3.connect(change.path.as_uri() + "?mode=rw", uri=True, timeout=0)
            connection.execute("BEGIN EXCLUSIVE")
            connection.rollback()
        except sqlite3.Error as exc:
            raise installer.SetupError("Close Orbit/SQLite processes before clean reset: " + str(change.path)) from exc
        finally:
            if connection is not None:
                connection.close()


def _restore_uninstall_targets(changes):
    """Restore only unmodified post-uninstall state; never overwrite owner drift.

    Preflight every target before the first restoration. This also makes an
    explicit recovery attempt safe to repeat.
    """
    pending = []
    staged_temps = []
    for change in changes:
        if change.replacement is not None:
            temp = change.path.with_name(change.path.name + ".orbit-uninstall-tmp")
            data = _read_file(temp)
            if data is not None:
                if data != change.replacement:
                    raise installer.SetupError("Recovery conflict (temporary config): " + str(temp))
                staged_temps.append(temp)
        current = _read_file(change.path)
        if current == change.original:
            continue
        if change.replacement is None:
            if current is not None:
                raise installer.SetupError("Recovery conflict (modified target): " + str(change.path))
        elif current != change.replacement:
            raise installer.SetupError("Recovery conflict (modified config): " + str(change.path))
        pending.append(change)
    for change in reversed(pending):
        current = _read_file(change.path)
        if change.replacement is None:
            if current is not None:
                raise installer.SetupError("Recovery target changed during restore: " + str(change.path))
            change.path.parent.mkdir(parents=True, exist_ok=True)
            if any(parent.is_symlink() for parent in change.path.parents):
                raise installer.SetupError("Recovery parent became a link: " + str(change.path))
            with change.path.open("xb") as handle:
                handle.write(change.original)
                handle.flush()
                os.fsync(handle.fileno())
        else:
            if current != change.replacement:
                raise installer.SetupError("Recovery config changed during restore: " + str(change.path))
            temp = change.path.with_name(change.path.name + ".orbit-restore-tmp")
            with temp.open("xb") as handle:
                handle.write(change.original)
                handle.flush()
                os.fsync(handle.fileno())
            temp.replace(change.path)
    for temp in staged_temps:
        if _read_file(temp) is not None:
            temp.unlink()
    return len(pending)


def inspect_uninstall_backup(backup):
    """Read-only verification. Historical v1 list manifests are not rewritten."""
    backup = Path(backup)
    home = installer.user_home().resolve()
    store = home / ".orbit-uninstall-backups"
    if backup.is_symlink() or store.is_symlink() or backup.resolve().parent != store.resolve():
        raise installer.SetupError("Recovery must select a direct, nonlinked Orbit backup")
    raw = (backup / "manifest.json")
    if raw.is_symlink() or not raw.is_file():
        raise installer.SetupError("Missing or linked recovery manifest")
    record = json.loads(raw.read_text(encoding="utf-8"))
    if isinstance(record, list):
        raise installer.SetupError("Legacy v1 backup: manual review required; no automatic restore")
    if not isinstance(record, dict) or record.get("schema") != _UNINSTALL_MANIFEST:
        raise installer.SetupError("Unknown recovery manifest format")
    if record.get("status") not in {"APPLYING", "ROLLBACK_REQUIRED", "ROLLED_BACK", "COMPLETE"}:
        raise installer.SetupError("Backup is not in a recoverable state")
    roots = [home]
    if record.get("project_root"):
        root = Path(record["project_root"])
        if not root.is_absolute() or root.is_symlink():
            raise installer.SetupError("Invalid recorded project root")
        roots.append(root.resolve())
    entries = record.get("entries")
    if not isinstance(entries, list) or not entries:
        raise installer.SetupError("Recovery manifest has no targets")
    changes = []
    seen = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict) or entry.get("backup_name") != f"{index:03d}.bak":
            raise installer.SetupError("Invalid recovery entry or backup name")
        raw_path = entry.get("original_path")
        if not isinstance(raw_path, str) or not raw_path:
            raise installer.SetupError("Invalid recovery target path")
        path = Path(raw_path)
        canonical = path.resolve()
        if not path.is_absolute() or not any(canonical == root or root in canonical.parents for root in roots):
            raise installer.SetupError("Recovery target outside recorded scope")
        if path in seen or path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
            raise installer.SetupError("Duplicate or linked recovery target")
        seen.add(path)
        source = backup / entry["backup_name"]
        if source.is_symlink() or not source.is_file():
            raise installer.SetupError("Missing recovery backup bytes")
        original = source.read_bytes()
        if hashlib.sha256(original).hexdigest() != entry.get("original_sha256"):
            raise installer.SetupError("Corrupt recovery backup bytes")
        action = entry.get("action")
        if action not in {"REMOVE", "EDIT"}:
            raise installer.SetupError("Invalid recovery action")
        replacement = None
        if action == "EDIT":
            proposed = backup / f"{index:03d}.proposed"
            if proposed.is_symlink() or not proposed.is_file():
                raise installer.SetupError("Missing recovery proposed-config bytes")
            replacement = proposed.read_bytes()
            if hashlib.sha256(replacement).hexdigest() != entry.get("replacement_sha256"):
                raise installer.SetupError("Corrupt recovery proposed-config bytes")
        changes.append(Removal(path, original, replacement, "Verified recovery"))
    return record, changes


def recover_uninstall(backup, *, confirmation=""):
    """Explicit, idempotent recovery after a crash. Never silently restore."""
    if confirmation != "RESTORE ORBIT":
        raise installer.SetupError('Recovery requires typing RESTORE ORBIT')
    backup = Path(backup)
    record, changes = inspect_uninstall_backup(backup)
    count = _restore_uninstall_targets(changes)
    record["status"] = "ROLLED_BACK"
    record["restored_count"] = count
    _write_uninstall_manifest(backup, record)
    return count


def apply_uninstall(changes, *, operation="uninstall", project=None, erase_memory=False):
    """Fail-closed uninstall with progress journal, rollback and explicit recovery."""
    if not changes:
        return None
    if operation not in {"uninstall", "clean"}:
        raise installer.SetupError("Unknown uninstall operation")
    if len({c.path for c in changes}) != len(changes):
        raise installer.SetupError("Duplicate uninstall path")
    for c in changes:
        if _read_file(c.path) != c.original:
            raise installer.SetupError("Uninstall plan stale: " + str(c.path))
        if c.replacement is not None and c.path.with_name(c.path.name + ".orbit-uninstall-tmp").exists():
            raise installer.SetupError("Existing uninstall temporary file: " + str(c.path))
    if operation == "clean" and erase_memory:
        _preflight_sqlite_removal(changes)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
    backup_root = installer.user_home() / ".orbit-uninstall-backups"
    if backup_root.is_symlink() or any(p.is_symlink() for p in backup_root.parents):
        raise installer.SetupError("Refusing linked uninstall backup root")
    backup = backup_root / stamp
    backup.mkdir(parents=True, exist_ok=False, mode=0o700)
    if os.name != "nt":
        backup.chmod(0o700)
    entries = []
    for i, c in enumerate(changes):
        dest = backup / f"{i:03d}.bak"
        with dest.open("xb") as file:
            file.write(c.original)
            file.flush()
            os.fsync(file.fileno())
        if os.name != "nt":
            dest.chmod(0o600)
        if c.replacement is not None:
            proposed = backup / f"{i:03d}.proposed"
            with proposed.open("xb") as file:
                file.write(c.replacement)
                file.flush()
                os.fsync(file.fileno())
            if os.name != "nt":
                proposed.chmod(0o600)
        entries.append({"original_path": str(c.path), "backup_name": dest.name,
                        "original_sha256": hashlib.sha256(c.original).hexdigest(),
                        "replacement_sha256": (hashlib.sha256(c.replacement).hexdigest()
                                               if c.replacement is not None else None),
                        "action": "REMOVE" if c.replacement is None else "EDIT",
                        "state": "PENDING"})
    record = {"schema": _UNINSTALL_MANIFEST, "status": "APPLYING",
              "operation": operation, "scope": "machine+project" if operation == "clean" and project else ("project" if project else "machine"),
              "erase_memory": bool(erase_memory),
              "project_root": str(Path(project).resolve()) if project else None,
              "started_at": datetime.now(timezone.utc).isoformat(),
              "entries": entries}
    _write_uninstall_manifest(backup, record)
    try:
        for i, c in enumerate(changes):
            if _read_file(c.path) != c.original:
                raise installer.SetupError("Uninstall plan became stale: " + str(c.path))
            record["entries"][i]["state"] = "STARTED"
            _write_uninstall_manifest(backup, record)
            if c.replacement is None:
                c.path.unlink()
            else:
                temp = c.path.with_name(c.path.name + ".orbit-uninstall-tmp")
                with temp.open("xb") as file:
                    file.write(c.replacement)
                    file.flush()
                    os.fsync(file.fileno())
                temp.replace(c.path)
            record["entries"][i]["state"] = "APPLIED"
            _write_uninstall_manifest(backup, record)
        record["status"] = "COMPLETE"
        _write_uninstall_manifest(backup, record)
    except (OSError, installer.SetupError) as exc:
        # Only restore if the observed state is still exactly our own output.
        # Preserve all recovery files when another process edits a target.
        try:
            restored = _restore_uninstall_targets(changes)
            record["status"] = "ROLLED_BACK"
            record["restored_count"] = restored
            record["failure"] = str(exc)
            _write_uninstall_manifest(backup, record)
            detail = "All original targets restored."
        except (OSError, installer.SetupError) as restore_exc:
            record["status"] = "ROLLBACK_REQUIRED"
            record["failure"] = str(exc)
            record["recovery_error"] = str(restore_exc)
            try:
                _write_uninstall_manifest(backup, record)
            except OSError:
                pass
            detail = "Automatic restoration incomplete: " + str(restore_exc)
        raise installer.SetupError("Removal incomplete; recovery backup: " + str(backup)
                                   + "\n" + str(exc) + "\n" + detail) from exc
    return backup



def apply_clean_reset(changes, project=None, *, erase_memory=False, confirmation=''):
    if confirmation != 'REMOVE ORBIT':
        raise installer.SetupError('Clean reset requires typing REMOVE ORBIT')
    fresh, _ = plan_clean_reset(project, erase_memory=erase_memory)
    if fresh != changes:
        raise installer.SetupError('Clean reset preview changed; review again')
    backup = apply_uninstall(changes, operation='clean', project=project, erase_memory=erase_memory)
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
            backup = apply_uninstall(changes, project=project if scope == "project" else None)
            print(f"Uninstalled {len(changes)} targets; backup at {backup}")
            print("Restart hosts. Shared runtime and project memories preserved.")
        else:
            print("No verified Orbit-managed host files to remove.")
        return 0
    if action == "update":
        print("UPDATE uses the local checked-out source; review/pull Git separately. Not a published release updater.")
    changes = installer.plan(project, hosts, scope)
    if action == "install":
        from orbit_priority import audit
        report = audit(home=installer.user_home(), project=project if scope == "project" else None,
                       hosts=hosts)
        if report["conflicts"]:
            print("ORBIT PRIORITY REVIEW: Possible existing overlapping plugin/skill names:")
            for entry in report["conflicts"][:10]:
                print("REVIEW", entry["host"], entry["kind"], entry["name"])
            print("Other plugins remain enabled. Host/tool precedence cannot be forced.")
    for change in changes:
        print(f"{change.action:8} {change.target}")
    if not apply:
        print("PREVIEW ONLY: use --apply to authorize installation/update.")
    else:
        paths = installer.install(changes)
        print(f"Applied {len(paths)} file changes/backups. Restart IDE and verify MCP.")
    return 0


def menu():
    print("\nORBIT SETUP â€” Install / Update / Uninstall")
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
    parser.add_argument("action", nargs="?", choices=["install","update","uninstall","clean","recover","status"])
    parser.add_argument("--scope", choices=installer.SCOPES, default="project")
    parser.add_argument("--project", help="Existing absolute project directory")
    parser.add_argument("--hosts", nargs="+", choices=HOSTS)
    parser.add_argument("--apply", action="store_true", help="Explicitly confirm changes")
    parser.add_argument('--erase-memory', action='store_true', help='Clean only: also delete saved memory for ALL projects and selected .orbit notes (backed up)')
    parser.add_argument('--confirm-clean', default='', help='Clean apply requires the exact text REMOVE ORBIT')
    parser.add_argument("--backup", help="Recover only: exact backup directory under .orbit-uninstall-backups")
    parser.add_argument("--confirm-recover", default="", help="Recover apply requires RESTORE ORBIT")
    parser.add_argument("--gui", action="store_true", help="Open native setup window (Tkinter)")
    args = parser.parse_args(argv)
    try:
        if args.gui:
            from orbit_compact_gui import launch
            launch()
            return 0
        if args.action == "status":
            from orbit_cli import doctor
            from orbit_priority import audit
            status = doctor(args.project)
            print("ORBIT COORDINATOR OVERLAP AUDIT (read-only):")
            print(json.dumps(audit(home=installer.user_home(), project=args.project,
                                   hosts=args.hosts or HOSTS), indent=2))
            return status
        if args.action == "recover":
            if not args.backup or args.erase_memory or args.confirm_clean or args.hosts:
                raise installer.SetupError("Recovery requires --backup and no clean/host arguments")
            record, targets = inspect_uninstall_backup(args.backup)
            print("RECOVERY PREVIEW:", record["operation"], record["status"], len(targets), "targets")
            if not args.apply:
                print('PREVIEW ONLY; apply requires --apply --confirm-recover "RESTORE ORBIT"')
            else:
                count = recover_uninstall(args.backup, confirmation=args.confirm_recover)
                print("Recovered", count, "targets. Verify IDE registrations before restarting hosts.")
            return 0
        if args.backup or args.confirm_recover:
            raise installer.SetupError("Recovery flags apply only to recover")
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
