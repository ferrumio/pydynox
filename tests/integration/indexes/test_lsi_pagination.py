"""Integration tests for LSI pagination with last_evaluated_key."""

import pytest
from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.indexes import LocalSecondaryIndex


@pytest.fixture
def lsi_pagination_client(dynamodb_endpoint):
    """Create a client and table with LSI for pagination tests."""
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
    )

    table_name = "lsi_pagination_table"

    # Clean up if exists
    if client.sync_table_exists(table_name):
        client.sync_delete_table(table_name)

    # Create table with LSI
    client.sync_create_table(
        table_name,
        hash_key=("pk", "S"),
        range_key=("sk", "S"),
        local_secondary_indexes=[
            {
                "index_name": "created-at-index",
                "range_key": ("created_at", "N"),
                "projection": "ALL",
            },
        ],
    )

    set_default_client(client)

    # Seed data - 15 items for pagination
    for i in range(15):
        client.put_item(
            table_name,
            {"pk": "LSI_PAGE#1", "sk": f"ORDER#{i:03d}", "created_at": i * 1000},
        )

    return client


class OrderWithLSI(Model):
    """Test model with LSI for pagination tests."""

    model_config = ModelConfig(table="lsi_pagination_table")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    created_at = NumberAttribute()

    created_at_index = LocalSecondaryIndex(
        index_name="created-at-index",
        range_key="created_at",
    )


def test_lsi_query_with_last_evaluated_key(lsi_pagination_client):
    """LSI query accepts last_evaluated_key for manual pagination."""
    # WHEN we query with a limit
    result = OrderWithLSI.created_at_index.query(pk="LSI_PAGE#1", limit=5, page_size=5)
    first_page = list(result)

    # THEN we get 5 items and a last_evaluated_key
    assert len(first_page) == 5
    assert result.last_evaluated_key is not None

    # WHEN we query again with the last_evaluated_key
    result2 = OrderWithLSI.created_at_index.query(
        pk="LSI_PAGE#1",
        limit=5,
        page_size=5,
        last_evaluated_key=result.last_evaluated_key,
    )
    second_page = list(result2)

    # THEN we get the next 5 items
    assert len(second_page) == 5

    # AND the items are different
    first_sks = {o.sk for o in first_page}
    second_sks = {o.sk for o in second_page}
    assert first_sks.isdisjoint(second_sks)


def test_lsi_query_pagination_exhausts_results(lsi_pagination_client):
    """LSI pagination eventually returns None for last_evaluated_key."""
    # WHEN we paginate through all items
    all_items = []
    last_key = None

    while True:
        result = OrderWithLSI.created_at_index.query(
            pk="LSI_PAGE#1",
            limit=5,
            page_size=5,
            last_evaluated_key=last_key,
        )
        items = list(result)
        all_items.extend(items)
        last_key = result.last_evaluated_key

        if last_key is None:
            break

    # THEN we get all 15 items
    assert len(all_items) == 15


@pytest.mark.asyncio
async def test_lsi_async_query_with_last_evaluated_key(lsi_pagination_client):
    """LSI async_query accepts last_evaluated_key for manual pagination."""
    # WHEN we query with a limit (async)
    result = OrderWithLSI.created_at_index.async_query(pk="LSI_PAGE#1", limit=5, page_size=5)
    first_page = [item async for item in result]

    # THEN we get 5 items
    assert len(first_page) == 5
