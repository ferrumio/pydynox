"""Integration tests for Model.create_table(), table_exists(), delete_table()."""

import uuid

import pytest
from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.indexes import GlobalSecondaryIndex


@pytest.fixture
def model_table_client(dynamodb_endpoint):
    """Create a pydynox client for table operations testing."""
    client = DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
    )
    set_default_client(client)
    return client


def unique_table_name() -> str:
    """Generate a unique table name for each test."""
    return f"test_table_{uuid.uuid4().hex[:8]}"


def test_create_table_basic(model_table_client):
    """Test Model.create_table() with basic model."""
    table_name = unique_table_name()

    class SimpleUser(Model):
        model_config = ModelConfig(table=table_name)
        pk = StringAttribute(hash_key=True)
        name = StringAttribute()

    # WHEN we create the table
    SimpleUser.create_table(wait=True)

    # THEN the table exists
    assert model_table_client.table_exists(table_name)

    # Cleanup
    model_table_client.delete_table(table_name)


def test_create_table_with_range_key(model_table_client):
    """Test Model.create_table() with hash and range key."""
    table_name = unique_table_name()

    class UserWithRange(Model):
        model_config = ModelConfig(table=table_name)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        name = StringAttribute()

    UserWithRange.create_table(wait=True)

    # Verify by saving and getting an item
    user = UserWithRange(pk="USER#1", sk="PROFILE", name="John")
    user.save()

    fetched = UserWithRange.get(pk="USER#1", sk="PROFILE")
    assert fetched is not None
    assert fetched.name == "John"

    # Cleanup
    model_table_client.delete_table(table_name)


def test_create_table_with_gsi(model_table_client):
    """Test Model.create_table() with GSI."""
    table_name = unique_table_name()

    class UserWithGSI(Model):
        model_config = ModelConfig(table=table_name)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        email = StringAttribute()
        status = StringAttribute()

        email_index = GlobalSecondaryIndex(
            index_name="email-index",
            hash_key="email",
        )

    UserWithGSI.create_table(wait=True)

    # Save some users
    UserWithGSI(pk="USER#1", sk="PROFILE", email="john@example.com", status="active").save()
    UserWithGSI(pk="USER#2", sk="PROFILE", email="jane@example.com", status="active").save()

    # Query by GSI
    results = list(UserWithGSI.email_index.query(email="john@example.com"))
    assert len(results) == 1
    assert results[0].pk == "USER#1"

    # Cleanup
    model_table_client.delete_table(table_name)


def test_create_table_with_gsi_and_range_key(model_table_client):
    """Test Model.create_table() with GSI that has range key."""
    table_name = unique_table_name()

    class UserWithGSIRange(Model):
        model_config = ModelConfig(table=table_name)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        status = StringAttribute()
        age = NumberAttribute()

        status_index = GlobalSecondaryIndex(
            index_name="status-index",
            hash_key="status",
            range_key="age",
        )

    UserWithGSIRange.create_table(wait=True)

    # Save users with different ages
    UserWithGSIRange(pk="USER#1", sk="PROFILE", status="active", age=30).save()
    UserWithGSIRange(pk="USER#2", sk="PROFILE", status="active", age=25).save()
    UserWithGSIRange(pk="USER#3", sk="PROFILE", status="inactive", age=35).save()

    # Query by status, ordered by age
    results = list(UserWithGSIRange.status_index.query(status="active"))
    assert len(results) == 2

    # Should be ordered by age (ascending by default)
    assert results[0].age == 25
    assert results[1].age == 30

    # Cleanup
    model_table_client.delete_table(table_name)


def test_create_table_with_multiple_gsis(model_table_client):
    """Test Model.create_table() with multiple GSIs."""
    table_name = unique_table_name()

    class UserMultiGSI(Model):
        model_config = ModelConfig(table=table_name)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        email = StringAttribute()
        status = StringAttribute()

        email_index = GlobalSecondaryIndex(
            index_name="email-index",
            hash_key="email",
        )

        status_index = GlobalSecondaryIndex(
            index_name="status-index",
            hash_key="status",
        )

    UserMultiGSI.create_table(wait=True)

    # Save a user
    UserMultiGSI(pk="USER#1", sk="PROFILE", email="john@example.com", status="active").save()

    # Query by email
    by_email = list(UserMultiGSI.email_index.query(email="john@example.com"))
    assert len(by_email) == 1

    # Query by status
    by_status = list(UserMultiGSI.status_index.query(status="active"))
    assert len(by_status) == 1

    # Cleanup
    model_table_client.delete_table(table_name)


def test_table_exists_true(model_table_client):
    """Test Model.table_exists() returns True when table exists."""
    table_name = unique_table_name()

    class ExistsModel(Model):
        model_config = ModelConfig(table=table_name)
        pk = StringAttribute(hash_key=True)

    # GIVEN a created table
    ExistsModel.create_table(wait=True)

    # WHEN we check if it exists
    # THEN it returns True
    assert ExistsModel.table_exists() is True

    # Cleanup
    model_table_client.delete_table(table_name)


def test_table_exists_false(model_table_client):
    """Test Model.table_exists() returns False when table doesn't exist."""
    table_name = unique_table_name()

    class NotExistsModel(Model):
        model_config = ModelConfig(table=table_name)
        pk = StringAttribute(hash_key=True)

    # Should not exist
    assert NotExistsModel.table_exists() is False


def test_delete_table(model_table_client):
    """Test Model.delete_table()."""
    table_name = unique_table_name()

    class DeleteModel(Model):
        model_config = ModelConfig(table=table_name)
        pk = StringAttribute(hash_key=True)

    # GIVEN a created table
    DeleteModel.create_table(wait=True)
    assert DeleteModel.table_exists() is True

    # WHEN we delete it
    DeleteModel.delete_table()

    # THEN it no longer exists
    assert DeleteModel.table_exists() is False


def test_create_table_provisioned(model_table_client):
    """Test Model.create_table() with provisioned capacity."""
    table_name = unique_table_name()

    class ProvisionedModel(Model):
        model_config = ModelConfig(table=table_name)
        pk = StringAttribute(hash_key=True)

    ProvisionedModel.create_table(
        billing_mode="PROVISIONED",
        read_capacity=5,
        write_capacity=5,
        wait=True,
    )

    assert ProvisionedModel.table_exists() is True

    # Cleanup
    model_table_client.delete_table(table_name)


def test_create_table_idempotent_check(model_table_client):
    """Test checking table_exists before create_table."""
    table_name = unique_table_name()

    class IdempotentModel(Model):
        model_config = ModelConfig(table=table_name)
        pk = StringAttribute(hash_key=True)

    # Pattern: check before create
    if not IdempotentModel.table_exists():
        IdempotentModel.create_table(wait=True)

    assert IdempotentModel.table_exists() is True

    # Second check should not create again
    if not IdempotentModel.table_exists():
        IdempotentModel.create_table(wait=True)

    # Still exists
    assert IdempotentModel.table_exists() is True

    # Cleanup
    model_table_client.delete_table(table_name)


def test_create_table_with_number_hash_key(model_table_client):
    """Test Model.create_table() with number hash key."""
    table_name = unique_table_name()

    class NumberKeyModel(Model):
        model_config = ModelConfig(table=table_name)
        id = NumberAttribute(hash_key=True)
        name = StringAttribute()

    NumberKeyModel.create_table(wait=True)

    # Save and get
    item = NumberKeyModel(id=123, name="Test")
    item.save()

    fetched = NumberKeyModel.get(id=123)
    assert fetched is not None
    assert fetched.name == "Test"

    # Cleanup
    model_table_client.delete_table(table_name)
