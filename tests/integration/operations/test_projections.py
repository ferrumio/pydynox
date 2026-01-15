"""Integration tests for field projections."""

import uuid

import pytest
from pydynox import DynamoDBClient, Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


@pytest.fixture
def projection_table(localstack_endpoint):
    """Create a table for projection tests."""
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url=localstack_endpoint,
        access_key="testing",
        secret_key="testing",
    )

    table_name = f"projection_test_{uuid.uuid4().hex[:8]}"

    client.create_table(
        table_name,
        hash_key=("pk", "S"),
        range_key=("sk", "S"),
        wait=True,
    )

    yield client, table_name

    # Cleanup
    client.delete_table(table_name)


def test_get_item_with_projection(projection_table):
    """Test get_item returns only projected fields."""
    client, table_name = projection_table
    pk = f"USER#{uuid.uuid4().hex}"

    # GIVEN an item with many fields
    client.put_item(
        table_name,
        {
            "pk": pk,
            "sk": "PROFILE",
            "name": "John Doe",
            "email": "[email]",
            "age": 30,
            "city": "NYC",
        },
    )

    # WHEN we get with projection
    item = client.get_item(
        table_name,
        {"pk": pk, "sk": "PROFILE"},
        projection=["name", "email"],
    )

    # THEN only projected fields are returned
    assert item is not None
    assert "name" in item
    assert "email" in item
    assert item["name"] == "John Doe"
    assert item["email"] == "[email]"
    # These should NOT be in the result
    assert "age" not in item
    assert "city" not in item


def test_query_with_projection_expression(projection_table):
    """Test query with projection_expression."""
    client, table_name = projection_table
    pk = f"USER#{uuid.uuid4().hex}"

    # Put multiple items
    for i in range(3):
        client.put_item(
            table_name,
            {
                "pk": pk,
                "sk": f"ORDER#{i}",
                "total": 100 + i,
                "status": "pending",
                "items": ["item1", "item2"],
            },
        )

    # Query with projection
    results = list(
        client.query(
            table_name,
            key_condition_expression="#pk = :pk",
            projection_expression="#total, #status",
            expression_attribute_names={"#pk": "pk", "#total": "total", "#status": "status"},
            expression_attribute_values={":pk": pk},
        )
    )

    assert len(results) == 3
    for item in results:
        assert "total" in item
        assert "status" in item
        # items field should NOT be present
        assert "items" not in item


def test_scan_with_projection_expression(projection_table):
    """Test scan with projection_expression."""
    client, table_name = projection_table
    pk = f"SCAN#{uuid.uuid4().hex}"

    # Put items
    for i in range(2):
        client.put_item(
            table_name,
            {
                "pk": pk,
                "sk": f"ITEM#{i}",
                "name": f"Item {i}",
                "description": "Long description here",
                "price": 99.99,
            },
        )

    # Scan with projection
    results = list(
        client.scan(
            table_name,
            filter_expression="#pk = :pk",
            projection_expression="#name",
            expression_attribute_names={"#pk": "pk", "#name": "name"},
            expression_attribute_values={":pk": pk},
        )
    )

    assert len(results) == 2
    for item in results:
        assert "name" in item
        # These should NOT be present
        assert "description" not in item
        assert "price" not in item


# ========== Model-level tests ==========


@pytest.fixture
def user_model(localstack_endpoint):
    """Create a User model for testing."""
    table_name = f"users_{uuid.uuid4().hex[:8]}"

    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url=localstack_endpoint,
        access_key="testing",
        secret_key="testing",
    )

    class User(Model):
        model_config = ModelConfig(table=table_name, client=client)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        name = StringAttribute()
        email = StringAttribute()
        age = NumberAttribute()
        city = StringAttribute()

    User.create_table(wait=True)

    yield User

    client.delete_table(table_name)


def test_model_query_with_fields(user_model):
    """Test Model.query with fields parameter."""
    User = user_model
    pk = f"USER#{uuid.uuid4().hex}"

    # Create users
    for i in range(3):
        user = User(
            pk=pk,
            sk=f"PROFILE#{i}",
            name=f"User {i}",
            email=f"user{i}@example.com",
            age=20 + i,
            city="NYC",
        )
        user.save()

    # Query with fields - returns dicts with only specified fields
    results = list(User.query(hash_key=pk, as_dict=True, fields=["name", "email"]))

    assert len(results) == 3
    for item in results:
        assert "name" in item
        assert "email" in item
        # age and city should NOT be present (except keys which DynamoDB always returns)
        assert "age" not in item
        assert "city" not in item


def test_model_scan_with_fields(user_model):
    """Test Model.scan with fields parameter."""
    User = user_model
    pk = f"SCAN#{uuid.uuid4().hex}"

    # Create users
    for i in range(2):
        user = User(
            pk=pk,
            sk=f"PROFILE#{i}",
            name=f"User {i}",
            email=f"user{i}@example.com",
            age=25,
            city="LA",
        )
        user.save()

    # Scan with fields
    results = list(User.scan(filter_condition=User.pk == pk, as_dict=True, fields=["pk", "name"]))

    assert len(results) == 2
    for item in results:
        assert "pk" in item
        assert "name" in item
        # email, age, city should NOT be present
        assert "email" not in item
        assert "age" not in item
        assert "city" not in item
