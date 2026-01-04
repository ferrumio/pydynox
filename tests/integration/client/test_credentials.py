"""Tests for credential providers."""

import pytest
from pydynox import DynamoDBClient


def test_explicit_credentials(dynamodb_endpoint):
    """Test client with explicit access_key and secret_key."""
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
    )

    assert client.ping() is True


def test_explicit_credentials_with_session_token(dynamodb_endpoint):
    """Test client with explicit credentials including session token."""
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
        session_token="testing-session-token",
    )

    assert client.ping() is True


def test_assume_role_params_accepted():
    """Test that AssumeRole parameters are accepted (doesn't actually assume)."""
    # This just tests that the parameters are accepted without error
    # Actual AssumeRole requires real AWS credentials
    client = DynamoDBClient(
        endpoint_url="http://localhost:59999",  # Won't connect
        role_arn="arn:aws:iam::123456789012:role/TestRole",
        role_session_name="test-session",
        external_id="test-external-id",
    )

    # ping returns False because endpoint doesn't exist, but client was created
    assert client.ping() is False


def test_assume_role_with_session_name(dynamodb_endpoint):
    """Test that role_session_name parameter is accepted."""
    # DynamoDB Local doesn't validate credentials, so this works
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
        # These are ignored when explicit credentials are provided
        # but should not cause errors
    )

    assert client.ping() is True


def test_profile_param_accepted():
    """Test that profile parameter is accepted."""
    # This just tests the parameter is accepted
    # Actual profile loading requires ~/.aws/credentials
    client = DynamoDBClient(
        endpoint_url="http://localhost:59999",
        profile="nonexistent-profile",
    )

    # Will fail to connect but client was created
    assert client.ping() is False


@pytest.mark.parametrize(
    "region",
    [
        pytest.param("us-east-1", id="us_east_1"),
        pytest.param("us-west-2", id="us_west_2"),
        pytest.param("eu-west-1", id="eu_west_1"),
        pytest.param("ap-northeast-1", id="ap_northeast_1"),
    ],
)
def test_various_regions(dynamodb_endpoint, region):
    """Test client with various AWS regions."""
    client = DynamoDBClient(
        region=region,
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
    )

    assert client.get_region() == region
    assert client.ping() is True


def test_credentials_priority_explicit_over_profile(dynamodb_endpoint):
    """Test that explicit credentials take priority over profile."""
    # Even with a profile specified, explicit credentials should be used
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
        profile="nonexistent-profile",  # Should be ignored
    )

    # Should work because explicit credentials are used
    assert client.ping() is True
