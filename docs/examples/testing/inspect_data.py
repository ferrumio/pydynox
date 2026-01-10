"""Inspecting data in the memory backend."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)


def test_inspect_tables(pydynox_memory_backend):
    """Access the backend to inspect stored data."""
    User(pk="USER#1", name="Alice").save()
    User(pk="USER#2", name="Bob").save()

    # Access tables directly
    assert "users" in pydynox_memory_backend.tables
    assert len(pydynox_memory_backend.tables["users"]) == 2

    # Check specific items
    items = pydynox_memory_backend.tables["users"]
    pks = [item["pk"] for item in items.values()]
    assert "USER#1" in pks
    assert "USER#2" in pks


def test_clear_data(pydynox_memory_backend):
    """Clear data mid-test for fresh state."""
    User(pk="USER#1", name="Test").save()
    assert User.get(pk="USER#1") is not None

    # Clear all data
    pydynox_memory_backend.clear()

    # Now it's gone
    assert User.get(pk="USER#1") is None


def test_isolation_between_tests(pydynox_memory_backend):
    """Each test starts with empty tables."""
    # This test doesn't see data from other tests
    assert User.get(pk="USER#1") is None

    # Create data for this test only
    User(pk="USER#1", name="Isolated").save()
    assert User.get(pk="USER#1") is not None
