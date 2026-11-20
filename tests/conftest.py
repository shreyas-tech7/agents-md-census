"""Shared test setup: an offline guard and a local fake API server."""

from __future__ import annotations

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
LOCAL = {"127.0.0.1", "localhost", "::1"}
_real_connect = socket.socket.connect
_real_getaddrinfo = socket.getaddrinfo
PROXY_VARS = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")


class NetworkBlocked(RuntimeError):
    pass


def _guarded_connect(self, address):
    host = address[0] if isinstance(address, tuple) else address
    if host not in LOCAL:
        raise NetworkBlocked(f"test tried to reach {host}")
    return _real_connect(self, address)


def _guarded_getaddrinfo(host, *args, **kw):
    if host not in LOCAL:
        raise NetworkBlocked(f"test tried to resolve {host}")
    return _real_getaddrinfo(host, *args, **kw)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """Fail any test that opens a connection to a host that is not local."""
    monkeypatch.setattr(socket.socket, "connect", _guarded_connect)
    monkeypatch.setattr(socket, "getaddrinfo", _guarded_getaddrinfo)
    for name in PROXY_VARS:
        monkeypatch.delenv(name, raising=False)


class FakeServer:
    """Serves scripted answers. routes maps a path to a list of
    (status, headers, body). Answers are used in order and the last repeats."""

    def __init__(self):
        self.routes: dict[str, list] = {}
        self.hits: list[str] = []
        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                server.hits.append(self.path)
                answers = (
                    server.routes.get(self.path)
                    or server.routes.get(self.path.split("?")[0])
                    or [(404, {}, "404: Not Found")]
                )
                status, headers, body = answers.pop(0) if len(answers) > 1 else answers[0]
                data = body.encode() if isinstance(body, str) else json.dumps(body).encode()
                self.send_response(status)
                for k, v in headers.items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def log_message(self, *a):
                pass

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def server():
    s = FakeServer()
    yield s
    s.close()


@pytest.fixture
def fixture_repos():
    return json.loads((FIXTURES / "repos.json").read_text())["repos"]


def serve_repos(server: FakeServer, repos: dict) -> None:
    for repo, files in repos.items():
        for path, body in files.items():
            server.routes[f"/{repo}/HEAD/{path}"] = [(200, {}, body)]


class FakeClock:
    """A clock that moves only when sleep() is called."""

    def __init__(self, start=1_000_000.0):
        self.now = start
        self.sleeps: list[float] = []

    def time(self):
        return self.now

    def sleep(self, s):
        self.sleeps.append(s)
        self.now += s
