"""Unit tests for MemoryBackend.

With async-first API:
- get(), save(), delete(), update() are async (default)
- sync_get(), sync_save(), sync_delete(), sync_update() are sync
"""

import pytest
from pydynox import Model, ModelConfig, get_default_client
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.testing import MemoryBackend


class User(Model):
    """Test model."""

    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)


def test_memory_backend_context_manager():
    """Test MemoryBackend as context manager."""
    with MemoryBackend():
        user = User(pk="USER#1", name="John")
        user.sync_save()

        found = User.sync_get(pk="USER#1")

        assert found is not None
        assert found.name == "John"


def test_memory_backend_decorator():
    """Test MemoryBackend as decorator."""

    @MemoryBackend()
    def inner():
        user = User(pk="USER#1", name="Jane")
        user.sync_save()
        return User.sync_get(pk="USER#1")

    result = inner()

    assert result is not None
    assert result.name == "Jane"


def test_memory_backend_restores_client():
    """Test that MemoryBackend restores previous client."""
    original = get_default_client()

    with MemoryBackend():
        pass

    assert get_default_client() == original


def test_put_and_get():
    """Test basic put and get operations."""
    with MemoryBackend():
        user = User(pk="USER#1", name="Alice", age=30)
        user.sync_save()

        found = User.sync_get(pk="USER#1")

        assert found is not None
        assert found.pk == "USER#1"
        assert found.name == "Alice"
        assert found.age == 30


def test_get_not_found():
    """Test get returns None for missing item."""
    with MemoryBackend():
        found = User.sync_get(pk="NONEXISTENT")
        assert found is None


def test_delete():
    """Test delete operation."""
    with MemoryBackend():
        user = User(pk="USER#1", name="Bob")
        user.sync_save()
        assert User.sync_get(pk="USER#1") is not None

        user.sync_delete()

        assert User.sync_get(pk="USER#1") is None


def test_update():
    """Test update operation."""
    with MemoryBackend():
        user = User(pk="USER#1", name="Charlie", age=25)
        user.sync_save()

        user.sync_update(name="Charles", age=26)

        found = User.sync_get(pk="USER#1")
        assert found is not None
        assert found.name == "Charles"
        assert found.age == 26


def test_atomic_increment():
    """Test atomic increment operation."""
    with MemoryBackend():
        user = User(pk="USER#1", name="Dave", age=0)
        user.sync_save()

        user.sync_update(atomic=[User.age.add(5)])

        found = User.sync_get(pk="USER#1")
        assert found is not None
        assert found.age == 5


def test_scan():
    """Test scan operation."""
    with MemoryBackend():
        User(pk="USER#1", name="Eve").sync_save()
        User(pk="USER#2", name="Frank").sync_save()
        User(pk="USER#3", name="Grace").sync_save()

        results = list(User.sync_scan())

        assert len(results) == 3


def test_query():
    """Test query operation."""

    class Order(Model):
        model_config = ModelConfig(table="orders")
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        total = NumberAttribute()

    with MemoryBackend():
        Order(pk="USER#1", sk="ORDER#001", total=100).sync_save()
        Order(pk="USER#1", sk="ORDER#002", total=200).sync_save()
        Order(pk="USER#2", sk="ORDER#001", total=50).sync_save()

        results = list(Order.sync_query(partition_key="USER#1"))

        assert len(results) == 2


def test_seed_data():
    """Test MemoryBackend with seed data."""
    seed = {
        "users": [
            {"pk": "USER#1", "name": "Seeded User", "age": 99},
        ]
    }

    with MemoryBackend(seed=seed):
        found = User.sync_get(pk="USER#1")

        assert found is not None
        assert found.name == "Seeded User"
        assert found.age == 99


def test_clear():
    """Test clearing all data."""
    with MemoryBackend() as backend:
        User(pk="USER#1", name="Test").sync_save()
        assert len(backend.tables.get("users", {})) == 1

        backend.clear()

        assert len(backend.tables) == 0


def test_tables_property():
    """Test accessing tables for inspection."""
    with MemoryBackend() as backend:
        User(pk="USER#1", name="Test").sync_save()

        assert "users" in backend.tables
        assert len(backend.tables["users"]) == 1


def test_condition_attribute_not_exists():
    """Test condition with attribute_not_exists."""
    with MemoryBackend():
        user = User(pk="USER#1", name="Test")
        user.sync_save(condition=User.pk.not_exists())

        user2 = User(pk="USER#1", name="Test2")

        with pytest.raises(Exception):
            user2.sync_save(condition=User.pk.not_exists())


def test_multiple_tables():
    """Test operations on multiple tables."""

    class Product(Model):
        model_config = ModelConfig(table="products")
        pk = StringAttribute(partition_key=True)
        name = StringAttribute()

    with MemoryBackend():
        User(pk="USER#1", name="User").sync_save()
        Product(pk="PROD#1", name="Product").sync_save()

        assert User.sync_get(pk="USER#1") is not None
        assert Product.sync_get(pk="PROD#1") is not None


def test_isolation_between_contexts():
    """Test that data is isolated between contexts."""
    with MemoryBackend():
        User(pk="USER#1", name="First").sync_save()

    with MemoryBackend():
        assert User.sync_get(pk="USER#1") is None


def test_table_exists():
    """Test table_exists method."""
    with MemoryBackend() as backend:
        assert not backend._client.sync_table_exists("users")

        User(pk="USER#1", name="Test").sync_save()

        assert backend._client.sync_table_exists("users")


def test_delete_by_key():
    """Test delete_by_key operation."""
    with MemoryBackend():
        User(pk="USER#1", name="Test").sync_save()
        assert User.sync_get(pk="USER#1") is not None

        User.sync_delete_by_key(pk="USER#1")

        assert User.sync_get(pk="USER#1") is None


def test_update_by_key():
    """Test update_by_key operation."""
    with MemoryBackend():
        User(pk="USER#1", name="Original", age=20).sync_save()

        User.sync_update_by_key(pk="USER#1", name="Updated")

        found = User.sync_get(pk="USER#1")
        assert found is not None
        assert found.name == "Updated"


# ========== ASYNC TESTS ==========


@pytest.mark.asyncio
async def test_async_put_and_get():
    """Test async put and get operations."""
    with MemoryBackend():
        user = User(pk="USER#1", name="Alice", age=30)
        await user.save()

        found = await User.get(pk="USER#1")

        assert found is not None
        assert found.pk == "USER#1"
        assert found.name == "Alice"


@pytest.mark.asyncio
async def test_async_delete():
    """Test async delete operation."""
    with MemoryBackend():
        user = User(pk="USER#1", name="Bob")
        await user.save()

        await user.delete()

        found = await User.get(pk="USER#1")
        assert found is None


@pytest.mark.asyncio
async def test_async_update():
    """Test async update operation."""
    with MemoryBackend():
        user = User(pk="USER#1", name="Charlie", age=25)
        await user.save()

        await user.update(name="Charles", age=26)

        found = await User.get(pk="USER#1")
        assert found is not None
        assert found.name == "Charles"
        assert found.age == 26


@pytest.mark.asyncio
async def test_async_delete_by_key():
    """Test async delete_by_key operation."""
    with MemoryBackend():
        User(pk="USER#1", name="Test").sync_save()

        await User.delete_by_key(pk="USER#1")

        found = await User.get(pk="USER#1")
        assert found is None


@pytest.mark.asyncio
async def test_async_update_by_key():
    """Test async update_by_key operation."""
    with MemoryBackend():
        User(pk="USER#1", name="Original", age=20).sync_save()

        await User.update_by_key(pk="USER#1", name="Updated")

        found = await User.get(pk="USER#1")
        assert found is not None
        assert found.name == "Updated"
