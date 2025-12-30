"""Tests for connection error handling."""

import pytest
from pydynox import DynamoDBClient
from pydynox.exceptions import ConnectionError


def test_connection_refused_gives_clear_error():
    """Test that connection refused gives a helpful error message."""
    # Connect to a port where nothing is running
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url="http://127.0.0.1:59999",
        access_key="testing",
        secret_key="testing",
    )

    with pytest.raises(ConnectionError, match="Connection failed"):
        client.put_item("test_table", {"pk": "TEST#1", "sk": "A"})


def test_connection_refused_on_get_item():
    """Test connection error on get_item."""
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url="http://127.0.0.1:59999",
        access_key="testing",
        secret_key="testing",
    )

    with pytest.raises(ConnectionError, match="Connection failed"):
        client.get_item("test_table", {"pk": "TEST#1", "sk": "A"})


def test_connection_refused_on_ping():
    """Test connection error on ping."""
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url="http://127.0.0.1:59999",
        access_key="testing",
        secret_key="testing",
    )

    # ping returns False on connection error, doesn't raise
    result = client.ping()
    assert result is False
