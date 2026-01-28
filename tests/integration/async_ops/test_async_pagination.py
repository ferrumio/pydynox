"""Tests for async pagination with last_evaluated_key."""

import pytest
from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.indexes import GlobalSecondaryIndex, LocalSecondaryIndex

TABLE_NAME = "async_pagination_test"


@pytest.fixture
def pagination_table(dynamo: DynamoDBClient):
    """Create a test table with indexes for pagination tests."""
    set_default_client(dynamo)
    if dynamo.sync_table_exists(TABLE_NAME):
        dynamo.sync_delete_table(TABLE_NAME)

    dynamo.sync_create_table(
        TABLE_NAME,
        hash_key=("pk", "S"),
        range_key=("sk", "S"),
        wait=True,
        global_secondary_indexes=[
            {
                "index_name": "status-index",
                "hash_key": ("status", "S"),
                "projection": "ALL",
            }
        ],
        local_secondary_indexes=[
            {
                "index_name": "age-index",
                "range_key": ("age", "N"),
                "projection": "ALL",
            }
        ],
    )
    yield dynamo


class PaginationUser(Model):
    model_config = ModelConfig(table=TABLE_NAME)
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    status = StringAttribute()
    age = NumberAttribute()

    status_index = GlobalSecondaryIndex(
        index_name="status-index",
        hash_key="status",
        projection="ALL",
    )
    age_index = LocalSecondaryIndex(
        index_name="age-index",
        range_key="age",
        projection="ALL",
    )


@pytest.fixture
def seeded_table(pagination_table: DynamoDBClient):
    """Seed the table with test data."""
    for i in range(25):
        item = {
            "pk": "USER#pagination",
            "sk": f"ITEM#{i:03d}",
            "name": f"User {i}",
            "status": "active",
            "age": 20 + i,
        }
        pagination_table.sync_put_item(TABLE_NAME, item)
    yield pagination_table


# ========== Model query pagination ==========


@pytest.mark.asyncio
async def test_query_last_evaluated_key(seeded_table: DynamoDBClient):
    """Test that query exposes last_evaluated_key for pagination."""
    # GIVEN a table with 25 items
    # WHEN we query with page_size=10
    result = PaginationUser.query(
        hash_key="USER#pagination",
        page_size=10,
    )

    # Consume first page
    first_page = []
    async for user in result:
        first_page.append(user)
        if len(first_page) == 10:
            break

    # THEN last_evaluated_key is available
    assert result.last_evaluated_key is not None
    assert len(first_page) == 10


@pytest.mark.asyncio
async def test_query_manual_pagination(seeded_table: DynamoDBClient):
    """Test manual pagination using last_evaluated_key."""
    # GIVEN a table with 25 items
    all_items = []
    last_key = None

    # WHEN we paginate manually
    while True:
        result = PaginationUser.query(
            hash_key="USER#pagination",
            page_size=10,
            last_evaluated_key=last_key,
        )

        async for user in result:
            all_items.append(user)

        last_key = result.last_evaluated_key
        if last_key is None:
            break

    # THEN we get all 25 items
    assert len(all_items) == 25


@pytest.mark.asyncio
async def test_query_collect(seeded_table: DynamoDBClient):
    """Test collecting all items from query."""
    # GIVEN a table with 25 items
    # WHEN we collect all items
    result = PaginationUser.query(hash_key="USER#pagination")
    all_items = []
    async for user in result:
        all_items.append(user)

    # THEN we get all 25 items
    assert len(all_items) == 25


# ========== Model scan pagination ==========


@pytest.mark.asyncio
async def test_scan_last_evaluated_key(seeded_table: DynamoDBClient):
    """Test that scan exposes last_evaluated_key for pagination."""
    # GIVEN a table with items
    # WHEN we scan with page_size=10
    result = PaginationUser.scan(page_size=10)

    # Consume first page
    first_page = []
    async for user in result:
        first_page.append(user)
        if len(first_page) == 10:
            break

    # THEN last_evaluated_key is available
    assert result.last_evaluated_key is not None
    assert len(first_page) == 10


@pytest.mark.asyncio
async def test_scan_manual_pagination(seeded_table: DynamoDBClient):
    """Test manual scan pagination using last_evaluated_key."""
    # GIVEN a table with items
    all_items = []
    last_key = None

    # WHEN we paginate manually
    while True:
        result = PaginationUser.scan(
            page_size=10,
            last_evaluated_key=last_key,
        )

        async for user in result:
            all_items.append(user)

        last_key = result.last_evaluated_key
        if last_key is None:
            break

    # THEN we get all items
    assert len(all_items) >= 25


# ========== GSI async pagination ==========


@pytest.mark.asyncio
async def test_gsi_query_last_evaluated_key(seeded_table: DynamoDBClient):
    """Test that GSI query exposes last_evaluated_key."""
    # GIVEN a table with 25 active users
    # WHEN we query the GSI with page_size=10
    result = PaginationUser.status_index.query(
        status="active",
        page_size=10,
    )

    # Consume first page
    first_page = []
    async for user in result:
        first_page.append(user)
        if len(first_page) == 10:
            break

    # THEN last_evaluated_key is available
    assert result.last_evaluated_key is not None
    assert len(first_page) == 10


@pytest.mark.asyncio
async def test_gsi_query_manual_pagination(seeded_table: DynamoDBClient):
    """Test GSI manual pagination using last_evaluated_key."""
    # GIVEN a table with 25 active users
    all_items = []
    last_key = None

    # WHEN we paginate manually through GSI
    while True:
        result = PaginationUser.status_index.query(
            status="active",
            page_size=10,
            last_evaluated_key=last_key,
        )

        async for user in result:
            all_items.append(user)

        last_key = result.last_evaluated_key
        if last_key is None:
            break

    # THEN we get all 25 items
    assert len(all_items) == 25


# ========== LSI async pagination ==========


@pytest.mark.asyncio
async def test_lsi_query_last_evaluated_key(seeded_table: DynamoDBClient):
    """Test that LSI query exposes last_evaluated_key."""
    # GIVEN a table with 25 users
    # WHEN we query the LSI with page_size=10
    result = PaginationUser.age_index.query(
        pk="USER#pagination",
        page_size=10,
    )

    # Consume first page
    first_page = []
    async for user in result:
        first_page.append(user)
        if len(first_page) == 10:
            break

    # THEN last_evaluated_key is available
    assert result.last_evaluated_key is not None
    assert len(first_page) == 10


@pytest.mark.asyncio
async def test_lsi_query_manual_pagination(seeded_table: DynamoDBClient):
    """Test LSI manual pagination using last_evaluated_key."""
    # GIVEN a table with 25 users
    all_items = []
    last_key = None

    # WHEN we paginate manually through LSI
    while True:
        result = PaginationUser.age_index.query(
            pk="USER#pagination",
            page_size=10,
            last_evaluated_key=last_key,
        )

        async for user in result:
            all_items.append(user)

        last_key = result.last_evaluated_key
        if last_key is None:
            break

    # THEN we get all 25 items
    assert len(all_items) == 25
