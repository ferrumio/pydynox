"""Integration tests for rate limiting with DynamoDB operations.

Note: DynamoDB Local does not simulate throttling, so we test that:
1. Rate limiter is called during operations
2. Metrics are tracked correctly
3. Operations still work with rate limiting enabled
"""

import time
import uuid

import pytest
from pydynox import DynamoDBClient
from pydynox.rate_limit import AdaptiveRate, FixedRate


def _unique_pk(prefix: str = "RATE") -> str:
    """Generate a unique pk to avoid test conflicts."""
    return f"{prefix}#{uuid.uuid4().hex[:8]}"


@pytest.fixture
def client_with_fixed_rate(table, dynamodb_endpoint):
    """Create a client with fixed rate limiting."""
    return DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
        rate_limit=FixedRate(rcu=100, wcu=50),
    )


@pytest.fixture
def client_with_adaptive_rate(table, dynamodb_endpoint):
    """Create a client with adaptive rate limiting."""
    return DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
        rate_limit=AdaptiveRate(max_rcu=100, max_wcu=50),
    )


def test_put_item_tracks_wcu(client_with_fixed_rate):
    """Test that put_item tracks WCU consumption."""
    client = client_with_fixed_rate
    pk = _unique_pk()

    # Initial WCU should be 0
    assert client.rate_limit.consumed_wcu == pytest.approx(0.0)

    # Put an item
    client.put_item("test_table", {"pk": pk, "sk": "PROFILE", "name": "Alice"})

    # WCU should be tracked
    assert client.rate_limit.consumed_wcu == pytest.approx(1.0)


def test_get_item_tracks_rcu(client_with_fixed_rate):
    """Test that get_item tracks RCU consumption."""
    client = client_with_fixed_rate
    pk = _unique_pk()

    # Put an item first
    client.put_item("test_table", {"pk": pk, "sk": "PROFILE", "name": "Alice"})

    # Reset by creating new client (or just check delta)
    initial_rcu = client.rate_limit.consumed_rcu

    # Get the item
    client.get_item("test_table", {"pk": pk, "sk": "PROFILE"})

    # RCU should be tracked
    assert client.rate_limit.consumed_rcu == pytest.approx(initial_rcu + 1.0)


def test_delete_item_tracks_wcu(client_with_fixed_rate):
    """Test that delete_item tracks WCU consumption."""
    client = client_with_fixed_rate
    pk = _unique_pk()

    # Put an item first
    client.put_item("test_table", {"pk": pk, "sk": "PROFILE", "name": "Alice"})
    initial_wcu = client.rate_limit.consumed_wcu

    # Delete the item
    client.delete_item("test_table", {"pk": pk, "sk": "PROFILE"})

    # WCU should be tracked
    assert client.rate_limit.consumed_wcu == pytest.approx(initial_wcu + 1.0)


def test_update_item_tracks_wcu(client_with_fixed_rate):
    """Test that update_item tracks WCU consumption."""
    client = client_with_fixed_rate
    pk = _unique_pk()

    # Put an item first
    client.put_item("test_table", {"pk": pk, "sk": "PROFILE", "name": "Alice"})
    initial_wcu = client.rate_limit.consumed_wcu

    # Update the item
    client.update_item(
        "test_table",
        {"pk": pk, "sk": "PROFILE"},
        updates={"name": "Bob"},
    )

    # WCU should be tracked
    assert client.rate_limit.consumed_wcu == pytest.approx(initial_wcu + 1.0)


def test_batch_write_tracks_wcu(client_with_fixed_rate):
    """Test that batch_write tracks WCU for all items."""
    client = client_with_fixed_rate
    pk1, pk2, pk3 = _unique_pk(), _unique_pk(), _unique_pk()

    initial_wcu = client.rate_limit.consumed_wcu

    # Batch write 3 items
    client.batch_write(
        "test_table",
        put_items=[
            {"pk": pk1, "sk": "PROFILE", "name": "Alice"},
            {"pk": pk2, "sk": "PROFILE", "name": "Bob"},
            {"pk": pk3, "sk": "PROFILE", "name": "Charlie"},
        ],
    )

    # WCU should track all 3 items
    assert client.rate_limit.consumed_wcu == pytest.approx(initial_wcu + 3.0)


def test_batch_get_tracks_rcu(client_with_fixed_rate):
    """Test that batch_get tracks RCU for all keys."""
    client = client_with_fixed_rate
    pk1, pk2 = _unique_pk(), _unique_pk()

    # Put items first
    client.batch_write(
        "test_table",
        put_items=[
            {"pk": pk1, "sk": "PROFILE", "name": "Alice"},
            {"pk": pk2, "sk": "PROFILE", "name": "Bob"},
        ],
    )

    initial_rcu = client.rate_limit.consumed_rcu

    # Batch get 2 items
    client.batch_get(
        "test_table",
        keys=[
            {"pk": pk1, "sk": "PROFILE"},
            {"pk": pk2, "sk": "PROFILE"},
        ],
    )

    # RCU should track both keys
    assert client.rate_limit.consumed_rcu == pytest.approx(initial_rcu + 2.0)


def test_query_tracks_rcu(client_with_fixed_rate):
    """Test that query tracks RCU consumption."""
    client = client_with_fixed_rate
    pk = _unique_pk("QUERY")

    # Put items first - use unique pk so we only get our items
    client.batch_write(
        "test_table",
        put_items=[
            {"pk": pk, "sk": "PROFILE", "name": "Alice"},
            {"pk": pk, "sk": "SETTINGS", "theme": "dark"},
        ],
    )

    initial_rcu = client.rate_limit.consumed_rcu

    # Query items
    results = list(
        client.query(
            "test_table",
            key_condition_expression="#pk = :pk",
            expression_attribute_names={"#pk": "pk"},
            expression_attribute_values={":pk": pk},
        )
    )

    # Should have found exactly 2 items
    assert len(results) == 2

    # RCU should be tracked (at least 1 for the query)
    assert client.rate_limit.consumed_rcu > initial_rcu


def test_adaptive_rate_starts_at_half_max(client_with_adaptive_rate):
    """Test that adaptive rate starts at 50% of max."""
    client = client_with_adaptive_rate

    assert client.rate_limit.current_rcu == pytest.approx(50.0)  # 50% of 100
    assert client.rate_limit.current_wcu == pytest.approx(25.0)  # 50% of 50


def test_operations_work_with_rate_limiting(client_with_fixed_rate):
    """Test that all operations work correctly with rate limiting."""
    client = client_with_fixed_rate
    pk = _unique_pk()

    # Put
    client.put_item("test_table", {"pk": pk, "sk": "PROFILE", "name": "Alice"})

    # Get
    item = client.get_item("test_table", {"pk": pk, "sk": "PROFILE"})
    assert item["name"] == "Alice"

    # Update
    client.update_item(
        "test_table",
        {"pk": pk, "sk": "PROFILE"},
        updates={"name": "Bob"},
    )

    # Verify update
    item = client.get_item("test_table", {"pk": pk, "sk": "PROFILE"})
    assert item["name"] == "Bob"

    # Delete
    client.delete_item("test_table", {"pk": pk, "sk": "PROFILE"})

    # Verify delete
    item = client.get_item("test_table", {"pk": pk, "sk": "PROFILE"})
    assert item is None


def test_rate_limiting_slows_operations(table, dynamodb_endpoint):
    """Test that rate limiting actually slows down operations."""
    pk1, pk2, pk3 = _unique_pk(), _unique_pk(), _unique_pk()

    # Create client with very low rate
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
        rate_limit=FixedRate(wcu=2),  # Only 2 WCU per second
    )

    # First 2 writes should be fast (tokens available)
    start = time.time()
    client.put_item("test_table", {"pk": pk1, "sk": "A", "data": "x"})
    client.put_item("test_table", {"pk": pk2, "sk": "A", "data": "x"})
    first_two = time.time() - start

    # Third write should wait for token refill
    start = time.time()
    client.put_item("test_table", {"pk": pk3, "sk": "A", "data": "x"})
    third = time.time() - start

    # First two should be fast
    assert first_two < 0.5

    # Third should have waited (at least 0.4 seconds for 1 token at 2/sec)
    assert third >= 0.4


def test_client_without_rate_limit_has_none(dynamo):
    """Test that client without rate_limit parameter has None."""
    assert dynamo.rate_limit is None


@pytest.mark.parametrize(
    "rate_limit",
    [
        pytest.param(FixedRate(rcu=50), id="fixed_rcu_only"),
        pytest.param(FixedRate(rcu=50, wcu=25), id="fixed_rcu_wcu"),
        pytest.param(AdaptiveRate(max_rcu=100), id="adaptive_rcu_only"),
        pytest.param(AdaptiveRate(max_rcu=100, max_wcu=50), id="adaptive_rcu_wcu"),
    ],
)
def test_various_rate_limit_configs_work(table, dynamodb_endpoint, rate_limit):
    """Test that various rate limit configurations work."""
    pk = _unique_pk()

    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
        rate_limit=rate_limit,
    )

    # Should be able to do basic operations
    client.put_item("test_table", {"pk": pk, "sk": "A", "data": "test"})
    item = client.get_item("test_table", {"pk": pk, "sk": "A"})
    assert item["data"] == "test"
