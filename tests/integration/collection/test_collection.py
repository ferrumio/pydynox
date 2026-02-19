"""Integration tests for Collection queries."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydynox import Collection, DynamoDBClient, Model, ModelConfig
from pydynox.attributes import StringAttribute


@pytest.fixture
def collection_models(dynamo):
    """Create two models that share the same client and table."""

    class User(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        _type = StringAttribute(discriminator=True)
        name = StringAttribute()

    class Order(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        _type = StringAttribute(discriminator=True)
        total = StringAttribute()

    return User, Order


@pytest.mark.asyncio
async def test_collection_query_with_shared_client(collection_models):
    """Collection.query returns typed items when models share one client."""
    User, Order = collection_models
    pk = f"COLLECTION#ASYNC#{uuid4().hex}"

    await User(pk=pk, sk="PROFILE", name="Alice").save()
    await Order(pk=pk, sk="ORDER#001", total="100").save()
    await Order(pk=pk, sk="ORDER#002", total="200").save()

    result = await Collection([User, Order]).query(pk=pk)

    assert len(result.users) == 1
    assert result.users[0].name == "Alice"
    assert len(result.orders) == 2
    assert {order.total for order in result.orders} == {"100", "200"}


def test_collection_sync_query_with_shared_client(collection_models):
    """Collection.sync_query returns typed items when models share one client."""
    User, Order = collection_models
    pk = f"COLLECTION#SYNC#{uuid4().hex}"

    User(pk=pk, sk="PROFILE", name="Bob").sync_save()
    Order(pk=pk, sk="ORDER#001", total="300").sync_save()
    Order(pk=pk, sk="ORDER#002", total="400").sync_save()

    result = Collection([User, Order]).sync_query(pk=pk)

    assert len(result.users) == 1
    assert result.users[0].name == "Bob"
    assert len(result.orders) == 2
    assert {order.total for order in result.orders} == {"300", "400"}


def test_collection_raises_when_models_use_different_client_instances(dynamodb_endpoint):
    """Collection validation rejects models with different client objects."""
    client_a = DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
    )
    client_b = DynamoDBClient(
        region="us-east-1",
        endpoint_url=dynamodb_endpoint,
        access_key="testing",
        secret_key="testing",
    )

    class User(Model):
        model_config = ModelConfig(table="test_table", client=client_a)
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        _type = StringAttribute(discriminator=True)
        name = StringAttribute()

    class Order(Model):
        model_config = ModelConfig(table="test_table", client=client_b)
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        _type = StringAttribute(discriminator=True)
        total = StringAttribute()

    with pytest.raises(ValueError, match="must use the same client"):
        Collection([User, Order])
