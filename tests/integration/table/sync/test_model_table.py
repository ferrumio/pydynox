"""Integration tests for Model table operations (sync).

Full test coverage using sync_* methods. Async API is validated separately
in test_model_table_async.py with minimal tests.
"""

import uuid

import pytest
from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.indexes import GlobalSecondaryIndex, LocalSecondaryIndex


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


# ============ Basic Table Operations ============


def test_sync_create_table_basic(model_table_client):
    """Test Model.sync_create_table() with basic model."""
    table_name = unique_table_name()

    class SimpleUser(Model):
        model_config = ModelConfig(table=table_name)
        pk = StringAttribute(hash_key=True)
        name = StringAttribute()

    SimpleUser.sync_create_table(wait=True)

    assert model_table_client.sync_table_exists(table_name)

    model_table_client.sync_delete_table(table_name)


@pytest.mark.asyncio
async def test_sync_create_table_with_range_key(model_table_client):
    """Test Model.sync_create_table() with hash and range key."""
    table_name = unique_table_name()

    class UserWithRange(Model):
        model_config = ModelConfig(table=table_name)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        name = StringAttribute()

    UserWithRange.sync_create_table(wait=True)

    # Verify by saving and getting an item (async)
    user = UserWithRange(pk="USER#1", sk="PROFILE", name="John")
    await user.save()

    fetched = await UserWithRange.get(pk="USER#1", sk="PROFILE")
    assert fetched is not None
    assert fetched.name == "John"

    model_table_client.sync_delete_table(table_name)


def test_sync_table_exists_true(model_table_client):
    """Test Model.sync_table_exists() returns True when table exists."""
    table_name = unique_table_name()

    class ExistsModel(Model):
        model_config = ModelConfig(table=table_name)
        pk = StringAttribute(hash_key=True)

    ExistsModel.sync_create_table(wait=True)

    assert ExistsModel.sync_table_exists() is True

    model_table_client.sync_delete_table(table_name)


def test_sync_table_exists_false(model_table_client):
    """Test Model.sync_table_exists() returns False when table doesn't exist."""
    table_name = unique_table_name()

    class NotExistsModel(Model):
        model_config = ModelConfig(table=table_name)
        pk = StringAttribute(hash_key=True)

    assert NotExistsModel.sync_table_exists() is False


def test_sync_delete_table(model_table_client):
    """Test Model.sync_delete_table()."""
    table_name = unique_table_name()

    class DeleteModel(Model):
        model_config = ModelConfig(table=table_name)
        pk = StringAttribute(hash_key=True)

    DeleteModel.sync_create_table(wait=True)
    assert DeleteModel.sync_table_exists() is True

    DeleteModel.sync_delete_table()

    assert DeleteModel.sync_table_exists() is False


def test_sync_create_table_provisioned(model_table_client):
    """Test Model.sync_create_table() with provisioned capacity."""
    table_name = unique_table_name()

    class ProvisionedModel(Model):
        model_config = ModelConfig(table=table_name)
        pk = StringAttribute(hash_key=True)

    ProvisionedModel.sync_create_table(
        billing_mode="PROVISIONED",
        read_capacity=5,
        write_capacity=5,
        wait=True,
    )

    assert ProvisionedModel.sync_table_exists() is True

    model_table_client.sync_delete_table(table_name)


def test_sync_create_table_idempotent_check(model_table_client):
    """Test checking sync_table_exists before sync_create_table."""
    table_name = unique_table_name()

    class IdempotentModel(Model):
        model_config = ModelConfig(table=table_name)
        pk = StringAttribute(hash_key=True)

    # Pattern: check before create
    if not IdempotentModel.sync_table_exists():
        IdempotentModel.sync_create_table(wait=True)

    assert IdempotentModel.sync_table_exists() is True

    # Second check should not create again
    if not IdempotentModel.sync_table_exists():
        IdempotentModel.sync_create_table(wait=True)

    assert IdempotentModel.sync_table_exists() is True

    model_table_client.sync_delete_table(table_name)


@pytest.mark.asyncio
async def test_sync_create_table_with_number_hash_key(model_table_client):
    """Test Model.sync_create_table() with number hash key."""
    table_name = unique_table_name()

    class NumberKeyModel(Model):
        model_config = ModelConfig(table=table_name)
        id = NumberAttribute(hash_key=True)
        name = StringAttribute()

    NumberKeyModel.sync_create_table(wait=True)

    item = NumberKeyModel(id=123, name="Test")
    await item.save()

    fetched = await NumberKeyModel.get(id=123)
    assert fetched is not None
    assert fetched.name == "Test"

    model_table_client.sync_delete_table(table_name)


# ============ GSI Tests ============


@pytest.mark.asyncio
async def test_sync_create_table_with_gsi(model_table_client):
    """Test Model.sync_create_table() with GSI."""
    table_name = unique_table_name()

    class UserWithGSI(Model):
        model_config = ModelConfig(table=table_name)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        email = StringAttribute()

        email_index = GlobalSecondaryIndex(
            index_name="email-index",
            hash_key="email",
        )

    UserWithGSI.sync_create_table(wait=True)

    await UserWithGSI(pk="USER#1", sk="PROFILE", email="john@example.com").save()

    results = [r async for r in UserWithGSI.email_index.query(email="john@example.com")]
    assert len(results) == 1
    assert results[0].pk == "USER#1"

    model_table_client.sync_delete_table(table_name)


@pytest.mark.asyncio
async def test_sync_create_table_with_gsi_and_range_key(model_table_client):
    """Test Model.sync_create_table() with GSI that has range key."""
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

    UserWithGSIRange.sync_create_table(wait=True)

    await UserWithGSIRange(pk="USER#1", sk="PROFILE", status="active", age=30).save()
    await UserWithGSIRange(pk="USER#2", sk="PROFILE", status="active", age=25).save()

    results = [r async for r in UserWithGSIRange.status_index.query(status="active")]
    assert len(results) == 2
    assert results[0].age == 25  # Ordered by age ascending
    assert results[1].age == 30

    model_table_client.sync_delete_table(table_name)


@pytest.mark.asyncio
async def test_sync_create_table_with_multiple_gsis(model_table_client):
    """Test Model.sync_create_table() with multiple GSIs."""
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

    UserMultiGSI.sync_create_table(wait=True)

    await UserMultiGSI(pk="USER#1", sk="PROFILE", email="john@example.com", status="active").save()

    by_email = [r async for r in UserMultiGSI.email_index.query(email="john@example.com")]
    assert len(by_email) == 1

    by_status = [r async for r in UserMultiGSI.status_index.query(status="active")]
    assert len(by_status) == 1

    model_table_client.sync_delete_table(table_name)


# ============ LSI Tests ============


@pytest.mark.asyncio
async def test_sync_create_table_with_lsi(model_table_client):
    """Test Model.sync_create_table() with LSI."""
    table_name = unique_table_name()

    class UserWithLSI(Model):
        model_config = ModelConfig(table=table_name)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        status = StringAttribute()

        status_index = LocalSecondaryIndex(
            index_name="status-index",
            range_key="status",
        )

    UserWithLSI.sync_create_table(wait=True)

    await UserWithLSI(pk="USER#1", sk="PROFILE#1", status="active").save()
    await UserWithLSI(pk="USER#1", sk="PROFILE#2", status="inactive").save()

    results = [r async for r in UserWithLSI.status_index.query(pk="USER#1")]
    assert len(results) == 2

    model_table_client.sync_delete_table(table_name)


@pytest.mark.asyncio
async def test_sync_create_table_with_lsi_range_condition(model_table_client):
    """Test Model.sync_create_table() with LSI and range condition query."""
    table_name = unique_table_name()

    class UserWithLSI(Model):
        model_config = ModelConfig(table=table_name)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        status = StringAttribute()

        status_index = LocalSecondaryIndex(
            index_name="status-index",
            range_key="status",
        )

    UserWithLSI.sync_create_table(wait=True)

    await UserWithLSI(pk="USER#1", sk="PROFILE#1", status="active").save()
    await UserWithLSI(pk="USER#1", sk="PROFILE#2", status="inactive").save()
    await UserWithLSI(pk="USER#1", sk="PROFILE#3", status="active").save()

    results = [
        r
        async for r in UserWithLSI.status_index.query(
            pk="USER#1",
            range_key_condition=UserWithLSI.status == "active",
        )
    ]

    assert len(results) == 2
    for user in results:
        assert user.status == "active"

    model_table_client.sync_delete_table(table_name)


@pytest.mark.asyncio
async def test_sync_create_table_with_gsi_and_lsi(model_table_client):
    """Test Model.sync_create_table() with both GSI and LSI."""
    table_name = unique_table_name()

    class UserBothIndexes(Model):
        model_config = ModelConfig(table=table_name)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        email = StringAttribute()
        status = StringAttribute()

        email_index = GlobalSecondaryIndex(
            index_name="email-index",
            hash_key="email",
        )

        status_index = LocalSecondaryIndex(
            index_name="status-index",
            range_key="status",
        )

    UserBothIndexes.sync_create_table(wait=True)

    await UserBothIndexes(
        pk="USER#1", sk="PROFILE", email="john@example.com", status="active"
    ).save()

    by_email = [r async for r in UserBothIndexes.email_index.query(email="john@example.com")]
    assert len(by_email) == 1

    by_status = [r async for r in UserBothIndexes.status_index.query(pk="USER#1")]
    assert len(by_status) == 1

    model_table_client.sync_delete_table(table_name)
