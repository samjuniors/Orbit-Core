"""Guard the installable source-setup ZIP from unapproved RAD P2 experiments.

The RAD P2 native/IPC/manual-acceptance prototypes are research-only until
privileged Windows and independent security acceptance. The repository keeps
them for code review and CI; the distributed setup ZIP must not carry them.
Read-only preflight diagnostics are explicitly retained.
"""
from __future__ import annotations

_READ_ONLY_P2 = frozenset({
    "scripts/rad_p2_preflight.py",
    "tests/test_rad_p2_preflight.py",
})
_UNAPPROVED_PREFIXES = ("scripts/rad_p2_", "tests/test_rad_p2_")


def excluded_from_setup_source_archive(relative_path: str) -> bool:
    """Whether a repository-relative POSIX path is non-shippable research.

    Fail closed on invalid/unsafe paths rather than silently packaging them.
    """
    if (type(relative_path) is not str or not relative_path
            or "\\" in relative_path
            or any(part in ("", ".", "..") for part in relative_path.split("/"))):
        raise ValueError("Source archive path must be a safe relative POSIX path")
    return (relative_path.startswith(_UNAPPROVED_PREFIXES)
            and relative_path not in _READ_ONLY_P2)
