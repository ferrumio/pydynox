"""proxy_url must not mutate process-wide HTTPS_PROXY (#552)."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

pydynox = pytest.importorskip("pydynox")
DynamoDBClient = pydynox.DynamoDBClient


def _child_https_proxy() -> str | None:
    """Read HTTPS_PROXY from a fresh child process (inherits the native env)."""
    completed = subprocess.run(
        [sys.executable, "-c", "import os; print(os.getenv('HTTPS_PROXY') or '')"],
        check=True,
        capture_output=True,
        text=True,
    )
    value = completed.stdout.strip()
    return value or None


@pytest.mark.parametrize(
    "initial",
    [None, "http://already-set.example:9999"],
)
def test_proxy_url_does_not_change_https_proxy_env(initial, monkeypatch):
    if initial is None:
        monkeypatch.delenv("HTTPS_PROXY", raising=False)
    else:
        monkeypatch.setenv("HTTPS_PROXY", initial)

    before = os.environ.get("HTTPS_PROXY")
    before_child = _child_https_proxy()

    clients = []
    for proxy in ("http://127.0.0.1:18080", "http://127.0.0.1:18081"):
        clients.append(
            DynamoDBClient(
                region="us-east-1",
                access_key="test",
                secret_key="test",
                proxy_url=proxy,
            )
        )
        assert os.environ.get("HTTPS_PROXY") == before
        assert _child_https_proxy() == before_child

    # Client without an explicit proxy also leaves the env alone.
    clients.append(
        DynamoDBClient(
            region="us-east-1",
            access_key="test",
            secret_key="test",
        )
    )
    assert os.environ.get("HTTPS_PROXY") == before
    assert _child_https_proxy() == before_child
