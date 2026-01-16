"""Testing conditions with pydynox_memory_backend."""

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.exceptions import ConditionalCheckFailedException


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    status = StringAttribute(default="active")
    version = NumberAttribute(default=1)


def test_prevent_overwrite(pydynox_memory_backend):
    """Test condition to prevent overwriting existing items."""
    user = User(pk="USER#1", name="John")
    user.save(condition=User.pk.not_exists())

    # Second save with same key should fail
    user2 = User(pk="USER#1", name="Jane")
    with pytest.raises(ConditionalCheckFailedException):
        user2.save(condition=User.pk.not_exists())


def test_conditional_delete(pydynox_memory_backend):
    """Test conditional delete."""
    user = User(pk="USER#1", name="John", status="inactive")
    user.save()

    # Can only delete inactive users
    user.delete(condition=User.status == "inactive")

    assert User.get(pk="USER#1") is None


def test_conditional_delete_fails(pydynox_memory_backend):
    """Test that conditional delete fails when condition not met."""
    user = User(pk="USER#1", name="John", status="active")
    user.save()

    # Cannot delete active users
    with pytest.raises(ConditionalCheckFailedException):
        user.delete(condition=User.status == "inactive")

    # User still exists
    assert User.get(pk="USER#1") is not None


def test_optimistic_locking(pydynox_memory_backend):
    """Test optimistic locking with version field."""
    user = User(pk="USER#1", name="John", version=1)
    user.save()

    # Simulate concurrent update
    user1 = User.get(pk="USER#1")
    user2 = User.get(pk="USER#1")

    # First update succeeds
    user1.name = "Jane"
    user1.version = 2
    user1.save(condition=User.version == 1)

    # Second update fails (version already changed)
    user2.name = "Bob"
    user2.version = 2
    with pytest.raises(ConditionalCheckFailedException):
        user2.save(condition=User.version == 1)
