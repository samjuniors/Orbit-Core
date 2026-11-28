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

try:
    import orbit_windows_fs
except ImportError:  # pragma: no cover - packaged import guard
    orbit_windows_fs = None

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
MAX_TOTAL_ENTRIES = 20000
MAX_FILE_BYTES = 512 * 1024
MAX_TOTAL_BYTES = 16 * 1024 * 1024
MAX_FINDINGS = 100
MAX_LINES_PER_SIGNAL = 20
# Windows scans require the packaged Win32 handle-pinning adapter.
_WINDOWS_SAFE_RELATIVE_SCAN = (
    os.name != "nt" or (orbit_windows_fs is not None and orbit_windows_fs.WINDOWS_SAFE)
)


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
            "id": "SOURCE_PYTHON_PARSE_" + hashlib.sha256(rel.encode("utf-8", "surrogatepass")).hexdigest()[:10].upper(),
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
        path_hash = hashlib.sha256(rel.encode("utf-8", "surrogatepass")).hexdigest()[:10].upper()
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


def _scan_source_posix(root: Path) -> dict:
    """Audit POSIX source through a pinned root and descriptor-relative opens."""
    import orbit_posix_fs

    if not orbit_posix_fs.SAFE:
        raise ValueError("Descriptor-relative POSIX source audit is unavailable")
    root = Path(root)
    if not root.is_absolute() or ".." in root.parts:
        raise ValueError("Project root must be an absolute normalized directory")
    root_fd = orbit_posix_fs.open_root(root)
    root_identity = hashlib.sha256(str(root).encode("utf-8", "surrogatepass")).hexdigest()[:16]
    if root == Path(root.anchor) or root == Path.home().resolve():
        os.close(root_fd)
        raise ValueError("Select a specific project directory")

    digest = hashlib.sha256()
    languages = Counter()
    unreadable = []
    findings = []
    skipped_symlinks = 0
    truncated = False
    files_read = total_bytes = python_files = python_parsed = test_files = todo_count = 0
    stack = [((), 0)]
    entries_seen = 0
    try:
        while stack:
            parts, depth = stack.pop()
            directory_fd = os.dup(root_fd)
            try:
                for component in parts:
                    child_fd = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                                       | getattr(os, "O_CLOEXEC", 0), dir_fd=directory_fd)
                    os.close(directory_fd)
                    directory_fd = child_fd
                try:
                    with os.scandir(directory_fd) as iterator:
                        entries = list(islice(iterator, MAX_ENTRIES_PER_DIR + 1))
                    if len(entries) > MAX_ENTRIES_PER_DIR:
                        truncated = True
                    remaining_entries = max(0, MAX_TOTAL_ENTRIES - entries_seen)
                    entries_seen += len(entries)
                    if entries_seen > MAX_TOTAL_ENTRIES:
                        truncated = True
                        entries = entries[:remaining_entries]
                    names = sorted((entry.name for entry in entries), key=str.casefold)
                except OSError:
                    unreadable.append("/".join(parts) or ".")
                    continue

                child_dirs = []
                for name in names:
                    try:
                        info = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                    except OSError:
                        unreadable.append("/".join(parts + (name,)))
                        continue
                    relative = "/".join(parts + (name,))
                    if stat.S_ISLNK(info.st_mode):
                        skipped_symlinks += 1
                        continue
                    if stat.S_ISDIR(info.st_mode):
                        low_name = name.casefold()
                        if (low_name in SKIP_DIRS or low_name in SENSITIVE_DIRS
                                or name.startswith(".")):
                            continue
                        if depth >= MAX_DEPTH:
                            truncated = True
                            continue
                        try:
                            child_fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
                                               | getattr(os, "O_CLOEXEC", 0), dir_fd=directory_fd)
                            try:
                                if not stat.S_ISDIR(os.fstat(child_fd).st_mode):
                                    unreadable.append(relative)
                                    continue
                            finally:
                                os.close(child_fd)
                            child_dirs.append((parts + (name,), depth + 1))
                        except OSError:
                            unreadable.append(relative)
                        continue
                    if not stat.S_ISREG(info.st_mode):
                        continue
                    suffix = Path(name).suffix.casefold()
                    if suffix not in SOURCE_SUFFIXES or not _safe_name(name):
                        continue
                    if any(part.casefold() in SENSITIVE_DIRS for part in parts):
                        continue
                    try:
                        flags = (os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0)
                                 | getattr(os, "O_NOCTTY", 0) | getattr(os, "O_CLOEXEC", 0))
                        fd = os.open(name, flags, dir_fd=directory_fd)
                        with os.fdopen(fd, "rb") as handle:
                            actual = os.fstat(handle.fileno())
                            if (not stat.S_ISREG(actual.st_mode) or actual.st_nlink != 1
                                    or actual.st_size != info.st_size):
                                unreadable.append(relative)
                                continue
                            if actual.st_size > MAX_FILE_BYTES:
                                unreadable.append(relative)
                                truncated = True
                                continue
                            if total_bytes + actual.st_size > MAX_TOTAL_BYTES:
                                truncated = True
                                break
                            raw = handle.read(MAX_FILE_BYTES + 1)
                            after = os.fstat(handle.fileno())
                            if (len(raw) != actual.st_size or len(raw) > MAX_FILE_BYTES
                                    or (after.st_size, after.st_mtime_ns, after.st_ctime_ns, after.st_nlink)
                                    != (actual.st_size, actual.st_mtime_ns, actual.st_ctime_ns, 1)):
                                unreadable.append(relative)
                                truncated = True
                                continue
                    except OSError:
                        unreadable.append(relative)
                        continue
                    try:
                        text = raw.decode("utf-8")
                    except UnicodeDecodeError:
                        unreadable.append(relative)
                        continue

                    encoded_path = relative.encode("utf-8", "surrogatepass")
                    digest.update(len(encoded_path).to_bytes(4, "big"))
                    digest.update(encoded_path)
                    digest.update(len(raw).to_bytes(8, "big"))
                    digest.update(hashlib.sha256(raw).digest())
                    total_bytes += len(raw)
                    files_read += 1
                    languages[suffix] += 1
                    name_low = name.casefold()
                    if (any(part.casefold() in {"test", "tests", "spec", "specs", "__tests__"}
                            for part in parts)
                            or name_low.startswith(("test_", "tests_"))
                            or name_low.endswith((".test.js", ".test.ts", ".spec.js", ".spec.ts", "_test.go", "_test.py"))):
                        test_files += 1
                    todo_count += len(re.findall(r"\b(?:TODO|FIXME|HACK)\b", text, flags=re.IGNORECASE))
                    if suffix in {".py", ".pyi"}:
                        python_files += 1
                        file_findings, parsed = _python_signals(text, relative)
                        python_parsed += parsed
                        for item in file_findings:
                            if len(findings) < MAX_FINDINGS:
                                findings.append(item)
                            else:
                                truncated = True
                    if files_read >= MAX_FILES:
                        truncated = True
                        break
                if files_read >= MAX_FILES:
                    break
                stack.extend(reversed(child_dirs))
            except OSError:
                unreadable.append("/".join(parts) or ".")
            finally:
                os.close(directory_fd)
            if files_read >= MAX_FILES:
                stack.clear()
                break
    finally:
        os.close(root_fd)

    return {
        "status": "SCANNED" if not truncated and not unreadable else "INCOMPLETE",
        "audit_scope": "SOURCE",
        "scan_mode": "BOUNDED_DESCRIPTOR_RELATIVE_POSIX_SOURCE_CONTENT_ANALYSIS",
        "root_identity": root_identity,
        "inventory_snapshot_sha256": digest.hexdigest(),
        "snapshot_semantics": "SHA256 over repository-relative source paths, byte lengths and per-file content SHA256; not a Git revision.",
        "limits": {"max_files": MAX_FILES, "max_depth": MAX_DEPTH,
                   "max_entries_per_directory": MAX_ENTRIES_PER_DIR,
                   "max_total_entries": MAX_TOTAL_ENTRIES,
                   "max_file_bytes": MAX_FILE_BYTES, "max_total_bytes": MAX_TOTAL_BYTES,
                   "max_findings": MAX_FINDINGS},
        "truncated": truncated,
        "unreadable_paths": unreadable[:30],
        "symlinks_skipped": skipped_symlinks,
        "summary": {"source_files": files_read, "source_bytes_read": total_bytes,
                    "python_files": python_files, "python_files_parsed": python_parsed,
                    "test_files": test_files, "todo_markers": todo_count,
                    "languages_by_extension": dict(sorted(languages.items()))},
        "findings": findings, "findings_count": len(findings),
        "audit_scope_description": "Deterministic static review leads only. No semantic architecture proof, dependency advisory scan, runtime test, exploitability determination or vulnerability certification.",
        "data_written": False, "source_contents_read": files_read > 0,
        "source_contents_returned": False, "source_contents_persisted": False,
        "project_scripts_executed": False, "project_files_written": False,
        "external_network_access": False,
    }


def scan_source(root: Path) -> dict:
    """Read bounded source files and emit content-hash-backed static review leads."""
    root = Path(root)
    if os.name != "nt":
        return _scan_source_posix(root)
    if not root.is_absolute():
        raise ValueError("Project root must be an absolute directory")
    if not _WINDOWS_SAFE_RELATIVE_SCAN:
        # Fail closed on Windows until traversal and file opens are relative to
        # verified directory handles. O_NOFOLLOW on the leaf does not protect
        # intermediate junction/reparse-point components from replacement.
        return {
            "status": "INCOMPLETE",
            "audit_scope": "SOURCE",
            "scan_mode": "BLOCKED_UNSAFE_WINDOWS_PATH_TRAVERSAL",
            "root_identity": hashlib.sha256(str(root).encode("utf-8", "surrogatepass")).hexdigest()[:16],
            "inventory_snapshot_sha256": None,
            "snapshot_semantics": "No source files were opened; no snapshot was produced.",
            "limits": {
                "max_files": MAX_FILES, "max_depth": MAX_DEPTH,
                "max_entries_per_directory": MAX_ENTRIES_PER_DIR,
                "max_file_bytes": MAX_FILE_BYTES, "max_total_bytes": MAX_TOTAL_BYTES,
                "max_findings": MAX_FINDINGS,
            },
            "truncated": True,
            "unreadable_paths": [],
            "symlinks_skipped": 0,
            "summary": {
                "source_files": 0, "source_bytes_read": 0,
                "python_files": 0, "python_files_parsed": 0,
                "test_files": 0, "todo_markers": 0,
                "languages_by_extension": {},
            },
            "findings": [], "findings_count": 0,
            "audit_scope_description": "Source audit is blocked on Windows until handle-relative reparse-safe traversal is implemented. No source content was read.",
            "scan_block_reason": "WINDOWS_REPARSE_POINT_SAFE_RELATIVE_OPEN_UNAVAILABLE",
            "data_written": False, "source_contents_read": False,
            "source_contents_returned": False, "source_contents_persisted": False,
            "project_scripts_executed": False, "project_files_written": False,
            "external_network_access": False,
        }
    pins = None
    if os.name == "nt" and _WINDOWS_SAFE_RELATIVE_SCAN:
        pins = orbit_windows_fs.pin_directory_chain(root)
        root = pins.root_path
    else:
        if root.is_symlink() or not root.is_dir():
            raise ValueError("Project root must be an absolute, existing non-symlink directory")
        root = root.resolve(strict=True)
    if root == Path(root.anchor) or root == Path.home().resolve():
        if pins is not None:
            pins.close()
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
                        child = Path(entry.path)
                        try:
                            if pins is not None:
                                pins.pin(child)
                            stack.append((child, depth + 1))
                        except OSError:
                            unreadable.append(child.relative_to(root).as_posix())
                elif entry.is_file(follow_symlinks=False):
                    suffix = Path(entry.name).suffix.casefold()
                    if suffix not in SOURCE_SUFFIXES or not _safe_name(entry.name):
                        continue
                    if any(part.casefold() in SENSITIVE_DIRS for part in Path(entry.path).relative_to(root).parts[:-1]):
                        continue
                    try:
                        if pins is not None:
                            fd = orbit_windows_fs.open_regular_file_fd(entry.path)
                            try:
                                info = os.fstat(fd)
                            finally:
                                os.close(fd)
                        else:
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
            if pins is not None:
                fd = orbit_windows_fs.open_regular_file_fd(path)
            else:
                flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
                fd = os.open(str(path), flags)
            with os.fdopen(fd, "rb") as handle:
                actual = os.fstat(handle.fileno())
                if not stat.S_ISREG(actual.st_mode):
                    unreadable.append(rel)
                    continue
                # Windows file identity fields (st_dev/st_ino) are not
                # consistently comparable between DirEntry.stat() and fstat().
                # Size is checked against discovery metadata; mtime is checked
                # on the same open handle before/after the bounded read.
                if actual.st_size != observed.st_size:
                    unreadable.append(rel)
                    continue
                if total_bytes + actual.st_size > MAX_TOTAL_BYTES:
                    truncated = True
                    stack.clear()
                    break
                raw = handle.read(MAX_FILE_BYTES + 1)
                after = os.fstat(handle.fileno())
                if (len(raw) > MAX_FILE_BYTES or len(raw) != actual.st_size
                        or (after.st_size, after.st_mtime_ns) != (actual.st_size, actual.st_mtime_ns)):
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
        "root_identity": hashlib.sha256(str(root).encode("utf-8", "surrogatepass")).hexdigest()[:16],
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
