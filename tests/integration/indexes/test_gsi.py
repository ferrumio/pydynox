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
    # Create test users
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

    # Query by email
    results = list(User.email_index.query(email="john@example.com"))

    assert len(results) == 1
    assert results[0].pk == "USER#1"
    assert results[0].name == "John"
    assert results[0].email == "john@example.com"


def test_gsi_query_by_status(gsi_client):
    """Test querying GSI by status."""
    # Create test users
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

    # Query active users
    results = list(User.status_index.query(status="active"))

    assert len(results) == 2
    pks = {r.pk for r in results}
    assert pks == {"USER#1", "USER#2"}


def test_gsi_query_with_range_key_condition(gsi_client):
    """Test GSI query with range key condition."""
    # Create test users
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

    # Query active users with pk starting with "USER#"
    results = list(
        User.status_index.query(
            status="active",
            range_key_condition=User.pk.begins_with("USER#"),
        )
    )

    assert len(results) == 2
    pks = {r.pk for r in results}
    assert pks == {"USER#1", "USER#2"}


def test_gsi_query_with_filter(gsi_client):
    """Test GSI query with filter condition."""
    # Create test users
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

    # Query active users with age >= 30
    results = list(
        User.status_index.query(
            status="active",
            filter_condition=User.age >= 30,
        )
    )

    assert len(results) == 1
    assert results[0].pk == "USER#1"
    assert results[0].name == "John"


def test_gsi_query_with_limit(gsi_client):
    """Test GSI query with limit."""
    # Create test users
    for i in range(5):
        User(
            pk=f"USER#{i}",
            sk="PROFILE",
            email=f"user{i}@example.com",
            status="active",
            name=f"User {i}",
            age=20 + i,
        ).save()

    # Query with limit
    results = list(User.status_index.query(status="active", limit=2))

    # Should get all 5 because limit is per page, not total
    # But we iterate through all pages
    assert len(results) == 5


def test_gsi_query_descending(gsi_client):
    """Test GSI query with descending order."""
    # Create test users
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

    # Query in descending order (by range key)
    results = list(
        User.status_index.query(
            status="active",
            scan_index_forward=False,
        )
    )

    assert len(results) == 2
    # Descending order by pk (range key)
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


def test_gsi_query_metrics(gsi_client):
    """Test that GSI query provides metrics."""
    User(
        pk="USER#1",
        sk="PROFILE",
        email="john@example.com",
        status="active",
        name="John",
        age=30,
    ).save()

    result = User.email_index.query(email="john@example.com")

    # Iterate to trigger the query
    items = list(result)
    assert len(items) == 1

    # Check metrics are available
    assert result.metrics is not None
    assert result.metrics.duration_ms >= 0
