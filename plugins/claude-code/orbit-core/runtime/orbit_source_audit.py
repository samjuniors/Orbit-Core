"""Bounded, read-only source inspection with explicit caller consent.

Reads selected source files for deterministic static signals. Never executes
project code, returns raw source, writes project files, or accesses the network.
"""
from __future__ import annotations

import ast
import hashlib
import os
import re
import stat
import sys
from collections import Counter
from itertools import islice
from pathlib import Path

SOURCE_SUFFIXES = {
    ".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
    ".vue", ".svelte", ".go", ".rs", ".java", ".kt", ".kts", ".swift",
    ".dart", ".php", ".rb", ".scala", ".cs", ".fs", ".c", ".h", ".cc",
    ".cpp", ".hpp", ".sql", ".sh", ".ps1",
}
SKIP_DIRS = {
    ".git", ".hg", ".svn", ".orbit", ".venv", "venv", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", "node_modules",
    "vendor", "dist", "build", "coverage", ".next", ".nuxt", ".svelte-kit",
    ".turbo", ".cache", ".gradle", ".idea", ".dart_tool", "target", "Pods",
}
SENSITIVE_DIRS = {"secrets", "credentials", "private", "certs", "certificates"}
SENSITIVE_NAMES = {
    ".env", ".env.local", ".npmrc", ".pypirc", "credentials", "credentials.json",
    "secrets", "secrets.json", "id_rsa", "id_ed25519",
}
SENSITIVE_SUFFIXES = {".pem", ".key", ".p12", ".pfx", ".jks", ".sqlite", ".db"}
MAX_FILES = 1200
MAX_DEPTH = 14
MAX_ENTRIES_PER_DIR = 4000
MAX_FILE_BYTES = 512 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
MAX_FINDINGS = 100
MAX_LINES_PER_SIGNAL = 20


def _safe_name(name: str) -> bool:
    low = name.casefold()
    return (
        low not in SENSITIVE_NAMES
        and not low.startswith(".env.")
        and Path(low).suffix not in SENSITIVE_SUFFIXES
    )


def _call_name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = _call_name(node.value)
        return (prefix + "." if prefix else "") + node.attr
    return ""


def _is_true(node):
    return isinstance(node, ast.Constant) and node.value is True


def _python_signals(text, rel):
    findings = []
    try:
        tree = ast.parse(text, filename=rel)
    except (SyntaxError, ValueError, RecursionError) as exc:
        line = getattr(exc, 'lineno', None) or 0
        findings.append({
            "id": "SOURCE_PYTHON_PARSE_" + hashlib.sha256(rel.encode("utf-8")).hexdigest()[:10].upper(),
            "category": "verification",
            "severity": "LOW",
            "confidence": "LOW",
            "status": "REVIEW_REQUIRED",
            "summary": f"Python parser ({sys.version_info.major}.{sys.version_info.minor}) could not parse this file at line {line}; confirm the project's target Python version and source validity.",
            "evidence": [rel],
            "recommendation": "Inspect the indicated line using the project's declared Python target; parser-version mismatch is possible.",
            "is_confirmed_defect": False,
        })
        return findings, 0

    hits = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = _call_name(node.func)
        rule = None
        description = ""
        if name in {"eval", "exec", "compile"}:
            rule = "DYNAMIC_CODE"
            description = "Dynamic code evaluation/compilation call"
        elif name == "os.system":
            rule = "OS_SYSTEM"
            description = "Operating-system command execution call"
        elif name.startswith("subprocess.") and any(
            keyword.arg == "shell" and _is_true(keyword.value)
            for keyword in node.keywords
        ):
            rule = "SUBPROCESS_SHELL_TRUE"
            description = "Subprocess call enables shell=True"
        elif name in {"pickle.load", "pickle.loads"}:
            rule = "PICKLE_DESERIALIZATION"
            description = "Pickle deserialization call; input trust boundary is not established"
        elif name == "yaml.load":
            loader = next((keyword.value for keyword in node.keywords if keyword.arg == "Loader"), None)
            loader_name = _call_name(loader) if loader is not None else ""
            if loader_name.rsplit(".", 1)[-1] not in {"SafeLoader", "CSafeLoader"}:
                rule = "YAML_LOADER"
                description = "yaml.load call does not visibly select a safe loader"
        if rule:
            hits.setdefault(rule, {"description": description, "lines": []})["lines"].append(
                getattr(node, "lineno", 0)
            )

    findings = []
    for rule, hit in sorted(hits.items()):
        lines = sorted(set(hit["lines"]))[:MAX_LINES_PER_SIGNAL]
        path_hash = hashlib.sha256(rel.encode("utf-8")).hexdigest()[:10].upper()
        confidence = "MEDIUM" if rule in {"SUBPROCESS_SHELL_TRUE", "YAML_LOADER"} else "LOW"
        findings.append({
            "id": f"SOURCE_{rule}_{path_hash}",
            "category": "security",
            "severity": "MEDIUM",
            "confidence": confidence,
            "status": "REVIEW_REQUIRED",
            "summary": f"{hit['description']} found at line(s) {', '.join(map(str, lines))}. Static presence alone does not establish exploitability.",
            "evidence": [rel],
            "recommendation": "Review the call site, data provenance, validation and intended behavior before classifying risk.",
            "is_confirmed_defect": False,
        })
    return findings, 1


def scan_source(root: Path) -> dict:
    """Read bounded source files and emit content-hash-backed static review leads."""
    root = Path(root)
    if root.is_symlink() or not root.is_absolute() or not root.is_dir():
        raise ValueError("Project root must be an absolute, existing non-symlink directory")
    root = root.resolve(strict=True)
    if root == Path(root.anchor) or root == Path.home().resolve():
        raise ValueError("Select a specific project directory")

    candidates = []
    unreadable = []
    skipped_symlinks = 0
    truncated = False
    stack = [(root, 0)]
    while stack:
        folder, depth = stack.pop()
        try:
            with os.scandir(folder) as iterator:
                entries = list(islice(iterator, MAX_ENTRIES_PER_DIR + 1))
                if len(entries) > MAX_ENTRIES_PER_DIR:
                    truncated = True
                entries.sort(key=lambda entry: entry.name.casefold())
        except OSError:
            unreadable.append(folder.relative_to(root).as_posix() or ".")
            continue
        for entry in entries:
            if entry.is_symlink():
                skipped_symlinks += 1
                continue
            try:
                if entry.is_dir(follow_symlinks=False):
                    low_name = entry.name.casefold()
                    if low_name in SKIP_DIRS or low_name in SENSITIVE_DIRS:
                        continue
                    if entry.name.startswith("."):
                        continue
                    if depth >= MAX_DEPTH:
                        truncated = True
                    else:
                        stack.append((Path(entry.path), depth + 1))
                elif entry.is_file(follow_symlinks=False):
                    suffix = Path(entry.name).suffix.casefold()
                    if suffix not in SOURCE_SUFFIXES or not _safe_name(entry.name):
                        continue
                    if any(part.casefold() in SENSITIVE_DIRS for part in Path(entry.path).relative_to(root).parts[:-1]):
                        continue
                    try:
                        info = entry.stat(follow_symlinks=False)
                    except OSError:
                        unreadable.append(Path(entry.path).relative_to(root).as_posix())
                        continue
                    if info.st_size > MAX_FILE_BYTES:
                        unreadable.append(Path(entry.path).relative_to(root).as_posix())
                        truncated = True
                        continue
                    if len(candidates) >= MAX_FILES:
                        truncated = True
                        stack.clear()
                        break
                    candidates.append((Path(entry.path), info))
            except OSError:
                unreadable.append(Path(entry.path).relative_to(root).as_posix())

    candidates.sort(key=lambda pair: pair[0].relative_to(root).as_posix().casefold())
    digest = hashlib.sha256()
    languages = Counter()
    test_files = 0
    python_files = 0
    python_parsed = 0
    todo_count = 0
    total_bytes = 0
    files_read = 0
    findings = []
    findings_truncated = False

    for path, observed in candidates:
        rel = path.relative_to(root).as_posix()
        try:
            flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(str(path), flags)
            with os.fdopen(fd, "rb") as handle:
                actual = os.fstat(handle.fileno())
                if not stat.S_ISREG(actual.st_mode):
                    unreadable.append(rel)
                    continue
                if (actual.st_dev, actual.st_ino, actual.st_size, actual.st_mtime_ns) != (
                    observed.st_dev, observed.st_ino, observed.st_size, observed.st_mtime_ns
                ):
                    unreadable.append(rel)
                    continue
                if total_bytes + actual.st_size > MAX_TOTAL_BYTES:
                    truncated = True
                    break
                raw = handle.read(MAX_FILE_BYTES + 1)
                if len(raw) > MAX_FILE_BYTES or len(raw) != actual.st_size:
                    unreadable.append(rel)
                    truncated = True
                    continue
        except OSError:
            unreadable.append(rel)
            continue

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            unreadable.append(rel)
            continue

        content_hash = hashlib.sha256(raw).digest()
        encoded_path = rel.encode("utf-8", "surrogatepass")
        digest.update(len(encoded_path).to_bytes(4, "big"))
        digest.update(encoded_path)
        digest.update(len(raw).to_bytes(8, "big"))
        digest.update(content_hash)
        total_bytes += len(raw)
        files_read += 1
        suffix = path.suffix.casefold()
        languages[suffix] += 1
        parts = {part.casefold() for part in Path(rel).parts[:-1]}
        name = path.name.casefold()
        if parts & {"test", "tests", "spec", "specs", "__tests__"} or name.startswith(("test_", "tests_")) or name.endswith((".test.js", ".test.ts", ".spec.js", ".spec.ts", "_test.go", "_test.py")):
            test_files += 1
        todo_count += len(re.findall(r"\b(?:TODO|FIXME|HACK)\b", text, flags=re.IGNORECASE))

        if suffix in {".py", ".pyi"}:
            python_files += 1
            file_findings, parsed = _python_signals(text, rel)
            python_parsed += parsed
            for item in file_findings:
                if len(findings) < MAX_FINDINGS:
                    findings.append(item)
                else:
                    findings_truncated = True

    truncated = truncated or findings_truncated
    complete = not truncated and not unreadable
    return {
        "status": "SCANNED" if complete else "INCOMPLETE",
        "audit_scope": "SOURCE",
        "scan_mode": "BOUNDED_READ_ONLY_SOURCE_CONTENT_ANALYSIS",
        "root_identity": hashlib.sha256(str(root).encode("utf-8")).hexdigest()[:16],
        "inventory_snapshot_sha256": digest.hexdigest(),
        "snapshot_semantics": "SHA256 over repository-relative source paths, byte lengths and per-file content SHA256; not a Git revision.",
        "limits": {
            "max_files": MAX_FILES,
            "max_depth": MAX_DEPTH,
            "max_entries_per_directory": MAX_ENTRIES_PER_DIR,
            "max_file_bytes": MAX_FILE_BYTES,
            "max_total_bytes": MAX_TOTAL_BYTES,
            "max_findings": MAX_FINDINGS,
        },
        "truncated": truncated,
        "unreadable_paths": unreadable[:30],
        "symlinks_skipped": skipped_symlinks,
        "summary": {
            "source_files": files_read,
            "source_bytes_read": total_bytes,
            "python_files": python_files,
            "python_files_parsed": python_parsed,
            "test_files": test_files,
            "todo_markers": todo_count,
            "languages_by_extension": dict(sorted(languages.items())),
        },
        "findings": findings,
        "findings_count": len(findings),
        "audit_scope_description": "Deterministic static review leads only. No semantic architecture proof, dependency advisory scan, runtime test, exploitability determination or vulnerability certification.",
        "data_written": False,
        "source_contents_read": files_read > 0,
        "source_contents_returned": False,
        "source_contents_persisted": False,
        "project_scripts_executed": False,
        "project_files_written": False,
        "external_network_access": False,
    }
