"""Sync integration tests for dataclass integration with real DynamoDB."""

import uuid
from dataclasses import dataclass

from pydynox import dynamodb_model


def test_sync_dataclass_save_and_get(dynamo):
    """Sync save and retrieve a dataclass item."""
    pk = f"SYNC_DC#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", hash_key="pk", range_key="sk", client=dynamo)
    @dataclass
    class User:
        pk: str
        sk: str
        name: str
        age: int = 0

    # GIVEN a dataclass model instance
    user = User(pk=pk, sk="PROFILE", name="John", age=30)

    # WHEN we save and retrieve it (sync)
    user.sync_save()
    retrieved = User.sync_get(pk=pk, sk="PROFILE")

    # THEN all fields are preserved
    assert retrieved is not None
    assert retrieved.pk == pk
    assert retrieved.name == "John"
    assert retrieved.age == 30


def test_sync_dataclass_update(dynamo):
    """Sync update a dataclass item."""
    pk = f"SYNC_DC#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", hash_key="pk", range_key="sk", client=dynamo)
    @dataclass
    class User:
        pk: str
        sk: str
        name: str
        age: int = 0

    # GIVEN a saved dataclass item
    user = User(pk=pk, sk="PROFILE", name="John", age=30)
    user.sync_save()

    # WHEN we update it (sync)
    user.sync_update(name="Jane", age=31)

    # THEN changes are persisted
    retrieved = User.sync_get(pk=pk, sk="PROFILE")
    assert retrieved.name == "Jane"
    assert retrieved.age == 31


def test_sync_dataclass_delete(dynamo):
    """Sync delete a dataclass item."""
    pk = f"SYNC_DC#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", hash_key="pk", range_key="sk", client=dynamo)
    @dataclass
    class User:
        pk: str
        sk: str
        name: str

    # GIVEN a saved dataclass item
    user = User(pk=pk, sk="PROFILE", name="John")
    user.sync_save()
    assert User.sync_get(pk=pk, sk="PROFILE") is not None

    # WHEN we delete it (sync)
    user.sync_delete()

    # THEN it's gone
    assert User.sync_get(pk=pk, sk="PROFILE") is None


def test_sync_dataclass_get_not_found(dynamo):
    """Sync get returns None for non-existent item."""
    pk = f"SYNC_DC#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", hash_key="pk", range_key="sk", client=dynamo)
    @dataclass
    class User:
        pk: str
        sk: str
        name: str

    result = User.sync_get(pk=pk, sk="NONEXISTENT")
    assert result is None


def test_sync_dataclass_with_complex_types(dynamo):
    """Sync dataclass with list and dict fields."""
    pk = f"SYNC_DC#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", hash_key="pk", range_key="sk", client=dynamo)
    @dataclass
    class ComplexItem:
        pk: str
        sk: str
        tags: list
        metadata: dict

    # GIVEN a dataclass with complex types
    item = ComplexItem(
        pk=pk,
        sk="COMPLEX",
        tags=["tag1", "tag2"],
        metadata={"key": "value", "count": 42},
    )

    # WHEN we save and retrieve it (sync)
    item.sync_save()
    retrieved = ComplexItem.sync_get(pk=pk, sk="COMPLEX")

    # THEN complex types are preserved
    assert retrieved.tags == ["tag1", "tag2"]
    assert retrieved.metadata == {"key": "value", "count": 42}
