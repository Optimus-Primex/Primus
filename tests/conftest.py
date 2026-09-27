"""Shared pytest fixtures."""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from primus import create_app
from primus.extensions import db as _db
from primus.models import Monitor, User


@pytest.fixture()
def app():
    application = create_app("testing")
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def db(app):
    return _db


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def user(app):
    account = User(username="alice", email="alice@example.com")
    account.set_password("password123")
    _db.session.add(account)
    _db.session.commit()
    return account


@pytest.fixture()
def other_user(app):
    account = User(username="bob", email="bob@example.com")
    account.set_password("password123")
    _db.session.add(account)
    _db.session.commit()
    return account


@pytest.fixture()
def auth_client(client, user):
    response = client.post("/login", data={"identity": "alice", "password": "password123"})
    assert response.status_code == 302
    return client


@pytest.fixture()
def api_headers(user):
    return {"Authorization": f"Bearer {user.api_token}"}


@pytest.fixture()
def sample_monitor(app, user):
    monitor = Monitor(
        user_id=user.id,
        name="Example",
        url="https://example.com/health",
        interval_seconds=60,
    )
    monitor.schedule_next()
    _db.session.add(monitor)
    _db.session.commit()
    return monitor


@pytest.fixture(scope="session")
def http_server():
    """A tiny HTTP server used to exercise the real checker over the network."""

    class Handler(BaseHTTPRequestHandler):
        def _respond(self, code: int, body: bytes) -> None:
            self.send_response(code)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def do_GET(self):  # noqa: N802 - http.server API
            if self.path == "/ok":
                self._respond(200, b"ok")
            elif self.path == "/bad":
                self._respond(500, b"boom")
            elif self.path == "/missing":
                self._respond(404, b"nope")
            else:
                self._respond(404, b"unknown")

        def do_HEAD(self):  # noqa: N802 - http.server API
            self._respond(200, b"")

        def log_message(self, *args):  # silence the test output
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
