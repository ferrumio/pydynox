"""Testing batch operations with pydynox_memory_backend."""

import pytest
from pydynox import BatchWriter, Model, ModelConfig
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

    async with BatchWriter(client, "users") as batch:
        for i in range(10):
            batch.put({"pk": f"USER#{i}", "name": f"User {i}", "age": 20 + i})

    users = await User.batch_get([{"pk": f"USER#{i}"} for i in range(10)])

    assert len(users) == 10
    assert {user.name for user in users} == {f"User {i}" for i in range(10)}


@pytest.mark.asyncio
async def test_batch_delete(pydynox_memory_backend):
    """Test deleting multiple items."""
    client = pydynox_memory_backend.client

    async with BatchWriter(client, "users") as batch:
        for i in range(5):
            batch.put({"pk": f"USER#{i}", "name": f"User {i}"})

    async with BatchWriter(client, "users") as batch:
        for i in range(3):
            batch.delete({"pk": f"USER#{i}"})

    remaining = await client.batch_get(
        "users",
        [{"pk": f"USER#{i}"} for i in range(5)],
    )

    assert {item["pk"] for item in remaining} == {"USER#3", "USER#4"}
