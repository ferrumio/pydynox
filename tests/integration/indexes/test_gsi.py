"""Integration tests for GlobalSecondaryIndex queries."""

import pytest
from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.indexes import GlobalSecondaryIndex


@pytest.fixture
def gsi_client(dynamodb_endpoint):
    """Create a pydynox client and table with GSIs for testing."""
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
    )

    # Delete if exists
    if client.table_exists("gsi_test_table"):
        client.delete_table("gsi_test_table")

    # Create table with GSIs
    client.create_table(
        "gsi_test_table",
        hash_key=("pk", "S"),
        range_key=("sk", "S"),
        global_secondary_indexes=[
            {
                "index_name": "email-index",
                "hash_key": ("email", "S"),
                "projection": "ALL",
            },
            {
                "index_name": "status-index",
                "hash_key": ("status", "S"),
                "range_key": ("pk", "S"),
                "projection": "ALL",
            },
        ],
    )

    set_default_client(client)
    return client


class User(Model):
    """Test model with GSIs."""

    model_config = ModelConfig(table="gsi_test_table")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    email = StringAttribute()
    status = StringAttribute()
    name = StringAttribute()
    age = NumberAttribute()

    email_index = GlobalSecondaryIndex(
        index_name="email-index",
        hash_key="email",
    )

    status_index = GlobalSecondaryIndex(
        index_name="status-index",
        hash_key="status",
        range_key="pk",
    )


def test_gsi_query_by_email(gsi_client):
    """Test querying GSI by email."""
    # GIVEN users saved with email attribute
    user1 = User(
        pk="USER#1",
        sk="PROFILE",
        email="john@example.com",
        status="active",
        name="John",
        age=30,
    )
    user1.save()

    user2 = User(
        pk="USER#2",
        sk="PROFILE",
        email="jane@example.com",
        status="active",
        name="Jane",
        age=25,
    )
    user2.save()

    # WHEN we query by email
    results = list(User.email_index.query(email="john@example.com"))

    # THEN only the matching user is returned
    assert len(results) == 1
    assert results[0].pk == "USER#1"
    assert results[0].name == "John"
    assert results[0].email == "john@example.com"


def test_gsi_query_by_status(gsi_client):
    """Test querying GSI by status."""
    # GIVEN users with different statuses
    User(
        pk="USER#1",
        sk="PROFILE",
        email="john@example.com",
        status="active",
        name="John",
        age=30,
    ).save()

    User(
        pk="USER#2",
        sk="PROFILE",
        email="jane@example.com",
        status="active",
        name="Jane",
        age=25,
    ).save()

    User(
        pk="USER#3",
        sk="PROFILE",
        email="bob@example.com",
        status="inactive",
        name="Bob",
        age=35,
    ).save()

    # WHEN we query active users
    results = list(User.status_index.query(status="active"))

    # THEN only active users are returned
    assert len(results) == 2
    pks = {r.pk for r in results}
    assert pks == {"USER#1", "USER#2"}


def test_gsi_query_with_range_key_condition(gsi_client):
    """Test GSI query with range key condition."""
    # GIVEN users with different pk prefixes
    User(
        pk="USER#1",
        sk="PROFILE",
        email="john@example.com",
        status="active",
        name="John",
        age=30,
    ).save()

    User(
        pk="USER#2",
        sk="PROFILE",
        email="jane@example.com",
        status="active",
        name="Jane",
        age=25,
    ).save()

    User(
        pk="ADMIN#1",
        sk="PROFILE",
        email="admin@example.com",
        status="active",
        name="Admin",
        age=40,
    ).save()

    # WHEN we query active users with pk starting with "USER#"
    results = list(
        User.status_index.query(
            status="active",
            range_key_condition=User.pk.begins_with("USER#"),
        )
    )

    # THEN only USER# items are returned
    assert len(results) == 2
    pks = {r.pk for r in results}
    assert pks == {"USER#1", "USER#2"}


def test_gsi_query_with_filter(gsi_client):
    """Test GSI query with filter condition."""
    # GIVEN users with different ages
    User(
        pk="USER#1",
        sk="PROFILE",
        email="john@example.com",
        status="active",
        name="John",
        age=30,
    ).save()

    User(
        pk="USER#2",
        sk="PROFILE",
        email="jane@example.com",
        status="active",
        name="Jane",
        age=25,
    ).save()

    # WHEN we query active users with age >= 30
    results = list(
        User.status_index.query(
            status="active",
            filter_condition=User.age >= 30,
        )
    )

    # THEN only users with age >= 30 are returned
    assert len(results) == 1
    assert results[0].pk == "USER#1"
    assert results[0].name == "John"


def test_gsi_query_with_limit(gsi_client):
    """Test GSI query with limit."""
    # GIVEN multiple users
    for i in range(5):
        User(
            pk=f"USER#{i}",
            sk="PROFILE",
            email=f"user{i}@example.com",
            status="active",
            name=f"User {i}",
            age=20 + i,
        ).save()

    # WHEN we query with limit
    results = list(User.status_index.query(status="active", limit=2))

    # THEN all items are returned (limit is per page, iterator fetches all)
    assert len(results) == 5


def test_gsi_query_descending(gsi_client):
    """Test GSI query with descending order."""
    # GIVEN users
    User(
        pk="USER#1",
        sk="PROFILE",
        email="john@example.com",
        status="active",
        name="John",
        age=30,
    ).save()

    User(
        pk="USER#2",
        sk="PROFILE",
        email="jane@example.com",
        status="active",
        name="Jane",
        age=25,
    ).save()

    # WHEN we query in descending order
    results = list(
        User.status_index.query(
            status="active",
            scan_index_forward=False,
        )
    )

    # THEN results are in descending order by pk (range key)
    assert len(results) == 2
    assert results[0].pk == "USER#2"
    assert results[1].pk == "USER#1"


def test_gsi_query_returns_model_instances(gsi_client):
    """Test that GSI query returns proper model instances."""
    User(
        pk="USER#1",
        sk="PROFILE",
        email="john@example.com",
        status="active",
        name="John",
        age=30,
    ).save()

    results = list(User.email_index.query(email="john@example.com"))

    assert len(results) == 1
    user = results[0]

    # Should be a User instance
    assert isinstance(user, User)

    # Should have all attributes
    assert user.pk == "USER#1"
    assert user.sk == "PROFILE"
    assert user.email == "john@example.com"
    assert user.status == "active"
    assert user.name == "John"
    assert user.age == 30


def test_gsi_query_empty_result(gsi_client):
    """Test GSI query with no matching items."""
    results = list(User.email_index.query(email="nonexistent@example.com"))

    assert len(results) == 0


# ========== ASYNC TESTS ==========


@pytest.mark.asyncio
async def test_async_gsi_query_by_email(gsi_client):
    """Test async querying GSI by email."""
    # GIVEN a user saved with email attribute
    User(
        pk="ASYNC#1",
        sk="PROFILE",
        email="async@example.com",
        status="active",
        name="Async User",
        age=25,
    ).save()

    # WHEN querying by email using async_query
    results = []
    async for user in User.email_index.async_query(email="async@example.com"):
        results.append(user)

    # THEN we get the user
    assert len(results) == 1
    assert results[0].name == "Async User"
    assert results[0].pk == "ASYNC#1"


@pytest.mark.asyncio
async def test_async_gsi_query_with_filter(gsi_client):
    """Test async GSI query with filter condition."""
    # GIVEN users with different ages
    for i in range(3):
        User(
            pk=f"ASYNC_FILTER#{i}",
            sk="PROFILE",
            email="filter_async@example.com",
            status="active",
            name=f"User {i}",
            age=20 + i * 10,  # 20, 30, 40
        ).save()

    # WHEN querying with age filter
    results = []
    async for user in User.email_index.async_query(
        email="filter_async@example.com",
        filter_condition=User.age >= 30,
    ):
        results.append(user)

    # THEN we get only users with age >= 30
    assert len(results) == 2
    ages = {u.age for u in results}
    assert ages == {30, 40}


@pytest.mark.asyncio
async def test_async_gsi_query_first(gsi_client):
    """Test async GSI query first() method."""
    # GIVEN a user
    User(
        pk="ASYNC_FIRST#1",
        sk="PROFILE",
        email="first_async@example.com",
        status="active",
        name="First User",
        age=30,
    ).save()

    # WHEN using first()
    user = await User.email_index.async_query(email="first_async@example.com").first()

    # THEN we get the user
    assert user is not None
    assert user.name == "First User"


@pytest.mark.asyncio
async def test_async_gsi_query_first_empty(gsi_client):
    """Test async GSI query first() with no results."""
    # WHEN querying for non-existent email
    user = await User.email_index.async_query(email="nonexistent_async@example.com").first()

    # THEN we get None
    assert user is None


@pytest.mark.asyncio
async def test_async_gsi_query_with_range_key_condition(gsi_client):
    """Test async GSI query with range key condition."""
    # GIVEN users with different pk prefixes
    for prefix in ["A", "B", "C"]:
        User(
            pk=f"{prefix}#ASYNC_RANGE",
            sk="PROFILE",
            email=f"range_async_{prefix}@example.com",
            status="range_async_test",
            name=f"User {prefix}",
            age=25,
        ).save()

    # WHEN querying with range key condition (pk begins_with "B")
    results = []
    async for user in User.status_index.async_query(
        status="range_async_test",
        range_key_condition=User.pk.begins_with("B"),
    ):
        results.append(user)

    # THEN we get only user B
    assert len(results) == 1
    assert results[0].pk == "B#ASYNC_RANGE"
