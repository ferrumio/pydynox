"""Integration tests for pytest fixtures.

These tests verify that the pytest plugin fixtures work correctly.
The fixtures are auto-registered via entry points in pyproject.toml.
"""

import pytest
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


@pytest.mark.asyncio
async def test_pydynox_memory_backend_basic_crud(pydynox_memory_backend):
    """Test basic CRUD with pydynox_memory_backend fixture."""
    # GIVEN a model instance
    user = User(pk="USER#1", name="John", age=30)

    # WHEN we save and get it
    await user.save()
    found = await User.get(pk="USER#1")

    # THEN it's found with correct data
    assert found is not None
    assert found.name == "John"
    assert found.age == 30


@pytest.mark.asyncio
async def test_pydynox_memory_backend_update(pydynox_memory_backend):
    """Test update with pydynox_memory_backend fixture."""
    # GIVEN a saved user
    user = User(pk="USER#1", name="Jane")
    await user.save()

    # WHEN we update it
    await user.update(name="Janet", age=25)

    # THEN changes are persisted
    found = await User.get(pk="USER#1")
    assert found.name == "Janet"
    assert found.age == 25


@pytest.mark.asyncio
async def test_pydynox_memory_backend_delete(pydynox_memory_backend):
    """Test delete with pydynox_memory_backend fixture."""
    # GIVEN a saved user
    user = User(pk="USER#1", name="Bob")
    await user.save()

    # WHEN we delete it
    await user.delete()

    # THEN it's gone
    assert await User.get(pk="USER#1") is None


@pytest.mark.asyncio
async def test_pydynox_memory_backend_query(pydynox_memory_backend):
    """Test query with pydynox_memory_backend fixture."""
    # GIVEN orders for different users
    await Order(pk="USER#1", sk="ORDER#001", total=100).save()
    await Order(pk="USER#1", sk="ORDER#002", total=200).save()
    await Order(pk="USER#2", sk="ORDER#001", total=50).save()

    # WHEN we query for USER#1
    results = [order async for order in Order.query(partition_key="USER#1")]

    # THEN only USER#1 orders are returned
    assert len(results) == 2


@pytest.mark.asyncio
async def test_pydynox_memory_backend_scan(pydynox_memory_backend):
    """Test scan with pydynox_memory_backend fixture."""
    await User(pk="USER#1", name="Alice").save()
    await User(pk="USER#2", name="Bob").save()
    await User(pk="USER#3", name="Charlie").save()

    results = [user async for user in User.scan()]
    assert len(results) == 3


@pytest.mark.asyncio
async def test_pydynox_memory_backend_isolation(pydynox_memory_backend):
    """Test that each test has isolated data."""
    # GIVEN a fresh test (no data from other tests)
    assert await User.get(pk="USER#1") is None

    # WHEN we save a user
    await User(pk="USER#1", name="Isolated").save()

    # THEN it exists in this test
    assert await User.get(pk="USER#1") is not None


@pytest.mark.asyncio
async def test_pydynox_memory_backend_tables_access(pydynox_memory_backend):
    """Test accessing tables for inspection."""
    await User(pk="USER#1", name="Test").save()

    # Can inspect the backend
    assert "users" in pydynox_memory_backend.tables
    assert len(pydynox_memory_backend.tables["users"]) == 1


@pytest.mark.asyncio
async def test_pydynox_memory_backend_clear(pydynox_memory_backend):
    """Test clearing data mid-test."""
    # GIVEN a saved user
    await User(pk="USER#1", name="Test").save()
    assert await User.get(pk="USER#1") is not None

    # WHEN we clear the backend
    pydynox_memory_backend.clear()

    # THEN data is gone
    assert await User.get(pk="USER#1") is None


# ========== Tests using pydynox_memory_backend_seeded fixture ==========


@pytest.mark.asyncio
async def test_pydynox_memory_backend_seeded_basic(pydynox_memory_backend_seeded):
    """Test seeded fixture (no seed data by default)."""
    # Default pydynox_seed returns empty dict
    assert await User.get(pk="USER#1") is None


# ========== Tests using pydynox_memory_backend_factory fixture ==========


@pytest.mark.asyncio
async def test_pydynox_memory_backend_factory_custom_seed(pydynox_memory_backend_factory):
    """Test factory fixture with custom seed."""
    seed = {
        "users": [
            {"pk": "USER#1", "name": "Seeded User", "age": 99},
            {"pk": "USER#2", "name": "Another User", "age": 50},
        ]
    }

    with pydynox_memory_backend_factory(seed=seed):
        user1 = await User.get(pk="USER#1")
        assert user1 is not None
        assert user1.name == "Seeded User"

        user2 = await User.get(pk="USER#2")
        assert user2 is not None
        assert user2.name == "Another User"


@pytest.mark.asyncio
async def test_pydynox_memory_backend_factory_multiple_tables(pydynox_memory_backend_factory):
    """Test factory with multiple tables seeded."""
    seed = {
        "users": [{"pk": "USER#1", "name": "John", "age": 30}],
        "orders": [{"pk": "USER#1", "sk": "ORDER#1", "total": 100}],
    }

    with pydynox_memory_backend_factory(seed=seed):
        user = await User.get(pk="USER#1")
        assert user is not None

        order = await Order.get(pk="USER#1", sk="ORDER#1")
        assert order is not None
        assert order.total == 100
