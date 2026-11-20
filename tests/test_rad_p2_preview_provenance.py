"""Non-invasive provenance and malformed-PE regressions for RAD P2 fixtures.

These tests never call the privileged AppContainer --apply path and never
modify the host Python installation or launch a native probe.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "rad_p2_disposable_host_acceptance.py"
SPEC = importlib.util.spec_from_file_location("orbit_rad_p2_provenance", SCRIPT)
HARNESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HARNESS)


def tiny_pe_manifest_fixture():
    """Synthetic PE32+ with a bounded single RT_MANIFEST resource type."""
    data = bytearray(0x500)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3c, 0x80)
    data[0x80:0x84] = b"PE\x00\x00"
    struct.pack_into("<H", data, 0x80 + 6, 1)
    struct.pack_into("<H", data, 0x80 + 20, 0xf0)
    opt = 0x80 + 24
    struct.pack_into("<H", data, opt, 0x20b)
    struct.pack_into("<II", data, opt + 128, 0x1000, 0x100)
    section = opt + 0xf0
    struct.pack_into("<IIII", data, section + 8, 0x100, 0x1000, 0x200, 0x200)
    struct.pack_into("<HH", data, 0x200 + 12, 0, 1)
    struct.pack_into("<II", data, 0x200 + 16, 24, 0x80000020)
    return data


class RADP2ProvenanceTests(unittest.TestCase):
    def test_operator_cannot_substitute_unreviewed_probe_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = root / "fake-probe.exe"
            fake.write_bytes(b"FAKE-TEST-ONLY")
            with patch.dict(os.environ, {"ORBIT_PROBE_EXECUTABLE": str(fake)}):
                with self.assertRaisesRegex(PermissionError, "override is forbidden"):
                    HARNESS.build_probe(root / "build")
            self.assertFalse((root / "build" / "probe.exe").exists())

    def test_override_rejected_even_with_empty_value(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"ORBIT_PROBE_EXECUTABLE": ""}):
                with self.assertRaises(PermissionError):
                    HARNESS.build_probe(Path(tmp) / "build")

    def test_valid_synthetic_manifest_is_modified_only_in_disposable_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = Path(tmp) / "original.dll"
            staged = Path(tmp) / "staged.dll"
            payload = tiny_pe_manifest_fixture()
            original.write_bytes(payload)
            staged.write_bytes(payload)
            self.assertTrue(HARNESS._neutralize_pe_manifest(staged))
            self.assertEqual(original.read_bytes(), payload)
            updated = staged.read_bytes()
            self.assertEqual(len(updated), len(payload))
            self.assertEqual(struct.unpack_from("<I", updated, 0x210)[0], 0x7fff)
            self.assertEqual(updated[:0x210], payload[:0x210])
            self.assertEqual(updated[0x214:], payload[0x214:])
            self.assertFalse(HARNESS._neutralize_pe_manifest(staged))

    def test_bad_headers_and_out_of_bounds_sections_never_mutate(self):
        valid = tiny_pe_manifest_fixture()
        cases = {}
        def modify(name, offset, fmt, value):
            buf = bytearray(valid)
            struct.pack_into(fmt, buf, offset, value)
            cases[name] = bytes(buf)
        modify("invalid_magic", 0x98, "<H", 0)
        modify("too_many_sections", 0x80 + 6, "<H", 1000)
        modify("truncated_optional_header", 0x80 + 20, "<H", 12)
        modify("section_table_outside_file", 0x80 + 20, "<H", 0x400)
        modify("resource_outside_section", 0x98 + 128, "<I", 0x5000)
        modify("resource_exceeds_raw_section", 0x98 + 128 + 4, "<I", 0x400)
        modify("resource_entry_overrun", 0x200 + 14, "<H", 8192)
        modify("resource_raw_pointer_overrun", 0x188 + 20, "<I", 0x1000)
        modify("invalid_signature", 0x80, "<I", 0)
        with tempfile.TemporaryDirectory() as tmp:
            candidate = Path(tmp) / "candidate.dll"
            for name, payload in cases.items():
                with self.subTest(name=name):
                    candidate.write_bytes(payload)
                    self.assertFalse(HARNESS._neutralize_pe_manifest(candidate))
                    self.assertEqual(candidate.read_bytes(), payload)

    def test_symlink_not_used_as_manifest_patch_target(self):
        if not hasattr(Path, "symlink_to"):
            self.skipTest("Symlinks unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            real = Path(tmp) / "actual.dll"
            alias = Path(tmp) / "alias.dll"
            payload = tiny_pe_manifest_fixture()
            real.write_bytes(payload)
            try:
                alias.symlink_to(real)
            except (OSError, NotImplementedError):
                self.skipTest("Symlink creation is not authorized here")
            self.assertFalse(HARNESS._neutralize_pe_manifest(alias))
            self.assertEqual(real.read_bytes(), payload)


if __name__ == "__main__":
    unittest.main()
