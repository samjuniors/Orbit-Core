"""Adversarial tests for descriptor-relative POSIX project filesystem operations."""
from __future__ import annotations

import errno
import os
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "source" / "runtime"
sys.path.insert(0, str(RUNTIME))

import orbit_posix_fs


@unittest.skipUnless(orbit_posix_fs.SAFE, "POSIX dir_fd/O_NOFOLLOW support required")
class PosixFilesystemTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "project"
        self.root.mkdir()
        self.outside = self.base / "outside"
        self.outside.mkdir()

    @unittest.skipUnless(orbit_posix_fs.BENEATH_PLATFORM, "openat2 is Linux-only")
    def test_create_beneath_writes_only_inside_root(self):
        parts = (".orbit", "candidates")
        os.close(orbit_posix_fs.ensure_directories(self.root, parts))
        orbit_posix_fs.create_beneath(self.root, ".orbit/candidates/AGENT.md", "body")
        self.assertEqual((self.root / ".orbit/candidates/AGENT.md").read_text(), "body")
        with self.assertRaises(FileExistsError):
            orbit_posix_fs.create_beneath(self.root, ".orbit/candidates/AGENT.md", "again")
        with self.assertRaises(ValueError):
            orbit_posix_fs.create_beneath(self.root, "../outside/AGENT.md", "x")

    @unittest.skipUnless(orbit_posix_fs.BENEATH_PLATFORM, "openat2 is Linux-only")
    def test_create_beneath_rejects_ancestor_replaced_by_symlink(self):
        (self.outside / "candidates").mkdir()
        os.symlink(self.outside, self.root / ".orbit")
        with self.assertRaises(orbit_posix_fs.UnsafePathError):
            orbit_posix_fs.create_beneath(self.root, ".orbit/candidates/AGENT.md", "x")
        self.assertFalse((self.outside / "candidates" / "AGENT.md").exists())

    def test_openat2_abi_allowlist(self):
        abi = orbit_posix_fs._beneath_abi
        for machine in ("x86_64", "amd64", "aarch64", "arm64", "riscv64",
                        "ppc64", "ppc64le", "s390x", "loongarch64"):
            with self.subTest(accepted=machine):
                self.assertTrue(abi("linux", machine, 8))
        for platform_name, machine, size in (
                ("linux", "x86_64", 4),        # x32 uses a different syscall number
                ("linux", "aarch64", 4), ("linux", "riscv64", 4),
                ("linux", "mips64", 8), ("linux", "mips", 4), ("linux", "alpha", 8),
                ("linux", "ia64", 8), ("linux", "armv7l", 4), ("linux", "i686", 4),
                ("linux", "sparc64", 8), ("linux", "unknown", 8),
                ("darwin", "arm64", 8), ("freebsd14", "amd64", 8)):
            with self.subTest(machine=machine, size=size, platform=platform_name):
                self.assertFalse(abi(platform_name, machine, size))

    def test_create_beneath_fails_closed_without_openat2(self):
        with mock.patch.object(orbit_posix_fs, "BENEATH_PLATFORM", True), \
                mock.patch.object(orbit_posix_fs, "_openat2", return_value=-errno.ENOSYS):
            with self.assertRaises(orbit_posix_fs.BeneathUnavailable):
                orbit_posix_fs.create_beneath(self.root, "AGENT.md", "x")
        self.assertFalse((self.root / "AGENT.md").exists())

    def test_root_walk_rejects_symlink_ancestor(self):
        real = self.base / "real"
        project = real / "project"
        project.mkdir(parents=True)
        alias = self.base / "alias"
        alias.symlink_to(real, target_is_directory=True)
        with self.assertRaises(OSError):
            orbit_posix_fs.open_root(alias / "project")

    def test_safe_exists_rejects_symlink_leaf_and_parent(self):
        secret = self.outside / "secret.txt"
        secret.write_text("outside", encoding="utf-8")
        (self.root / "linked.txt").symlink_to(secret)
        (self.root / "linked-dir").symlink_to(self.outside, target_is_directory=True)
        with self.assertRaises(orbit_posix_fs.UnsafePathError):
            orbit_posix_fs.safe_exists(self.root, "linked.txt")
        with self.assertRaises(OSError):
            orbit_posix_fs.safe_exists(self.root, "linked-dir/secret.txt")

    def test_missing_intermediate_component_is_not_an_error(self):
        self.assertFalse(orbit_posix_fs.safe_exists(self.root, ".orbit/agent-candidates/AGENT.md"))

    def test_directory_creation_and_file_write_are_exclusive(self):
        parent = orbit_posix_fs.ensure_directories(
            self.root, (".orbit", "agent-candidates", "orbit-qa")
        )
        try:
            orbit_posix_fs.write_new_file(parent, "AGENT.md", "first")
            with self.assertRaises(FileExistsError):
                orbit_posix_fs.write_new_file(parent, "AGENT.md", "second")
        finally:
            os.close(parent)
        self.assertEqual(
            (self.root / ".orbit/agent-candidates/orbit-qa/AGENT.md").read_text(encoding="utf-8"),
            "first",
        )

    def test_write_does_not_follow_existing_symlink(self):
        secret = self.outside / "secret.txt"
        secret.write_text("untouched", encoding="utf-8")
        parent = orbit_posix_fs.ensure_directories(self.root, (".orbit",))
        try:
            (self.root / ".orbit/linked.txt").symlink_to(secret)
            with self.assertRaises(OSError):
                orbit_posix_fs.write_new_file(parent, "linked.txt", "overwrite")
        finally:
            os.close(parent)
        self.assertEqual(secret.read_text(encoding="utf-8"), "untouched")

    def test_safe_exists_rejects_hard_linked_file(self):
        original = self.root / "original.txt"
        linked = self.root / "linked.txt"
        original.write_text("shared", encoding="utf-8")
        try:
            os.link(original, linked)
        except OSError as exc:
            self.skipTest("Hard-link creation unavailable: " + str(exc))
        with self.assertRaises(orbit_posix_fs.UnsafePathError):
            orbit_posix_fs.safe_exists(self.root, "linked.txt", expected="file")

    def test_path_traversal_is_rejected(self):
        with self.assertRaises(ValueError):
            orbit_posix_fs.safe_exists(self.root, "../outside/secret.txt")

    def test_directory_creation_rejects_symlink_parent(self):
        (self.root / ".orbit").symlink_to(self.outside, target_is_directory=True)
        with self.assertRaises(OSError):
            orbit_posix_fs.ensure_directories(self.root, (".orbit", "agent-candidates"))
        self.assertFalse((self.outside / "agent-candidates").exists())


if __name__ == "__main__":
    unittest.main()
