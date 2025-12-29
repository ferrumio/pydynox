"""Shared fixtures for benchmarks."""

import os
import signal
import socket
import subprocess
import time

import boto3
import pytest
from pynamodb.attributes import UnicodeAttribute, NumberAttribute
from pynamodb.models import Model

from pydynox import DynamoDBClient


MOTO_PORT = 5557
MOTO_ENDPOINT = f"http://127.0.0.1:{MOTO_PORT}"


def _is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


@pytest.fixture(scope="session")
def moto_server():
    """Start moto server for benchmarks."""
    proc = subprocess.Popen(
        ["uv", "run", "moto_server", "-p", str(MOTO_PORT)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid,
    )

    max_wait = 10
    waited = 0
    while not _is_port_in_use(MOTO_PORT) and waited < max_wait:
        time.sleep(0.5)
        waited += 0.5

    if not _is_port_in_use(MOTO_PORT):
        proc.terminate()
        pytest.fail("Moto server failed to start")

    yield proc

    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        proc.wait()
    except (ProcessLookupError, OSError):
        pass  # Process already terminated


@pytest.fixture(scope="session")
def boto_client(moto_server):
    """Create a boto3 DynamoDB client."""
    return boto3.client(
        "dynamodb",
        region_name="us-east-1",
        endpoint_url=MOTO_ENDPOINT,
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
    )


@pytest.fixture(scope="session")
def bench_table(boto_client):
    """Create a DynamoDB table for benchmarks."""
    try:
        boto_client.delete_table(TableName="bench_table")
        time.sleep(0.5)
    except boto_client.exceptions.ResourceNotFoundException:
        pass

    boto_client.create_table(
        TableName="bench_table",
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
    time.sleep(0.5)
    return boto_client


@pytest.fixture(scope="session")
def pydynox_client(bench_table):
    """Create a pydynox DynamoDBClient."""
    return DynamoDBClient(
        region="us-east-1",
        endpoint_url=MOTO_ENDPOINT,
        access_key="testing",
        secret_key="testing",
    )


class BenchModel(Model):
    """PynamoDB model for benchmarks."""

    class Meta:
        table_name = "bench_table"
        region = "us-east-1"
        host = MOTO_ENDPOINT
        aws_access_key_id = "testing"
        aws_secret_access_key = "testing"

    pk = UnicodeAttribute(hash_key=True)
    sk = UnicodeAttribute(range_key=True)
    name = UnicodeAttribute(null=True)
    age = NumberAttribute(null=True)
    email = UnicodeAttribute(null=True)
    status = UnicodeAttribute(null=True)


@pytest.fixture(scope="session")
def pynamodb_model(bench_table):
    """Return the PynamoDB model class."""
    # Force PynamoDB to describe the table and cache metadata
    if not BenchModel.exists():
        raise RuntimeError("Table should exist")
    return BenchModel
