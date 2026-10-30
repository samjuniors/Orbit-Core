"""Plan or explicitly stage an Antigravity migration without discarding user data.

The normal command is READ ONLY. An apply requires explicit confirmation,
backs up all affected configuration and customization files and only removes
known Orbit entries. Does not install or enable a plugin.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
from pathlib import Path

KNOWN_AGENTS = {
    "orbit.md", "orbit-architect.md", "orbit-backend.md", "orbit-data.md",
    "orbit-devops.md", "orbit-frontend.md", "orbit-integrator.md",
    "orbit-qa.md", "orbit-research.md", "orbit-reviewer.md",
    "orbit-security.md", "orbit-ux.md", "orbit-writer.md"
}


def _ensure_regular(path: Path) -> None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError(f"Unsafe file path: {path}")


def _ensure_tree(path: Path) -> None:
    if path.is_symlink():
        raise ValueError(f"Unsafe symlinked path: {path}")
    if path.exists():
        for child in path.rglob("*"):
            if child.is_symlink():
                raise ValueError(f"Unsafe symlinked skill reference: {child}")


def inspect(home: Path) -> dict:
    home = Path(home).resolve()
    config_dir = home / ".gemini" / "config"
    config = config_dir / "mcp_config.json"
    _ensure_regular(config)
    if not config.exists():
        entries = {}
    else:
        payload = json.loads(config.read_text(encoding="utf-8-sig"))
        entries = payload.get("mcpServers", {})
        if not isinstance(entries, dict):
            raise ValueError("Invalid Antigravity MCP configuration")
    legacy = entries.get("orbit-core-native")
    if legacy is not None:
        if not isinstance(legacy, dict):
            raise ValueError("Non-object Orbit MCP registration; manual review")
        args = legacy.get("args", [])
        # Migration only accepts the Orbit entry, not an arbitrary custom command.
        if not isinstance(args, list) or not any(
            isinstance(x, str) and x.replace("\\", "/").endswith("/orbit_mcp.py")
            for x in args
        ):
            raise ValueError("Unknown orbit-core-native definition; manual review")
    legacy_env = legacy.get("env", {}) if legacy else {}
    if not isinstance(legacy_env, dict):
        raise ValueError("Unknown legacy Orbit MCP environment; manual review")
    # A host-specific ORBIT_LOCAL_DB override must not be silently discarded.
    custom_db = "ORBIT_LOCAL_DB" in legacy_env
    conflicts = sorted(name for name in entries
                       if name.startswith("orbit-") and name != "orbit-core-native")
    agents_dir = config_dir / "agents"
    _ensure_tree(agents_dir)
    agents = sorted(path for path in agents_dir.glob("orbit*.md")
                    if path.name in KNOWN_AGENTS)
    skill = config_dir / "skills" / "orbit"
    _ensure_tree(skill)
    plugin = config_dir / "plugins" / "orbit-core"
    _ensure_tree(plugin)
    return {
        "config": str(config),
        "legacy_mcp": legacy is not None,
        "legacy_custom_database_override": custom_db,
        "additional_orbit_mcp_servers": conflicts,
        "global_agents": [str(p) for p in agents],
        "global_orbit_skill": str(skill) if skill.exists() else None,
        "installed_orbit_plugin": str(plugin) if plugin.exists() else None,
        "safe_to_install_now": legacy is None and not conflicts and not agents and not skill.exists() and not plugin.exists(),
    }


def stage_migration(home: Path, confirm: str) -> dict:
    if confirm != "ARCHIVE_LEGACY_ORBIT_AND_KEEP_BACKUPS":
        raise ValueError("Explicit review and confirmation required")
    home = Path(home).resolve()
    plan = inspect(home)
    if plan["legacy_custom_database_override"]:
        raise ValueError("Legacy Orbit uses ORBIT_LOCAL_DB; preserve that explicit data path before migrating")
    if plan["additional_orbit_mcp_servers"]:
        raise ValueError("Other Orbit test/MCP servers present; review them separately")
    if plan["installed_orbit_plugin"]:
        raise ValueError("Existing Orbit plugin present; inspect update rather than migrate")
    if plan["safe_to_install_now"]:
        return {"status": "NO_LEGACY_INTEGRATION", "backups": None}
    config = Path(plan["config"])
    base = home / ".gemini" / "config"
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = base / "orbit-core-migration-backups" / stamp
    if backup.exists():
        raise FileExistsError("Migration backup directory already exists")
    backup.mkdir(parents=True, exist_ok=False)
    try:
        if config.exists():
            shutil.copy2(config, backup / "mcp_config.json")
        archived = backup / "agents"
        for agent in plan["global_agents"]:
            original = Path(agent)
            archived.mkdir(exist_ok=True)
            shutil.copy2(original, archived / original.name)
        if plan["global_orbit_skill"]:
            shutil.copytree(plan["global_orbit_skill"], backup / "skill")
        # Verify snapshots BEFORE modifying anything live.
        for agent in plan["global_agents"]:
            original = Path(agent)
            if original.read_bytes() != (archived / original.name).read_bytes():
                raise OSError("Agent backup verification failed")
        if config.exists() and config.read_bytes() != (backup / "mcp_config.json").read_bytes():
            raise OSError("MCP backup verification failed")
        # Write a new JSON document preserving all unrelated entries.
        if plan["legacy_mcp"]:
            payload = json.loads(config.read_text(encoding="utf-8-sig"))
            payload["mcpServers"].pop("orbit-core-native")
            staged = config.with_name("mcp_config.json.orbit-migration-stage")
            if staged.exists():
                raise FileExistsError("A migration staging file already exists")
            staged.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            staged.replace(config)
        for agent in plan["global_agents"]:
            Path(agent).unlink()
        if plan["global_orbit_skill"]:
            shutil.rmtree(plan["global_orbit_skill"])
    except Exception:
        # An incomplete migration must remain inspectable. Restore originals
        # only when destinations were removed (never overwrite concurrent edits).
        if config.exists() and (backup / "mcp_config.json").exists():
            shutil.copy2(backup / "mcp_config.json", config)
        for agent in plan["global_agents"]:
            dest = Path(agent)
            source = backup / "agents" / dest.name
            if not dest.exists() and source.exists():
                shutil.copy2(source, dest)
        skill = base / "skills" / "orbit"
        if not skill.exists() and (backup / "skill").exists():
            shutil.copytree(backup / "skill", skill)
        raise
    return {"status": "LEGACY_ARCHIVED_PLUGIN_NOT_INSTALLED",
            "backup": str(backup), "archived_agents": len(plan["global_agents"]),
            "archived_skill": bool(plan["global_orbit_skill"]),
            "archived_mcp_registration": plan["legacy_mcp"]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", default="")
    opts = parser.parse_args()
    print(json.dumps(stage_migration(opts.home, opts.confirm) if opts.apply
                     else inspect(opts.home), indent=2))


if __name__ == "__main__":
    main()
