"""Pure deterministic tests for the non-installed RAD P2 WSGI-over-IPC fixture.

These do NOT provision AppContainers, start HTTP listeners or exercise a
privileged Windows kernel pipe. Native acceptance remains NOT VERIFIED.
"""
from __future__ import annotations

import base64
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from rad_p2_preview_ipc import protocol
from rad_p2_preview_ipc import fixture_wsgi


class SyntheticWSGIOverIPC(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve(strict=True)
        self.session = protocol.PreviewIPCSession(
            profile="orbit-rad-fixture", child_pid=1234, session_id=2,
            project_root=self.root, max_requests=5)
        self.peer = protocol.OSVerifiedPeer(
            1234, 2, "orbit-rad-fixture",
            _native_origin=protocol._OS_ATTESTATION)
        hello = protocol.encode_envelope({
            "v": 1, "type": "hello", "nonce": self.session.nonce})
        self.session.challenge()
        self.assertEqual(
            self.session.accept_hello(hello, self.peer)["status"],
            "HANDSHAKE_VERIFIED_NOT_READY")

    def roundtrip(self, method, path):
        request = self.session.begin_host_request(
            method=method, path=path, peer=self.peer)
        response = fixture_wsgi.dispatch_fixture_request(request)
        return self.session.accept_response(response, self.peer)

    def test_actual_synthetic_wsgi_health_response(self):
        result = self.roundtrip("GET", "/health")
        self.assertEqual(result["status"], 200)
        self.assertEqual(result["body"], b"ORBIT_ISOLATED_WSGI_OK\n")
        self.assertEqual(result["content_type"], "text/plain; charset=utf-8")
        self.assertIs(result["preview_ready"], False)
        self.assertNotIn("url", result)

    def test_index_head_and_not_found_routes(self):
        index = self.roundtrip("GET", "/")
        self.assertEqual(index["status"], 200)
        self.assertIn(b"Orbit disposable WSGI fixture", index["body"])
        head = self.roundtrip("HEAD", "/index.html")
        self.assertEqual(head["status"], 200)
        self.assertEqual(head["body"], b"")
        missing = self.roundtrip("GET", "/not-present")
        self.assertEqual(missing["status"], 404)
        self.assertEqual(missing["body"], b"Not Found\n")

    def test_host_request_requires_strict_methods_and_paths(self):
        for method, path in (
            ("POST", "/health"), ("CONNECT", "/health"), ("GET", "//evil"),
            ("GET", "/../secrets"), ("GET", "http://localhost/private"),
            ("GET", "/file?token=secret"), ("GET", "/%2e%2e/"),
            ("GET", "/a\\b"), ("GET", "/a#fragment"),
        ):
            with self.subTest(method=method, path=path):
                with self.assertRaises(protocol.IPCSecurityHold):
                    self.session.begin_host_request(
                        method=method, path=path, peer=self.peer)
        self.assertIsNone(self.session._pending)

    def test_replayed_or_wrong_sequence_is_denied(self):
        request = self.session.begin_host_request(
            method="GET", path="/health", peer=self.peer)
        with self.assertRaises(protocol.IPCSecurityHold):
            self.session.begin_host_request(
                method="GET", path="/health", peer=self.peer)
        valid = protocol.parse_envelope(
            fixture_wsgi.dispatch_fixture_request(request))
        valid["seq"] = 17
        with self.assertRaises(protocol.IPCSecurityHold):
            self.session.accept_response(protocol.encode_envelope(valid), self.peer)
        self.assertEqual(self.session._pending, 1)
        self.session.accept_response(
            fixture_wsgi.dispatch_fixture_request(request), self.peer)

    def test_expired_closed_and_unverified_peer_stay_blocked(self):
        self.session.close()
        with self.assertRaises(protocol.IPCSecurityHold):
            self.session.begin_host_request(
                method="GET", path="/health", peer=self.peer)
        with self.assertRaises(protocol.IPCSecurityHold):
            protocol.OSVerifiedPeer(1234, 2, "orbit-rad-fixture")

    def test_fixture_rejects_extra_headers_or_ambiguous_fields(self):
        cases = (
            {"v": 1, "type": "request", "seq": 1, "method": "GET", "path": "/health",
             "Authorization": "Bearer secret"},
            {"v": 1, "type": "request", "seq": 1, "method": "POST", "path": "/health"},
            {"v": 1, "type": "request", "seq": True, "method": "GET", "path": "/health"},
            {"v": 1, "type": "request", "seq": 1, "method": "GET", "path": "/../"},
            {"v": 1, "type": "request", "seq": 0, "method": "GET", "path": "/health"},
        )
        for entry in cases:
            with self.subTest(entry=entry), self.assertRaises(protocol.IPCSecurityHold):
                fixture_wsgi.dispatch_fixture_request(protocol.encode_envelope(entry))
        with self.assertRaises(protocol.IPCSecurityHold):
            fixture_wsgi.dispatch_fixture_request(
                b'{"v":1,"type":"request","seq":1,"seq":1,"method":"GET","path":"/"}')

    def test_untrusted_wsgi_app_may_not_emit_oversized_response(self):
        def oversized(environ, start_response):
            start_response("200 OK", [
                ("Content-Type", "text/plain; charset=utf-8"),
                ("Content-Length", str(protocol.MAX_BODY + 1))])
            return [b"x" * (protocol.MAX_BODY + 1)]
        raw = protocol.encode_envelope({
            "v": 1, "type": "request", "seq": 1,
            "method": "GET", "path": "/"})
        with patch.object(fixture_wsgi, "application", oversized):
            with self.assertRaises(protocol.IPCSecurityHold):
                fixture_wsgi.dispatch_fixture_request(raw)

    def test_disposable_ipc_never_imported_by_installed_runtime(self):
        source = Path(__file__).resolve().parents[1] / "source" / "runtime"
        modules = list(source.glob("*.py"))
        self.assertTrue(modules)
        for module in modules:
            with self.subTest(module=module.name):
                self.assertNotIn("rad_p2_preview_ipc",
                                 module.read_text(encoding="utf-8"))
        # No prototype file may appear in installer-managed shared runtime.
        self.assertFalse((source / "fixture_wsgi.py").exists())
        self.assertFalse((source / "rad_p2_preview_ipc").exists())

    def test_no_socket_or_external_file_activity_in_fixture(self):
        with patch("socket.socket", side_effect=AssertionError("network used")):
            self.assertEqual(self.roundtrip("GET", "/health")["status"], 200)
        self.assertEqual(list(self.root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
