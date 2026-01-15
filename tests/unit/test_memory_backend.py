"""Unit tests for MemoryBackend."""

import pytest
from pydynox import Model, ModelConfig, get_default_client
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.testing import MemoryBackend


class User(Model):
    """Test model."""

    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)


def test_memory_backend_context_manager():
    """Test MemoryBackend as context manager."""
    # WHEN we use MemoryBackend as context manager
    with MemoryBackend():
        user = User(pk="USER#1", name="John")
        user.save()

        found = User.get(pk="USER#1")

        # THEN operations should work in memory
        assert found is not None
        assert found.name == "John"


def test_memory_backend_decorator():
    """Test MemoryBackend as decorator."""

    # GIVEN a function decorated with MemoryBackend
    @MemoryBackend()
    def inner():
        user = User(pk="USER#1", name="Jane")
        user.save()
        return User.get(pk="USER#1")

    # WHEN we call the function
    result = inner()

    # THEN operations should work in memory
    assert result is not None
    assert result.name == "Jane"


def test_memory_backend_restores_client():
    """Test that MemoryBackend restores previous client."""
    # GIVEN the original client
    original = get_default_client()

    # WHEN we use MemoryBackend
    with MemoryBackend():
        pass

    # THEN the original client should be restored
    assert get_default_client() == original


def test_put_and_get():
    """Test basic put and get operations."""
    # GIVEN a MemoryBackend
    with MemoryBackend():
        # WHEN we save and get a user
        user = User(pk="USER#1", name="Alice", age=30)
        user.save()

        found = User.get(pk="USER#1")

        # THEN the user should be found with correct data
        assert found is not None
        assert found.pk == "USER#1"
        assert found.name == "Alice"
        assert found.age == 30


def test_get_not_found():
    """Test get returns None for missing item."""
    # GIVEN a MemoryBackend
    with MemoryBackend():
        # WHEN we get a non-existent item
        found = User.get(pk="NONEXISTENT")

        # THEN None should be returned
        assert found is None


def test_delete():
    """Test delete operation."""
    # GIVEN a saved user
    with MemoryBackend():
        user = User(pk="USER#1", name="Bob")
        user.save()
        assert User.get(pk="USER#1") is not None

        # WHEN we delete
        user.delete()

        # THEN the user should be gone
        assert User.get(pk="USER#1") is None


def test_update():
    """Test update operation."""
    # GIVEN a saved user
    with MemoryBackend():
        user = User(pk="USER#1", name="Charlie", age=25)
        user.save()

        # WHEN we update
        user.update(name="Charles", age=26)

        # THEN the changes should be persisted
        found = User.get(pk="USER#1")
        assert found is not None
        assert found.name == "Charles"
        assert found.age == 26


def test_atomic_increment():
    """Test atomic increment operation."""
    # GIVEN a saved user with age=0
    with MemoryBackend():
        user = User(pk="USER#1", name="Dave", age=0)
        user.save()

        # WHEN we do atomic increment
        user.update(atomic=[User.age.add(5)])

        # THEN age should be incremented
        found = User.get(pk="USER#1")
        assert found is not None
        assert found.age == 5


def test_scan():
    """Test scan operation."""
    # GIVEN multiple saved users
    with MemoryBackend():
        User(pk="USER#1", name="Eve").save()
        User(pk="USER#2", name="Frank").save()
        User(pk="USER#3", name="Grace").save()

        # WHEN we scan
        results = list(User.scan())

        # THEN all users should be returned
        assert len(results) == 3


def test_query():
    """Test query operation."""

    # GIVEN an Order model with hash and range key
    class Order(Model):
        model_config = ModelConfig(table="orders")
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        total = NumberAttribute()

    # AND multiple orders for different users
    with MemoryBackend():
        Order(pk="USER#1", sk="ORDER#001", total=100).save()
        Order(pk="USER#1", sk="ORDER#002", total=200).save()
        Order(pk="USER#2", sk="ORDER#001", total=50).save()

        # WHEN we query for USER#1
        results = list(Order.query(hash_key="USER#1"))

        # THEN only USER#1's orders should be returned
        assert len(results) == 2


def test_seed_data():
    """Test MemoryBackend with seed data."""
    # GIVEN seed data
    seed = {
        "users": [
            {"pk": "USER#1", "name": "Seeded User", "age": 99},
        ]
    }

    # WHEN we use MemoryBackend with seed
    with MemoryBackend(seed=seed):
        found = User.get(pk="USER#1")

        # THEN seeded data should be available
        assert found is not None
        assert found.name == "Seeded User"
        assert found.age == 99


def test_clear():
    """Test clearing all data."""
    # GIVEN a MemoryBackend with data
    with MemoryBackend() as backend:
        User(pk="USER#1", name="Test").save()
        assert len(backend.tables.get("users", {})) == 1

        # WHEN we clear
        backend.clear()

        # THEN all data should be gone
        assert len(backend.tables) == 0


def test_tables_property():
    """Test accessing tables for inspection."""
    # GIVEN a MemoryBackend with data
    with MemoryBackend() as backend:
        User(pk="USER#1", name="Test").save()

        # THEN tables should be accessible
        assert "users" in backend.tables
        assert len(backend.tables["users"]) == 1


def test_condition_attribute_not_exists():
    """Test condition with attribute_not_exists."""
    # GIVEN a saved user
    with MemoryBackend():
        user = User(pk="USER#1", name="Test")
        user.save(condition=User.pk.does_not_exist())

        # WHEN we try to save again with same condition
        user2 = User(pk="USER#1", name="Test2")

        # THEN it should fail
        with pytest.raises(Exception):  # ConditionCheckFailedError
            user2.save(condition=User.pk.does_not_exist())


def test_multiple_tables():
    """Test operations on multiple tables."""

    # GIVEN a Product model
    class Product(Model):
        model_config = ModelConfig(table="products")
        pk = StringAttribute(hash_key=True)
        name = StringAttribute()

    # WHEN we save to multiple tables
    with MemoryBackend():
        User(pk="USER#1", name="User").save()
        Product(pk="PROD#1", name="Product").save()

        # THEN both should be retrievable
        assert User.get(pk="USER#1") is not None
        assert Product.get(pk="PROD#1") is not None


def test_isolation_between_contexts():
    """Test that data is isolated between contexts."""
    # GIVEN data saved in one context
    with MemoryBackend():
        User(pk="USER#1", name="First").save()

    # WHEN we use a new context
    with MemoryBackend():
        # THEN data from previous context should not exist
        assert User.get(pk="USER#1") is None


def test_table_exists():
    """Test table_exists method."""
    # GIVEN a MemoryBackend
    with MemoryBackend() as backend:
        # THEN table doesn't exist yet
        assert not backend._client.table_exists("users")

        # WHEN we save
        User(pk="USER#1", name="Test").save()

        # THEN table should exist
        assert backend._client.table_exists("users")


def test_delete_by_key():
    """Test delete_by_key operation."""
    # GIVEN a saved user
    with MemoryBackend():
        User(pk="USER#1", name="Test").save()
        assert User.get(pk="USER#1") is not None

        # WHEN we delete by key
        User.delete_by_key(pk="USER#1")

        # THEN user should be gone
        assert User.get(pk="USER#1") is None


def test_update_by_key():
    """Test update_by_key operation."""
    # GIVEN a saved user
    with MemoryBackend():
        User(pk="USER#1", name="Original", age=20).save()

        # WHEN we update by key
        User.update_by_key(pk="USER#1", name="Updated")

        # THEN changes should be persisted
        found = User.get(pk="USER#1")
        assert found is not None
        assert found.name == "Updated"
