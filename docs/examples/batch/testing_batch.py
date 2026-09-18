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
async def test_batch_write_and_get(pydynox_memory_backend):
    """Test writing and reading multiple items."""
    client = pydynox_memory_backend.client
    items = [{"pk": f"USER#{i}", "name": f"User {i}", "age": 20 + i} for i in range(10)]

    await client.batch_write("users", put_items=items)
    users = await User.batch_get([{"pk": f"USER#{i}"} for i in range(10)])

    assert len(users) == 10
    assert {user.name for user in users} == {f"User {i}" for i in range(10)}


@pytest.mark.asyncio
async def test_batch_delete(pydynox_memory_backend):
    """Test deleting multiple items."""
    client = pydynox_memory_backend.client
    items = [{"pk": f"USER#{i}", "name": f"User {i}"} for i in range(5)]

    await client.batch_write("users", put_items=items)
    await client.batch_write(
        "users",
        delete_keys=[{"pk": f"USER#{i}"} for i in range(3)],
    )
    remaining = await client.batch_get(
        "users",
        [{"pk": f"USER#{i}"} for i in range(5)],
    )

    assert {item["pk"] for item in remaining} == {"USER#3", "USER#4"}
