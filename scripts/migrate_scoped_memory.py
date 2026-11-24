"""Owner-operated legacy-to-root memory copy. No implicit changes.

Usage (trusted, authorized operator session):
  ORBIT_TRUSTED_ROOTS=<workspace parent> python scripts/migrate_scoped_memory.py
      --database <absolute sqlite path> --project <slug> --project-root <root>
  Add --apply --confirm "MIGRATE SCOPED MEMORY" after reviewing the preview.

Copies rows and creates a consistent adjacent backup first. Original legacy
memories are retained to avoid breaking pre-existing NORMAL-mode workflows.
This is not identity verification, OS isolation, or a credential migration.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "source" / "runtime"))
import orbit_mcp  # noqa: E402
import orbit_defense  # noqa: E402


MEMORY_COLUMNS = (
    "key", "kind", "summary", "source", "importance", "evidence",
    "created_at", "updated_at", "status", "archived_at", "archive_reason",
)


def preview_or_apply(database: Path, project: str, project_root: Path,
                     *, apply: bool = False, confirmation: str = ""):
    # Require an explicit host-root allowlist even for the CLI; do not
    # migrate records from an arbitrary attacker-supplied project directory.
    if not os.environ.get("ORBIT_TRUSTED_ROOTS", "").strip():
        raise ValueError("Set ORBIT_TRUSTED_ROOTS in the trusted operator environment")
    _, namespace = orbit_mcp.memory_scope({
        "project": project, "project_root": str(project_root),
    })
    if not orbit_defense.exact_trusted_root(str(project_root.resolve())):
        raise ValueError("Exact project root must be in ORBIT_TRUSTED_ROOTS")
    source = orbit_mcp.project_key({"project": project})
    db = Path(database).expanduser()
    if not db.is_absolute() or db.is_symlink() or not db.is_file():
        raise ValueError("Database must be an existing absolute regular file")
    if apply and confirmation != "MIGRATE SCOPED MEMORY":
        raise ValueError("Explicit confirmation is required for migration")

    # Read-only URI prevents creating or modifying an accidentally misspelled
    # database during a dry run. Backup and copy only after explicit approval.
    if not apply:
        connection = sqlite3.connect(db.resolve().as_uri() + "?mode=ro", uri=True)
    else:
        connection = sqlite3.connect(str(db.resolve()), timeout=15)
    try:
        tables = {x[0] for x in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        if "memories" not in tables:
            raise ValueError("No Orbit memories table in the selected database")
        legacy_count = connection.execute(
            "SELECT COUNT(*) FROM memories WHERE project=?", (source,)).fetchone()[0]
        scoped_count = connection.execute(
            "SELECT COUNT(*) FROM memories WHERE project=?", (namespace,)).fetchone()[0]
        summary = {
            "status": "PREVIEW_ONLY" if not apply else "MIGRATED",
            "legacy_count": legacy_count, "scoped_count_before": scoped_count,
            "migration_is_copy": True, "legacy_retained": True,
            "owner_authenticated": False,
        }
        if not apply:
            return summary
        if legacy_count == 0:
            return {**summary, "copied": 0, "status": "NO_LEGACY_ROWS"}
        # sqlite3.backup makes a consistent snapshot even for a WAL database.
        # tempfile creates an exclusive new adjacent backup; no older backup
        # or owner file is overwritten.
        fd, path = tempfile.mkstemp(prefix=db.name + ".before-scope-",
                                    suffix=".sqlite3", dir=str(db.parent))
        os.close(fd)
        backup = Path(path)
        try:
            with closing(sqlite3.connect(str(backup))) as destination:
                connection.backup(destination)
            if os.name != "nt":
                backup.chmod(0o600)
        except Exception:
            backup.unlink(missing_ok=True)
            raise

        columns = ", ".join(MEMORY_COLUMNS)
        placeholders = ", ".join("src." + c for c in MEMORY_COLUMNS)
        with connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                f"INSERT OR IGNORE INTO memories (project, {columns}) "
                f"SELECT ?, {placeholders} FROM memories AS src "
                "WHERE src.project=?", (namespace, source),
            )
        after = connection.execute(
            "SELECT COUNT(*) FROM memories WHERE project=?", (namespace,)).fetchone()[0]
        return {**summary, "copied": after - scoped_count,
                "scoped_count_after": after, "backup_created": True,
                "backup_name": backup.name,
                "conflicts_preserved": legacy_count - (after - scoped_count)}
    finally:
        connection.close()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--database", type=Path, required=True)
    p.add_argument("--project", required=True)
    p.add_argument("--project-root", type=Path, required=True)
    p.add_argument("--apply", action="store_true")
    p.add_argument("--confirm", default="")
    args = p.parse_args(argv)
    try:
        result = preview_or_apply(args.database, args.project, args.project_root,
                                  apply=args.apply, confirmation=args.confirm)
    except (ValueError, OSError, sqlite3.Error) as exc:
        p.exit(2, "Migration refused: " + str(exc) + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
