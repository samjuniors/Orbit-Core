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
    return mapped
