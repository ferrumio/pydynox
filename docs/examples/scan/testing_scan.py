"""Testing scan operations with pydynox_memory_backend."""

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)
    status = StringAttribute(default="active")


@pytest.mark.asyncio
async def test_scan_all_items(pydynox_memory_backend):
    """Test scanning all items in a table."""
    await User(pk="USER#1", name="Alice", age=30).save()
    await User(pk="USER#2", name="Bob", age=25).save()
    await User(pk="USER#3", name="Charlie", age=35).save()

    results = [u async for u in User.scan()]

    assert len(results) == 3


@pytest.mark.asyncio
async def test_scan_with_filter(pydynox_memory_backend):
    """Test scan with filter condition."""
    await User(pk="USER#1", name="Alice", age=30, status="active").save()
    await User(pk="USER#2", name="Bob", age=25, status="inactive").save()
    await User(pk="USER#3", name="Charlie", age=35, status="active").save()

    results = [u async for u in User.scan(filter_condition=User.status == "active")]

    assert len(results) == 2
    assert all(r.status == "active" for r in results)


@pytest.mark.asyncio
async def test_scan_with_numeric_filter(pydynox_memory_backend):
    """Test scan with numeric filter."""
    await User(pk="USER#1", name="Alice", age=30).save()
    await User(pk="USER#2", name="Bob", age=25).save()
    await User(pk="USER#3", name="Charlie", age=35).save()

    results = [u async for u in User.scan(filter_condition=User.age > 28)]

    assert len(results) == 2


@pytest.mark.asyncio
async def test_count_items(pydynox_memory_backend):
    """Test counting items."""
    await User(pk="USER#1", name="Alice", age=30).save()
    await User(pk="USER#2", name="Bob", age=25).save()
    await User(pk="USER#3", name="Charlie", age=35).save()

    count, _ = await User.count()

    assert count == 3
