"""Rebuild a versioned Claude Desktop bundle from canonical source.

When preparing a *new* SemVer release, pass --template-version pointing to an
already published .mcpb to reuse its non-code metadata. Never modify the old
tag/bundle: write only ORBIT-Claude-Desktop-v<current VERSION>.mcpb.
"""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build(root=ROOT, template_version=None):
    root = Path(root)
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("Invalid current VERSION")
    target = root / ("ORBIT-Claude-Desktop-v" + version + ".mcpb")
    if target.exists():
        template = target
    else:
        if (not template_version or
                not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", template_version) or
                tuple(map(int, template_version.split("."))) >= tuple(map(int, version.split(".")))):
            raise ValueError("New version requires --template-version with an older published bundle")
        template = root / ("ORBIT-Claude-Desktop-v" + template_version + ".mcpb")
        if not template.is_file():
            raise FileNotFoundError("Published template bundle is missing")

    with zipfile.ZipFile(template) as z:
        manifest = json.loads(z.read("manifest.json"))
        existing_version = manifest.get("version")
        if existing_version != (version if target.exists() else template_version):
            raise ValueError("Desktop template manifest version mismatch")
        # Preserve icons and non-code package resources, but replace all runtime
        # Python modules with source/runtime only.
        extras = [(name, z.read(name)) for name in z.namelist()
                  if name != "manifest.json" and not (name.startswith("server/") and name.endswith(".py"))]

    manifest["version"] = version
    # Published extensions must not inherit legacy mojibake or stale prose from
    # older templates. Keep the stable MCP identity and non-code resources.
    manifest["display_name"] = "Orbit Core - Memory & Agent Tasks"
    manifest["description"] = (
        "Local-first MCP for project planning, specialist task coordination and checkpoints."
    )
    manifest["long_description"] = (
        "Orbit Core coordinates approved plans, local project memory, specialist task "
        "handoffs and verification evidence across supported coding hosts. "
        "The host controls model selection, permissions and actual code execution; "
        "Orbit does not install providers or execute subagents by itself."
    )
    entries = [("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8"))]
    entries.extend(extras)
    entries.extend((f"server/{p.name}", p.read_bytes())
                   for p in sorted((root / "source/runtime").glob("*.py")))
    if len(entries) != len({name for name, _ in entries}):
        raise ValueError("Duplicate desktop bundle entry")

    temporary = target.with_suffix(".mcpb.tmp")
    try:
        with zipfile.ZipFile(temporary, "w") as archive:
            for name, data in entries:
                entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                entry.external_attr = 0o644 << 16
                archive.writestr(entry, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--template-version", help="Previously published bundle version for an initial new-version build")
    args = parser.parse_args()
    print("Rebuilt", build(template_version=args.template_version).name, "from source/runtime")
