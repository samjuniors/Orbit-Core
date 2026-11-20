"""In-memory, synthetic WSGI application for RAD P2 IPC acceptance only.

This module has no listener, sockets, arbitrary application import, filesystem
access, subprocesses, or MCP exposure. It proves actual Python WSGI request
handling can be encoded as a bounded IPC response; it does NOT prove a
production HTTP/browser preview or Windows AppContainer isolation.
"""
from __future__ import annotations

import base64
import io

from .protocol import (
    CONTENT_TYPES, IPCSecurityHold, MAX_BODY, MAX_REQUESTS,
    encode_envelope, parse_envelope, validate_local_path,
)

_HEALTH = b"ORBIT_ISOLATED_WSGI_OK\n"
_INDEX = (
    b'<!doctype html><html lang="en"><head><meta charset="utf-8">'
    b"<title>Orbit disposable WSGI fixture</title></head>"
    b"<body><h1>Orbit disposable WSGI fixture</h1></body></html>"
)


def application(environ, start_response):
    """A real WSGI callable with fixed synthetic routes and no side effects."""
    method = environ["REQUEST_METHOD"]
    path = environ["PATH_INFO"]
    if method not in ("GET", "HEAD"):
        status, content_type, body = ("405 Method Not Allowed",
                                      "text/plain; charset=utf-8", b"")
    elif path == "/health":
        status, content_type, body = ("200 OK", "text/plain; charset=utf-8", _HEALTH)
    elif path in ("/", "/index.html"):
        status, content_type, body = ("200 OK", "text/html; charset=utf-8", _INDEX)
    else:
        status, content_type, body = ("404 Not Found", "text/plain; charset=utf-8",
                                      b"Not Found\n")
    start_response(status, [("Content-Type", content_type),
                            ("Content-Length", str(len(body)))])
    return [b"" if method == "HEAD" else body]


def dispatch_fixture_request(data):
    """Consume one strict host request through a synthetic WSGI invocation.

    No external HTTP, preview port, file, header, URL, authentication value,
    or arbitrary Python project code can be supplied through this envelope.
    """
    msg = parse_envelope(data)
    if (set(msg) != {"v", "type", "seq", "method", "path"}
            or msg["type"] != "request"
            or type(msg["seq"]) is not int or not 1 <= msg["seq"] <= MAX_REQUESTS
            or type(msg["method"]) is not str or msg["method"] not in ("GET", "HEAD")):
        raise IPCSecurityHold("Invalid synthetic WSGI request")
    path = validate_local_path(msg["path"])
    captured = []

    def start_response(status, headers, exc_info=None):
        if captured or exc_info is not None:
            raise IPCSecurityHold("Unsupported synthetic WSGI headers")
        captured.append((status, headers))

    environ = {
        "REQUEST_METHOD": msg["method"], "SCRIPT_NAME": "",
        "PATH_INFO": path, "QUERY_STRING": "", "SERVER_NAME": "localhost",
        "SERVER_PORT": "0", "SERVER_PROTOCOL": "HTTP/1.1",
        "wsgi.version": (1, 0), "wsgi.url_scheme": "http",
        "wsgi.input": io.BytesIO(b""), "wsgi.errors": io.StringIO(),
        "wsgi.multithread": False, "wsgi.multiprocess": False,
        "wsgi.run_once": True,
    }
    parts = application(environ, start_response)
    buffer = bytearray()
    try:
        for part in parts:
            if type(part) is not bytes:
                raise IPCSecurityHold("WSGI response must contain bytes")
            buffer.extend(part)
            if len(buffer) > MAX_BODY:
                raise IPCSecurityHold("WSGI response exceeds IPC body limit")
    finally:
        if hasattr(parts, "close"):
            parts.close()
    if len(captured) != 1:
        raise IPCSecurityHold("WSGI did not provide an HTTP response")
    status, headers = captured[0]
    codes = {"200 OK": 200, "404 Not Found": 404}
    if type(status) is not str or status not in codes or type(headers) is not list:
        raise IPCSecurityHold("Unexpected WSGI status or headers")
    if len(headers) != 2 or headers[0][0] != "Content-Type" or headers[1][0] != "Content-Length":
        raise IPCSecurityHold("Unexpected WSGI metadata")
    content_type = headers[0][1]
    if type(content_type) is not str or content_type not in CONTENT_TYPES:
        raise IPCSecurityHold("Unsupported WSGI content type")
    if type(headers[1][1]) is not str or not headers[1][1].isdigit():
        raise IPCSecurityHold("Malformed WSGI content length")
    declared = int(headers[1][1])
    if (declared > MAX_BODY or
            (msg["method"] == "GET" and declared != len(buffer)) or
            (msg["method"] == "HEAD" and buffer)):
        raise IPCSecurityHold("WSGI content length or HEAD response mismatch")
    return encode_envelope({
        "v": 1, "type": "response", "seq": msg["seq"],
        "status": codes[status], "content_type": content_type,
        "body": base64.b64encode(buffer).decode("ascii"),
    })
