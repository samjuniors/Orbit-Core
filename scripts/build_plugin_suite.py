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
# Committed copy of the Claude Code adapter, served by .claude-plugin/marketplace.json
# so `/plugin marketplace add samjuniors/Orbit-Core` works without a ZIP.
CLAUDE_CODE_PLUGIN_DIR = Path("plugins") / "claude-code" / "orbit-core"

def json_bytes(obj):
    return (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode()

def entries(root=ROOT):
    root = Path(root)
    version = (root / "VERSION").read_text().strip()
    source = build_files(root)
    mapped = {}
    # The same download also contains the working Windows launcher and the
    # legacy safe host setup backend; users do not need a second installer ZIP.
    launcher = (
        "Orbit Setup.cmd", "orbit_setup.py", "orbit_setup_ui_model.py",
        "orbit_compact_gui.py", "installer.py", "orbit_priority.py", "install_orbit_gui.pyw",
        "orbit_cli.py", "orbit_update_gui.py", "VERSION", "NEXT_VERSION",
        "CHANGELOG.md", "README.md",
    )
    for item in launcher:
        mapped["orbit-core-suite/" + item] = (root / item).read_bytes()
    for item in sorted((root / "source").rglob("*")):
        if item.is_file() and not item.is_symlink() and "__pycache__" not in item.parts:
            mapped["orbit-core-suite/" + item.relative_to(root).as_posix()] = item.read_bytes()
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
    for name, blob in claude_code_files(root, source).items():
        mapped[f"orbit-core-suite/claude-code/orbit-core/{name}"] = blob
    mapped["orbit-core-suite/README.md"] = (
        "One Orbit Core ZIP, separate Antigravity/Codex/Claude Code adapters.\n"
        "DeepSeek Harness requires a separate Cordis adapter; NOT supported.\n"
        "No cloud server is needed; locally launched MCP still requires Python.\n"
        "Native plugin activation, paths and permissions require real-host tests.\n"
        "Extracting this archive does not modify any host configuration.\n").encode()
    return mapped

# Antigravity agent tool -> Claude Code built-in tools. Without a `tools` field a
# Claude Code plugin agent inherits every session tool, so read-only roles must keep theirs.
CLAUDE_CODE_TOOL_MAP = {
    "view_file": ("Read",), "grep_search": ("Grep", "Glob"),
    "replace_file_content": ("Edit",), "write_to_file": ("Write",), "run_command": ("Bash",),
}

def claude_code_tools(header, name):
    listed, in_tools = [], False
    for line in header.splitlines():
        if line.startswith("tools:"):
            in_tools = True
        elif in_tools and line.startswith("  - "):
            listed.append(line[4:].strip())
        else:
            in_tools = False
    if not listed:
        raise ValueError("Agent has no tool allowlist: " + name)
    mapped = []
    for tool in listed:
        if tool not in CLAUDE_CODE_TOOL_MAP:
            raise ValueError(f"Unmapped agent tool {tool!r} in {name}")
        mapped += [t for t in CLAUDE_CODE_TOOL_MAP[tool] if t not in mapped]
    return ", ".join(mapped)

def claude_code_files(root=ROOT, source=None):
    """Claude Code plugin layout (relative names) generated from canonical source."""
    root = Path(root)
    version = (root / "VERSION").read_text().strip()
    source = build_files(root) if source is None else source
    claude = {name: blob for name, blob in source.items()
              if name.startswith(("runtime/", "skills/"))}
    claude[".claude-plugin/plugin.json"] = json_bytes({
        "name": "orbit-core", "version": version,
        "description": "Orbit Core local workflow, MCP and specialist agents",
        "author": {"name": "samjuniors"},
        "homepage": "https://github.com/samjuniors/Orbit-Core",
        "repository": "https://github.com/samjuniors/Orbit-Core", "license": "MIT"})
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
        tools = claude_code_tools(header, name)
        claude[name] = (f"---\nname: {Path(name).stem}\n"
                        f"description: {description}\ntools: {tools}\nmodel: inherit\n---\n" +
                        details).encode("utf-8")
    return claude

def sync_claude_code_plugin(root=ROOT):
    """Rewrite the committed Claude Code plugin directory to match canonical source."""
    root = Path(root)
    target = root / CLAUDE_CODE_PLUGIN_DIR
    desired = claude_code_files(root)
    if target.is_symlink():
        raise ValueError("Refusing symlinked Claude Code plugin directory")
    for item in sorted(target.rglob("*"), reverse=True) if target.exists() else ():
        rel = item.relative_to(target).as_posix()
        if item.is_symlink() or (item.is_file() and rel not in desired):
            item.unlink()
        elif item.is_dir() and not any(item.iterdir()):
            item.rmdir()
    for name, blob in desired.items():
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.is_file() or path.read_bytes() != blob:
            path.write_bytes(blob)
    return {"directory": CLAUDE_CODE_PLUGIN_DIR.as_posix(), "files": len(desired)}

def verify(root, path):
    desired = entries(root)
    with zipfile.ZipFile(path) as archive:
        if sorted(archive.namelist()) != sorted(desired):
            raise ValueError("Plugin suite inventory differs from canonical source")
        for name, content in desired.items():
            if archive.read(name) != content:
                raise ValueError("Plugin suite differs from source: " + name)
    digest = hashlib.sha256(Path(path).read_bytes()).hexdigest()
    checksum = Path(str(path) + ".sha256")
    if not checksum.is_file() or checksum.read_text(encoding="ascii") != f"{digest}  {Path(path).name}\n":
        raise ValueError("Plugin suite checksum missing or incorrect")
    return {"files": len(desired), "sha256": digest}

def build(root=ROOT, path=None):
    root = Path(root)
    version = (root / "VERSION").read_text().strip()
    path = Path(path) if path else root / "dist" / f"Orbit-Core-Plugin-Suite-v{version}.zip"
    if path.is_symlink():
        raise ValueError("Refusing symlinked suite archive")
    if path.exists():
        return verify(root, path)
    path.parent.mkdir(exist_ok=True, parents=True)
    with zipfile.ZipFile(path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, body in sorted(entries(root).items()):
            if ".." in Path(name).parts or name.startswith("/"):
                raise ValueError("Unsafe ZIP path")
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, body)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    Path(str(path) + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="ascii")
    return verify(root, path)

if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["--sync-claude-code"]:
        print(json.dumps(sync_claude_code_plugin(), indent=2))
    else:
        print(json.dumps(build(), indent=2))
