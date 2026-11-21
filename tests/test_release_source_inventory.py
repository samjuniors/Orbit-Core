"""Check that the setup ZIP inventory cannot accidentally ship RAD P2 PoCs.

No privileged Windows fixtures are invoked by these regression tests.
"""
from __future__ import annotations

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from release_source_inventory import excluded_from_setup_source_archive


class TestReleaseSourceInventory(unittest.TestCase):
    def test_manual_native_and_ipc_research_is_not_shippable(self):
        for path in (
            "scripts/rad_p2_disposable_host_acceptance.py",
            "scripts/rad_p2_disposable_probe.c",
            "scripts/rad_p2_preview_ipc/protocol.py",
            "scripts/rad_p2_preview_ipc/http_snapshot.py",
            "scripts/rad_p2_future_unreviewed.py",
            "tests/test_rad_p2_http_snapshot.py",
            "tests/test_rad_p2_pipe_native.py",
            "tests/test_rad_p2_wsgi_ipc.py",
            "tests/test_rad_p2_future_unreviewed.py",
        ):
            with self.subTest(path=path):
                self.assertTrue(excluded_from_setup_source_archive(path))

    def test_read_only_diagnostics_and_ordinary_release_files_remain(self):
        for path in (
            "scripts/rad_p2_preflight.py",
            "tests/test_rad_p2_preflight.py",
            "scripts/build_release.py",
            "scripts/release_source_inventory.py",
            "tests/test_release_source_inventory.py",
            "source/runtime/orbit_mcp.py",
            "tests/test_rad_defense.py",
            "docs/RAD-P2-LOCAL-PREVIEW-TRANSPORT.md",
            "Orbit.ps1",
        ):
            with self.subTest(path=path):
                self.assertFalse(excluded_from_setup_source_archive(path))

    def test_unsafe_archive_path_is_rejected(self):
        for path in ("", "../secret", "scripts/../secret", "/absolute", "a//b",
                     "a/./b", "a\\b", 123, None):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    excluded_from_setup_source_archive(path)


if __name__ == "__main__":
    unittest.main()
