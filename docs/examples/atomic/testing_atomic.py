"""Testing atomic updates with pydynox_memory_backend."""

from pydynox import Model, ModelConfig
from pydynox.attributes import ListAttribute, NumberAttribute, StringAttribute


class Counter(Model):
    model_config = ModelConfig(table="counters")
    pk = StringAttribute(partition_key=True)
    count = NumberAttribute(default=0)
    tags = ListAttribute(default=list)


def test_atomic_increment(pydynox_memory_backend):
    """Test atomic counter increment."""
    counter = Counter(pk="views", count=0)
    counter.save()

    # Increment atomically
    counter.update(atomic=[Counter.count.add(1)])
    counter.update(atomic=[Counter.count.add(1)])
    counter.update(atomic=[Counter.count.add(1)])

    found = Counter.get(pk="views")
    assert found.count == 3


def test_atomic_decrement(pydynox_memory_backend):
    """Test atomic counter decrement."""
    counter = Counter(pk="stock", count=100)
    counter.save()

    # Decrement atomically
    counter.update(atomic=[Counter.count.add(-10)])

    found = Counter.get(pk="stock")
    assert found.count == 90


def test_atomic_append(pydynox_memory_backend):
    """Test atomic list append."""
    counter = Counter(pk="item", tags=["initial"])
    counter.save()

    # Append atomically
    counter.update(atomic=[Counter.tags.append(["new_tag"])])

    found = Counter.get(pk="item")
    assert "initial" in found.tags
    assert "new_tag" in found.tags


def test_atomic_set(pydynox_memory_backend):
    """Test atomic set operation."""
    counter = Counter(pk="item", count=10)
    counter.save()

    # Set atomically
    counter.update(atomic=[Counter.count.set(99)])

    found = Counter.get(pk="item")
    assert found.count == 99
