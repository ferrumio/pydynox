"""Async integration tests for Model table operations.

Minimal tests to validate async API works. Full coverage is in test_model_table.py.
"""

import uuid

import pytest
from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import StringAttribute
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
    return f"async_table_{uuid.uuid4().hex[:8]}"


@pytest.mark.asyncio
async def test_async_create_table_basic(model_table_client):
    """Test Model.create_table() async works."""
    table_name = unique_table_name()

    class SimpleUser(Model):
        model_config = ModelConfig(table=table_name)
        pk = StringAttribute(hash_key=True)
        name = StringAttribute()

    await SimpleUser.create_table(wait=True)

    exists = await SimpleUser.table_exists()
    assert exists is True

    await SimpleUser.delete_table()


@pytest.mark.asyncio
async def test_async_table_exists_false(model_table_client):
    """Test Model.table_exists() async returns False for non-existent."""
    table_name = unique_table_name()

    class NotExistsModel(Model):
        model_config = ModelConfig(table=table_name)
        pk = StringAttribute(hash_key=True)

    exists = await NotExistsModel.table_exists()
    assert exists is False


@pytest.mark.asyncio
async def test_async_create_table_with_gsi(model_table_client):
    """Test Model.create_table() async with GSI."""
    table_name = unique_table_name()

    class UserWithGSI(Model):
        model_config = ModelConfig(table=table_name)
        pk = StringAttribute(hash_key=True)
        email = StringAttribute()

        email_index = GlobalSecondaryIndex(
            index_name="email-index",
            hash_key="email",
        )

    await UserWithGSI.create_table(wait=True)

    exists = await UserWithGSI.table_exists()
    assert exists is True

    # Verify GSI works by saving and querying
    user = UserWithGSI(pk="USER#1", email="john@example.com")
    await user.save()

    results = [x async for x in UserWithGSI.email_index.query(email="john@example.com")]
    assert len(results) == 1

    await UserWithGSI.delete_table()


@pytest.mark.asyncio
async def test_async_delete_table(model_table_client):
    """Test Model.delete_table() async works."""
    table_name = unique_table_name()

    class DeleteModel(Model):
        model_config = ModelConfig(table=table_name)
        pk = StringAttribute(hash_key=True)

    await DeleteModel.create_table(wait=True)
    assert await DeleteModel.table_exists() is True

    await DeleteModel.delete_table()

    assert await DeleteModel.table_exists() is False
