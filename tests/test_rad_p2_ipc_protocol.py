"""Pure, nonprivileged coverage of RAD P2 bounded IPC transcript.

This is a protocol test, not privileged Windows AppContainer/transport QA.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from rad_p2_preview_ipc import protocol as ipc


class TestBoundedPreviewIPC(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve(strict=True)
        self.t = [100.0]
        self.gate = ipc.PreviewIPCSession(
            profile="orbit-rad-example", child_pid=123, session_id=7,
            project_root=self.root, max_requests=2, now=lambda: self.t[0])
        self.peer = self.proof(123, 7, "orbit-rad-example")

    def proof(self, pid, session, profile):
        # Test-only minting; production creates this only after Win32 API checks.
        return ipc.OSVerifiedPeer(pid, session, profile,
                                  _native_origin=ipc._OS_ATTESTATION)

    def msg(self, **fields):
        return ipc.encode_envelope({"v": 1, **fields})

    def hello(self):
        data = self.msg(type="hello", nonce=self.gate.nonce)
        return self.gate.accept_hello(data, self.peer)

    def test_does_not_launch_bind_or_claim_ready(self):
        result = self.hello()
        self.assertEqual(result["status"], "HANDSHAKE_VERIFIED_NOT_READY")
        self.assertIs(result["preview_ready"], False)
        self.assertIs(result["host_approval_verified"], False)
        self.assertNotIn("url", result)

    def test_one_shot_handshake_replay_rejected(self):
        self.hello()
        with self.assertRaises(ipc.IPCSecurityHold):
            self.hello()

    def test_challenge_fresh_per_session(self):
        gate2 = ipc.PreviewIPCSession(
            profile="orbit-rad-example", child_pid=123, session_id=7,
            project_root=self.root)
        self.assertNotEqual(self.gate.nonce, gate2.nonce)
        self.assertEqual(ipc.parse_envelope(self.gate.challenge())["type"], "challenge")
        with self.assertRaises(ipc.IPCSecurityHold):
            self.gate.accept_hello(self.msg(type="hello", nonce=gate2.nonce), self.peer)

    def test_public_peer_receipt_cannot_be_constructed_from_claims(self):
        with self.assertRaises(ipc.IPCSecurityHold):
            ipc.OSVerifiedPeer(123, 7, "orbit-rad-example")
        with self.assertRaises(ipc.IPCSecurityHold):
            ipc.OSVerifiedPeer(123, 7, "orbit-rad-example", _native_origin="yes")

    def test_wrong_peer_profile_pid_session_holds(self):
        msg = self.msg(type="hello", nonce=self.gate.nonce)
        for peer in (None, {}, self.proof(124, 7, "orbit-rad-example"),
                     self.proof(123, 8, "orbit-rad-example"),
                     self.proof(123, 7, "orbit-rad-other")):
            with self.subTest(peer=peer), self.assertRaises(ipc.IPCSecurityHold):
                self.gate.accept_hello(msg, peer)

    def test_expired_or_closed_session_holds(self):
        self.t[0] = 130.0
        with self.assertRaises(ipc.IPCSecurityHold):
            self.hello()
        self.t[0] = 100.0
        self.gate.close()
        with self.assertRaises(ipc.IPCSecurityHold):
            self.hello()

    def test_cannot_request_before_attestation(self):
        with self.assertRaises(ipc.IPCSecurityHold):
            self.gate.accept_request(self.msg(type="request", seq=1, method="GET", path="/"), self.peer)

    def test_one_bounded_request_and_reply(self):
        self.hello()
        request = self.gate.accept_request(self.msg(type="request", seq=1, method="GET",
                                                    path="/index.html"), self.peer)
        self.assertEqual(request["path"], "/index.html")
        self.assertIs(request["approved_for_execution"], False)
        reply = self.gate.accept_response(self.msg(
            type="response", seq=1, status=200,
            content_type="text/plain; charset=utf-8",
            body=base64.b64encode(b"OK").decode()), self.peer)
        self.assertEqual(reply["body"], b"OK")
        self.assertIs(reply["preview_ready"], False)
        self.gate.accept_request(self.msg(type="request", seq=2, method="HEAD", path="/"), self.peer)
        self.gate.accept_response(self.msg(type="response", seq=2, status=404,
                                           content_type="application/json", body=""), self.peer)
        with self.assertRaises(ipc.IPCSecurityHold):
            self.gate.accept_request(self.msg(type="request", seq=3,
                                              method="GET", path="/"), self.peer)

    def test_same_request_cannot_be_pipelined_or_replayed(self):
        self.hello()
        request = self.msg(type="request", seq=1, method="GET", path="/")
        self.gate.accept_request(request, self.peer)
        with self.assertRaises(ipc.IPCSecurityHold):
            self.gate.accept_request(request, self.peer)
        self.gate.accept_response(self.msg(type="response", seq=1, status=200,
                                           content_type="application/json", body=""), self.peer)
        with self.assertRaises(ipc.IPCSecurityHold):
            self.gate.accept_request(request, self.peer)

    def test_reject_ssrf_traversal_query_and_public_bind(self):
        self.hello()
        bad = ("http://example.org/", "https://127.0.0.1/", "//evil", "/..",
               "/a/../b", "/a/./b", "/a\\b", "/a?token=1", "/a#anchor",
               "/%2e%2e/", "/%2Fetc", "/a//b", "\r\n", "/é")
        for path in bad:
            with self.subTest(path=path), self.assertRaises(ipc.IPCSecurityHold):
                self.gate.accept_request(self.msg(type="request", seq=1,
                                                  method="GET", path=path), self.peer)

    def test_reject_arbitrary_methods_and_extra_headers(self):
        self.hello()
        for field in (
            {"method": "POST", "path": "/"},
            {"method": "CONNECT", "path": "/"},
            {"method": "GET", "path": "/", "host": "evil.com"},
            {"method": "GET", "path": "/", "authorization": "bearer x"},
        ):
            with self.subTest(field=field), self.assertRaises(ipc.IPCSecurityHold):
                self.gate.accept_request(self.msg(type="request", seq=1, **field), self.peer)

    def test_reject_duplicate_json_keys_and_malformed_bytes(self):
        cases = (b'{"v":1,"v":1,"type":"hello"}', b'{"v":1,"type":',
                 b'\xff', b'{"v":1,"type":"hello","nonce":1}', b'[]', b'',
                 b' ' * (ipc.MAX_ENVELOPE + 1))
        for raw in cases:
            with self.subTest(raw=raw[:50]), self.assertRaises(ipc.IPCSecurityHold):
                self.gate.accept_hello(raw, self.peer)

    def test_response_rejects_oversized_or_unapproved_payload(self):
        self.hello()
        self.gate.accept_request(self.msg(type="request", seq=1, method="GET", path="/"), self.peer)
        examples = (
            {"status": 302, "content_type": "text/html; charset=utf-8", "body": ""},
            {"status": 200, "content_type": "image/svg+xml", "body": ""},
            {"status": 200, "content_type": "text/plain; charset=utf-8", "body": "###"},
            {"status": 200, "content_type": "text/plain; charset=utf-8",
             "body": base64.b64encode(b"X" * (ipc.MAX_BODY + 1)).decode()},
        )
        for fields in examples:
            with self.subTest(fields=str(fields)[:50]), self.assertRaises(ipc.IPCSecurityHold):
                self.gate.accept_response(self.msg(type="response", seq=1, **fields), self.peer)
        self.assertEqual(self.gate._pending, 1)

    def test_noncanonical_or_symlink_root_holds(self):
        with self.assertRaises(ipc.IPCSecurityHold):
            ipc.PreviewIPCSession(profile="orbit-rad-test", child_pid=1, session_id=1,
                                  project_root="relative/path")
        sub = self.root / "sub"
        sub.mkdir()
        with self.assertRaises(ipc.IPCSecurityHold):
            ipc.PreviewIPCSession(profile="orbit-rad-test", child_pid=1, session_id=1,
                                  project_root=sub / "..")

    def test_native_verifier_never_falls_back_to_pid_claim(self):
        if sys.platform == "win32":
            with self.assertRaises(ipc.IPCSecurityHold):
                ipc.verify_connected_pipe_peer(0, child=None, job=None, profile="orbit-rad-test")
        else:
            with self.assertRaises(ipc.IPCSecurityHold):
                ipc.verify_connected_pipe_peer(1, child=object(), job=object(), profile="orbit-rad-test")

    def test_protocol_not_wired_to_production_preview(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source" / "runtime"))
        import orbit_preview
        self.assertNotIn("rad_p2_preview_ipc", orbit_preview.start.__code__.co_names)
        self.assertIn("HOLD_OS_ISOLATION_ENDPOINT_UNVERIFIED",
                      orbit_preview.start.__code__.co_consts)


if __name__ == "__main__":
    unittest.main()
