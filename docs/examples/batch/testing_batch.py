"""Testing batch operations with pydynox_memory_backend."""

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)


@pytest.mark.asyncio
async def test_batch_save(pydynox_memory_backend):
    """Test saving multiple items."""
    users = [User(pk=f"USER#{i}", name=f"User {i}", age=20 + i) for i in range(10)]

    for user in users:
        await user.save()

    # Verify all saved
    for i in range(10):
        found = await User.get(pk=f"USER#{i}")
        assert found is not None
        assert found.name == f"User {i}"


@pytest.mark.asyncio
async def test_batch_delete(pydynox_memory_backend):
    """Test deleting multiple items."""
    # Create users
    for i in range(5):
        await User(pk=f"USER#{i}", name=f"User {i}").save()

    # Delete some
    for i in range(3):
        user = await User.get(pk=f"USER#{i}")
        await user.delete()

    # Verify
    assert await User.get(pk="USER#0") is None
    assert await User.get(pk="USER#1") is None
    assert await User.get(pk="USER#2") is None
    assert await User.get(pk="USER#3") is not None
    assert await User.get(pk="USER#4") is not None


@pytest.mark.asyncio
async def test_batch_get(pydynox_memory_backend):
    """Test getting multiple items."""
    # Create users
    for i in range(5):
        await User(pk=f"USER#{i}", name=f"User {i}").save()

    # Batch get
    keys = [{"pk": f"USER#{i}"} for i in range(5)]
    results = await User.batch_get(keys)

    assert len(results) == 5
