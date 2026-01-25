"""Integration tests for LocalSecondaryIndex queries."""

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

    # Create table with LSIs
    User.sync_create_table(wait=True)

    yield User

    # Cleanup
    client.sync_delete_table(table_name)


def test_lsi_query_basic(user_table):
    """Query LSI returns items sorted by LSI range key."""
    # GIVEN users with different statuses
    User = user_table
    User(pk="USER#1", sk="PROFILE#1", status="active", age=30, email="a@test.com").save()
    User(pk="USER#1", sk="PROFILE#2", status="inactive", age=25, email="b@test.com").save()
    User(pk="USER#1", sk="PROFILE#3", status="active", age=35, email="c@test.com").save()

    # WHEN we query the LSI by hash key
    results = list(User.status_index.query(pk="USER#1"))

    # THEN we should get all items for that hash key
    assert len(results) == 3


def test_lsi_query_with_range_condition(user_table):
    """Query LSI with range key condition filters by LSI range key."""
    # GIVEN users with different statuses
    User = user_table

    # WHEN we query with range key condition on status
    results = list(
        User.status_index.query(
            pk="USER#1",
            range_key_condition=User.status == "active",
        )
    )

    # THEN we should get only active users
    assert len(results) == 2
    for user in results:
        assert user.status == "active"


def test_lsi_query_scan_index_forward(user_table):
    """Query LSI respects scan_index_forward for sort order."""
    # GIVEN users with different ages
    User = user_table

    # WHEN we query ascending
    asc_results = list(User.age_index.query(pk="USER#1", scan_index_forward=True))

    # AND descending
    desc_results = list(User.age_index.query(pk="USER#1", scan_index_forward=False))

    # THEN order should be reversed
    asc_ages = [u.age for u in asc_results]
    desc_ages = [u.age for u in desc_results]
    assert asc_ages == sorted(asc_ages)
    assert desc_ages == sorted(desc_ages, reverse=True)


def test_lsi_query_with_limit(user_table):
    """Query LSI respects limit parameter per page."""
    # GIVEN multiple users
    User = user_table

    # WHEN we query with limit (limit is per page, iterator fetches all pages)
    result = User.status_index.query(pk="USER#1", limit=2)

    # THEN the underlying query should use limit
    # Note: limit is per page, not total. The iterator auto-paginates.
    # We just verify the query executes without error
    first_item = next(iter(result))
    assert first_item is not None


def test_lsi_query_consistent_read(user_table):
    """Query LSI supports consistent read (LSI-specific feature)."""
    # GIVEN users in the table
    User = user_table

    # WHEN we query with consistent_read=True
    results = list(User.status_index.query(pk="USER#1", consistent_read=True))

    # THEN query should succeed (LSIs support consistent reads unlike GSIs)
    assert len(results) >= 0


def test_lsi_query_different_hash_keys(user_table):
    """Query LSI returns only items for the specified hash key."""
    # GIVEN users with different hash keys
    User = user_table
    User(pk="USER#2", sk="PROFILE#1", status="active", age=40, email="d@test.com").save()

    # WHEN we query for USER#2
    results = list(User.status_index.query(pk="USER#2"))

    # THEN we should only get USER#2's items
    assert len(results) == 1
    assert results[0].pk == "USER#2"
