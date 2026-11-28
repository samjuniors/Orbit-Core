"""Windows filesystem primitives that pin directory identities during project I/O.

The caller must keep every ancestor PinnedDirectory alive while operating on
its descendants. Handles intentionally omit FILE_SHARE_DELETE so an attacker
cannot rename/replace a pinned directory while path-based Win32 opens are
resolved beneath it. Every leaf open uses FILE_FLAG_OPEN_REPARSE_POINT and
rejects reparse points; regular files with multiple hard links are rejected.
"""
from __future__ import annotations

import ctypes
import os
from pathlib import Path

if os.name == "nt":
    import msvcrt
else:  # pragma: no cover - Windows-only implementation
    msvcrt = None

WINDOWS_SAFE = os.name == "nt"


class UnsafePathError(OSError):
    """A path resolves to a reparse point, directory/file type mismatch or hard link."""


if WINDOWS_SAFE:
    from ctypes import wintypes

    _kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    _INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

    _GENERIC_READ = 0x80000000
    _GENERIC_WRITE = 0x40000000
    _FILE_LIST_DIRECTORY = 0x0001
    _FILE_READ_ATTRIBUTES = 0x0080
    _FILE_SHARE_READ = 0x00000001
    _FILE_SHARE_WRITE = 0x00000002
    _OPEN_EXISTING = 3
    _CREATE_NEW = 1
    _FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
    _FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
    _FILE_FLAG_SEQUENTIAL_SCAN = 0x08000000
    _FILE_ATTRIBUTE_DIRECTORY = 0x00000010
    _FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400
    _ERROR_FILE_NOT_FOUND = 2
    _ERROR_PATH_NOT_FOUND = 3
    _ERROR_FILE_EXISTS = 80
    _ERROR_ALREADY_EXISTS = 183

    class _FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", wintypes.DWORD),
                    ("dwHighDateTime", wintypes.DWORD)]

    class _BY_HANDLE_FILE_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("dwFileAttributes", wintypes.DWORD),
            ("ftCreationTime", _FILETIME),
            ("ftLastAccessTime", _FILETIME),
            ("ftLastWriteTime", _FILETIME),
            ("dwVolumeSerialNumber", wintypes.DWORD),
            ("nFileSizeHigh", wintypes.DWORD),
            ("nFileSizeLow", wintypes.DWORD),
            ("nNumberOfLinks", wintypes.DWORD),
            ("nFileIndexHigh", wintypes.DWORD),
            ("nFileIndexLow", wintypes.DWORD),
        ]

    class _FILE_ID_INFO(ctypes.Structure):
        _fields_ = [("VolumeSerialNumber", ctypes.c_ulonglong),
                    ("FileId", ctypes.c_ubyte * 16)]

    _FILE_ID_INFO_CLASS = 18  # FILE_INFO_BY_HANDLE_CLASS.FileIdInfo
    _GetFileInformationByHandleEx = _kernel32.GetFileInformationByHandleEx
    _GetFileInformationByHandleEx.argtypes = [
        wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD
    ]
    _GetFileInformationByHandleEx.restype = wintypes.BOOL

    _CreateFileW = _kernel32.CreateFileW
    _CreateFileW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
        wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE,
    ]
    _CreateFileW.restype = wintypes.HANDLE
    _CloseHandle = _kernel32.CloseHandle
    _CloseHandle.argtypes = [wintypes.HANDLE]
    _CloseHandle.restype = wintypes.BOOL
    _GetFileInformationByHandle = _kernel32.GetFileInformationByHandle
    _GetFileInformationByHandle.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(_BY_HANDLE_FILE_INFORMATION)
    ]
    _GetFileInformationByHandle.restype = wintypes.BOOL
    _GetFinalPathNameByHandleW = _kernel32.GetFinalPathNameByHandleW
    _GetFinalPathNameByHandleW.argtypes = [
        wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD
    ]
    _GetFinalPathNameByHandleW.restype = wintypes.DWORD
    _CreateDirectoryW = _kernel32.CreateDirectoryW
    _CreateDirectoryW.argtypes = [wintypes.LPCWSTR, wintypes.LPVOID]
    _CreateDirectoryW.restype = wintypes.BOOL


def _win_path(path: Path | str) -> str:
    value = os.path.abspath(os.fspath(path))
    if value.startswith("\\\\?\\"):
        return value
    if value.startswith("\\\\"):
        return "\\\\?\\UNC\\" + value[2:]
    return "\\\\?\\" + value


def _last_error(path: str) -> OSError:
    code = ctypes.get_last_error()
    if code in {_ERROR_FILE_NOT_FOUND, _ERROR_PATH_NOT_FOUND}:
        return FileNotFoundError(code, ctypes.FormatError(code), path)
    if code == _ERROR_FILE_EXISTS:
        return FileExistsError(code, ctypes.FormatError(code), path)
    if code == _ERROR_ALREADY_EXISTS:
        return FileExistsError(code, ctypes.FormatError(code), path)
    return OSError(code, ctypes.FormatError(code), path)


def _open_handle(path: Path | str, access: int, flags: int, *, create_new=False):
    if not WINDOWS_SAFE:
        raise OSError("Windows handle APIs are unavailable on this platform")
    value = _win_path(path)
    handle = _CreateFileW(
        value, access, _FILE_SHARE_READ | _FILE_SHARE_WRITE, None,
        _CREATE_NEW if create_new else _OPEN_EXISTING,
        flags | _FILE_FLAG_OPEN_REPARSE_POINT, None,
    )
    raw = ctypes.cast(handle, ctypes.c_void_p).value
    if raw == _INVALID_HANDLE_VALUE or raw is None:
        raise _last_error(value)
    info = _BY_HANDLE_FILE_INFORMATION()
    if not _GetFileInformationByHandle(handle, ctypes.byref(info)):
        error = _last_error(value)
        _CloseHandle(handle)
        raise error
    return handle, info


def _file_id(handle, path) -> tuple[int, bytes]:
    """Full 128-bit volume/file identity (FileIdInfo).

    The 64-bit index from GetFileInformationByHandle is not unique on ReFS and
    may be partial on network filesystems, so it is never used as identity.
    A filesystem that cannot report FileIdInfo fails closed.
    """
    info = _FILE_ID_INFO()
    if not _GetFileInformationByHandleEx(
            handle, _FILE_ID_INFO_CLASS, ctypes.byref(info), ctypes.sizeof(info)):
        raise UnsafePathError(
            "Filesystem cannot report a 128-bit file identity; refusing", str(path))
    file_id = bytes(info.FileId)
    if info.VolumeSerialNumber == 0 or file_id == bytes(16):
        raise UnsafePathError("Filesystem reported an empty file identity; refusing", str(path))
    return info.VolumeSerialNumber, file_id


def _final_path(handle) -> str:
    buffer = ctypes.create_unicode_buffer(32768)
    length = _GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0)
    if not length or length >= len(buffer):
        raise OSError(ctypes.get_last_error(), "Unable to resolve pinned directory identity")
    value = buffer.value
    if value.startswith("\\\\?\\UNC\\"):
        value = "\\\\" + value[8:]
    elif value.startswith("\\\\?\\"):
        value = value[4:]
    return os.path.normcase(os.path.normpath(value))


class PinSet:
    """Keep a root and descendant directory handles alive for one scan/write."""

    def __init__(self):
        self.handles: list[PinnedDirectory] = []
        self.root_path: Path | None = None

    def pin(self, path: Path | str) -> "PinnedDirectory":
        handle = pin_directory(path)
        self.handles.append(handle)
        return handle

    def close(self):
        for handle in reversed(self.handles):
            handle.close()
        self.handles.clear()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def __del__(self):  # best-effort cleanup if a caller exits unexpectedly
        self.close()


class PinnedDirectory:
    """Open directory handle that prevents rename/reparse replacement until closed."""

    def __init__(self, path: Path, handle, info):
        self.path = Path(path)
        self.handle = handle
        self.info = info
        self.closed = False

    def close(self):
        if not self.closed:
            _CloseHandle(self.handle)
            self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def pin_directory(path: Path | str, *, expected_final_path: Path | str | None = None) -> PinnedDirectory:
    """Open a directory itself (never its reparse target) and deny delete sharing."""
    path = Path(path)
    handle, info = _open_handle(
        path, _FILE_LIST_DIRECTORY | _FILE_READ_ATTRIBUTES,
        _FILE_FLAG_BACKUP_SEMANTICS,
    )
    attrs = info.dwFileAttributes
    if attrs & _FILE_ATTRIBUTE_REPARSE_POINT:
        _CloseHandle(handle)
        raise UnsafePathError("Refusing to traverse a Windows reparse point", str(path))
    if not attrs & _FILE_ATTRIBUTE_DIRECTORY:
        _CloseHandle(handle)
        raise NotADirectoryError(str(path))
    pinned = PinnedDirectory(path, handle, info)
    if expected_final_path is not None:
        expected = os.path.normcase(os.path.normpath(os.path.abspath(os.fspath(expected_final_path))))
        actual = _final_path(handle)
        if actual != expected:
            pinned.close()
            raise UnsafePathError("Pinned root identity differs from the selected project path", str(path))
    return pinned


def pin_directory_chain(path: Path | str) -> PinSet:
    """Pin every directory from the volume/share root through the project root.

    Pinning only the project directory leaves its ancestor path components
    replaceable. Holding the complete resolved ancestor chain prevents a
    junction swap in a parent directory from redirecting later path opens.
    """
    original = Path(path)
    pins = PinSet()
    selected = None
    try:
        # Open the selected directory before resolving its ancestors. This
        # captures the actual object selected by the first kernel open.
        selected = pin_directory(original)
        pins.handles.append(selected)
        actual = _final_path(selected.handle)
        resolved = original.resolve(strict=True)
        expected = os.path.normcase(os.path.normpath(os.path.abspath(os.fspath(resolved))))
        if actual != expected:
            raise UnsafePathError("Selected project path changed while resolving its ancestors", str(original))
        current = Path(resolved.anchor)
        pins.pin(current)
        for part in resolved.parts[1:]:
            current = current / part
            pins.pin(current)
        # Re-open the final canonical path only after every ancestor is pinned.
        # Its volume/file ID must be identical to the original selected handle.
        canonical_root = pins.handles[-1]
        selected_id = _file_id(selected.handle, original)
        canonical_id = _file_id(canonical_root.handle, resolved)
        if selected_id != canonical_id:
            raise UnsafePathError("Project root identity changed while pinning ancestors", str(original))
        pins.root_path = resolved
        return pins
    except Exception:
        pins.close()
        if selected is not None and selected not in pins.handles:
            selected.close()
        raise


def open_regular_file_fd(path: Path | str, *, create_new=False, write=False):
    """Open a single-link regular file without following reparse points or allowing rename."""
    path = Path(path)
    access = (_GENERIC_WRITE | _FILE_READ_ATTRIBUTES) if write else (_GENERIC_READ | _FILE_READ_ATTRIBUTES)
    flags = _FILE_FLAG_SEQUENTIAL_SCAN
    handle, info = _open_handle(path, access, flags, create_new=create_new)
    attrs = info.dwFileAttributes
    if attrs & _FILE_ATTRIBUTE_REPARSE_POINT:
        _CloseHandle(handle)
        raise UnsafePathError("Refusing to open a Windows reparse point", str(path))
    if attrs & _FILE_ATTRIBUTE_DIRECTORY:
        _CloseHandle(handle)
        raise IsADirectoryError(str(path))
    if info.nNumberOfLinks != 1:
        _CloseHandle(handle)
        raise UnsafePathError("Refusing to read or write a multiply-linked file", str(path))
    flags = os.O_BINARY | (os.O_WRONLY if write else os.O_RDONLY)
    try:
        return msvcrt.open_osfhandle(
            ctypes.cast(handle, ctypes.c_void_p).value, flags
        )
    except Exception:
        _CloseHandle(handle)
        raise


def create_directory(path: Path | str) -> bool:
    """Create exactly one directory; never follows a final reparse point."""
    value = _win_path(path)
    if _CreateDirectoryW(value, None):
        return True
    code = ctypes.get_last_error()
    if code == _ERROR_ALREADY_EXISTS:
        return False
    raise _last_error(value)


def ensure_directories(root: Path | str, relative_parts: tuple[str, ...] | list[str]) -> tuple[PinSet, Path]:
    """Create/pin a directory chain beneath a pinned project root.

    Returned pins must remain alive until all descendant operations finish.
    """
    root = Path(root)
    pins = PinSet()
    try:
        pins = pin_directory_chain(root)
        current = pins.root_path
        for part in relative_parts:
            if (not isinstance(part, str) or not part or part in {".", ".."}
                    or any(ch in part for ch in "\\\\/:\\x00")):
                raise ValueError("Invalid directory component")
            current = current / part
            try:
                pins.pin(current)
            except FileNotFoundError:
                create_directory(current)
                pins.pin(current)
        return pins, current
    except Exception:
        pins.close()
        raise


def safe_exists(root: Path | str, relative: Path | str, *, expected: str = "file") -> bool:
    """Inspect a repository-relative path while pinning each ancestor directory."""
    rel = Path(relative)
    if rel.is_absolute() or not rel.parts or any(part in {"", ".", ".."} for part in rel.parts):
        raise ValueError("Expected a normalized project-relative path")
    if any("\\\\" in part or ":" in part or "\x00" in part for part in rel.parts):
        raise ValueError("Invalid project-relative path")
    handles: list[PinnedDirectory] = []
    try:
        root_pins = pin_directory_chain(root)
        handles.extend(root_pins.handles)
        root_pins.handles = []  # ownership transferred to this scope
        current = root_pins.root_path
        for part in rel.parts[:-1]:
            current = current / part
            try:
                handles.append(pin_directory(current))
            except FileNotFoundError:
                return False
            except NotADirectoryError:
                return False
        if expected not in {"file", "directory", "any"}:
            raise ValueError("Expected file, directory or any")
        target = current / rel.parts[-1]
        try:
            handle, info = _open_handle(
                target, _FILE_READ_ATTRIBUTES, _FILE_FLAG_BACKUP_SEMANTICS
            )
        except FileNotFoundError:
            return False
        attrs = info.dwFileAttributes
        try:
            if attrs & _FILE_ATTRIBUTE_REPARSE_POINT:
                raise UnsafePathError("Refusing to inspect a Windows reparse point", str(target))
            is_directory = bool(attrs & _FILE_ATTRIBUTE_DIRECTORY)
            if not is_directory and info.nNumberOfLinks != 1:
                raise UnsafePathError("Refusing to inspect a multiply-linked file", str(target))
            return expected == "any" or (expected == "directory" and is_directory) or (expected == "file" and not is_directory)
        finally:
            _CloseHandle(handle)
    finally:
        for handle in reversed(handles):
            handle.close()


def write_new_file(path: Path | str, content: str) -> None:
    """Create a new UTF-8 file exclusively beneath already-pinned parent directories."""
    fd = open_regular_file_fd(path, create_new=True, write=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        # fdopen owns fd after construction; the context closes it.
        raise
