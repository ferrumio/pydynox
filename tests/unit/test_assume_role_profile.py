"""Check AssumeRole signing through the Python API and real Rust SDK."""

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

import pytest

_ROLE_ARN = "arn:aws:iam::123456789012:role/AppRole"
_ROLE_OPTIONS = {
    "role_arn": _ROLE_ARN,
    "role_session_name": "test-session",
    "external_id": "test-external-id",
}
_ASSUME_ROLE_RESPONSE = b"""
<AssumeRoleResponse xmlns="https://sts.amazonaws.com/doc/2011-06-15/">
  <AssumeRoleResult>
    <Credentials>
      <AccessKeyId>ASSUMEDKEY</AccessKeyId>
      <SecretAccessKey>assumed-secret</SecretAccessKey>
      <SessionToken>assumed-token</SessionToken>
      <Expiration>2099-01-01T00:00:00Z</Expiration>
    </Credentials>
    <AssumedRoleUser>
      <AssumedRoleId>ROLEID:test-session</AssumedRoleId>
      <Arn>arn:aws:sts::123456789012:assumed-role/AppRole/test-session</Arn>
    </AssumedRoleUser>
  </AssumeRoleResult>
  <ResponseMetadata><RequestId>test-request</RequestId></ResponseMetadata>
</AssumeRoleResponse>
"""
# A fresh process prevents SDK credential caches or Rust environment reads from
# leaking between tests. The parent owns both fake HTTP endpoints.
_CLIENT_SCRIPT = """
import asyncio
import json
import sys

from pydynox import DynamoDBClient

options = json.loads(sys.argv[1])
mode = options.pop("mode")
try:
    client = DynamoDBClient(**options)
    if mode == "sync":
        item = client.sync_get_item("test-table", {"pk": "example"})
    else:
        item = asyncio.run(client.get_item("test-table", {"pk": "example"}))
except Exception as exc:
    print(json.dumps({"error": type(exc).__name__}))
else:
    print(json.dumps({"item": item}))
"""


@pytest.fixture
def aws_endpoint():
    """Record signed STS and DynamoDB requests and return fake responses."""
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            is_dynamodb = self.headers.get("X-Amz-Target") == "DynamoDB_20120810.GetItem"
            requests.append(
                {
                    "service": "dynamodb" if is_dynamodb else "sts",
                    "authorization": self.headers.get("Authorization", ""),
                    "token": self.headers.get("X-Amz-Security-Token"),
                    "body": json.loads(body) if is_dynamodb else parse_qs(body.decode()),
                }
            )
            payload = b'{"Item":{"pk":{"S":"example"}}}' if is_dynamodb else _ASSUME_ROLE_RESPONSE
            self.send_response(200)
            self.send_header(
                "Content-Type", "application/x-amz-json-1.0" if is_dynamodb else "text/xml"
            )
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}", requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture
def credential_env(tmp_path):
    credentials = tmp_path / "credentials"
    credentials.write_text(
        "[default]\naws_access_key_id=DEFAULTKEY\naws_secret_access_key=default-secret\n"
        "[source]\naws_access_key_id=SOURCEKEY\naws_secret_access_key=source-secret\n"
        "aws_session_token=source-token\n"
    )
    config = tmp_path / "config"
    config.write_text("[default]\nregion=us-east-1\n")
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("AWS_")
        and key.lower() not in {"http_proxy", "https_proxy", "all_proxy", "no_proxy"}
    }
    env.update(
        AWS_SHARED_CREDENTIALS_FILE=str(credentials),
        AWS_CONFIG_FILE=str(config),
        AWS_REGION="us-east-1",
        AWS_EC2_METADATA_DISABLED="true",
        AWS_MAX_ATTEMPTS="1",
        AWS_ACCESS_KEY_ID="ENVKEY",
        AWS_SECRET_ACCESS_KEY="env-secret",
        AWS_SESSION_TOKEN="env-token",
    )
    return env


@pytest.mark.parametrize("mode", ["sync", "async"])
@pytest.mark.parametrize(
    "options,source_key,source_token,use_env",
    [
        pytest.param(
            {"profile": "source", **_ROLE_OPTIONS},
            "SOURCEKEY",
            "source-token",
            True,
            id="profile-and-role",
        ),
        pytest.param(_ROLE_OPTIONS, "ENVKEY", "env-token", True, id="role-with-env"),
        pytest.param(_ROLE_OPTIONS, "DEFAULTKEY", None, False, id="role-with-default-profile"),
        pytest.param(
            {"profile": "missing", **_ROLE_OPTIONS}, None, None, True, id="missing-profile"
        ),
        pytest.param({"profile": "source"}, "SOURCEKEY", "source-token", True, id="profile-only"),
        pytest.param(
            {
                "profile": "missing",
                **_ROLE_OPTIONS,
                "access_key": "STATICKEY",
                "secret_key": "static-secret",
                "session_token": "static-token",
            },
            "STATICKEY",
            "static-token",
            True,
            id="static-credentials-take-precedence",
        ),
    ],
)
def test_assume_role_credentials(
    aws_endpoint, credential_env, tmp_path, mode, options, source_key, source_token, use_env
):
    # GIVEN distinct credentials in the environment, default profile, and named profile
    endpoint, requests = aws_endpoint
    credential_env["AWS_ENDPOINT_URL_STS"] = endpoint
    if not use_env:
        for name in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
            credential_env.pop(name)
    client_options = {
        "region": "us-east-1",
        "endpoint_url": endpoint,
        "mode": mode,
        **options,
    }

    # WHEN the public client sends a request through the real SDK
    result = subprocess.run(
        [sys.executable, "-c", _CLIENT_SCRIPT, json.dumps(client_options)],
        cwd=tmp_path,
        env=credential_env,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    response = json.loads(result.stdout)

    # THEN a missing explicit profile fails before either service is called
    if source_key is None:
        assert "error" in response, response
        assert requests == []
        return

    assert response == {"item": {"pk": "example"}}
    uses_role = "role_arn" in options and "access_key" not in options
    assert len(requests) == (2 if uses_role else 1)
    if uses_role:
        sts_request = requests[0]
        assert sts_request["service"] == "sts"
        assert f"Credential={source_key}/" in sts_request["authorization"]
        assert sts_request["token"] == source_token
        assert sts_request["body"]["Action"] == ["AssumeRole"]
        assert sts_request["body"]["RoleArn"] == [_ROLE_ARN]
        assert sts_request["body"]["RoleSessionName"] == ["test-session"]
        assert sts_request["body"]["ExternalId"] == ["test-external-id"]

    # AND DynamoDB uses the assumed credentials, or the direct source without a role
    dynamodb_request = requests[-1]
    expected_key = "ASSUMEDKEY" if uses_role else source_key
    expected_token = "assumed-token" if uses_role else source_token
    assert dynamodb_request["service"] == "dynamodb"
    assert f"Credential={expected_key}/" in dynamodb_request["authorization"]
    assert dynamodb_request["token"] == expected_token
