"""Descriptor-relative POSIX filesystem operations for project-scoped writes.

All path traversal is rooted at an opened directory descriptor. Symlinks,
non-regular leaves and multiply-linked files fail closed. Callers own and must
close descriptors returned by open_root() and ensure_directories().
"""
from __future__ import annotations

import ctypes
import errno
import os
import platform
import stat
import struct
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


# openat2(2), Linux 5.6+. 437 is its number on the 64-bit ABIs listed in
# _BENEATH_MACHINES (the generic table, plus powerpc and s390, which match it).
# Other ABIs use different numbers (MIPS 4437/5437/6437, Alpha 547, IA-64 1461,
# x32 0x40000000+437), so they and any unknown ABI fail closed.
_OPENAT2_NR = 437
_BENEATH_MACHINES = frozenset({
    "x86_64", "amd64", "aarch64", "arm64", "riscv64",
    "ppc64", "ppc64le", "s390x", "loongarch64",
})
_RESOLVE_NO_MAGICLINKS = 0x02
_RESOLVE_NO_SYMLINKS = 0x04
_RESOLVE_BENEATH = 0x08
# Only Linux offers an atomic "create beneath this directory" primitive. Other
# POSIX systems fail closed for confirmed writes; previews remain available.
def _beneath_abi(platform_name, machine, pointer_bytes):
    """openat2 = 437 is only trusted on the listed 64-bit Linux ABIs.

    The pointer-width check excludes x32, which reports machine x86_64.
    """
    return (platform_name.startswith("linux") and pointer_bytes == 8
            and machine in _BENEATH_MACHINES)


BENEATH_PLATFORM = _beneath_abi(sys.platform, platform.machine().lower(),
                                struct.calcsize("P"))


class BeneathUnavailable(OSError):
    """The kernel cannot confine a lookup beneath a directory (no openat2)."""


class WriteRolledBackError(OSError):
    """Writing failed after create; the new file was removed through its held parent."""


class CleanupFailedError(OSError):
    """Writing failed after create and the new file could not be removed."""


class UnsafeOwnershipError(OSError):
    """A candidate directory is writable or owned by someone other than this user."""


class MovedAfterCreateError(OSError):
    """Best-effort check: the created file is no longer at its path beneath root."""


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


def require_private_dirs(root, relative_parts, *, allow_missing=False):
    """Fail closed unless no other local user can rename the candidate chain.

    The root must be owned by the effective user and not group/other writable.
    Every directory below it must be owned by the effective user with no
    group/other permissions (0700). Existing directories are checked too.
    """
    uid = os.geteuid()
    current = open_root(root)
    try:
        info = os.fstat(current)
        if info.st_uid != uid or info.st_mode & 0o022:
            raise UnsafeOwnershipError(errno.EPERM, "Project root is not owned by this user "
                                       "or is writable by group or others", ".")
        seen = []
        for raw in tuple(relative_parts):
            try:
                child = _open_dir_at(current, raw)
            except FileNotFoundError:
                if allow_missing:
                    return  # check existing components before creating new ones
                raise
            os.close(current)
            current = child
            seen.append(raw)
            info = os.fstat(current)
            if info.st_uid != uid or info.st_mode & 0o077:
                raise UnsafeOwnershipError(errno.EPERM, "Directory is not owned by this "
                                           "user or is not private (0700)", "/".join(seen))
    finally:
        os.close(current)


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
    path = "/".join(parts)
    name = parts[-1]
    root_fd = open_root(root)
    parent_fd = -1
    try:
        # Hold the parent (resolved beneath root) for rollback; the file itself is
        # still created only by the root-relative openat2 call below.
        if len(parts) > 1:
            parent_fd = _openat2(root_fd, "/".join(parts[:-1]),
                                 os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC, 0, resolve)
            if parent_fd < 0:
                code = -parent_fd
                if code == errno.ENOSYS:
                    raise BeneathUnavailable(code, "openat2 unavailable", os.fspath(relative))
                if code in (errno.ELOOP, errno.EXDEV):
                    raise UnsafePathError(code, "Path escapes the project or crosses a link",
                                          os.fspath(relative))
                raise OSError(code, os.strerror(code), os.fspath(relative))
        else:
            parent_fd = os.dup(root_fd)
        for _ in range(3):
            fd = _openat2(root_fd, path, flags, 0o600, resolve)
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
        info = None
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise UnsafePathError("Created file is not a single-link regular file")
            with os.fdopen(fd, "wb") as stream:
                fd = -1
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        except OSError as exc:
            if fd >= 0:
                os.close(fd)
                fd = -1
            code = exc.errno or errno.EIO
            # Roll back only if the name in the held parent is still our inode.
            try:
                if info is None:
                    raise OSError(errno.EIO, "created file identity unknown")
                here = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
                if (here.st_dev, here.st_ino) != (info.st_dev, info.st_ino):
                    raise OSError(errno.ESTALE, "created file moved")
                os.unlink(name, dir_fd=parent_fd)
            except OSError as cleanup:
                raise CleanupFailedError(code, "Candidate write failed and the file could "
                                         "not be removed", os.fspath(relative)) from cleanup
            raise WriteRolledBackError(code, "Candidate write failed; file removed",
                                       os.fspath(relative)) from exc
        finally:
            if fd >= 0:
                os.close(fd)
        # Best-effort detection only: the open file follows a renamed folder, so
        # confirm the written inode is still at its path beneath root right now.
        check = _openat2(root_fd, path, os.O_PATH | os.O_NOFOLLOW | os.O_CLOEXEC, 0, resolve)
        if check < 0:
            raise MovedAfterCreateError(-check, "Created file is no longer at its path",
                                        os.fspath(relative))
        try:
            now = os.fstat(check)
        finally:
            os.close(check)
        if (now.st_dev, now.st_ino) != (info.st_dev, info.st_ino):
            raise MovedAfterCreateError(errno.ESTALE, "Created file is no longer at its path",
                                        os.fspath(relative))
    finally:
        if parent_fd >= 0:
            os.close(parent_fd)
        os.close(root_fd)
