"""Read-only, offline release readiness checks for every CI and publication run.

The published 0.26.0 changelog is a historical long-form prerelease. New
versions (starting with 0.27.0) require concise, structured public notes.
This script never modifies Git tags, host settings, release artifacts or docs.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
REQUIRED_SECTIONS = (
    "### Highlights",
    "### Install and upgrade",
    "### Compatibility",
    "### Known limitations",
)
LEGACY_PUBLIC_NOTE_CUTOFF = (0, 26, 0)
RELEASE_ASSETS = (
    "ORBIT-Universal-Setup",
    "Orbit-Antigravity-Plugin",
    "Orbit-Core-Plugin-Suite",
    "ORBIT-Claude-Desktop",
)


def version_tuple(value: str):
    if not SEMVER.fullmatch(value):
        raise ValueError("VERSION must contain strict MAJOR.MINOR.PATCH")
    return tuple(int(part) for part in value.split("."))


def check_release(root: Path = ROOT) -> list[str]:
    root = Path(root)
    errors: list[str] = []
    version_path = root / "VERSION"
    if not version_path.exists():
        return ["VERSION is missing"]
    version = version_path.read_text(encoding="utf-8").strip()
    try:
        semver = version_tuple(version)
    except ValueError as exc:
        return [str(exc)]

    changelog = root / "CHANGELOG.md"
    if not changelog.is_file():
        errors.append("CHANGELOG.md is missing")
    else:
        notes = changelog.read_text(encoding="utf-8")
        matches = list(re.finditer(r"(?m)^## \[([^]]+)\][^\n]*$", notes))
        current = [i for i, match in enumerate(matches) if match.group(1) == version]
        if len(current) != 1:
            errors.append(f"Expected one CHANGELOG.md ## [{version}] entry")
        else:
            i = current[0]
            start = matches[i].end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(notes)
            section = notes[start:end]
            if not section.strip():
                errors.append("Public release notes section is empty")
            if semver > LEGACY_PUBLIC_NOTE_CUTOFF:
                for heading in REQUIRED_SECTIONS:
                    if heading not in section:
                        errors.append(f"Release notes must include {heading}")
                if re.search(r"(?i)\b(not (?:yet )?published|unpublished candidate|no release is authorized)\b", section):
                    errors.append("Release notes contain stale not-published wording")
                if len(section) > 9000:
                    errors.append("Release notes too long for the concise public template (max 9000 chars)")

    readme = root / "README.md"
    quickstart = root / "docs" / "RELEASE-QUICKSTART.md"
    process = root / "docs" / "RELEASE-PROCESS.md"
    for filename, path in (("README.md", readme), ("docs/RELEASE-QUICKSTART.md", quickstart),
                           ("docs/RELEASE-PROCESS.md", process)):
        if not path.is_file():
            errors.append(f"Missing {filename}")
            continue
        body = path.read_text(encoding="utf-8")
        if "https://github.com/samjuniors/Orbit-Core/releases" not in body:
            errors.append(f"{filename} must link to the canonical release list")
        if re.search(r"(?i)(?:latest|currently)\s+(?:published\s+)?(?:release|package|version)\s+is\s+(?:\*\*)?v\d+\.\d+\.\d+", body):
            errors.append(f"{filename}: hard-coded latest release can go stale")
    if readme.is_file():
        s = readme.read_text(encoding="utf-8").lower()
        if re.search(r"v" + re.escape(version) + r"[^\n]{0,70}(?:unpublished|not published)", s):
            errors.append("README.md describes current VERSION as unpublished")
    bundle = root / f"ORBIT-Claude-Desktop-v{version}.mcpb"
    if not bundle.is_file():
        errors.append(f"Desktop bundle ORBIT-Claude-Desktop-v{version}.mcpb is missing; prepare candidate first")
    else:
        try:
            with zipfile.ZipFile(bundle) as z:
                manifest = json.loads(z.read("manifest.json").decode("utf-8"))
            if manifest.get("version") != version:
                errors.append("Desktop extension VERSION mismatch")
            if manifest.get("name") != "orbit-core-native":
                errors.append("Desktop extension MCP identity changed unexpectedly")
            title = manifest.get("display_name", "")
            detail = manifest.get("long_description", "")
            if not isinstance(title, str) or title != "Orbit Core - Memory & Agent Tasks":
                errors.append("Desktop extension display_name is stale or malformed")
            if not isinstance(detail, str) or "switching.." in detail or "Ã" in detail:
                errors.append("Desktop extension long_description is stale or contains mojibake")
        except (OSError, ValueError, KeyError, zipfile.BadZipFile) as exc:
            errors.append("Cannot parse versioned desktop extension manifest: " + str(exc))
    return errors


def main():
    errors = check_release()
    if errors:
        for error in errors:
            print("RELEASE_READINESS_FAIL: " + error, file=sys.stderr)
        raise SystemExit(1)
    print("RELEASE_READINESS_PASS: version, public notes, installation docs and extension metadata")


if __name__ == "__main__":
    main()
