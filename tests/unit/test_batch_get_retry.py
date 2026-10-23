"""Unit tests for batch_get retries of unprocessed keys.

DynamoDB can return some keys as UnprocessedKeys. The Rust core sends them
again. These tests use a local HTTP server that acts as DynamoDB, so the real
retry loop runs without Docker or AWS.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

import pytest
from pydynox import DynamoDBClient


class FakeDynamoDB:
    """Answers each request with the next queued response and keeps the requests."""

    def __init__(self) -> None:
        self.responses: list[dict[str, Any]] = []
        self.requests: list[dict[str, Any]] = []
        self.endpoint_url = ""


@pytest.fixture
def fake_dynamodb():
    fake = FakeDynamoDB()

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers["Content-Length"])
            fake.requests.append(json.loads(self.rfile.read(length)))
            body = json.dumps(fake.responses.pop(0)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/x-amz-json-1.0")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: Any) -> None:
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    fake.endpoint_url = f"http://127.0.0.1:{server.server_port}"
    yield fake
    server.shutdown()
    server.server_close()


@pytest.mark.asyncio
@pytest.mark.parametrize("sync", [False, True], ids=["async", "sync"])
async def test_batch_get_retry_keeps_projection(fake_dynamodb, sync):
    """Unprocessed keys are sent again with the same projection."""
    # GIVEN DynamoDB returns key "b" as unprocessed, with only its key and no projection
    fake_dynamodb.responses = [
        {
            "Responses": {"users": [{"pk": {"S": "a"}, "name": {"S": "Ann"}}]},
            "UnprocessedKeys": {"users": {"Keys": [{"pk": {"S": "b"}}]}},
        },
        {
            "Responses": {"users": [{"pk": {"S": "b"}, "name": {"S": "Bob"}}]},
            "UnprocessedKeys": {},
        },
    ]
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url=fake_dynamodb.endpoint_url,
        access_key="testing",
        secret_key="testing",
    )
    keys = [{"pk": "a"}, {"pk": "b"}]

    # WHEN batch getting with a projection on a reserved word
    if sync:
        items = client.sync_batch_get("users", keys, projection=["name"])
    else:
        items = await client.batch_get("users", keys, projection=["name"])

    # THEN items from both requests come back
    assert sorted(item["name"] for item in items) == ["Ann", "Bob"]

    # AND the retry asks only for "b", with the same projection and names
    assert len(fake_dynamodb.requests) == 2
    first = fake_dynamodb.requests[0]["RequestItems"]["users"]
    retry = fake_dynamodb.requests[1]["RequestItems"]["users"]
    assert retry["Keys"] == [{"pk": {"S": "b"}}]
    assert retry["ProjectionExpression"] == first["ProjectionExpression"]
    assert retry["ExpressionAttributeNames"] == first["ExpressionAttributeNames"]
    assert retry["ExpressionAttributeNames"] == {"#p0": "name"}
