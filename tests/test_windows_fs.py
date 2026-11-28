"""Adversarial Windows filesystem tests for Orbit project scans and writes."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "source" / "runtime"
sys.path.insert(0, str(RUNTIME))

import orbit_windows_fs
import orbit_project_audit
import orbit_source_audit
import orbit_agent_factory


@unittest.skipUnless(os.name == "nt", "Windows handle semantics required")
class WindowsFilesystemTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "project"
        self.root.mkdir()
        self.outside = Path(self.temp.name) / "outside"
        self.outside.mkdir()

    def test_root_identity_uses_128_bit_file_id(self):
        # ReFS file IDs are 128-bit; the 64-bit index is not unique there.
        with orbit_windows_fs.pin_directory(self.root) as a, \
                orbit_windows_fs.pin_directory(self.outside) as b:
            vol_a, id_a = orbit_windows_fs._file_id(a.handle, self.root)
            vol_b, id_b = orbit_windows_fs._file_id(b.handle, self.outside)
        self.assertEqual(len(id_a), 16)
        self.assertEqual(vol_a, vol_b)
        self.assertNotEqual(id_a, id_b)

    def test_missing_128_bit_file_id_fails_closed(self):
        with mock.patch.object(orbit_windows_fs, "_GetFileInformationByHandleEx",
                               return_value=False):
            with self.assertRaises(orbit_windows_fs.UnsafePathError):
                orbit_windows_fs.pin_directory_chain(self.root)

    def test_pinned_directory_denies_rename_until_released(self):
        child = self.root / "child"
        child.mkdir()
        pinned = orbit_windows_fs.pin_directory(child)
        moved = child.with_name("moved")
        try:
            with self.assertRaises(OSError):
                os.rename(child, moved)
            self.assertTrue(child.is_dir())
            self.assertFalse(moved.exists())
        finally:
            pinned.close()
        os.rename(child, moved)
        self.assertTrue(moved.is_dir())

    def test_project_ancestor_chain_prevents_parent_replacement(self):
        outer = self.root / "outer"
        project = outer / "project"
        outer.mkdir()
        project.mkdir()
        moved = outer.with_name("outer-moved")
        pins = orbit_windows_fs.pin_directory_chain(project)
        try:
            with self.assertRaises(OSError):
                os.rename(outer, moved)
            self.assertTrue(project.is_dir())
        finally:
            pins.close()
        os.rename(outer, moved)
        os.rename(moved, outer)

    def test_hard_linked_files_are_rejected(self):
        original = self.root / "original.py"
        linked = self.root / "linked.py"
        original.write_text("owner data", encoding="utf-8")
        try:
            os.link(original, linked)
        except OSError as exc:
            self.skipTest("Hard-link creation unavailable: " + str(exc))
        with self.assertRaises(orbit_windows_fs.UnsafePathError):
            orbit_windows_fs.open_regular_file_fd(linked)

    def test_reparse_junction_is_rejected(self):
        secret = self.outside / "outside-secret.py"
        secret.write_text("SHOULD_NEVER_BE_READ = True", encoding="utf-8")
        junction = self.root / "junction"
        result = subprocess.run(
            ["cmd.exe", "/c", "mklink", "/J", str(junction), str(self.outside)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            self.skipTest("Junction creation unavailable: " + result.stderr[-200:])
        with self.assertRaises(orbit_windows_fs.UnsafePathError):
            orbit_windows_fs.pin_directory(junction)
        with self.assertRaises(orbit_windows_fs.UnsafePathError):
            orbit_windows_fs.safe_exists(self.root, "junction/outside-secret.py")
        structural = orbit_project_audit.scan_project(self.root)
        self.assertNotIn("junction/outside-secret.py",
                         structural["discovered"]["test_files"])
        source = orbit_source_audit.scan_source(self.root)
        self.assertNotIn("junction/outside-secret.py",
                         source["unreadable_paths"])

    def _junction(self, link, target):
        result = subprocess.run(
            ["cmd.exe", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            self.skipTest("Junction creation unavailable: " + result.stderr[-200:])

    def test_structural_scan_rejects_junction_swapped_after_enumeration(self):
        victim = self.root / "victim"
        victim.mkdir()
        secret = self.outside / "outside-secret.py"
        secret.write_text("SHOULD_NEVER_BE_INVENTORIED", encoding="utf-8")
        original_pin = orbit_windows_fs.PinSet.pin
        swapped = False

        def swap_before_pin(pin_set, path):
            nonlocal swapped
            candidate = Path(path)
            if (candidate.name.casefold() == victim.name.casefold()
                    and candidate.parent.name.casefold() == self.root.name.casefold()
                    and not swapped):
                swapped = True
                os.rename(victim, self.root / "victim-original")
                self._junction(victim, self.outside)
            return original_pin(pin_set, path)

        with mock.patch.object(orbit_windows_fs.PinSet, "pin", swap_before_pin):
            result = orbit_project_audit.scan_project(self.root)
        self.assertTrue(swapped, "The junction replacement must occur before the descendant pin")
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertEqual(result["summary"]["files"], 0)
        self.assertFalse(any("outside-secret.py" in path
                             for path in result["discovered"]["test_files"]))

    def test_source_scan_rejects_junction_swapped_after_enumeration(self):
        victim = self.root / "victim"
        victim.mkdir()
        secret = self.outside / "outside-secret.py"
        secret.write_text("SHOULD_NEVER_BE_READ", encoding="utf-8")
        original_pin = orbit_windows_fs.PinSet.pin
        swapped = False

        def swap_before_pin(pin_set, path):
            nonlocal swapped
            candidate = Path(path)
            if (candidate.name.casefold() == victim.name.casefold()
                    and candidate.parent.name.casefold() == self.root.name.casefold()
                    and not swapped):
                swapped = True
                os.rename(victim, self.root / "victim-original")
                self._junction(victim, self.outside)
            return original_pin(pin_set, path)

        with mock.patch.object(orbit_windows_fs.PinSet, "pin", swap_before_pin):
            result = orbit_source_audit.scan_source(self.root)
        self.assertTrue(swapped, "The junction replacement must occur before the descendant pin")
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertFalse(result["source_contents_read"])
        self.assertNotIn("SHOULD_NEVER_BE_READ", str(result))

    def test_source_scan_rejects_hardlink_inserted_before_open(self):
        source = self.root / "main.py"
        source.write_text("value = 1\\n", encoding="utf-8")
        external = self.outside / "external.py"
        external.write_text("EXTERNAL_CONTENT_MUST_NOT_BE_READ", encoding="utf-8")
        original_open = orbit_windows_fs.open_regular_file_fd
        swapped = False

        def replace_with_hardlink(path, **kwargs):
            nonlocal swapped
            candidate = Path(path)
            if candidate.name.casefold() == source.name.casefold() and candidate.parent.name.casefold() == self.root.name.casefold() and not swapped:
                swapped = True
                source.unlink()
                os.link(external, source)
            return original_open(path, **kwargs)

        with mock.patch.object(orbit_windows_fs, "open_regular_file_fd", replace_with_hardlink):
            result = orbit_source_audit.scan_source(self.root)
        self.assertTrue(swapped, "The hard-link replacement must occur before the file open")
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertFalse(result["source_contents_read"])
        self.assertNotIn("EXTERNAL_CONTENT_MUST_NOT_BE_READ", str(result))

    def test_safe_structural_and_source_scans_work(self):
        (self.root / "src").mkdir()
        (self.root / "tests").mkdir()
        (self.root / "README.md").write_text("# sample", encoding="utf-8")
        (self.root / "src" / "main.py").write_text(
            "value = eval(user_input)\n", encoding="utf-8"
        )
        (self.root / "tests" / "test_main.py").write_text(
            "def test_main(): pass\n", encoding="utf-8"
        )
        structural = orbit_project_audit.scan_project(self.root)
        self.assertEqual(structural["status"], "SCANNED")
        self.assertEqual(structural["summary"]["source_files"], 2)
        source = orbit_source_audit.scan_source(self.root)
        self.assertEqual(source["status"], "SCANNED")
        self.assertEqual(source["summary"]["source_files"], 2)
        self.assertTrue(any(x["id"].startswith("SOURCE_DYNAMIC_CODE_")
                            for x in source["findings"]))

    def test_candidate_write_is_exclusive_and_project_scoped(self):
        args = {
            "role": "specialist-qa",
            "mission": "Review test architecture and improve deterministic test coverage.",
            "acceptance": "Deliver a reviewed test matrix with reproducible passing evidence.",
            "resource_review": "Inspect existing project test tools before proposing new dependencies.",
            "confirm_write": True,
        }
        result = orbit_agent_factory.candidate(self.root, "sample", args)
        self.assertEqual(result["status"], "AGENT_CANDIDATE_DRAFTED")
        path = self.root / ".orbit" / "agent-candidates" / "orbit-specialist-qa" / "AGENT.md"
        self.assertTrue(path.is_file())
        self.assertIn("Candidate specialist", path.read_text(encoding="utf-8"))
        again = orbit_agent_factory.candidate(self.root, "sample", args)
        self.assertEqual(again["status"], "HOLD_EXISTING_CANDIDATE")

    def test_ensure_directories_and_new_file_rejects_overwrite(self):
        pins, parent = orbit_windows_fs.ensure_directories(
            self.root, (".orbit", "safe", "child")
        )
        self.addCleanup(pins.close)
        target = parent / "data.txt"
        orbit_windows_fs.write_new_file(target, "one")
        with self.assertRaises(FileExistsError):
            orbit_windows_fs.write_new_file(target, "two")
        self.assertEqual(target.read_text(encoding="utf-8"), "one")


if __name__ == "__main__":
    unittest.main()
