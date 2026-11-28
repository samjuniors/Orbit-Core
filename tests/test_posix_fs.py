"""Adversarial tests for descriptor-relative POSIX project filesystem operations."""
from __future__ import annotations

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

    def test_same_directory_at_rejects_ancestor_moved_during_walk(self):
        parts = (".orbit", "agent-candidates", "x")
        fd = orbit_posix_fs.ensure_directories(self.root, parts)
        self.addCleanup(os.close, fd)
        self.assertTrue(orbit_posix_fs.same_directory_at(self.root, parts, fd))
        real_open = orbit_posix_fs._open_dir_at
        moved = []

        def open_then_move(parent_fd, name):
            child = real_open(parent_fd, name)
            if name == ".orbit" and not moved:
                # The walk now holds .orbit; move it out before descending further.
                (self.root / ".orbit").rename(self.outside / ".orbit")
                moved.append(True)
            return child

        with mock.patch.object(orbit_posix_fs, "_open_dir_at", open_then_move):
            self.assertFalse(orbit_posix_fs.same_directory_at(self.root, parts, fd))

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
