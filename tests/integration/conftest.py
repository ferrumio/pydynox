"""Shared fixtures for integration tests.

Uses LocalStack for DynamoDB, S3, and KMS via testcontainers.
Docker must be running to execute integration tests.
"""

import time

import pytest
from pydynox import DynamoDBClient
from testcontainers.localstack import LocalStackContainer


@pytest.fixture(scope="session")
def localstack_container():
    """Start LocalStack container for the test session."""
    print("\n🐳 Starting LocalStack container...")

    container = LocalStackContainer(image="localstack/localstack:latest")
    container.with_services("dynamodb", "s3", "kms")

    container.start()

    # Wait for services to be ready
    time.sleep(2)

    endpoint = container.get_url()
    print(f"✅ LocalStack ready at {endpoint}")

    yield container

    print("\n🛑 Stopping LocalStack container...")
    container.stop()


@pytest.fixture(scope="session")
def localstack_endpoint(localstack_container):
    """Get the LocalStack endpoint URL."""
    return localstack_container.get_url()


@pytest.fixture(scope="session")
def dynamodb_endpoint(localstack_endpoint):
    """Alias for localstack_endpoint (backward compatibility)."""
    return localstack_endpoint


@pytest.fixture(scope="session")
def _session_client(localstack_endpoint):
    """Internal client for session-scoped table creation."""
    return DynamoDBClient(
        region="us-east-1",
        endpoint_url=localstack_endpoint,
        access_key="testing",
        secret_key="testing",
    )


@pytest.fixture(scope="session")
def _create_table(_session_client):
    """Create the test table once per session."""
    table_name = "test_table"

    if not _session_client.sync_table_exists(table_name):
        _session_client.sync_create_table(
            table_name,
            hash_key=("pk", "S"),
            range_key=("sk", "S"),
            wait=True,
        )

    return _session_client


@pytest.fixture
def table(_create_table, localstack_endpoint):
    """Provide a client with the test table ready.

    Note: Tests should use unique keys to avoid conflicts.
    Use uuid or test-specific prefixes in pk/sk values.
    """
    return DynamoDBClient(
        region="us-east-1",
        endpoint_url=localstack_endpoint,
        access_key="testing",
        secret_key="testing",
    )


@pytest.fixture
def dynamo(table):
    """Alias for table fixture - provides a pydynox DynamoDBClient."""
    return table


@pytest.fixture(scope="session")
def s3_bucket(localstack_endpoint):
    """Create test S3 bucket."""
    import boto3

    s3 = boto3.client(
        "s3",
        endpoint_url=localstack_endpoint,
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
        region_name="us-east-1",
    )

    bucket_name = "test-bucket"
    try:
        s3.create_bucket(Bucket=bucket_name)
    except s3.exceptions.BucketAlreadyExists:
        pass

    return bucket_name


@pytest.fixture(scope="session")
def kms_key_id(localstack_endpoint):
    """Create a KMS key for encryption tests."""
    import boto3

    kms = boto3.client(
        "kms",
        endpoint_url=localstack_endpoint,
        aws_access_key_id="testing",
        aws_secret_access_key="testing",
        region_name="us-east-1",
    )

    response = kms.create_key(
        Description="Test key for pydynox integration tests",
        KeyUsage="ENCRYPT_DECRYPT",
    )

    key_id = response["KeyMetadata"]["KeyId"]
    print(f"✅ Created KMS key: {key_id}")

    return key_id
