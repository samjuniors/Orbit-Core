"""Build an unpublished, version-consistent candidate MCPB from a prior bundle.

This does not tag, install, publish or update any previous release.
Run before CI tests that inspect the matching current-version desktop bundle.
"""
from __future__ import annotations

import hashlib
import json
import re
import zipfile
from pathlib import Path

from build_desktop_extension import build

ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


def semver(value):
    if not isinstance(value, str) or not SEMVER.fullmatch(value):
        raise ValueError("Invalid release version")
    return tuple(map(int, value.split(".")))


def source_parity(root, bundle, expected_version):
    """Check all shipped Python runtime modules against canonical source."""
    with zipfile.ZipFile(bundle) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("version") != expected_version:
            raise ValueError("Candidate manifest version mismatch")
        files = sorted((root / "source/runtime").glob("*.py"))
        actual = sorted(name for name in archive.namelist()
                        if name.startswith("server/") and name.endswith(".py"))
        desired = sorted("server/" + p.name for p in files)
        if actual != desired:
            raise ValueError("Desktop bundle runtime module inventory differs from source")
        if any(archive.read("server/" + p.name) != p.read_bytes() for p in files):
            raise ValueError("Desktop bundle runtime source differs from checkout")
    return hashlib.sha256(bundle.read_bytes()).hexdigest()


def prepare(root=ROOT):
    root = Path(root)
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    current = semver(version)
    target = root / ("ORBIT-Claude-Desktop-v" + version + ".mcpb")
    if not target.exists():
        options = []
        for path in root.glob("ORBIT-Claude-Desktop-v*.mcpb"):
            old = path.name.removeprefix("ORBIT-Claude-Desktop-v").removesuffix(".mcpb")
            try:
                parsed = semver(old)
            except ValueError:
                continue
            if parsed < current and path.is_file() and not path.is_symlink():
                options.append((parsed, old))
        if not options:
            raise ValueError("No prior immutable desktop bundle available for the candidate")
        _, previous = max(options)
        path = root / ("ORBIT-Claude-Desktop-v" + previous + ".mcpb")
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        build(root=root, template_version=previous)
        if hashlib.sha256(path.read_bytes()).hexdigest() != before:
            raise ValueError("Previous published bundle was modified")
        created = True
    else:
        if target.is_symlink() or not target.is_file():
            raise ValueError("Candidate bundle must be a regular file")
        created = False
    digest = source_parity(root, target, version)
    return {"version": version, "bundle": str(target), "sha256": digest, "generated": created}


if __name__ == "__main__":
    print(json.dumps(prepare(), indent=2))
