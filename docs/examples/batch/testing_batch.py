"""Testing batch operations with pydynox_memory_backend."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)


def test_batch_save(pydynox_memory_backend):
    """Test saving multiple items."""
    users = [User(pk=f"USER#{i}", name=f"User {i}", age=20 + i) for i in range(10)]

    for user in users:
        user.save()

    # Verify all saved
    for i in range(10):
        found = User.get(pk=f"USER#{i}")
        assert found is not None
        assert found.name == f"User {i}"


def test_batch_delete(pydynox_memory_backend):
    """Test deleting multiple items."""
    # Create users
    for i in range(5):
        User(pk=f"USER#{i}", name=f"User {i}").save()

    # Delete some
    for i in range(3):
        user = User.get(pk=f"USER#{i}")
        user.delete()

    # Verify
    assert User.get(pk="USER#0") is None
    assert User.get(pk="USER#1") is None
    assert User.get(pk="USER#2") is None
    assert User.get(pk="USER#3") is not None
    assert User.get(pk="USER#4") is not None


def test_batch_get(pydynox_memory_backend):
    """Test getting multiple items."""
    # Create users
    for i in range(5):
        User(pk=f"USER#{i}", name=f"User {i}").save()

    # Batch get
    keys = [{"pk": f"USER#{i}"} for i in range(5)]
    results = User.batch_get(keys)

    assert len(results) == 5
