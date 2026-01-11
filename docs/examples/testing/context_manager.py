"""Using MemoryBackend as context manager (without pytest)."""

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute
from pydynox.testing import MemoryBackend


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()


# Use as context manager
def main():
    with MemoryBackend() as backend:
        # All pydynox operations use in-memory storage
        user = User(pk="USER#1", name="John")
        user.save()

        found = User.get(pk="USER#1")
        print(f"Found: {found.name}")  # Output: Found: John

        # Inspect the data
        print(f"Tables: {list(backend.tables.keys())}")
        print(f"Items: {len(backend.tables['users'])}")


# Use as decorator
@MemoryBackend()
def test_function():
    user = User(pk="USER#1", name="Jane")
    user.save()

    assert User.get(pk="USER#1") is not None


# Use with seed data
def test_with_seed():
    seed = {"users": [{"pk": "USER#1", "name": "Seeded"}]}

    with MemoryBackend(seed=seed):
        user = User.get(pk="USER#1")
        assert user.name == "Seeded"


if __name__ == "__main__":
    main()
    test_function()
    test_with_seed()
    print("All tests passed!")
