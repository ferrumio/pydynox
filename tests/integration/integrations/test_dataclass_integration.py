"""Integration tests for dataclass integration with real DynamoDB."""

import uuid
from dataclasses import dataclass

from pydynox import dynamodb_model


def test_dataclass_save_and_get(dynamo):
    """Save and retrieve a dataclass item."""
    pk = f"DC_TEST#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", hash_key="pk", range_key="sk", client=dynamo)
    @dataclass
    class User:
        pk: str
        sk: str
        name: str
        age: int = 0

    user = User(pk=pk, sk="PROFILE", name="John", age=30)
    user.save()

    retrieved = User.get(pk=pk, sk="PROFILE")

    assert retrieved is not None
    assert retrieved.pk == pk
    assert retrieved.name == "John"
    assert retrieved.age == 30


def test_dataclass_update(dynamo):
    """Update a dataclass item."""
    pk = f"DC_TEST#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", hash_key="pk", range_key="sk", client=dynamo)
    @dataclass
    class User:
        pk: str
        sk: str
        name: str
        age: int = 0

    user = User(pk=pk, sk="PROFILE", name="John", age=30)
    user.save()

    user.update(name="Jane", age=31)

    retrieved = User.get(pk=pk, sk="PROFILE")
    assert retrieved.name == "Jane"
    assert retrieved.age == 31


def test_dataclass_delete(dynamo):
    """Delete a dataclass item."""
    pk = f"DC_TEST#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", hash_key="pk", range_key="sk", client=dynamo)
    @dataclass
    class User:
        pk: str
        sk: str
        name: str

    user = User(pk=pk, sk="PROFILE", name="John")
    user.save()

    assert User.get(pk=pk, sk="PROFILE") is not None

    user.delete()

    assert User.get(pk=pk, sk="PROFILE") is None


def test_dataclass_get_not_found(dynamo):
    """Get returns None for non-existent item."""
    pk = f"DC_TEST#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", hash_key="pk", range_key="sk", client=dynamo)
    @dataclass
    class User:
        pk: str
        sk: str
        name: str

    result = User.get(pk=pk, sk="NONEXISTENT")
    assert result is None


def test_dataclass_with_complex_types(dynamo):
    """Dataclass with list and dict fields."""
    pk = f"DC_TEST#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", hash_key="pk", range_key="sk", client=dynamo)
    @dataclass
    class ComplexItem:
        pk: str
        sk: str
        tags: list
        metadata: dict

    item = ComplexItem(
        pk=pk,
        sk="COMPLEX",
        tags=["tag1", "tag2"],
        metadata={"key": "value", "count": 42},
    )
    item.save()

    retrieved = ComplexItem.get(pk=pk, sk="COMPLEX")
    assert retrieved.tags == ["tag1", "tag2"]
    assert retrieved.metadata == {"key": "value", "count": 42}
