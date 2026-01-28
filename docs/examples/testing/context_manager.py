"""Using MemoryBackend as context manager (without pytest)."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute
from pydynox.testing import MemoryBackend


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()


# Use as context manager (async)
async def main():
    with MemoryBackend() as backend:
        # All pydynox operations use in-memory storage
        user = User(pk="USER#1", name="John")
        await user.save()

        found = await User.get(pk="USER#1")
        print(f"Found: {found.name}")  # Output: Found: John

        # Inspect the data
        print(f"Tables: {list(backend.tables.keys())}")
        print(f"Items: {len(backend.tables['users'])}")


# Use with seed data (async)
async def test_with_seed():
    seed = {"users": [{"pk": "USER#1", "name": "Seeded"}]}

    with MemoryBackend(seed=seed):
        user = await User.get(pk="USER#1")
        assert user.name == "Seeded"
        print("Seed test passed!")


if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(test_with_seed())
    print("All tests passed!")
