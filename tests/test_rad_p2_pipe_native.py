"""No privileged operations: verify RAD P2 experimental pipe refuses unsafe input.

The CI matrix does not create AppContainer profiles, alter real ACLs or launch
an LPAC Python app. Actual Windows named-pipe interoperability remains HOLD.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from rad_p2_preview_ipc import protocol as ipc
from rad_p2_preview_ipc import winpipe as native
from rad_p2_preview_ipc import client


class TestLPACPipeFailClosed(unittest.TestCase):
    def test_only_expected_sid_syntax_accepted(self):
        for bad in (
            "S-1-15-2-123)(A;;GA;;;WD)",
            "S-1-15-2-123\nD:(A;;GA;;;WD)",
            "S-1-15-2-123;",
            "EVERYONE", "", 123, None,
        ):
            with self.subTest(bad=bad), self.assertRaises(ipc.IPCSecurityHold):
                native._pipe_descriptor(bad, "S-1-15-2-123")

    def test_untrusted_profile_is_rejected_before_native_effects(self):
        for name in ("", "other-profile", "../orbit-rad-a", None):
            with self.subTest(name=name), self.assertRaises(ipc.IPCSecurityHold):
                native._trusted_profile_sid(name)

    def test_pipe_does_not_offer_cross_platform_fallback(self):
        if os.name == "nt":
            self.skipTest("Windows native behavior checked separately")
        with self.assertRaises(ipc.IPCSecurityHold):
            native.DisposableLPACPipe(profile="orbit-rad-fake")
        with self.assertRaises(ipc.IPCSecurityHold):
            native._current_user_sid()

    def test_bounded_child_client_never_accepts_injected_pipe_name(self):
        self.assertEqual(client.main([]), 2)
        valid = "\\\\.\\pipe\\LOCAL\\orbit-rad-p2-" + "a" * 32
        self.assertTrue(client._PIPE_NAME.fullmatch(valid))
        for path in ("", "http://127.0.0.1/", "\\\\evil\\pipe\\PWN",
                     valid + "..", "\\\\.\\pipe\\LOCAL\\another"):
            with self.subTest(path=path), self.assertRaises(ipc.IPCSecurityHold):
                client.disposable_child_hello(path, expected_server_pid=1)

    @unittest.skipUnless(os.name == "nt", "Windows only")
    def test_unregistered_profile_does_not_create_pipe(self):
        import secrets
        missing = "orbit-rad-ci-not-registered-" + secrets.token_hex(12)
        with self.assertRaises(ipc.IPCSecurityHold):
            native.DisposableLPACPipe(profile=missing)


if __name__ == "__main__":
    unittest.main()
