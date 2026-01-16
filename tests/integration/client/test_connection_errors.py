"""Tests for connection error handling."""

import pytest
from pydynox import DynamoDBClient
from pydynox.exceptions import ConnectionException


def test_connection_refused_gives_clear_error():
    """Test that connection refused gives a helpful error message."""
    # GIVEN a client pointing to a non-existent endpoint
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url="http://127.0.0.1:59999",
        access_key="testing",
        secret_key="testing",
    )

    # WHEN we try to put an item
    # THEN a ConnectionException is raised
    with pytest.raises(ConnectionException, match="Connection failed"):
        client.put_item("test_table", {"pk": "TEST#1", "sk": "A"})


def test_connection_refused_on_get_item():
    """Test connection error on get_item."""
    # GIVEN a client pointing to a non-existent endpoint
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url="http://127.0.0.1:59999",
        access_key="testing",
        secret_key="testing",
    )

    # WHEN we try to get an item
    # THEN a ConnectionException is raised
    with pytest.raises(ConnectionException, match="Connection failed"):
        client.get_item("test_table", {"pk": "TEST#1", "sk": "A"})


def test_connection_refused_on_ping():
    """Test connection error on ping."""
    # GIVEN a client pointing to a non-existent endpoint
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url="http://127.0.0.1:59999",
        access_key="testing",
        secret_key="testing",
    )

    # WHEN we ping
    result = client.ping()

    # THEN it returns False (doesn't raise)
    assert result is False
