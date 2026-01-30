"""Example: Testing template keys with MemoryBackend."""

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute
from pydynox.indexes import GlobalSecondaryIndex
from pydynox.testing import MemoryBackend


class UserOrder(Model):
    model_config = ModelConfig(table="app")

    pk = StringAttribute(hash_key=True, template="USER#{user_id}")
    sk = StringAttribute(range_key=True, template="ORDER#{order_id}")
    user_id = StringAttribute()
    order_id = StringAttribute()
    status = StringAttribute()

    by_order = GlobalSecondaryIndex(
        index_name="inverted",
        hash_key="sk",
        range_key="pk",
    )


@pytest.fixture
def memory_backend():
    with MemoryBackend():
        yield


@pytest.mark.asyncio
async def test_template_key_building(memory_backend):
    # GIVEN an order with template keys
    order = UserOrder(user_id="alice", order_id="001", status="pending")

    # THEN keys are built from template
    assert order.pk == "USER#alice"
    assert order.sk == "ORDER#001"


@pytest.mark.asyncio
async def test_query_with_placeholder(memory_backend):
    # GIVEN saved orders
    await UserOrder(user_id="alice", order_id="001", status="shipped").save()
    await UserOrder(user_id="alice", order_id="002", status="pending").save()

    # WHEN querying by placeholder
    orders = [o async for o in UserOrder.query(user_id="alice")]

    # THEN returns matching orders
    assert len(orders) == 2
    assert orders[0].user_id == "alice"


@pytest.mark.asyncio
async def test_gsi_query_with_placeholder(memory_backend):
    # GIVEN saved orders
    await UserOrder(user_id="alice", order_id="001", status="shipped").save()
    await UserOrder(user_id="bob", order_id="002", status="pending").save()

    # WHEN querying GSI by placeholder
    results = [r async for r in UserOrder.by_order.query(order_id="001")]

    # THEN returns the order owner
    assert len(results) == 1
    assert results[0].user_id == "alice"
