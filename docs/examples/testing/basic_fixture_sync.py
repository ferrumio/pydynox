"""Basic usage of pydynox_memory_backend fixture (sync)."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)


def test_create_user(pydynox_memory_backend):
    """Test creating a user - no DynamoDB needed!"""
    user = User(pk="USER#1", name="John", age=30)
    user.sync_save()

    found = User.sync_get(pk="USER#1")
    assert found is not None
    assert found.name == "John"
    assert found.age == 30


def test_update_user(pydynox_memory_backend):
    """Test updating a user."""
    user = User(pk="USER#1", name="Jane")
    user.sync_save()

    user.sync_update(name="Janet", age=25)

    found = User.sync_get(pk="USER#1")
    assert found.name == "Janet"
    assert found.age == 25


def test_delete_user(pydynox_memory_backend):
    """Test deleting a user."""
    user = User(pk="USER#1", name="Bob")
    user.sync_save()

    user.sync_delete()

    assert User.sync_get(pk="USER#1") is None
