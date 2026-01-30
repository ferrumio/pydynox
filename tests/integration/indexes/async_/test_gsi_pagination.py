"""Integration tests for GSI pagination with last_evaluated_key."""

import pytest
from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.indexes import GlobalSecondaryIndex


@pytest.fixture
def gsi_pagination_client(dynamodb_endpoint):
    """Create a client and table with GSI for pagination tests."""
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
    )

    table_name = "gsi_pagination_table"

    # Clean up if exists
    if client.sync_table_exists(table_name):
        client.sync_delete_table(table_name)

    # Create table with GSI
    client.sync_create_table(
        table_name,
        partition_key=("pk", "S"),
        sort_key=("sk", "S"),
        global_secondary_indexes=[
            {
                "index_name": "status-index",
                "hash_key": ("status", "S"),
                "range_key": ("age", "N"),
                "projection": "ALL",
            },
        ],
    )

    set_default_client(client)

    # Seed data - 15 items for pagination
    for i in range(15):
        client.sync_put_item(
            table_name,
            {"pk": f"GSI_PAGE#{i}", "sk": "PROFILE", "status": "active", "age": i},
        )

    return client


class UserWithGSI(Model):
    """Test model with GSI for pagination tests."""

    model_config = ModelConfig(table="gsi_pagination_table")

    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    status = StringAttribute()
    age = NumberAttribute()

    status_index = GlobalSecondaryIndex(
        index_name="status-index",
        partition_key="status",
        sort_key="age",
    )


@pytest.mark.asyncio
async def test_gsi_query_with_last_evaluated_key(gsi_pagination_client):
    """GSI query accepts last_evaluated_key for manual pagination."""
    # WHEN we query with a limit
    result = UserWithGSI.status_index.query(status="active", limit=5, page_size=5)
    first_page = [x async for x in result]

    # THEN we get 5 items and a last_evaluated_key
    assert len(first_page) == 5
    assert result.last_evaluated_key is not None

    # WHEN we query again with the last_evaluated_key
    result2 = UserWithGSI.status_index.query(
        status="active",
        limit=5,
        page_size=5,
        last_evaluated_key=result.last_evaluated_key,
    )
    second_page = [x async for x in result2]

    # THEN we get the next 5 items
    assert len(second_page) == 5

    # AND the items are different
    first_pks = {u.pk for u in first_page}
    second_pks = {u.pk for u in second_page}
    assert first_pks.isdisjoint(second_pks)


@pytest.mark.asyncio
async def test_gsi_query_pagination_exhausts_results(gsi_pagination_client):
    """GSI pagination eventually returns None for last_evaluated_key."""
    # WHEN we paginate through all items
    all_items = []
    last_key = None

    while True:
        result = UserWithGSI.status_index.query(
            status="active",
            limit=5,
            page_size=5,
            last_evaluated_key=last_key,
        )
        items = [x async for x in result]
        all_items.extend(items)
        last_key = result.last_evaluated_key

        if last_key is None:
            break

    # THEN we get all 15 items
    assert len(all_items) == 15


@pytest.mark.asyncio
async def test_gsi_async_query_with_last_evaluated_key(gsi_pagination_client):
    """GSI query accepts last_evaluated_key for manual pagination."""
    # WHEN we query with a limit (async)
    result = UserWithGSI.status_index.query(status="active", limit=5, page_size=5)
    first_page = [item async for item in result]

    # THEN we get 5 items
    assert len(first_page) == 5
