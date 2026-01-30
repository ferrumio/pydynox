"""Sync integration tests for pytest fixtures.

These tests verify that the pytest plugin fixtures work correctly with sync API.
"""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    """Test model for fixture tests."""

    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)


class Order(Model):
    """Test model with composite key."""

    model_config = ModelConfig(table="orders")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    total = NumberAttribute()


# ========== Tests using pydynox_memory_backend fixture ==========


def test_sync_pydynox_memory_backend_basic_crud(pydynox_memory_backend):
    """Test basic sync CRUD with pydynox_memory_backend fixture."""
    # GIVEN a model instance
    user = User(pk="SYNC_USER#1", name="John", age=30)

    # WHEN we save and get it (sync)
    user.sync_save()
    found = User.sync_get(pk="SYNC_USER#1")

    # THEN it's found with correct data
    assert found is not None
    assert found.name == "John"
    assert found.age == 30


def test_sync_pydynox_memory_backend_update(pydynox_memory_backend):
    """Test sync update with pydynox_memory_backend fixture."""
    # GIVEN a saved user
    user = User(pk="SYNC_USER#2", name="Jane")
    user.sync_save()

    # WHEN we update it (sync)
    user.sync_update(name="Janet", age=25)

    # THEN changes are persisted
    found = User.sync_get(pk="SYNC_USER#2")
    assert found.name == "Janet"
    assert found.age == 25


def test_sync_pydynox_memory_backend_delete(pydynox_memory_backend):
    """Test sync delete with pydynox_memory_backend fixture."""
    # GIVEN a saved user
    user = User(pk="SYNC_USER#3", name="Bob")
    user.sync_save()

    # WHEN we delete it (sync)
    user.sync_delete()

    # THEN it's gone
    assert User.sync_get(pk="SYNC_USER#3") is None


def test_sync_pydynox_memory_backend_query(pydynox_memory_backend):
    """Test sync query with pydynox_memory_backend fixture."""
    # GIVEN orders for different users
    Order(pk="SYNC_USER#1", sk="ORDER#001", total=100).sync_save()
    Order(pk="SYNC_USER#1", sk="ORDER#002", total=200).sync_save()
    Order(pk="SYNC_USER#2", sk="ORDER#001", total=50).sync_save()

    # WHEN we query for SYNC_USER#1 (sync)
    results = list(Order.sync_query(partition_key="SYNC_USER#1"))

    # THEN only SYNC_USER#1 orders are returned
    assert len(results) == 2


def test_sync_pydynox_memory_backend_scan(pydynox_memory_backend):
    """Test sync scan with pydynox_memory_backend fixture."""
    User(pk="SYNC_SCAN#1", name="Alice").sync_save()
    User(pk="SYNC_SCAN#2", name="Bob").sync_save()
    User(pk="SYNC_SCAN#3", name="Charlie").sync_save()

    results = list(User.sync_scan())
    assert len(results) == 3


def test_sync_pydynox_memory_backend_isolation(pydynox_memory_backend):
    """Test that each test has isolated data (sync)."""
    # GIVEN a fresh test (no data from other tests)
    assert User.sync_get(pk="SYNC_ISO#1") is None

    # WHEN we save a user
    User(pk="SYNC_ISO#1", name="Isolated").sync_save()

    # THEN it exists in this test
    assert User.sync_get(pk="SYNC_ISO#1") is not None


def test_sync_pydynox_memory_backend_tables_access(pydynox_memory_backend):
    """Test accessing tables for inspection (sync)."""
    User(pk="SYNC_ACCESS#1", name="Test").sync_save()

    # Can inspect the backend
    assert "users" in pydynox_memory_backend.tables
    assert len(pydynox_memory_backend.tables["users"]) == 1


def test_sync_pydynox_memory_backend_clear(pydynox_memory_backend):
    """Test clearing data mid-test (sync)."""
    # GIVEN a saved user
    User(pk="SYNC_CLEAR#1", name="Test").sync_save()
    assert User.sync_get(pk="SYNC_CLEAR#1") is not None

    # WHEN we clear the backend
    pydynox_memory_backend.clear()

    # THEN data is gone
    assert User.sync_get(pk="SYNC_CLEAR#1") is None
