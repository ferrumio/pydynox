"""Local HTTPS proxy fixtures for the real SDK transport."""

import json
import os
import ssl
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

_CLIENT_SCRIPT = """
import asyncio
import concurrent.futures
import json
import sys

from pydynox import DynamoDBClient

options = json.loads(sys.argv[1])
mode = options.pop("mode")
proxies = options.pop("proxies")
clients = [DynamoDBClient(**options, proxy_url=proxy) for proxy in proxies]

async def read():
    if mode == "async":
        return await asyncio.gather(*[
            client.get_item("test-table", {"pk": "example"}) for client in clients
        ])
    with concurrent.futures.ThreadPoolExecutor() as pool:
        return list(pool.map(
            lambda client: client.sync_get_item("test-table", {"pk": "example"}), clients
        ))

try:
    print(json.dumps({"items": asyncio.run(read())}))
except Exception as exc:
    print(json.dumps({"error": type(exc).__name__, "message": str(exc)}))
"""

_ASSUME_ROLE_RESPONSE = b"""
<AssumeRoleResponse xmlns="https://sts.amazonaws.com/doc/2011-06-15/">
  <AssumeRoleResult>
    <Credentials>
      <AccessKeyId>ASSUMEDKEY</AccessKeyId>
      <SecretAccessKey>assumed-secret</SecretAccessKey>
      <SessionToken>assumed-token</SessionToken>
      <Expiration>2099-01-01T00:00:00Z</Expiration>
    </Credentials>
  </AssumeRoleResult>
</AssumeRoleResponse>
"""


@pytest.fixture(scope="module")
def proxy_tls(tmp_path_factory):
    """Create a CA and certificate for endpoints that only exist behind the proxy."""
    path = tmp_path_factory.mktemp("proxy-tls")
    commands = [
        [
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            "ca.key",
            "-out",
            "ca.pem",
            "-days",
            "1",
            "-subj",
            "/CN=pydynox test CA",
            "-config",
            "ca.cnf",
        ],
        [
            "req",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            "server.key",
            "-out",
            "server.csr",
            "-subj",
            "/CN=dynamodb.invalid",
        ],
        [
            "x509",
            "-req",
            "-in",
            "server.csr",
            "-CA",
            "ca.pem",
            "-CAkey",
            "ca.key",
            "-CAcreateserial",
            "-out",
            "server.pem",
            "-days",
            "1",
            "-extfile",
            "server.ext",
        ],
    ]
    (path / "ca.cnf").write_text(
        "[req]\ndistinguished_name=dn\nx509_extensions=ca\n"
        "[dn]\n[ca]\nbasicConstraints=critical,CA:TRUE\n"
    )
    (path / "server.ext").write_text(
        "subjectAltName=DNS:dynamodb.invalid,DNS:sts.invalid\n"
        "basicConstraints=critical,CA:FALSE\n"
        "keyUsage=digitalSignature,keyEncipherment\n"
        "extendedKeyUsage=serverAuth\n"
    )
    for command in commands:
        subprocess.run(["openssl", *command], cwd=path, capture_output=True, check=True)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(path / "server.pem", path / "server.key")
    return context, path / "ca.pem"


@pytest.fixture
def proxy_server(proxy_tls):
    """Terminate CONNECT tunnels locally and record signed DynamoDB/STS requests."""
    context, _ = proxy_tls
    servers = []

    def make(*, connect_delay=0, read_delay=0):
        calls = []
        targets = []

        class Endpoint(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                dynamodb = self.headers.get("X-Amz-Target") == "DynamoDB_20120810.GetItem"
                calls.append(
                    {
                        "service": "dynamodb" if dynamodb else "sts",
                        "authorization": self.headers.get("Authorization", ""),
                        "token": self.headers.get("X-Amz-Security-Token"),
                    }
                )
                time.sleep(read_delay)
                payload = b'{"Item":{"pk":{"S":"example"}}}' if dynamodb else _ASSUME_ROLE_RESPONSE
                self.send_response(200)
                self.send_header(
                    "Content-Type", "application/x-amz-json-1.0" if dynamodb else "text/xml"
                )
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        class Proxy(BaseHTTPRequestHandler):
            def do_CONNECT(self):
                self.close_connection = True
                targets.append(self.path)
                time.sleep(connect_delay)
                try:
                    self.send_response(200)
                    self.end_headers()
                    with context.wrap_socket(self.connection, server_side=True) as connection:
                        Endpoint(connection, self.client_address, self.server)
                except (OSError, ssl.SSLError):
                    # Timeouts deliberately close a tunnel before its response.
                    pass

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Proxy)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        servers.append((server, thread))
        return f"http://127.0.0.1:{server.server_port}", targets, calls

    yield make
    for server, thread in servers:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture
def proxy_client(proxy_tls, tmp_path):
    """Run Python clients in a fresh process with only local test credentials."""
    _, ca = proxy_tls
    credentials = tmp_path / "credentials"
    credentials.write_text("[source]\naws_access_key_id=SOURCEKEY\naws_secret_access_key=secret\n")
    config = tmp_path / "config"
    config.write_text(
        "[profile chained]\nregion=us-east-1\n"
        "role_arn=arn:aws:iam::123456789012:role/ProfileRole\nsource_profile=source\n"
    )
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("AWS_")
        and key.lower() not in {"http_proxy", "https_proxy", "all_proxy", "no_proxy"}
    }
    env.update(
        AWS_SHARED_CREDENTIALS_FILE=str(credentials),
        AWS_CONFIG_FILE=str(config),
        AWS_ACCESS_KEY_ID="ENVKEY",
        AWS_SECRET_ACCESS_KEY="env-secret",
        AWS_EC2_METADATA_DISABLED="true",
        AWS_MAX_ATTEMPTS="1",
        AWS_ENDPOINT_URL_STS="https://sts.invalid",
        SSL_CERT_FILE=str(ca),
    )

    def call(proxies, mode, **options):
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                _CLIENT_SCRIPT,
                json.dumps(
                    {
                        "region": "us-east-1",
                        "endpoint_url": "https://dynamodb.invalid",
                        "max_retries": 1,
                        "proxies": proxies,
                        "mode": mode,
                        **options,
                    }
                ),
            ],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
        return json.loads(result.stdout)

    return call
