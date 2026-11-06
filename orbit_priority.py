"""Read-only Orbit coordinator overlap audit.

Names and paths provide hints, not proof that a host selected or ran a plugin.
Never loads competitor skill content or edits host settings.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path

HOSTS = ("antigravity", "codex", "claude-code", "vscode")
SERVER = "orbit-core-native"
ORBIT_ALIAS = re.compile(r"(?<![a-z0-9])orbit(?![a-z0-9])", re.I)
ROLE_ALIAS = re.compile(r"orchestrat|agent[-_ ]?manager|multi[-_ ]?agent|swarm", re.I)
CODEX_TABLE = re.compile(
    r"""(?m)^\s*\[mcp_servers\.(?:"([^"]+)"|'([^']+)'|([A-Za-z0-9_-]+))\]\s*(?:#.*)?$"""
)


def _read(path, warnings):
    if path.is_symlink() or any(x.is_symlink() for x in path.parents):
        warnings.append("SKIP linked config path: " + str(path))
        return None
    if not path.exists():
        return None
    if not path.is_file() or path.stat().st_size > 1_000_000:
        warnings.append("SKIP invalid or oversized config: " + str(path))
        return None
    try:
        return path.read_bytes()
    except OSError:
        warnings.append("SKIP unreadable config: " + str(path))
        return None


def _names(path, host, warnings):
    data = _read(path, warnings)
    if data is None:
        return set()
    try:
        if host == "codex":
            # Name-only conservative TOML header scan, Python 3.10 compatible.
            return {next(x for x in m.groups() if x is not None)
                    for m in CODEX_TABLE.finditer(data.decode("utf-8"))}
        value = json.loads(data.decode("utf-8-sig"))
        section = "servers" if host == "vscode" else "mcpServers"
        servers = value.get(section) if isinstance(value, dict) else None
        if servers is None:
            return set()
        if not isinstance(servers, dict):
            raise ValueError("invalid section")
        return {name for name in servers if isinstance(name, str)}
    except (UnicodeError, ValueError):
        warnings.append("SKIP unrecognized config format: " + str(path))
        return set()


def _paths(home, project):
    return {
        "antigravity": (home / ".gemini/config/mcp_config.json",
                        project / ".agents/mcp_config.json" if project else None),
        "codex": (home / ".codex/config.toml",
                  project / ".codex/config.toml" if project else None),
        "claude-code": (home / ".claude.json",
                        project / ".mcp.json" if project else None),
        "vscode": ((home / "AppData/Roaming/Code/User/mcp.json" if os.name == "nt"
                    else home / ".config/Code/User/mcp.json"),
                   project / ".vscode/mcp.json" if project else None),
    }


def audit(home, project=None, hosts=HOSTS):
    """Inspect known host registrations without network, execution or writes."""
    user = Path(home).expanduser().absolute()
    project = Path(project).expanduser().absolute() if project else None
    chosen = tuple(dict.fromkeys(hosts))
    if not chosen or set(chosen) - set(HOSTS):
        raise ValueError("Select valid hosts")
    warnings = []
    conflicts = []
    summary = {}
    locations = _paths(user, project)
    for host in chosen:
        seen = {}
        for scope, target in zip(("user", "project"), locations[host]):
            if target is not None:
                seen[scope] = _names(target, host, warnings)
        present = [scope for scope, names in seen.items() if SERVER in names]
        summary[host] = {
            "orbit_configured_scopes": present,
            "other_server_count": sum(len(names - {SERVER}) for names in seen.values()),
        }
        if len(present) > 1:
            conflicts.append({"host": host, "kind": "ORBIT_SCOPE_OVERLAP",
                              "name": SERVER, "summary": "Review host-specific project/user precedence."})
        for scope, names in seen.items():
            for name in sorted(names, key=str.casefold):
                if name == SERVER:
                    continue
                kind = ("POSSIBLE_ORBIT_ALIAS" if ORBIT_ALIAS.search(name)
                        else "POSSIBLE_COORDINATOR_OVERLAP" if ROLE_ALIAS.search(name)
                        else None)
                if kind:
                    conflicts.append({"host": host, "scope": scope, "kind": kind,
                                      "name": "".join(ch if ch.isprintable() else "?" for ch in name)[:80], "summary":
                                      "Name-only hint; independently review purpose before adjusting tools."})
    skills = {
        "antigravity": (user / ".gemini/config/skills/orbit/SKILL.md",
                        project / ".agents/skills/orbit/SKILL.md" if project else None),
        "codex": (user / ".agents/skills/orbit/SKILL.md",
                  project / ".agents/skills/orbit/SKILL.md" if project else None),
        "claude-code": (user / ".claude/skills/orbit/SKILL.md",
                        project / ".claude/skills/orbit/SKILL.md" if project else None),
        "vscode": (None, None),
    }
    for host in chosen:
        found = []
        for scope, target in zip(("user", "project"), skills[host]):
            if target is None:
                continue
            if target.is_symlink() or any(x.is_symlink() for x in target.parents):
                warnings.append("SKIP linked Orbit skill path: " + str(target))
            elif target.is_file():
                found.append(scope)
        if len(found) > 1:
            conflicts.append({"host": host, "kind": "ORBIT_SKILL_SCOPE_OVERLAP",
                              "name": "orbit", "summary":
                              "Orbit skills exist at user and project scope; host precedence is unverified."})
    return {
        "status": ("REVIEW_POSSIBLE_OVERLAP" if conflicts else "REVIEW_INCOMPLETE" if warnings else "NO_OBVIOUS_NAME_COLLISION"),
        "preference": "ORBIT_PREFERRED_FOR_PROJECT_LIFECYCLE",
        "priority_enforced": False,
        "host_connection_verified": False,
        "configuration_modified": False,
        "hosts": summary,
        "conflicts": conflicts[:25],
        "more_conflicts_omitted": max(0, len(conflicts) - 25),
        "warnings": warnings[:25],
        "recommended_action":
            "Explicitly select Orbit for project coordination and use other plugins "
            "for specialist tasks. Review overlaps; do not disable or uninstall competing tools.",
        "limits": "Config names and skill paths do not establish purpose, priority, activation or permission.",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only Orbit coordinator collision inventory")
    parser.add_argument("--project", help="Optional project to include")
    parser.add_argument("--hosts", nargs="+", choices=HOSTS, default=HOSTS)
    args = parser.parse_args(argv)
    try:
        home = os.environ.get("ORBIT_SETUP_HOME") or str(Path.home())
        print(json.dumps(audit(home, args.project, args.hosts), indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print("PRIORITY AUDIT BLOCKED:", str(exc))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
