"""Descriptor-relative POSIX filesystem operations for project-scoped writes.

All path traversal is rooted at an opened directory descriptor. Symlinks,
non-regular leaves and multiply-linked files fail closed. Callers own and must
close descriptors returned by open_root() and ensure_directories().
"""
from __future__ import annotations

import ctypes
import errno
import os
import stat
import sys
from pathlib import Path

SAFE = (
    os.name != "nt"
    and hasattr(os, "O_NOFOLLOW")
    and hasattr(os, "O_DIRECTORY")
    and os.open in os.supports_dir_fd
    and os.mkdir in os.supports_dir_fd
    and os.stat in os.supports_dir_fd
)


# openat2(2), Linux 5.6+. Same syscall number on every Linux architecture.
_OPENAT2_NR = 437
_RESOLVE_NO_MAGICLINKS = 0x02
_RESOLVE_NO_SYMLINKS = 0x04
_RESOLVE_BENEATH = 0x08
# Only Linux offers an atomic "create beneath this directory" primitive. Other
# POSIX systems fail closed for confirmed writes; previews remain available.
BENEATH_PLATFORM = sys.platform.startswith("linux")


class BeneathUnavailable(OSError):
    """The kernel cannot confine a lookup beneath a directory (no openat2)."""


class _OpenHow(ctypes.Structure):
    _fields_ = [("flags", ctypes.c_uint64), ("mode", ctypes.c_uint64),
                ("resolve", ctypes.c_uint64)]


def _openat2(dir_fd, path, flags, mode, resolve):
    """Return a new fd, or a negative errno."""
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    how = _OpenHow(flags, mode, resolve)
    result = libc.syscall(ctypes.c_long(_OPENAT2_NR), ctypes.c_int(dir_fd),
                          ctypes.c_char_p(os.fsencode(path)), ctypes.byref(how),
                          ctypes.c_size_t(ctypes.sizeof(how)))
    return result if result >= 0 else -ctypes.get_errno()


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


def beneath_available(root):
    """Probe openat2 against root before any directory is created."""
    if not (SAFE and BENEATH_PLATFORM):
        return False
    root_fd = open_root(root)
    try:
        fd = _openat2(root_fd, ".", os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0),
                      0, _RESOLVE_BENEATH)
    finally:
        os.close(root_fd)
    if fd >= 0:
        os.close(fd)
        return True
    return False


def create_beneath(root, relative, content):
    """Exclusively create root/relative with one openat2 call confined beneath root.

    The kernel resolves every component beneath the pinned root fd, rejects
    symlinks and magic links, and returns EAGAIN if a concurrent rename races the
    lookup, so the file can only be created inside the project. Parent
    directories must already exist. Raises BeneathUnavailable where openat2 is
    missing; never falls back to a path- or child-descriptor-based create.

    Threat model: this is a point-in-time guarantee about where the file is
    created. A process running as the same user can still rename the file or its
    folders afterwards; post-creation renames are outside this boundary.
    """
    _require_safe()
    if not BENEATH_PLATFORM:
        raise BeneathUnavailable(errno.ENOSYS, "openat2 is Linux-only")
    parts = _relative_parts(relative)
    data = content.encode("utf-8") if isinstance(content, str) else bytes(content)
    flags = (os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
             | getattr(os, "O_CLOEXEC", 0))
    resolve = _RESOLVE_BENEATH | _RESOLVE_NO_SYMLINKS | _RESOLVE_NO_MAGICLINKS
    root_fd = open_root(root)
    try:
        for _ in range(3):
            fd = _openat2(root_fd, "/".join(parts), flags, 0o600, resolve)
            if fd != -errno.EAGAIN:
                break
        if fd < 0:
            code = -fd
            if code == errno.ENOSYS:
                raise BeneathUnavailable(code, "openat2 unavailable", os.fspath(relative))
            if code == errno.EEXIST:
                raise FileExistsError(code, os.strerror(code), os.fspath(relative))
            if code in (errno.ELOOP, errno.EXDEV):
                raise UnsafePathError(code, "Path escapes the project or crosses a link",
                                      os.fspath(relative))
            raise OSError(code, os.strerror(code), os.fspath(relative))
    finally:
        os.close(root_fd)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise UnsafePathError("Created file is not a single-link regular file")
        with os.fdopen(fd, "wb") as stream:
            fd = -1
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        if fd >= 0:
            os.close(fd)
