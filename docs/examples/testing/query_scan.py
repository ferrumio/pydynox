"""Testing query and scan operations (async - default)."""

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.conditions import Attr


class Order(Model):
    model_config = ModelConfig(table="orders")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    status = StringAttribute()
    total = NumberAttribute()


@pytest.mark.asyncio
async def test_query_by_partition_key(pydynox_memory_backend):
    """Test querying items by partition key."""
    await Order(pk="USER#1", sk="ORDER#001", status="pending", total=100).save()
    await Order(pk="USER#1", sk="ORDER#002", status="shipped", total=200).save()
    await Order(pk="USER#2", sk="ORDER#001", status="pending", total=50).save()

    # Query returns only USER#1's orders
    results = [order async for order in Order.query(partition_key="USER#1")]
    assert len(results) == 2


@pytest.mark.asyncio
async def test_query_with_filter(pydynox_memory_backend):
    """Test query with filter condition."""
    await Order(pk="USER#1", sk="ORDER#001", status="pending", total=100).save()
    await Order(pk="USER#1", sk="ORDER#002", status="shipped", total=200).save()
    await Order(pk="USER#1", sk="ORDER#003", status="pending", total=300).save()

    # Filter by status
    results = [
        order
        async for order in Order.query(
            partition_key="USER#1",
            filter_condition=Attr("status").eq("pending"),
        )
    ]
    assert len(results) == 2


@pytest.mark.asyncio
async def test_scan_all_items(pydynox_memory_backend):
    """Test scanning all items in a table."""
    await Order(pk="USER#1", sk="ORDER#001", status="pending", total=100).save()
    await Order(pk="USER#2", sk="ORDER#001", status="shipped", total=200).save()
    await Order(pk="USER#3", sk="ORDER#001", status="pending", total=300).save()

    results = [order async for order in Order.scan()]
    assert len(results) == 3


@pytest.mark.asyncio
async def test_scan_with_filter(pydynox_memory_backend):
    """Test scan with filter condition."""
    await Order(pk="USER#1", sk="ORDER#001", status="pending", total=100).save()
    await Order(pk="USER#2", sk="ORDER#001", status="shipped", total=200).save()
    await Order(pk="USER#3", sk="ORDER#001", status="pending", total=300).save()

    # Filter by total > 150
    results = [order async for order in Order.scan(filter_condition=Attr("total").gt(150))]
    assert len(results) == 2
