"""Basic usage of pydynox_memory_backend fixture (async - default)."""

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)


@pytest.mark.asyncio
async def test_create_user(pydynox_memory_backend):
    """Test creating a user - no DynamoDB needed!"""
    user = User(pk="USER#1", name="John", age=30)
    await user.save()

    found = await User.get(pk="USER#1")
    assert found is not None
    assert found.name == "John"
    assert found.age == 30


@pytest.mark.asyncio
async def test_update_user(pydynox_memory_backend):
    """Test updating a user."""
    user = User(pk="USER#1", name="Jane")
    await user.save()

    await user.update(name="Janet", age=25)

    found = await User.get(pk="USER#1")
    assert found.name == "Janet"
    assert found.age == 25


@pytest.mark.asyncio
async def test_delete_user(pydynox_memory_backend):
    """Test deleting a user."""
    user = User(pk="USER#1", name="Bob")
    await user.save()

    await user.delete()

    assert await User.get(pk="USER#1") is None
