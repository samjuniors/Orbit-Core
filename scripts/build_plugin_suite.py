"""Build a single ZIP holding distinct host adapter directories."""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path
try:
    from .build_antigravity_plugin import build_files
except ImportError:
    from build_antigravity_plugin import build_files

ROOT = Path(__file__).resolve().parents[1]

def json_bytes(obj):
    return (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode()

def entries(root=ROOT):
    root = Path(root)
    version = (root / "VERSION").read_text().strip()
    source = build_files(root)
    mapped = {}
    for name, blob in source.items():
        mapped[f"orbit-core-suite/antigravity/orbit-core/{name}"] = blob
    common = {name: blob for name, blob in source.items()
              if name.startswith(("runtime/", "skills/"))}
    codex = dict(common)
    codex["plugin.json"] = json_bytes({
        "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
        "name": "orbit-core", "version": version,
        "description": "Orbit Core local-first coding workflows"})
    codex["mcp.json"] = json_bytes({"mcpServers": {"orbit-core-mcp": {
        "command": "python", "args": ["${PLUGIN_ROOT}/runtime/orbit_mcp.py"]}}})
    for name, blob in codex.items():
        mapped[f"orbit-core-suite/codex/orbit-core/{name}"] = blob
    claude = dict(common)
    claude[".claude-plugin/plugin.json"] = json_bytes({
        "name": "orbit-core", "version": version,
        "description": "Orbit Core local workflow, MCP and specialist agents"})
    claude[".mcp.json"] = json_bytes({"mcpServers": {"orbit-core-mcp": {
        "command": "python", "args": ["${CLAUDE_PLUGIN_ROOT}/runtime/orbit_mcp.py"]}}})
    for name, body in source.items():
        if not name.startswith("agents/") or name == "agents/orbit-lead-agent.md":
            continue
        raw = body.decode("utf-8")
        header, _, details = raw[4:].partition("\n---\n")
        description = next((line.split(":", 1)[1].strip()
                            for line in header.splitlines()
                            if line.startswith("description:")), Path(name).stem)
        claude[name] = (f"---\nname: {Path(name).stem}\n"
                        f"description: {description}\nmodel: inherit\n---\n" +
                        details).encode("utf-8")
    for name, blob in claude.items():
        mapped[f"orbit-core-suite/claude-code/orbit-core/{name}"] = blob
    mapped["orbit-core-suite/README.md"] = (
        "One Orbit Core ZIP, separate Antigravity/Codex/Claude Code adapters.\n"
        "DeepSeek Harness requires a separate Cordis adapter; NOT supported.\n"
        "No cloud server is needed; locally launched MCP still requires Python.\n"
        "Native plugin activation, paths and permissions require real-host tests.\n"
        "Extracting this archive does not modify any host configuration.\n").encode()
    return mapped
