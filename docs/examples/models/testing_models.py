"""Testing models with pydynox_memory_backend (sync tests use sync_ prefix)."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)


def test_create_and_get(pydynox_memory_backend):
    """Test creating and getting a model."""
    user = User(pk="USER#1", sk="PROFILE", name="John", age=30)
    user.sync_save()

    found = User.sync_get(pk="USER#1", sk="PROFILE")
    assert found is not None
    assert found.name == "John"
    assert found.age == 30


def test_update(pydynox_memory_backend):
    """Test updating a model."""
    user = User(pk="USER#1", sk="PROFILE", name="John")
    user.sync_save()

    user.sync_update(name="Jane", age=25)

    found = User.sync_get(pk="USER#1", sk="PROFILE")
    assert found.name == "Jane"
    assert found.age == 25


def test_delete(pydynox_memory_backend):
    """Test deleting a model."""
    user = User(pk="USER#1", sk="PROFILE", name="John")
    user.sync_save()

    user.sync_delete()

    assert User.sync_get(pk="USER#1", sk="PROFILE") is None


def test_get_not_found(pydynox_memory_backend):
    """Test getting a non-existent model."""
    found = User.sync_get(pk="USER#999", sk="PROFILE")
    assert found is None


def test_update_by_key(pydynox_memory_backend):
    """Test updating by key without fetching first."""
    User(pk="USER#1", sk="PROFILE", name="John").sync_save()

    User.sync_update_by_key(pk="USER#1", sk="PROFILE", name="Jane")

    found = User.sync_get(pk="USER#1", sk="PROFILE")
    assert found.name == "Jane"


def test_delete_by_key(pydynox_memory_backend):
    """Test deleting by key without fetching first."""
    User(pk="USER#1", sk="PROFILE", name="John").sync_save()

    User.sync_delete_by_key(pk="USER#1", sk="PROFILE")

    assert User.sync_get(pk="USER#1", sk="PROFILE") is None
