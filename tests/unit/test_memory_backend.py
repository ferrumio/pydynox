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
    with MemoryBackend():
        user = User(pk="USER#1", name="John")
        user.save()

        found = User.get(pk="USER#1")
        assert found is not None
        assert found.name == "John"


def test_memory_backend_decorator():
    """Test MemoryBackend as decorator."""

    @MemoryBackend()
    def inner():
        user = User(pk="USER#1", name="Jane")
        user.save()
        return User.get(pk="USER#1")

    result = inner()
    assert result is not None
    assert result.name == "Jane"


def test_memory_backend_restores_client():
    """Test that MemoryBackend restores previous client."""
    original = get_default_client()

    with MemoryBackend():
        # Inside context, client is MemoryClient
        pass

    # After context, client is restored
    assert get_default_client() == original


def test_put_and_get():
    """Test basic put and get operations."""
    with MemoryBackend():
        user = User(pk="USER#1", name="Alice", age=30)
        user.save()

        found = User.get(pk="USER#1")
        assert found is not None
        assert found.pk == "USER#1"
        assert found.name == "Alice"
        assert found.age == 30


def test_get_not_found():
    """Test get returns None for missing item."""
    with MemoryBackend():
        found = User.get(pk="NONEXISTENT")
        assert found is None


def test_delete():
    """Test delete operation."""
    with MemoryBackend():
        user = User(pk="USER#1", name="Bob")
        user.save()

        # Verify exists
        assert User.get(pk="USER#1") is not None

        # Delete
        user.delete()

        # Verify gone
        assert User.get(pk="USER#1") is None


def test_update():
    """Test update operation."""
    with MemoryBackend():
        user = User(pk="USER#1", name="Charlie", age=25)
        user.save()

        # Update
        user.update(name="Charles", age=26)

        # Verify
        found = User.get(pk="USER#1")
        assert found is not None
        assert found.name == "Charles"
        assert found.age == 26


def test_atomic_increment():
    """Test atomic increment operation."""
    with MemoryBackend():
        user = User(pk="USER#1", name="Dave", age=0)
        user.save()

        # Atomic increment
        user.update(atomic=[User.age.add(5)])

        found = User.get(pk="USER#1")
        assert found is not None
        assert found.age == 5


def test_scan():
    """Test scan operation."""
    with MemoryBackend():
        User(pk="USER#1", name="Eve").save()
        User(pk="USER#2", name="Frank").save()
        User(pk="USER#3", name="Grace").save()

        results = list(User.scan())
        assert len(results) == 3


def test_query():
    """Test query operation."""

    class Order(Model):
        model_config = ModelConfig(table="orders")
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        total = NumberAttribute()

    with MemoryBackend():
        Order(pk="USER#1", sk="ORDER#001", total=100).save()
        Order(pk="USER#1", sk="ORDER#002", total=200).save()
        Order(pk="USER#2", sk="ORDER#001", total=50).save()

        results = list(Order.query(hash_key="USER#1"))
        assert len(results) == 2


def test_seed_data():
    """Test MemoryBackend with seed data."""
    seed = {
        "users": [
            {"pk": "USER#1", "name": "Seeded User", "age": 99},
        ]
    }

    with MemoryBackend(seed=seed):
        found = User.get(pk="USER#1")
        assert found is not None
        assert found.name == "Seeded User"
        assert found.age == 99


def test_clear():
    """Test clearing all data."""
    with MemoryBackend() as backend:
        User(pk="USER#1", name="Test").save()
        assert len(backend.tables.get("users", {})) == 1

        backend.clear()
        assert len(backend.tables) == 0


def test_tables_property():
    """Test accessing tables for inspection."""
    with MemoryBackend() as backend:
        User(pk="USER#1", name="Test").save()

        assert "users" in backend.tables
        assert len(backend.tables["users"]) == 1


def test_condition_attribute_not_exists():
    """Test condition with attribute_not_exists."""
    with MemoryBackend():
        user = User(pk="USER#1", name="Test")
        user.save(condition=User.pk.does_not_exist())

        # Second save should fail
        user2 = User(pk="USER#1", name="Test2")
        with pytest.raises(Exception):  # ConditionCheckFailedError
            user2.save(condition=User.pk.does_not_exist())


def test_multiple_tables():
    """Test operations on multiple tables."""

    class Product(Model):
        model_config = ModelConfig(table="products")
        pk = StringAttribute(hash_key=True)
        name = StringAttribute()

    with MemoryBackend():
        User(pk="USER#1", name="User").save()
        Product(pk="PROD#1", name="Product").save()

        assert User.get(pk="USER#1") is not None
        assert Product.get(pk="PROD#1") is not None


def test_isolation_between_contexts():
    """Test that data is isolated between contexts."""
    with MemoryBackend():
        User(pk="USER#1", name="First").save()

    with MemoryBackend():
        # Should not find user from previous context
        assert User.get(pk="USER#1") is None


def test_table_exists():
    """Test table_exists method."""
    with MemoryBackend() as backend:
        # Table doesn't exist yet
        assert not backend._client.table_exists("users")

        # After save, table exists
        User(pk="USER#1", name="Test").save()
        assert backend._client.table_exists("users")


def test_delete_by_key():
    """Test delete_by_key operation."""
    with MemoryBackend():
        User(pk="USER#1", name="Test").save()
        assert User.get(pk="USER#1") is not None

        User.delete_by_key(pk="USER#1")
        assert User.get(pk="USER#1") is None


def test_update_by_key():
    """Test update_by_key operation."""
    with MemoryBackend():
        User(pk="USER#1", name="Original", age=20).save()

        User.update_by_key(pk="USER#1", name="Updated")

        found = User.get(pk="USER#1")
        assert found is not None
        assert found.name == "Updated"
