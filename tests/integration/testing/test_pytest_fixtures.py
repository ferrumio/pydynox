"""Integration tests for pytest fixtures.

These tests verify that the pytest plugin fixtures work correctly.
The fixtures are auto-registered via entry points in pyproject.toml.
"""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    """Test model for fixture tests."""

    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)


class Order(Model):
    """Test model with composite key."""

    model_config = ModelConfig(table="orders")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    total = NumberAttribute()


# ========== Tests using pydynox_memory_backend fixture ==========


def test_pydynox_memory_backend_basic_crud(pydynox_memory_backend):
    """Test basic CRUD with pydynox_memory_backend fixture."""
    # GIVEN a model instance
    user = User(pk="USER#1", name="John", age=30)

    # WHEN we save and get it
    user.save()
    found = User.get(pk="USER#1")

    # THEN it's found with correct data
    assert found is not None
    assert found.name == "John"
    assert found.age == 30


def test_pydynox_memory_backend_update(pydynox_memory_backend):
    """Test update with pydynox_memory_backend fixture."""
    # GIVEN a saved user
    user = User(pk="USER#1", name="Jane")
    user.save()

    # WHEN we update it
    user.update(name="Janet", age=25)

    # THEN changes are persisted
    found = User.get(pk="USER#1")
    assert found.name == "Janet"
    assert found.age == 25


def test_pydynox_memory_backend_delete(pydynox_memory_backend):
    """Test delete with pydynox_memory_backend fixture."""
    # GIVEN a saved user
    user = User(pk="USER#1", name="Bob")
    user.save()

    # WHEN we delete it
    user.delete()

    # THEN it's gone
    assert User.get(pk="USER#1") is None


def test_pydynox_memory_backend_query(pydynox_memory_backend):
    """Test query with pydynox_memory_backend fixture."""
    # GIVEN orders for different users
    Order(pk="USER#1", sk="ORDER#001", total=100).save()
    Order(pk="USER#1", sk="ORDER#002", total=200).save()
    Order(pk="USER#2", sk="ORDER#001", total=50).save()

    # WHEN we query for USER#1
    results = list(Order.query(hash_key="USER#1"))

    # THEN only USER#1 orders are returned
    assert len(results) == 2


def test_pydynox_memory_backend_scan(pydynox_memory_backend):
    """Test scan with pydynox_memory_backend fixture."""
    User(pk="USER#1", name="Alice").save()
    User(pk="USER#2", name="Bob").save()
    User(pk="USER#3", name="Charlie").save()

    results = list(User.scan())
    assert len(results) == 3


def test_pydynox_memory_backend_isolation(pydynox_memory_backend):
    """Test that each test has isolated data."""
    # GIVEN a fresh test (no data from other tests)
    assert User.get(pk="USER#1") is None

    # WHEN we save a user
    User(pk="USER#1", name="Isolated").save()

    # THEN it exists in this test
    assert User.get(pk="USER#1") is not None


def test_pydynox_memory_backend_tables_access(pydynox_memory_backend):
    """Test accessing tables for inspection."""
    User(pk="USER#1", name="Test").save()

    # Can inspect the backend
    assert "users" in pydynox_memory_backend.tables
    assert len(pydynox_memory_backend.tables["users"]) == 1


def test_pydynox_memory_backend_clear(pydynox_memory_backend):
    """Test clearing data mid-test."""
    # GIVEN a saved user
    User(pk="USER#1", name="Test").save()
    assert User.get(pk="USER#1") is not None

    # WHEN we clear the backend
    pydynox_memory_backend.clear()

    # THEN data is gone
    assert User.get(pk="USER#1") is None


# ========== Tests using pydynox_memory_backend_seeded fixture ==========


def test_pydynox_memory_backend_seeded_basic(pydynox_memory_backend_seeded):
    """Test seeded fixture (no seed data by default)."""
    # Default pydynox_seed returns empty dict
    assert User.get(pk="USER#1") is None


# ========== Tests using pydynox_memory_backend_factory fixture ==========


def test_pydynox_memory_backend_factory_custom_seed(pydynox_memory_backend_factory):
    """Test factory fixture with custom seed."""
    seed = {
        "users": [
            {"pk": "USER#1", "name": "Seeded User", "age": 99},
            {"pk": "USER#2", "name": "Another User", "age": 50},
        ]
    }

    with pydynox_memory_backend_factory(seed=seed):
        user1 = User.get(pk="USER#1")
        assert user1 is not None
        assert user1.name == "Seeded User"

        user2 = User.get(pk="USER#2")
        assert user2 is not None
        assert user2.name == "Another User"


def test_pydynox_memory_backend_factory_multiple_tables(pydynox_memory_backend_factory):
    """Test factory with multiple tables seeded."""
    seed = {
        "users": [{"pk": "USER#1", "name": "John", "age": 30}],
        "orders": [{"pk": "USER#1", "sk": "ORDER#1", "total": 100}],
    }

    with pydynox_memory_backend_factory(seed=seed):
        user = User.get(pk="USER#1")
        assert user is not None

        order = Order.get(pk="USER#1", sk="ORDER#1")
        assert order is not None
        assert order.total == 100
