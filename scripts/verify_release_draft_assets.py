"""Fail-closed integrity gate for resuming an existing GitHub release draft.

Read-only: never uploads, deletes, tags, or publishes anything.
The release workflow separately requires manual main-branch dispatch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys


def required_assets(version: str) -> dict[str, str]:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Version must be strict MAJOR.MINOR.PATCH")
    names = (
        f"ORBIT-Universal-Setup-v{version}.zip",
        f"Orbit-Antigravity-Plugin-v{version}.zip",
        f"Orbit-Core-Plugin-Suite-v{version}.zip",
    )
    out = {name: f"dist/{name}" for name in names}
    for name in names:
        out[name + ".sha256"] = f"dist/{name}.sha256"
    desktop = f"ORBIT-Claude-Desktop-v{version}.mcpb"
    out[desktop] = desktop
    out[desktop + ".sha256"] = f"dist/{desktop}.sha256"
    return out


def verify_draft_assets(version: str, assets: object, root: Path,
                        *, allow_empty: bool = False) -> str:
    """Return EMPTY or COMPLETE. Partial, extra, and corrupt sets fail."""
    expected = required_assets(version)
    if not isinstance(assets, list):
        raise ValueError("GitHub assets response is not a list")
    if not assets and allow_empty:
        return "EMPTY"
    actual: dict[str, dict] = {}
    for item in assets:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise ValueError("Invalid GitHub asset entry")
        name = item["name"]
        if name in actual:
            raise ValueError("Duplicate GitHub release asset: " + name)
        actual[name] = item
    if set(actual) != set(expected):
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        raise ValueError(f"Draft has partial or unexpected assets (missing={missing}, extra={extra}); manual review required")
    root = root.resolve(strict=True)
    for name, relative in expected.items():
        local = (root / relative).resolve(strict=True)
        if root not in local.parents or not local.is_file():
            raise ValueError("Unsafe or missing local release artifact: " + name)
        metadata = actual[name]
        digest = metadata.get("digest")
        if not isinstance(digest, str) or not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest):
            raise ValueError("Missing/invalid GitHub SHA256 digest: " + name)
        local_digest = hashlib.sha256(local.read_bytes()).hexdigest()
        if digest.lower() != "sha256:" + local_digest:
            raise ValueError("Release draft artifact differs from rebuilt source: " + name)
        if metadata.get("size") != local.stat().st_size:
            raise ValueError("Release draft artifact size differs: " + name)
    return "COMPLETE"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--assets-json", type=Path, required=True,
                        help="Saved gh release view --json assets output")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--allow-empty", action="store_true",
                        help="Allow only zero assets or an exact complete set")
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.assets_json.read_text(encoding="utf-8-sig"))
        status = verify_draft_assets(args.version, payload["assets"], args.root,
                                     allow_empty=args.allow_empty)
    except (KeyError, ValueError, OSError, TypeError) as exc:
        print("RELEASE_DRAFT_ASSETS_BLOCKED: " + str(exc), file=sys.stderr)
        return 1
    print(status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
