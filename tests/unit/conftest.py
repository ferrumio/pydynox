"""Shared fixtures for unit tests.

Unit tests should NOT use moto server or real DynamoDB.
They use mocks instead.
"""

import json
import threading
from collections.abc import Callable, Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import pytest
from pydynox import clear_default_client


@pytest.fixture(autouse=True)
def reset_default_client():
    """Reset default client before and after each test."""
    clear_default_client()
    yield
    clear_default_client()


_ERROR_PREFIX = "com.amazonaws.dynamodb.v20120810#"


class FakeDynamoDB:
    """Local HTTP server that acts as DynamoDB, so the real Rust core runs without Docker.

    ``scripts`` maps an operation name (the part after the dot in X-Amz-Target,
    for example ``"DescribeTable"``) to a list of outcomes. Each request to that
    operation takes the next outcome. The last outcome repeats once the list is
    used up. An outcome is one of:

    - a dict: sent as the body of a 200 response
    - a str: a DynamoDB error type such as ``"ResourceNotFoundException"``, sent as a 400
    - a ``(status, dict)`` tuple: sent as is

    An operation with no script answers 200 with an empty body.
    Requests are kept in ``requests`` (JSON bodies) and ``calls`` (operation names).
    """

    def __init__(self, scripts: dict[str, list[Any]] | None = None) -> None:
        self.scripts = scripts or {}
        self.requests: list[dict[str, Any]] = []
        self.calls: list[str] = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:
                length = int(self.headers.get("Content-Length", 0))
                fake.requests.append(json.loads(self.rfile.read(length) or b"{}"))
                operation = self.headers["X-Amz-Target"].split(".")[-1]
                fake.calls.append(operation)
                script = fake.scripts.get(operation)
                outcome = (
                    script[min(fake.calls.count(operation) - 1, len(script) - 1)] if script else {}
                )
                status, body = fake._response(outcome)
                payload = json.dumps(body).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/x-amz-json-1.0")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format: str, *args: Any) -> None:
                pass

        self._server = HTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @staticmethod
    def _response(outcome: Any) -> tuple[int, dict[str, Any]]:
        if isinstance(outcome, str):
            return 400, {"__type": _ERROR_PREFIX + outcome, "message": outcome}
        if isinstance(outcome, tuple):
            return outcome
        return 200, outcome

    @property
    def endpoint_url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_port}"

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()


@pytest.fixture
def fake_dynamodb() -> Iterator[Callable[..., FakeDynamoDB]]:
    """Return a factory for started FakeDynamoDB servers. All are stopped after the test."""
    servers: list[FakeDynamoDB] = []

    def make(scripts: dict[str, list[Any]] | None = None) -> FakeDynamoDB:
        server = FakeDynamoDB(scripts)
        server.start()
        servers.append(server)
        return server

    yield make
    for server in servers:
        server.stop()
