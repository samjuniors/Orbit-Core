"""Disposable, host-owned browser snapshot of a bounded IPC WSGI response.

Inactive research prototype. It never imports into Orbit's MCP runtime,
opens a listener at import time, or reports preview READY. Only an explicitly
constructed instance binds IPv4 loopback for one request and a short deadline.
The bytes must first come from a separately verified IPC transcript; this
module cannot itself attest native LPAC/pipe ownership.
"""
from __future__ import annotations

from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
import secrets
import time

from .protocol import CONTENT_TYPES, IPCSecurityHold, MAX_BODY

MAX_BROWSER_SECONDS = 10
MAX_HEADER_BYTES = 4096
MAX_HEADER_FIELDS = 20
_CSP = "sandbox; default-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"


@dataclass(frozen=True)
class BrowserSnapshot:
    status: int
    content_type: str
    body: bytes

    def __post_init__(self):
        if (type(self.status) is not int or self.status not in (200, 404, 500)
                or type(self.content_type) is not str
                or self.content_type not in CONTENT_TYPES
                or type(self.body) is not bytes or len(self.body) > MAX_BODY):
            raise IPCSecurityHold("Invalid bounded HTTP snapshot content")

    @classmethod
    def from_ipc_response(cls, result):
        """Convert only the bounded response shape from PreviewIPCSession.

        The caller must provide the result of a *verified* native IPC receipt.
        A plain dict is NOT an identity attestation; use is experimental only.
        """
        if (type(result) is not dict
                or set(result) != {"status", "content_type", "body", "preview_ready"}
                or type(result["status"]) is not int
                or result["status"] not in (200, 404, 500)
                or type(result["content_type"]) is not str
                or result["content_type"] not in CONTENT_TYPES
                or type(result["body"]) is not bytes
                or len(result["body"]) > MAX_BODY
                or result["preview_ready"] is not False):
            raise IPCSecurityHold("Unverified or unbounded synthetic browser snapshot")
        return cls(result["status"], result["content_type"], result["body"])


class _LoopbackHTTPServer(HTTPServer):
    allow_reuse_address = False
    request_queue_size = 1


class DisposableBrowserSnapshot:
    """One-use loopback HTTP viewer for fixed, previously obtained IPC bytes.

    A failed or rejected HTTP attempt consumes the single request. This is a
    strict smoke-test viewer, not a live arbitrary-project app or an HTTP proxy.
    """

    def __init__(self, snapshot, *, lifetime_seconds=3):
        if type(snapshot) is not BrowserSnapshot:
            raise IPCSecurityHold("Browser fixture requires a bounded IPC snapshot")
        if (type(lifetime_seconds) not in (int, float)
                or not 0 < lifetime_seconds <= MAX_BROWSER_SECONDS):
            raise IPCSecurityHold("Browser fixture lifetime exceeds policy")
        self._snapshot = snapshot
        self._lifetime = lifetime_seconds
        self._token = secrets.token_hex(24)
        self._server = None
        self._used = False
        self._started = False
        self._closed = False

    def __enter__(self):
        if self._server is not None or self._closed:
            raise IPCSecurityHold("Browser fixture cannot be reopened")
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.0"
            server_version = "OrbitDisposableHTTP"
            sys_version = ""

            def log_message(self, *_):
                # Never log a bearer path, token, source HTML or browser header.
                return None

            def do_GET(self):
                self._respond(send_body=True)

            def do_HEAD(self):
                self._respond(send_body=False)

            def do_POST(self):
                self._reject()

            def do_OPTIONS(self):
                self._reject()

            def _reject(self):
                owner._used = True
                self.send_response_only(403)
                self.send_header("Content-Length", "0")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Connection", "close")
                self.end_headers()
                self.close_connection = True

            def _respond(self, *, send_body):
                owner._used = True
                headers = self.headers
                expected_host = f"127.0.0.1:{owner.port}"
                raw_headers = headers.items()
                if (self.client_address[0] != "127.0.0.1"
                        or self.path != owner._path
                        or headers.get_all("Host", []) != [expected_host]
                        or headers.get_all("Sec-Fetch-Site", []) not in (
                            [], ["none"], ["same-origin"])
                        or len(self.raw_requestline) > 512
                        or len(raw_headers) > MAX_HEADER_FIELDS
                        or sum(len(k) + len(v) for k, v in raw_headers) > MAX_HEADER_BYTES
                        or any(headers.get(h) is not None for h in (
                            "Origin", "Referer", "Cookie", "Authorization",
                            "Proxy-Authorization", "Content-Length",
                            "Transfer-Encoding", "Upgrade", "Forwarded"))
                        or any(k.lower().startswith("x-forwarded-") for k, _ in raw_headers)):
                    self._reject()
                    return
                snapshot = owner._snapshot
                self.send_response_only(snapshot.status)
                self.send_header("Content-Type", snapshot.content_type)
                self.send_header("Content-Length", str(len(snapshot.body)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Cache-Control", "no-store, private")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("Content-Security-Policy", _CSP)
                self.send_header("X-Frame-Options", "DENY")
                self.send_header("Cross-Origin-Resource-Policy", "same-origin")
                self.send_header("Connection", "close")
                self.end_headers()
                if send_body:
                    self.wfile.write(snapshot.body)
                self.close_connection = True

        # Python's HTTPServer is a convenience protocol parser, not a
        # production-hardened web front end. We do not expose arbitrary apps.
        self._server = _LoopbackHTTPServer(("127.0.0.1", 0), Handler)
        self._server.timeout = 0.1
        self.port = self._server.server_address[1]
        self._path = "/orbit-rad-preview/" + self._token
        self.url = f"http://127.0.0.1:{self.port}{self._path}"
        return self

    def serve_once(self):
        if self._server is None or self._closed or self._started:
            raise IPCSecurityHold("Browser fixture not active or already consumed")
        self._started = True
        deadline = time.monotonic() + self._lifetime
        try:
            while not self._used and time.monotonic() < deadline:
                self._server.handle_request()
        finally:
            self.close()
        return {"status": "BROWSER_SNAPSHOT_EXPIRED_NOT_READY",
                "request_consumed": self._used, "preview_ready": False}

    def close(self):
        if not self._closed:
            self._closed = True
            if self._server is not None:
                self._server.server_close()

    def __exit__(self, *_):
        self.close()
