"""Integration tests for Collection."""

from __future__ import annotations

import pytest
from pydynox import Collection, Model, ModelConfig
from pydynox.attributes import StringAttribute


@pytest.fixture
def models(dynamo):
    """Create test models with discriminator."""

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

    class Address(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        _type = StringAttribute(discriminator=True)
        city = StringAttribute()

    return {"User": User, "Order": Order, "Address": Address}


@pytest.mark.asyncio
async def test_collection_query_multiple_types(models):
    User = models["User"]
    Order = models["Order"]
    Address = models["Address"]

    # Save test data
    user = User(pk="USER#123", sk="PROFILE", name="John")
    await user.save()

    order1 = Order(pk="USER#123", sk="ORDER#001", total="100")
    await order1.save()

    order2 = Order(pk="USER#123", sk="ORDER#002", total="200")
    await order2.save()

    address = Address(pk="USER#123", sk="ADDRESS#HOME", city="NYC")
    await address.save()

    # Query with Collection
    collection = Collection([User, Order, Address])
    result = await collection.query(pk="USER#123")

    # Check results
    assert len(result.users) == 1
    assert result.users[0].name == "John"

    assert len(result.orders) == 2
    assert {o.total for o in result.orders} == {"100", "200"}

    assert len(result.addresss) == 1
    assert result.addresss[0].city == "NYC"


@pytest.mark.asyncio
async def test_collection_query_with_sk_begins_with(models):
    User = models["User"]
    Order = models["Order"]

    # Save test data
    user = User(pk="USER#456", sk="PROFILE", name="Jane")
    await user.save()

    order = Order(pk="USER#456", sk="ORDER#001", total="50")
    await order.save()

    # Query only orders
    collection = Collection([User, Order])
    result = await collection.query(pk="USER#456", sk_begins_with="ORDER#")

    assert len(result.users) == 0
    assert len(result.orders) == 1
    assert result.orders[0].total == "50"


@pytest.mark.asyncio
async def test_collection_query_with_limit(models):
    Order = models["Order"]

    # Save multiple orders
    for i in range(5):
        order = Order(pk="USER#789", sk=f"ORDER#{i:03d}", total=str(i * 10))
        await order.save()

    # Query with limit
    collection = Collection([Order])
    result = await collection.query(pk="USER#789", limit=2)

    assert len(result.orders) == 2


@pytest.mark.asyncio
async def test_collection_get_method(models):
    User = models["User"]
    Order = models["Order"]

    user = User(pk="USER#GET", sk="PROFILE", name="Test")
    await user.save()

    order = Order(pk="USER#GET", sk="ORDER#001", total="999")
    await order.save()

    collection = Collection([User, Order])
    result = await collection.query(pk="USER#GET")

    # Use get() method
    users = result.get(User)
    orders = result.get(Order)

    assert len(users) == 1
    assert isinstance(users[0], User)
    assert users[0].name == "Test"

    assert len(orders) == 1
    assert isinstance(orders[0], Order)
    assert orders[0].total == "999"


def test_collection_sync_query(models):
    User = models["User"]
    Order = models["Order"]

    # Save test data (sync)
    user = User(pk="USER#SYNC", sk="PROFILE", name="Sync")
    user.sync_save()

    order = Order(pk="USER#SYNC", sk="ORDER#001", total="111")
    order.sync_save()

    # Query with Collection (sync)
    collection = Collection([User, Order])
    result = collection.sync_query(pk="USER#SYNC")

    assert len(result.users) == 1
    assert result.users[0].name == "Sync"

    assert len(result.orders) == 1
    assert result.orders[0].total == "111"
