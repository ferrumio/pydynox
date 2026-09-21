"""Use the memory backend fixture for direct client calls."""


def test_batch_write(pydynox_memory_backend):
    """Test direct batch operations without connecting to DynamoDB."""
    # GIVEN the client exposed by the memory backend fixture
    client = pydynox_memory_backend.client

    # WHEN we batch write and read two items
    client.sync_batch_write(
        "users",
        put_items=[
            {"pk": "USER#1", "name": "Alice"},
            {"pk": "USER#2", "name": "Bob"},
        ],
    )

    items = client.sync_batch_get(
        "users",
        [{"pk": "USER#1"}, {"pk": "USER#2"}],
    )

    # THEN both items are returned from in-memory storage
    assert len(items) == 2
