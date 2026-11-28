"""Descriptor-relative POSIX filesystem operations for project-scoped writes.

All path traversal is rooted at an opened directory descriptor. Symlinks,
non-regular leaves and multiply-linked files fail closed. Callers own and must
close descriptors returned by open_root() and ensure_directories().
"""
from __future__ import annotations

import os
import stat
from pathlib import Path

SAFE = (
    os.name != "nt"
    and hasattr(os, "O_NOFOLLOW")
    and hasattr(os, "O_DIRECTORY")
    and os.open in os.supports_dir_fd
    and os.mkdir in os.supports_dir_fd
    and os.stat in os.supports_dir_fd
)


class UnsafePathError(OSError):
    """A path component is a link, wrong type, or otherwise unsafe."""


def _require_safe():
    if not SAFE:
        raise OSError("Descriptor-relative POSIX filesystem operations unavailable")


def _dir_flags():
    return (os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            | getattr(os, "O_CLOEXEC", 0))


def _component(name):
    if (not isinstance(name, str) or not name or name in {".", ".."}
            or "/" in name or "\\" in name or "\x00" in name):
        raise ValueError("Expected one safe path component")
    return name


def _relative_parts(relative):
    raw = os.fspath(relative)
    if not isinstance(raw, str) or not raw or raw.startswith("/") or "\\" in raw or "\x00" in raw:
        raise ValueError("Expected a normalized project-relative path")
    parts = raw.split("/")
    return tuple(_component(part) for part in parts)


def open_root(root):
    """Open an absolute directory by walking every component with O_NOFOLLOW."""
    _require_safe()
    path = Path(root)
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError("Project root must be absolute and normalized")
    anchor, *parts = path.parts
    fd = os.open(anchor, _dir_flags())
    try:
        for part in parts:
            child = os.open(_component(part), _dir_flags(), dir_fd=fd)
            if not stat.S_ISDIR(os.fstat(child).st_mode):
                os.close(child)
                raise UnsafePathError("Project path component is not a directory")
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def _open_dir_at(parent_fd, name):
    child = os.open(_component(name), _dir_flags(), dir_fd=parent_fd)
    if not stat.S_ISDIR(os.fstat(child).st_mode):
        os.close(child)
        raise UnsafePathError("Path component is not a directory")
    return child


def safe_exists(root, relative, *, expected="any"):
    """Check a relative leaf without following links or accepting special files."""
    if expected not in {"file", "directory", "any"}:
        raise ValueError("Expected file, directory or any")
    parts = _relative_parts(relative)
    parent_fd = open_root(root)
    try:
        for part in parts[:-1]:
            try:
                child = _open_dir_at(parent_fd, part)
            except FileNotFoundError:
                return False
            os.close(parent_fd)
            parent_fd = child
        name = parts[-1]
        try:
            info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            return False
        if stat.S_ISLNK(info.st_mode):
            raise UnsafePathError("Refusing to follow a symbolic link")
        if stat.S_ISDIR(info.st_mode):
            child = _open_dir_at(parent_fd, name)
            os.close(child)
            if expected == "file":
                raise UnsafePathError("Expected a regular file")
            return True
        flags = (os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0)
                 | getattr(os, "O_CLOEXEC", 0))
        fd = os.open(name, flags, dir_fd=parent_fd)
        try:
            actual = os.fstat(fd)
            if not stat.S_ISREG(actual.st_mode) or actual.st_nlink != 1:
                raise UnsafePathError("Refusing a non-regular or multiply-linked file")
            if expected == "directory":
                raise UnsafePathError("Expected a directory")
            return True
        finally:
            os.close(fd)
    finally:
        os.close(parent_fd)


def ensure_directories(root, relative_parts):
    """Create/open a directory chain relative to a pinned root; return its fd."""
    _require_safe()
    fd = open_root(root)
    try:
        for raw in relative_parts:
            name = _component(raw)
            try:
                os.mkdir(name, mode=0o700, dir_fd=fd)
                os.fsync(fd)
            except FileExistsError:
                pass
            child = _open_dir_at(fd, name)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def same_directory_at(root, relative_parts, fd):
    """True if root/relative_parts (walked without following links) is fd's directory.

    A held descriptor follows its directory if it is renamed, so a write through
    it is only inside the project if the directory is still at this location.
    """
    expected = os.fstat(fd)
    current = open_root(root)
    try:
        for raw in relative_parts:
            try:
                child = _open_dir_at(current, raw)
            except FileNotFoundError:
                return False
            os.close(current)
            current = child
        actual = os.fstat(current)
        return (actual.st_dev, actual.st_ino) == (expected.st_dev, expected.st_ino)
    finally:
        os.close(current)


def write_new_file(parent_fd, name, content):
    """Exclusively create a private regular file relative to a held parent fd."""
    name = _component(name)
    data = content.encode("utf-8") if isinstance(content, str) else bytes(content)
    flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
             | getattr(os, "O_CLOEXEC", 0))
    fd = os.open(name, flags, 0o600, dir_fd=parent_fd)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise UnsafePathError("Created candidate is not a single-link regular file")
        with os.fdopen(fd, "wb") as stream:
            fd = -1
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if fd >= 0:
            os.close(fd)
