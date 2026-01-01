"""Shared fixtures for integration tests."""

import os
import signal
import socket
import subprocess
import time

import boto3
import pytest
from pydynox import DynamoDBClient

MOTO_PORT = 5556
MOTO_ENDPOINT = f"http://127.0.0.1:{MOTO_PORT}"


def _is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


@pytest.fixture(scope="session")
def moto_server():
    """Start moto server for the test session."""
    import sys

    if os.name == "nt":
        # Windows: use CREATE_NEW_PROCESS_GROUP for proper cleanup
        proc = subprocess.Popen(
            [sys.executable, "-m", "moto.server", "-p", str(MOTO_PORT)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    else:
        proc = subprocess.Popen(
            [sys.executable, "-m", "moto.server", "-p", str(MOTO_PORT)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid,
        )

    # Wait longer for CI environments (can be slow)
    max_wait = 30
    waited = 0
    while not _is_port_in_use(MOTO_PORT) and waited < max_wait:
        time.sleep(0.5)
        waited += 0.5

    if not _is_port_in_use(MOTO_PORT):
        proc.terminate()
        pytest.fail(f"Moto server failed to start after {max_wait}s")

    yield proc

    if os.name == "nt":
        # Windows: kill the process tree
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
            capture_output=True,
        )
    else:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    proc.wait(timeout=5)


@pytest.fixture
def boto_client(moto_server):
    """Create a boto3 DynamoDB client."""
    return boto3.client(
        "dynamodb",
        region_name="us-east-1",
        endpoint_url=MOTO_ENDPOINT,
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
    )


@pytest.fixture
def table(boto_client):
    """Create a DynamoDB table for testing."""
    try:
        boto_client.delete_table(TableName="test_table")
        time.sleep(0.1)
    except boto_client.exceptions.ResourceNotFoundException:
        pass

    boto_client.create_table(
        TableName="test_table",
        KeySchema=[
            {"AttributeName": "pk", "KeyType": "HASH"},
            {"AttributeName": "sk", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "pk", "AttributeType": "S"},
            {"AttributeName": "sk", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    return boto_client


@pytest.fixture
def dynamo(table):
    """Create a pydynox DynamoDBClient."""
    return DynamoDBClient(
        region="us-east-1",
        endpoint_url=MOTO_ENDPOINT,
        access_key="testing",
        secret_key="testing",
    )
