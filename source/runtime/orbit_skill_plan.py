"""Original Orbit skill shortlist / integrity preview (v0.29 development).

Read-only, dependency-free, no external catalog download, host installation,
permission grant or skill execution. Skill names and frontmatter are untrusted.
This module is not an AAS runtime, importer, or approval authenticator.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

MAX_SELECTED = 5
MAX_SKILL_BYTES = 65536
MAX_DESCRIPTION_CHARS = 320
SKILL_NAME = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
HEX_DIGEST = re.compile(r"[a-f0-9]{64}\Z")
PRODUCT_TYPES = frozenset({
    "website", "web-app", "mobile-app", "desktop-app", "api-service",
    "cli", "sdk-library", "plugin-mcp", "os-platform", "game",
    "data-automation", "other",
})
PLATFORMS = frozenset({
    "web", "server", "android", "ios", "mobile-cross-platform",
    "windows", "linux", "macos", "desktop-cross-platform", "embedded",
    "console", "other",
})
HOSTS = frozenset({"unknown", "codex", "claude-code", "antigravity"})
TARGETS_BY_PRODUCT = {
    "website": frozenset({"web", "server", "other"}),
    "web-app": frozenset({"web", "server", "other"}),
    "mobile-app": frozenset({"android", "ios", "mobile-cross-platform", "other"}),
    "desktop-app": frozenset({"windows", "linux", "macos", "desktop-cross-platform", "other"}),
    "os-platform": frozenset({"windows", "linux", "macos", "embedded", "other"}),
    "api-service": frozenset({"server", "windows", "linux", "macos", "other"}),
    "cli": frozenset({"server", "windows", "linux", "macos", "other"}),
    "sdk-library": frozenset({"web", "server", "android", "ios", "windows",
                               "linux", "macos", "other"}),
    "plugin-mcp": frozenset({"server", "windows", "linux", "macos", "other"}),
    "data-automation": frozenset({"server", "windows", "linux", "macos", "other"}),
    "game": frozenset({"web", "android", "ios", "windows", "linux",
                        "macos", "console", "other"}),
}
OPERATIONS = frozenset({
    "build", "add-feature", "fix", "debug", "redesign", "maintain",
    "resume", "review", "research", "test",
})
# Guidance only; a declared technology never asserts the host has its SDK.
TECHNOLOGIES = frozenset({
    "react", "nextjs", "vue", "angular", "svelte", "typescript",
    "javascript", "python", "django", "fastapi", "rust", "tauri",
    "electron", "dotnet", "flutter", "dart", "swift", "swiftui",
    "kotlin", "kotlin-compose", "react-native", "pytorch",
    "tensorflow", "unity", "unreal", "go", "java", "csharp", "cpp",
    "other",
})
# A small explicit mismatch guard avoids projecting unrelated web guidance
# onto a native or ML project. Nothing here silently switches frameworks.
WEB_MARKERS = frozenset({"react", "next", "nextjs", "vue", "angular", "svelte", "dom", "css", "browser", "webapp"})
MOBILE_MARKERS = frozenset({"flutter", "dart", "swift", "swiftui", "kotlin", "android", "ios", "mobile", "compose"})
GAME_MARKERS = frozenset({"unity", "unreal", "game", "gamedev", "gameplay"})
ML_MARKERS = frozenset({"pytorch", "tensorflow", "ml", "model", "machine", "inference", "training"})
NATIVE_MARKERS = frozenset({"rust", "cargo", "tauri", "electron", "dotnet", "native", "desktop", "cpp"})
STOPWORDS = frozenset({"a", "an", "for", "the", "and", "to", "of", "in", "with", "on", "or", "from", "this", "that"})


def _profile(value):
    """Reject unknown and oversized input without inferring codebase state."""
    if value is None:
        return {"product_type": "other", "platform": "other",
                "technologies": [], "operation": "research"}
    if not isinstance(value, dict) or set(value) - {"product_type", "platform", "technologies", "operation"}:
        raise ValueError("project_profile may only include product_type, platform, technologies, operation")
    product = value.get("product_type", "other")
    platform = value.get("platform", "other")
    operation = value.get("operation", "research")
    technologies = value.get("technologies", [])
    if (not isinstance(product, str) or not isinstance(platform, str)
            or not isinstance(operation, str) or product not in PRODUCT_TYPES
            or platform not in PLATFORMS or operation not in OPERATIONS):
        raise ValueError("Unknown project_profile classification")
    if product in TARGETS_BY_PRODUCT and platform not in TARGETS_BY_PRODUCT[product]:
        raise ValueError("Declared platform conflicts with product type")
    if not isinstance(technologies, list) or len(technologies) > 8 or any(
        not isinstance(t, str) or t not in TECHNOLOGIES for t in technologies
    ):
        raise ValueError("project_profile.technologies must be up to 8 supported labels")
    return {"product_type": product, "platform": platform, "operation": operation,
            "technologies": sorted(set(technologies))}


def _tokens(s):
    return set(re.findall(r"[a-z0-9]+", s.lower())) - STOPWORDS


def _incompatible(name, profile):
    """Conservatively block a skill strongly tied to another platform."""
    parts = _tokens(name.replace("-", " "))
    kind = profile["product_type"]
    # React Native uses a different UI/runtime contract than React DOM,
    # despite sharing the word "react" in its skill identifier.
    if "react" in parts and "native" in parts and kind not in {"mobile-app"}:
        return "REACT_NATIVE_SKILL_ON_NONMOBILE"
    if kind in {"mobile-app"} or profile["platform"] in {"android", "ios", "mobile-cross-platform"}:
        # React Native is mobile, but React DOM / Next.js is not.
        if (parts & WEB_MARKERS) and not (parts & MOBILE_MARKERS) and not (
            "react" in parts and "native" in parts
        ):
            return "WEB_ONLY_SKILL_ON_MOBILE"
    if kind in {"cli", "os-platform"} and (parts & WEB_MARKERS) and not parts & NATIVE_MARKERS:
        return "WEB_ONLY_SKILL_ON_SYSTEM_PROJECT"
    if kind == "game" and (parts & WEB_MARKERS) and not (parts & GAME_MARKERS):
        return "WEB_ONLY_SKILL_ON_GAME"
    if kind in {"website", "web-app"} and (parts & (MOBILE_MARKERS | GAME_MARKERS)) and not parts & WEB_MARKERS:
        return "NATIVE_ONLY_SKILL_ON_WEB"
    if kind == "data-automation" and (parts & WEB_MARKERS) and not parts & ML_MARKERS:
        return "WEB_ONLY_SKILL_ON_DATA_PROJECT"
    return None


def _allowed_bases(project_root, home):
    root = Path(project_root).resolve()
    h = Path(home).resolve() if home is not None else Path(
        os.getenv("ORBIT_UNIVERSAL_HOME") or Path.home()
    ).resolve()
    return [root / ".agents" / "skills", root / ".claude" / "skills",
            h / ".agents" / "skills", h / ".gemini" / "config" / "skills",
            h / ".claude" / "skills"]


def _host_location_mismatch(path, host):
    """A directory is only an installation *hint*, never host attestation."""
    if host == "unknown":
        return False
    p = Path(path)
    normalized = p.as_posix().lower()
    if "/.claude/skills/" in normalized:
        return host != "claude-code"
    if "/.gemini/config/skills/" in normalized:
        return host != "antigravity"
    # .agents/skills is a shared candidate. Actual IDE integration may vary.
    return False


def _digest_installed(item, allowed):
    """Return file identity only for a regular, bounded, unchanged skill file.

    The filesystem and skill metadata are not trusted; host must independently
    inspect the text and the actual permission/sandbox before loading it.
    """
    try:
        p = Path(item["path"])
        if p.name != "SKILL.md" or p.is_symlink() or p.parent.is_symlink():
            return None
        root = p.parent.parent
        if root.is_symlink() or not any(root == base for base in allowed):
            return None
        if not p.is_file() or not p.parent.is_dir():
            return None
        before = p.stat()
        if before.st_size > MAX_SKILL_BYTES or before.st_size < 1:
            return None
        # File race isn't an authorization mechanism. Recheck inode+size+mtime
        # and verify the pin again just before any future host activation.
        content = p.read_bytes()
        after = p.stat()
        if (before.st_ino, before.st_mtime_ns, before.st_size) != (
            after.st_ino, after.st_mtime_ns, after.st_size
        ) or len(content) != before.st_size:
            return None
        # Preserve only safe name, hash, and unverified provenance.
        return hashlib.sha256(content).hexdigest()
    except (KeyError, ValueError, OSError, RuntimeError, TypeError):
        return None


def _validate_requested(names):
    if names is None:
        return None
    if not isinstance(names, list) or len(names) > MAX_SELECTED or any(
        not isinstance(n, str) or not SKILL_NAME.fullmatch(n) for n in names
    ) or len(set(names)) != len(names):
        raise ValueError("requested_skill_names must be a unique list of up to 5 skill ids")
    return names


def _manifest_identity(project_root, objective, profile, host):
    payload = {"root": str(Path(project_root).resolve()), "objective": objective.strip(),
               "profile": profile, "declared_host": host}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _revalidate(expected, actual):
    if expected is None:
        return {"status": "NOT_REQUESTED", "host_activation_verified": False}
    if not isinstance(expected, dict) or set(expected) != {
        "format", "context_sha256", "skills"
    } or expected.get("format") != "orbit-skill-plan-v1":
        raise ValueError("review_manifest must be an Orbit v1 read-only skill manifest")
    digest = expected.get("context_sha256")
    refs = expected.get("skills")
    if not isinstance(digest, str) or not HEX_DIGEST.fullmatch(digest):
        raise ValueError("Invalid review_manifest context digest")
    if not isinstance(refs, list) or len(refs) > MAX_SELECTED:
        raise ValueError("Invalid review_manifest skill list")
    for ref in refs:
        if not isinstance(ref, dict) or set(ref) != {"name", "sha256"} or not (
            isinstance(ref["name"], str) and SKILL_NAME.fullmatch(ref["name"])
            and isinstance(ref["sha256"], str) and HEX_DIGEST.fullmatch(ref["sha256"])
        ):
            raise ValueError("Invalid review_manifest skill identity")
    if len({r["name"] for r in refs}) != len(refs):
        raise ValueError("Duplicate skill identity in review_manifest")
    if expected != actual:
        return {"status": "HOLD_CHANGED_OR_MISSING_SKILLS",
                "host_activation_verified": False,
                "next": "Inspect changed context, source and skill digests; obtain fresh permission and review."}
    return {"status": "PINS_MATCH_CURRENT_PREVIEW_ONLY",
            "host_activation_verified": False,
            "next": "Hashes match a read-only snapshot, not authorization, trust or live host activation."}


def preview(project_root, objective, available, *, project_profile=None,
            requested_skill_names=None, review_manifest=None, home=None,
            permission_state="UNKNOWN", host="unknown"):
    """Build a bounded project-scoped shortlist and inspectable pin manifest.

    No writes, model calls, network fetches, host config edits or executions.
    All returned fitness and provenance decisions require actual host review.
    """
    if not isinstance(objective, str) or not 1 <= len(objective.strip()) <= 1500:
        raise ValueError("objective must contain 1..1500 characters")
    if permission_state not in ("UNKNOWN", "APPROVED", "DENIED"):
        raise ValueError("Invalid permission_state")
    if not isinstance(host, str) or host not in HOSTS:
        raise ValueError("Unsupported host declaration")
    p = _profile(project_profile)
    requested = _validate_requested(requested_skill_names)
    if not isinstance(available, dict):
        raise ValueError("Invalid discovered capability inventory")
    installed = available.get("skills", [])
    if not isinstance(installed, list):
        raise ValueError("Invalid discovered skills inventory")
    allowed = _allowed_bases(project_root, home)
    words = _tokens(objective)
    techwords = set()
    for tech in p["technologies"]:
        techwords |= _tokens(tech.replace("-", " "))
    match_words = words | techwords
    records = {}
    duplicates = set()
    excluded = []
    for row in installed[:120]:
        if not isinstance(row, dict):
            continue
        name = row.get("name")
        if not isinstance(name, str) or not SKILL_NAME.fullmatch(name) or name == "orbit":
            continue
        if _host_location_mismatch(row.get("path", ""), host):
            if requested is not None and name in requested:
                excluded.append({"name": name, "reason": "SKILL_DIRECTORY_FOR_OTHER_HOST"})
            continue
        if name in records:
            duplicates.add(name)
            continue
        records[name] = row
    matches = []
    for name in sorted(records):
        if name in duplicates:
            excluded.append({"name": name, "reason": "DUPLICATE_IDENTITY_REQUIRES_REVIEW"})
            continue
        row = records[name]
        conflict = _incompatible(name, p)
        if conflict:
            if requested is not None and name in requested:
                excluded.append({"name": name, "reason": conflict})
            continue
        digest = _digest_installed(row, allowed)
        if digest is None:
            if requested is not None and name in requested:
                excluded.append({"name": name, "reason": "UNSAFE_OR_CHANGED_LOCAL_SKILL"})
            continue
        # Only untrusted metadata for discovery; never copy its instructions
        # into goals, model prompts or manifest claims.
        desc = row.get("description", "")
        raw = (name + " " + (desc[:MAX_DESCRIPTION_CHARS] if isinstance(desc, str) else ""))
        overlap = len(_tokens(raw) & match_words)
        exact = len(_tokens(name.replace("-", " ")) & techwords)
        score = overlap + 3 * exact
        if requested is None and score == 0:
            continue
        matches.append({"name": name, "sha256": digest, "match_score": score,
                        "source": "LOCAL_SKILL_UNVERIFIED", "license": "UNKNOWN_REVIEW_REQUIRED",
                        "license_claim_unverified": row.get("declared_license_unverified"),
                        "version_claim_unverified": row.get("declared_version_unverified"),
                        "host_compatibility": "DIRECTORY_CANDIDATE_NOT_VERIFIED",
                        "trust_review": "REQUIRED",
                        "reason": "DECLARED_STACK_AND_OBJECTIVE_OVERLAP" if score else "EXPLICITLY_REQUESTED_REVIEW"})
    matches.sort(key=lambda x: (-x["match_score"], x["name"]))
    if requested is not None:
        # The manifest is always in deterministic request order.
        chosen = [next((x for x in matches if x["name"] == name), None) for name in requested]
        chosen = [x for x in chosen if x is not None]
    else:
        chosen = matches[:MAX_SELECTED]
    missing = [name for name in (requested or []) if name not in {x["name"] for x in chosen}]
    pins = [{"name": x["name"], "sha256": x["sha256"]} for x in chosen]
    manifest = {"format": "orbit-skill-plan-v1",
                "context_sha256": _manifest_identity(project_root, objective, p, host),
                "skills": pins}
    checked = _revalidate(review_manifest, manifest)
    denied = permission_state == "DENIED"
    status = ("HOLD_PERMISSION_DENIED" if denied else
              "HOLD_REQUESTED_SKILLS_UNAVAILABLE" if missing else
              "SKILL_SHORTLIST_READY" if chosen else "NO_RELEVANT_INSTALLED_SKILLS")
    if checked["status"] == "HOLD_CHANGED_OR_MISSING_SKILLS":
        status = "HOLD_STALE_MANIFEST"
    return {
        "status": status, "mode": "READ_ONLY_SKILL_PLAN",
        "project_profile": p,
        "declared_host": host,
        "host_source": "CALLER_DECLARED_NOT_ATTESTED",
        "profile_source": "CALLER_DECLARED_NOT_CODEBASE_VERIFIED",
        "shortlist": chosen, "excluded_requested": excluded[:MAX_SELECTED],
        "missing_requested": missing, "duplicate_skill_ids": sorted(duplicates)[:12],
        "manifest": manifest, "revalidation": checked,
        "discovered_count": len(installed), "selected_count": len(chosen),
        "context_budget": {"max_selected": MAX_SELECTED,
                           "descriptions_not_loaded_as_instructions": True,
                           "full_skill_text_returned": False},
        "fallback": "Use built-in host tools and the existing Orbit specialist/task workflow.",
        "needs_license_review": bool(chosen), "needs_owner_approval": bool(chosen),
        "host_tool_verified": False, "permission_verified": False,
        "skill_content_trusted": False, "activation_allowed": False,
        "state_written": False, "skill_installed": False, "agent_spawned": False,
        "external_catalog_queried": False, "third_party_code_executed": False,
        "next": ("Permission was denied: do not activate or replace a skill/provider."
                 if denied else
                 "Review provenance, license, skill text, platform compatibility and owner/host permission; "
                 "recompute pins immediately before any separate host-controlled activation. "
                 "No installation, saved approval or automatic execution is offered by this preview."),
    }
