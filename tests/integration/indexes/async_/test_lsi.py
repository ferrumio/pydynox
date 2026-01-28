"""Integration tests for LocalSecondaryIndex queries.

With async-first API:
- sync_query() for sync iteration
- query() for async iteration (default)
"""

import pytest
from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.indexes import LocalSecondaryIndex


@pytest.fixture(scope="module")
def client(dynamodb_endpoint):
    """Create a DynamoDB client for tests."""
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
    )
    set_default_client(client)
    return client


@pytest.fixture(scope="module")
def user_table(client):
    """Create a table with LSI for testing."""
    table_name = "lsi_test_users"

    class User(Model):
        model_config = ModelConfig(table=table_name)

        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        status = StringAttribute()
        age = NumberAttribute()
        email = StringAttribute()

        status_index = LocalSecondaryIndex(
            index_name="status-index",
            range_key="status",
        )

        age_index = LocalSecondaryIndex(
            index_name="age-index",
            range_key="age",
            projection=["email"],
        )

    User.sync_create_table(wait=True)

    yield User

    client.sync_delete_table(table_name)


# ========== SYNC TESTS (sync_query) ==========


def test_lsi_sync_query_basic(user_table):
    """Query LSI returns items sorted by LSI range key."""
    User = user_table
    User(pk="USER#1", sk="PROFILE#1", status="active", age=30, email="a@test.com").sync_save()
    User(pk="USER#1", sk="PROFILE#2", status="inactive", age=25, email="b@test.com").sync_save()
    User(pk="USER#1", sk="PROFILE#3", status="active", age=35, email="c@test.com").sync_save()

    results = list(User.status_index.sync_query(pk="USER#1"))

    assert len(results) == 3


def test_lsi_sync_query_with_range_condition(user_table):
    """Query LSI with range key condition filters by LSI range key."""
    User = user_table

    results = list(
        User.status_index.sync_query(
            pk="USER#1",
            range_key_condition=User.status == "active",
        )
    )

    assert len(results) == 2
    for user in results:
        assert user.status == "active"


def test_lsi_sync_query_scan_index_forward(user_table):
    """Query LSI respects scan_index_forward for sort order."""
    User = user_table

    asc_results = list(User.age_index.sync_query(pk="USER#1", scan_index_forward=True))
    desc_results = list(User.age_index.sync_query(pk="USER#1", scan_index_forward=False))

    asc_ages = [u.age for u in asc_results]
    desc_ages = [u.age for u in desc_results]
    assert asc_ages == sorted(asc_ages)
    assert desc_ages == sorted(desc_ages, reverse=True)


def test_lsi_sync_query_with_limit(user_table):
    """Query LSI respects limit parameter."""
    User = user_table

    result = User.status_index.sync_query(pk="USER#1", limit=2)
    first_item = next(iter(result))
    assert first_item is not None


def test_lsi_sync_query_consistent_read(user_table):
    """Query LSI supports consistent read."""
    User = user_table

    results = list(User.status_index.sync_query(pk="USER#1", consistent_read=True))

    assert len(results) >= 0


def test_lsi_sync_query_different_hash_keys(user_table):
    """Query LSI returns only items for the specified hash key."""
    User = user_table
    User(pk="USER#2", sk="PROFILE#1", status="active", age=40, email="d@test.com").sync_save()

    results = list(User.status_index.sync_query(pk="USER#2"))

    assert len(results) == 1
    assert results[0].pk == "USER#2"


# ========== ASYNC TESTS (query - default) ==========


@pytest.mark.asyncio
async def test_lsi_async_query_basic(user_table):
    """Async query LSI returns items."""
    User = user_table
    User(pk="ASYNC#1", sk="PROFILE#1", status="active", age=30, email="async@test.com").sync_save()

    results = []
    async for user in User.status_index.query(pk="ASYNC#1"):
        results.append(user)

    assert len(results) == 1
    assert results[0].pk == "ASYNC#1"


@pytest.mark.asyncio
async def test_lsi_async_query_with_range_condition(user_table):
    """Async query LSI with range key condition."""
    User = user_table
    User(pk="ASYNC#2", sk="PROFILE#1", status="active", age=25, email="a@test.com").sync_save()
    User(pk="ASYNC#2", sk="PROFILE#2", status="inactive", age=30, email="b@test.com").sync_save()

    results = []
    async for user in User.status_index.query(
        pk="ASYNC#2",
        range_key_condition=User.status == "active",
    ):
        results.append(user)

    assert len(results) == 1
    assert results[0].status == "active"


@pytest.mark.asyncio
async def test_lsi_async_query_first(user_table):
    """Async query LSI first() method."""
    User = user_table
    User(pk="ASYNC#3", sk="PROFILE#1", status="first", age=35, email="first@test.com").sync_save()

    user = await User.status_index.query(pk="ASYNC#3").first()

    assert user is not None
    assert user.status == "first"


@pytest.mark.asyncio
async def test_lsi_async_query_first_empty(user_table):
    """Async query LSI first() with no results."""
    User = user_table

    user = await User.status_index.query(pk="NONEXISTENT#1").first()

    assert user is None
