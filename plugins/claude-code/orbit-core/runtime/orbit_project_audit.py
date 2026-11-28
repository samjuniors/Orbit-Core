"""Bounded, read-only structural project inventory and gap signals.

This module inspects names and filesystem metadata only. It does not read source
contents, execute project scripts, follow symlinks, modify files, or certify
semantic/security correctness. Findings are review leads, not verified defects.
"""
from __future__ import annotations

import hashlib
import os
from itertools import islice
from collections import Counter
from pathlib import Path

try:
    import orbit_windows_fs
except ImportError:  # pragma: no cover - packaged import guard
    orbit_windows_fs = None

SKIP_DIRS = {
    ".git", ".hg", ".svn", ".orbit", ".venv", "venv", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", ".nox",
    "node_modules", "vendor", "dist", "build", "coverage", ".next",
    ".nuxt", ".svelte-kit", ".turbo", ".cache", ".idea", ".vscode",
    ".gradle", ".dart_tool", ".expo", "target", "Pods",
}
SOURCE_SUFFIXES = {
    ".py", ".pyi", ".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx",
    ".vue", ".svelte", ".go", ".rs", ".java", ".kt", ".kts",
    ".swift", ".dart", ".php", ".rb", ".scala", ".cs", ".fs",
    ".c", ".h", ".cc", ".cpp", ".hpp", ".sql", ".sh", ".ps1",
}
MANIFESTS = {
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt",
    "package.json", "cargo.toml", "go.mod", "pom.xml", "build.gradle",
    "build.gradle.kts", "gemfile", "composer.json", "pubspec.yaml",
    "mix.exs", "deno.json", "deno.jsonc", "makefile",
}
LOCKFILES = {
    "poetry.lock", "uv.lock", "pdm.lock", "package-lock.json",
    "pnpm-lock.yaml", "yarn.lock", "cargo.lock", "go.sum",
    "composer.lock", "gemfile.lock", "pubspec.lock",
}
README_NAMES = {"readme", "readme.md", "readme.rst", "readme.txt"}
ARCH_DOCS = {"architecture.md", "system-design.md", "design.md"}
SECURITY_DOCS = {"security.md", "threat-model.md", "security-policy.md"}
TEST_DIRS = {"test", "tests", "spec", "specs", "__tests__"}
CI_MARKERS = {".github/workflows", ".gitlab-ci.yml", ".circleci", "azure-pipelines.yml", "Jenkinsfile"}
MAX_FILES = 2500
MAX_DIRECTORIES = 600
MAX_DEPTH = 14
# Windows scans are enabled only when the handle-pinning Win32 adapter is packaged.
_WINDOWS_SAFE_RELATIVE_SCAN = (
    os.name != "nt" or (orbit_windows_fs is not None and orbit_windows_fs.WINDOWS_SAFE)
)


def _blocked_windows_scan(root: Path) -> dict:
    """Return an explicit no-traversal result until handle-relative scan exists."""
    return {
        "status": "INCOMPLETE",
        "scan_mode": "BLOCKED_UNSAFE_WINDOWS_PATH_TRAVERSAL",
        "root_identity": hashlib.sha256(
            str(root).encode("utf-8", "surrogatepass")
        ).hexdigest()[:16],
        "inventory_snapshot_sha256": None,
        "snapshot_semantics": (
            "No directory entries were opened; no project inventory snapshot was produced."
        ),
        "limits": {
            "max_files": MAX_FILES,
            "max_directories": MAX_DIRECTORIES,
            "max_depth": MAX_DEPTH,
        },
        "truncated": True,
        "unreadable_paths": [],
        "symlinks_skipped": 0,
        "summary": {
            "files": 0,
            "directories": 0,
            "source_files": 0,
            "test_files": 0,
            "test_directories": 0,
            "languages_by_extension": {},
        },
        "discovered": {
            "readmes": [],
            "architecture_docs": [],
            "security_docs": [],
            "test_files": [],
            "test_directories": [],
            "dependency_manifests": [],
            "dependency_lockfiles": [],
            "ci_markers": [],
        },
        "findings": [],
        "findings_count": 0,
        "audit_scope": (
            "Structural metadata scan blocked on Windows until handle-relative, "
            "reparse-safe directory traversal is implemented. No directory entries "
            "were read."
        ),
        "scan_block_reason": "WINDOWS_REPARSE_POINT_SAFE_RELATIVE_OPEN_UNAVAILABLE",
        "next": (
            "Use host-native project inspection for now; do not treat this result "
            "as an empty project."
        ),
        "data_written": False,
        "project_scripts_executed": False,
        "source_contents_read": False,
    }


def _is_test_file(rel: str, name: str) -> bool:
    low = name.lower()
    parts = {part.lower() for part in Path(rel).parts[:-1]}
    return (
        bool(parts & TEST_DIRS)
        or low.startswith(("test_", "tests_"))
        or low.endswith(("_test.py", "_test.go", ".test.js", ".test.jsx",
                         ".test.ts", ".test.tsx", ".spec.js", ".spec.ts",
                         ".spec.tsx", "_spec.rb"))
    )


def _scan_posix_inventory(root):
    """Inventory POSIX projects through pinned directory descriptors."""
    import orbit_specialists
    skipped = [0]
    unreadable = []
    files = []
    directories = []
    truncated = False
    walk_truncated = [False]
    for parts, dir_fd, dirs, names in orbit_specialists._visual_walk(
            root, skipped=skipped, unreadable=unreadable, truncated=walk_truncated):
        depth = len(parts)
        dirs[:] = sorted((name for name in dirs if name.casefold() not in SKIP_DIRS),
                         key=str.casefold)
        names = sorted(names, key=str.casefold)
        if len(dirs) + len(names) > MAX_FILES + MAX_DIRECTORIES:
            truncated = True
        if depth >= MAX_DEPTH:
            if dirs:
                truncated = True
            dirs[:] = []
        for name in dirs:
            if len(directories) >= MAX_DIRECTORIES:
                truncated = True
                dirs[:] = []
                break
            directories.append("/".join(parts + (name,)))
        for name in names:
            if len(files) >= MAX_FILES:
                truncated = True
                dirs[:] = []
                break
            relative = "/".join(parts + (name,))
            try:
                stream, info = orbit_specialists._open_visual_source(dir_fd, name)
                stream.close()
                if info.st_nlink != 1:
                    unreadable.append(relative)
                    continue
            except OSError:
                unreadable.append(relative)
                continue
            files.append({"path": relative, "name": name, "size": info.st_size,
                          "mtime_ns": info.st_mtime_ns,
                          "suffix": Path(name).suffix.lower()})
    return files, directories, skipped[0], unreadable, truncated or walk_truncated[0]


def scan_project(root: Path, profile: dict | None = None) -> dict:
    """Return a bounded inventory and conservative structural gap signals."""
    root = Path(root)
    if not root.is_absolute():
        raise ValueError("Project root must be an absolute directory")
    pins = None
    if os.name == "nt" and _WINDOWS_SAFE_RELATIVE_SCAN:
        pins = orbit_windows_fs.pin_directory_chain(root)
        # All resolved ancestors, including the volume/share root, remain
        # pinned for the complete traversal. Descendant path opens cannot be
        # redirected by replacing a parent component.
        root = pins.root_path
    else:
        if root.is_symlink() or not root.is_dir():
            raise ValueError("Project root must be an absolute, existing non-symlink directory")
        root = root.resolve(strict=True)
    if root == Path(root.anchor) or root == Path.home().resolve():
        if pins is not None:
            pins.close()
        raise ValueError("Select a specific project directory")
    if not _WINDOWS_SAFE_RELATIVE_SCAN:
        return _blocked_windows_scan(root)

    if os.name != "nt":
        files, directories, skipped_symlinks, unreadable, truncated = _scan_posix_inventory(root)
        stack = []
    else:
        files = []
        directories = []
        skipped_symlinks = 0
        unreadable = []
        truncated = False
        stack = [(root, 0)]
    while stack:
        folder, depth = stack.pop()
        try:
            with os.scandir(folder) as iterator:
                entries = sorted(islice(iterator, MAX_FILES + MAX_DIRECTORIES + 1), key=lambda entry: entry.name.casefold())
                if len(entries) >= MAX_FILES + MAX_DIRECTORIES + 1:
                    truncated = True
        except OSError:
            unreadable.append(folder.relative_to(root).as_posix() or ".")
            continue
        for entry in entries:
            if entry.is_symlink():
                skipped_symlinks += 1
                continue
            try:
                if entry.is_dir(follow_symlinks=False):
                    if entry.name in SKIP_DIRS:
                        continue
                    if len(directories) >= MAX_DIRECTORIES:
                        truncated = True
                        continue
                    rel = Path(entry.path).relative_to(root).as_posix()
                    directories.append(rel)
                    if depth < MAX_DEPTH:
                        child = Path(entry.path)
                        try:
                            if pins is not None:
                                pins.pin(child)
                            stack.append((child, depth + 1))
                        except OSError:
                            unreadable.append(child.relative_to(root).as_posix())
                    else:
                        truncated = True
                elif entry.is_file(follow_symlinks=False):
                    rel = Path(entry.path).relative_to(root).as_posix()
                    try:
                        if pins is not None:
                            fd = orbit_windows_fs.open_regular_file_fd(entry.path)
                            try:
                                stat = os.fstat(fd)
                            finally:
                                os.close(fd)
                        else:
                            stat = entry.stat(follow_symlinks=False)
                    except OSError:
                        unreadable.append(rel)
                        continue
                    files.append({
                        "path": rel,
                        "name": entry.name,
                        "size": stat.st_size,
                        "mtime_ns": stat.st_mtime_ns,
                        "suffix": Path(entry.name).suffix.lower(),
                    })
                    if len(files) >= MAX_FILES:
                        truncated = True
                        stack.clear()
                        break
            except OSError:
                unreadable.append(Path(entry.path).relative_to(root).as_posix())

    files.sort(key=lambda item: item["path"].casefold())
    directories.sort(key=str.casefold)
    by_name = {item["name"].casefold(): item["path"] for item in files}
    by_path = {item["path"].casefold(): item["path"] for item in files}
    source_files = [item for item in files if item["suffix"] in SOURCE_SUFFIXES]
    languages = Counter(item["suffix"] for item in source_files)
    manifests = [item["path"] for item in files if item["name"].casefold() in MANIFESTS]
    lockfiles = [item["path"] for item in files if item["name"].casefold() in LOCKFILES]
    readmes = [item["path"] for item in files if item["name"].casefold() in README_NAMES]
    architecture_docs = [item["path"] for item in files if item["name"].casefold() in ARCH_DOCS]
    security_docs = [item["path"] for item in files if item["name"].casefold() in SECURITY_DOCS]
    test_files = [item["path"] for item in files if _is_test_file(item["path"], item["name"])]
    test_dirs = [path for path in directories if Path(path).name.casefold() in TEST_DIRS]
    directory_keys = {path.casefold() for path in directories}
    workflows = [path for path in CI_MARKERS if path.casefold() in directory_keys or path.casefold() in by_path or path.casefold() in by_name]

    digest = hashlib.sha256()
    for item in files:
        rel = item["path"].encode("utf-8", "surrogatepass")
        digest.update(len(rel).to_bytes(4, "big"))
        digest.update(rel)
        digest.update(item["size"].to_bytes(8, "big"))
        digest.update(item["mtime_ns"].to_bytes(8, "big", signed=True))
    # Directories drive findings too (e.g. an empty tests/), so they are part of
    # the snapshot; the "D" marker keeps them distinct from file records.
    for path in directories:
        rel = path.encode("utf-8", "surrogatepass")
        digest.update(b"D" + len(rel).to_bytes(4, "big"))
        digest.update(rel)
    snapshot = digest.hexdigest()

    findings = []

    def finding(code, category, severity, confidence, summary, evidence, recommendation):
        findings.append({
            "id": code,
            "category": category,
            "severity": severity,
            "confidence": confidence,
            "status": "REVIEW_REQUIRED",
            "summary": summary,
            "evidence": evidence,
            "recommendation": recommendation,
            "is_confirmed_defect": False,
        })

    complete = not truncated and not unreadable
    if not readmes and complete:
        finding("DOCS_README_NOT_FOUND", "documentation", "LOW", "HIGH",
                "No common README filename was found in the scanned project tree.",
                [], "Confirm whether an existing product overview lives under a non-standard name; add or index one if absent.")
    if source_files and not (test_files or test_dirs) and complete:
        finding("TEST_STRUCTURE_NOT_DISCOVERED", "testing", "MEDIUM", "MEDIUM",
                "Source files were discovered, but no conventional test directory or test filename pattern was found.",
                [item["path"] for item in source_files[:8]],
                "Inspect the project's actual test strategy and CI before concluding tests are missing.")
    if len(source_files) >= 40 and not architecture_docs and complete:
        finding("ARCHITECTURE_DOC_NOT_FOUND", "architecture", "LOW", "MEDIUM",
                "A non-trivial source tree was found without a conventional architecture document.",
                [item["path"] for item in source_files[:5]],
                "Check for equivalent architecture decisions elsewhere; document module boundaries if they are not recorded.")
    if manifests and not lockfiles and complete:
        finding("DEPENDENCY_LOCKFILE_NOT_DISCOVERED", "dependencies", "LOW", "LOW",
                "A dependency manifest was found but no recognized lockfile was discovered.",
                manifests[:8],
                "Check the package ecosystem and release policy; some projects intentionally do not commit lockfiles.")
    if profile and profile.get("complexity") == "high-assurance" and not security_docs and complete:
        finding("SECURITY_DOCUMENTATION_NOT_FOUND", "security", "MEDIUM", "MEDIUM",
                "The approved project profile is high-assurance, but no conventional security or threat-model document was found.",
                manifests[:5] or [item["path"] for item in source_files[:5]],
                "Review existing security controls and threat documentation; do not infer a vulnerability from missing filenames.")
    if source_files and not workflows and complete:
        finding("CI_CONFIGURATION_NOT_DISCOVERED", "verification", "LOW", "LOW",
                "Source files were found, but no conventional CI configuration marker was discovered.",
                [item["path"] for item in source_files[:5]],
                "Check for external CI configuration or a deliberate manual release process before adding automation.")

    return {
        "status": "INCOMPLETE" if not complete else "SCANNED",
        "scan_mode": "READ_ONLY_FILESYSTEM_METADATA",
        "root_identity": hashlib.sha256(str(root).encode("utf-8", "surrogatepass")).hexdigest()[:16],
        "inventory_snapshot_sha256": snapshot,
        "snapshot_semantics": "Path, size and modification-time metadata only; not a content hash or Git revision.",
        "limits": {"max_files": MAX_FILES, "max_directories": MAX_DIRECTORIES, "max_depth": MAX_DEPTH},
        "truncated": truncated,
        "unreadable_paths": unreadable[:30],
        "symlinks_skipped": skipped_symlinks,
        "summary": {
            "files": len(files),
            "directories": len(directories),
            "source_files": len(source_files),
            "test_files": len(test_files),
            "test_directories": len(test_dirs),
            "languages_by_extension": dict(sorted(languages.items())),
        },
        "discovered": {
            "readmes": readmes[:20],
            "architecture_docs": architecture_docs[:20],
            "security_docs": security_docs[:20],
            "test_files": test_files[:40],
            "test_directories": test_dirs[:20],
            "dependency_manifests": manifests[:20],
            "dependency_lockfiles": lockfiles[:20],
            "ci_markers": workflows,
        },
        "findings": findings,
        "findings_count": len(findings),
        "audit_scope": "Structural repository signals only. Source contents, dependency advisories, runtime behavior, semantic documentation and security vulnerabilities are not audited.",
        "next": "Review each finding against owner requirements and actual source. Convert accepted findings into tasks only after review.",
        "data_written": False,
        "project_scripts_executed": False,
        "source_contents_read": False,
    }
