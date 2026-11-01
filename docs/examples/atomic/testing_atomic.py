"""Testing atomic updates with pydynox_memory_backend."""

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import ListAttribute, NumberAttribute, StringAttribute


class Counter(Model):
    model_config = ModelConfig(table="counters")
    pk = StringAttribute(partition_key=True)
    value = NumberAttribute(default=0)
    tags = ListAttribute()


@pytest.mark.asyncio
async def test_atomic_increment(pydynox_memory_backend):
    """Test atomic counter increment."""
    counter = Counter(pk="views", value=0)
    await counter.save()

    # Increment atomically
    await counter.update(atomic=[Counter.value.add(1)])
    await counter.update(atomic=[Counter.value.add(1)])
    await counter.update(atomic=[Counter.value.add(1)])

    found = await Counter.get(pk="views")
    assert found is not None
    assert found.value == 3


@pytest.mark.asyncio
async def test_atomic_decrement(pydynox_memory_backend):
    """Test atomic counter decrement."""
    counter = Counter(pk="stock", value=100)
    await counter.save()

    # Decrement atomically
    await counter.update(atomic=[Counter.value.add(-10)])

    found = await Counter.get(pk="stock")
    assert found is not None
    assert found.value == 90


@pytest.mark.asyncio
async def test_atomic_append(pydynox_memory_backend):
    """Test atomic list append."""
    counter = Counter(pk="item", tags=["initial"])
    await counter.save()

    # Append atomically
    await counter.update(atomic=[Counter.tags.append(["new_tag"])])

    found = await Counter.get(pk="item")
    assert found is not None
    assert found.tags == ["initial", "new_tag"]


@pytest.mark.asyncio
async def test_atomic_set(pydynox_memory_backend):
    """Test atomic set operation."""
    counter = Counter(pk="item", value=10)
    await counter.save()

    # Set atomically
    await counter.update(atomic=[Counter.value.set(99)])

    found = await Counter.get(pk="item")
    assert found is not None
    assert found.value == 99
