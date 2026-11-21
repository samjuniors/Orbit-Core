"""Non-privileged local-loopback acceptance tests for disposable HTTP snapshot.

Only the synthetic WSGI callable is exercised. No AppContainer is created;
no host credentials, IDE permission, remote traffic or preview READY exists.
"""
from __future__ import annotations

import http.client
from pathlib import Path
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from rad_p2_preview_ipc import protocol, fixture_wsgi, http_snapshot


class TestDisposableBrowserSnapshot(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve(strict=True)
        self.session = protocol.PreviewIPCSession(
            profile="orbit-rad-web-fixture", child_pid=1234,
            session_id=2, project_root=self.root)
        self.peer = protocol.OSVerifiedPeer(
            1234, 2, "orbit-rad-web-fixture",
            _native_origin=protocol._OS_ATTESTATION)
        self.session.challenge()
        self.session.accept_hello(protocol.encode_envelope({
            "v": 1, "type": "hello", "nonce": self.session.nonce,
        }), self.peer)

    def snapshot(self, path="/health", method="GET"):
        outgoing = self.session.begin_host_request(
            method=method, path=path, peer=self.peer)
        response = self.session.accept_response(
            fixture_wsgi.dispatch_fixture_request(outgoing), self.peer)
        return http_snapshot.BrowserSnapshot.from_ipc_response(response)

    def request_once(self, snapshot, *, path=None, method="GET", headers=None):
        with http_snapshot.DisposableBrowserSnapshot(
                snapshot, lifetime_seconds=3) as viewer:
            self.assertEqual(viewer._server.server_address[0], "127.0.0.1")
            self.assertTrue(viewer.url.startswith("http://127.0.0.1:"))
            target = viewer._path if path is None else path
            worker = threading.Thread(target=viewer.serve_once, daemon=True)
            worker.start()
            conn = http.client.HTTPConnection("127.0.0.1", viewer.port, timeout=3)
            try:
                conn.request(method, target, headers=headers or {})
                response = conn.getresponse()
                body = response.read()
                result = {
                    "status": response.status, "body": body,
                    "headers": dict(response.getheaders()),
                    "viewer_url": viewer.url,
                }
            finally:
                conn.close()
                worker.join(timeout=4)
            self.assertFalse(worker.is_alive(), "One-shot HTTP server did not close")
            self.assertTrue(viewer._closed)
            return result

    def test_verified_fixture_health_becomes_host_owned_http_snapshot(self):
        snap = self.snapshot()
        actual = self.request_once(snap)
        self.assertEqual(actual["status"], 200)
        self.assertEqual(actual["body"], b"ORBIT_ISOLATED_WSGI_OK\n")
        self.assertEqual(actual["headers"]["Content-Type"],
                         "text/plain; charset=utf-8")
        self.assertEqual(int(actual["headers"]["Content-Length"]),
                         len(actual["body"]))
        self.assertEqual(actual["headers"]["X-Content-Type-Options"], "nosniff")
        self.assertEqual(actual["headers"]["Referrer-Policy"], "no-referrer")
        self.assertIn("sandbox;", actual["headers"]["Content-Security-Policy"])
        self.assertNotIn("Access-Control-Allow-Origin", actual["headers"])
        self.assertNotIn("Set-Cookie", actual["headers"])
        self.assertNotIn("/orbit-rad-preview/", actual["body"].decode())
        self.assertNotIn("READY", actual["headers"])

    def test_html_is_csp_sandboxed(self):
        snap = self.snapshot("/")
        actual = self.request_once(snap)
        self.assertEqual(actual["status"], 200)
        self.assertIn(b"Orbit disposable WSGI fixture", actual["body"])
        self.assertEqual(actual["headers"]["Content-Type"],
                         "text/html; charset=utf-8")
        self.assertIn("default-src 'none'", actual["headers"]["Content-Security-Policy"])

    def test_host_rejects_dns_rebinding_origin_cookie_and_referer(self):
        for hostile in (
            {"Host": "attacker.test:9999"},
            {"Origin": "https://attacker.test"},
            {"Referer": "https://attacker.test/"},
            {"Cookie": "session=secret"},
            {"Authorization": "Bearer fake"},
            {"Proxy-Authorization": "Basic fake"},
            {"X-Forwarded-Host": "attacker.test"},
            {"Sec-Fetch-Site": "cross-site"},
        ):
            with self.subTest(hostile=hostile):
                actual = self.request_once(self.snapshot(), headers=hostile)
                self.assertEqual(actual["status"], 403)
                self.assertEqual(actual["body"], b"")
                self.assertNotIn(b"ORBIT_ISOLATED_WSGI_OK", actual["body"])

    def test_duplicate_host_header_is_rejected_as_dns_rebinding_attempt(self):
        with http_snapshot.DisposableBrowserSnapshot(self.snapshot()) as viewer:
            worker = threading.Thread(target=viewer.serve_once, daemon=True)
            worker.start()
            conn = http.client.HTTPConnection("127.0.0.1", viewer.port, timeout=3)
            try:
                conn.putrequest("GET", viewer._path, skip_host=True)
                conn.putheader("Host", f"127.0.0.1:{viewer.port}")
                conn.putheader("Host", "attacker.test")
                conn.endheaders()
                response = conn.getresponse()
                self.assertEqual(response.status, 403)
                self.assertEqual(response.read(), b"")
            finally:
                conn.close()
                worker.join(timeout=4)
            self.assertFalse(worker.is_alive())

    def test_bearer_url_exact_path_no_queries_or_fake_routes(self):
        for path in (
            "/orbit-rad-preview/wrong", "/", "/health",
            "//evil.test/", "http://127.0.0.1/", "/../credentials",
        ):
            with self.subTest(path=path):
                actual = self.request_once(self.snapshot(), path=path)
                self.assertEqual(actual["status"], 403)
        with http_snapshot.DisposableBrowserSnapshot(self.snapshot()) as viewer:
            invalid = viewer._path + "?copy=1"
            worker = threading.Thread(target=viewer.serve_once, daemon=True)
            worker.start()
            conn = http.client.HTTPConnection("127.0.0.1", viewer.port, timeout=3)
            try:
                conn.request("GET", invalid)
                self.assertEqual(conn.getresponse().status, 403)
            finally:
                conn.close()
                worker.join(timeout=4)
            self.assertFalse(worker.is_alive())

    def test_post_denied_and_head_has_no_body(self):
        for method in ("POST", "PUT", "DELETE", "TRACE", "PATCH", "OPTIONS"):
            with self.subTest(method=method):
                response = self.request_once(self.snapshot(), method=method)
                self.assertEqual(response["status"], 403)
                self.assertEqual(response["body"], b"")
        response = self.request_once(self.snapshot(), method="HEAD")
        self.assertEqual(response["status"], 200)
        self.assertEqual(response["body"], b"")
        self.assertEqual(int(response["headers"]["Content-Length"]),
                         len(b"ORBIT_ISOLATED_WSGI_OK\n"))

    def test_direct_snapshot_object_cannot_bypass_bounded_validation(self):
        for args in (
            (True, "text/plain; charset=utf-8", b"ok"),
            (200, "text/plain; charset=utf-8\\r\\nX-Evil: 1", b"ok"),
            (200, "text/plain; charset=utf-8", b"x" * (protocol.MAX_BODY + 1)),
        ):
            with self.subTest(args=str(args)[:50]):
                with self.assertRaises(protocol.IPCSecurityHold):
                    http_snapshot.BrowserSnapshot(*args)

    def test_invalid_snapshot_cannot_be_served(self):
        good = {
            "status": 200, "content_type": "text/plain; charset=utf-8",
            "body": b"example", "preview_ready": False,
        }
        for bad in (
            dict(good, status=True),
            dict(good, content_type="application/octet-stream"),
            dict(good, body="not-bytes"),
            dict(good, body=b"x" * (protocol.MAX_BODY + 1)),
            dict(good, preview_ready=True),
            dict(good, extra_field=1),
        ):
            with self.subTest(bad=str(bad)[:40]):
                with self.assertRaises(protocol.IPCSecurityHold):
                    http_snapshot.BrowserSnapshot.from_ipc_response(bad)

    def test_cannot_reactivate_server_or_mark_preview_ready(self):
        with http_snapshot.DisposableBrowserSnapshot(self.snapshot()) as viewer:
            self.assertFalse(viewer._started)
            self.assertFalse(viewer._used)
            self.assertNotIn("READY", viewer.url)
        with self.assertRaises(protocol.IPCSecurityHold):
            viewer.__enter__()
        with self.assertRaises(protocol.IPCSecurityHold):
            viewer.serve_once()

    def test_timeout_closes_listener_without_request(self):
        with http_snapshot.DisposableBrowserSnapshot(
                self.snapshot(), lifetime_seconds=0.2) as viewer:
            state = viewer.serve_once()
            self.assertEqual(state["status"], "BROWSER_SNAPSHOT_EXPIRED_NOT_READY")
            self.assertFalse(state["request_consumed"])
            self.assertFalse(state["preview_ready"])
            self.assertTrue(viewer._closed)

    def test_prototype_remains_absent_from_installed_runtime(self):
        source = Path(__file__).resolve().parents[1] / "source" / "runtime"
        for module in source.glob("*.py"):
            with self.subTest(module=module.name):
                self.assertNotIn("rad_p2_preview_ipc",
                                 module.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
