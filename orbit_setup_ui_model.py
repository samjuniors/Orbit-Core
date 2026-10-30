"""Pure, read-only planning for the compact Orbit Core Windows setup.

The GUI only executes a plan after a separate human confirmation.
Host configuration and local Orbit SQLite are never touched during detection.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import installer
import orbit_setup
from orbit_cli import detect

DISPLAY_NAMES = {
    "antigravity": "Antigravity",
    "codex": "Codex",
    "claude-code": "Claude Code",
    "vscode": "VS Code (MCP)",
}
# DeepSeek Harness has its own Cordis plugin format and is NOT a verified host.
UNSUPPORTED_NOTICES = (
    "Claude Desktop uses a separate .mcpb extension.",
    "DeepSeek Harness is research-only; a native Cordis adapter is not verified.",
)


@dataclass(frozen=True)
class SetupPreview:
    action: str
    changes: tuple
    notes: tuple[str, ...]
    hosts: tuple[str, ...]
    scope: str
    project: str | None


def detected_hosts(project: str | None = None) -> dict[str, bool]:
    found = {row["host"]: bool(row["detected"]) for row in detect(project)}
    return {name: found.get(name, False) for name in DISPLAY_NAMES}


def preview(action: str, hosts: list[str] | tuple[str, ...], scope: str = "machine",
            project: str | None = None, *, delete_memory: bool = False) -> SetupPreview:
    if scope not in installer.SCOPES:
        raise installer.SetupError("Choose This computer or One project")
    if scope == "project":
        if not project:
            raise installer.SetupError("Select an existing project folder")
        project = str(installer.check_project(project))
    else:
        project = None
    chosen = tuple(dict.fromkeys(hosts))
    if action not in {"install", "update", "uninstall", "clean"}:
        raise installer.SetupError("Unsupported setup action")
    if action != "clean" and (not chosen or set(chosen) - set(installer.HOSTS)):
        raise installer.SetupError("Select at least one supported coding host")
    if action == "clean":
        changes, notes = orbit_setup.plan_clean_reset(project, erase_memory=delete_memory)
        # Clean reset is intentionally machine-wide, with optional project scope.
        return SetupPreview(action, tuple(changes), tuple(notes), tuple(installer.HOSTS),
                            scope, project)
    if delete_memory:
        raise installer.SetupError("Memory deletion is only available under explicit Clean reset")
    if action == "uninstall":
        changes, notes = orbit_setup.plan_uninstall(project, chosen, scope)
        return SetupPreview(action, tuple(changes), tuple(notes), chosen, scope, project)
    changes = tuple(installer.plan(project, chosen, scope))
    return SetupPreview(action, changes, tuple(), chosen, scope, project)


def local_state(preview_result: SetupPreview) -> str:
    """Classify a verified *bundled local* setup plan; not an online update query."""
    if preview_result.action in ("uninstall", "clean"):
        return preview_result.action
    writable = [c for c in preview_result.changes if c.action not in {"SKIP", "PRESERVE"}]
    if not writable:
        return "current"
    if any(c.action in {"UPGRADE", "MERGE", "APPEND"} for c in writable):
        return "update"
    # An already present file must never be presented as a clean new install.
    if any(c.target.exists() for c in preview_result.changes):
        # An already-installed host with a missing component is a repair/update,
        # not a new installation. Keep the UI to three requested actions.
        return "update"
    return "install"


def preview_lines(review: SetupPreview) -> str:
    lines = []
    for c in review.changes:
        if review.action in ("uninstall", "clean"):
            flag = "REMOVE" if c.replacement is None else "EDIT"
            lines.append(f"{flag:8} {c.path}")
        else:
            lines.append(f"{c.action:8} {c.target}")
    lines.extend(review.notes)
    lines.append(f"\n{len(review.changes)} planned entries. Nothing has changed.")
    return "\n".join(lines)


def apply(review: SetupPreview, *, confirmation: str, delete_memory: bool = False):
    """Apply exactly the previewed plan. GUI must have shown it to the user."""
    if review.action == "clean":
        if confirmation != "REMOVE ORBIT":
            raise installer.SetupError("Clean reset requires typed REMOVE ORBIT confirmation")
        return orbit_setup.apply_clean_reset(list(review.changes), review.project,
                                             erase_memory=delete_memory, confirmation=confirmation)
    if confirmation != "CONFIRM":
        raise installer.SetupError("Approval required before changes")
    if review.action == "uninstall":
        return orbit_setup.apply_uninstall(list(review.changes))
    # Replan just before execution; the underlying installer rechecks file content
    # and makes backups before overwriting recognized host configuration.
    current = preview(review.action, review.hosts, review.scope, review.project)
    if current.changes != review.changes:
        raise installer.SetupError("Files changed after preview; review the new plan")
    return installer.install(list(review.changes))
