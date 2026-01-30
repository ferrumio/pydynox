"""Integration tests for dataclass integration with real DynamoDB."""

import uuid
from dataclasses import dataclass

import pytest
from pydynox import dynamodb_model


@pytest.mark.asyncio
async def test_dataclass_save_and_get(dynamo):
    """Save and retrieve a dataclass item."""
    pk = f"DC_TEST#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", partition_key="pk", sort_key="sk", client=dynamo)
    @dataclass
    class User:
        pk: str
        sk: str
        name: str
        age: int = 0

    # GIVEN a dataclass model instance
    user = User(pk=pk, sk="PROFILE", name="John", age=30)

    # WHEN we save and retrieve it
    await user.save()
    retrieved = await User.get(pk=pk, sk="PROFILE")

    # THEN all fields are preserved
    assert retrieved is not None
    assert retrieved.pk == pk
    assert retrieved.name == "John"
    assert retrieved.age == 30


@pytest.mark.asyncio
async def test_dataclass_update(dynamo):
    """Update a dataclass item."""
    pk = f"DC_TEST#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", partition_key="pk", sort_key="sk", client=dynamo)
    @dataclass
    class User:
        pk: str
        sk: str
        name: str
        age: int = 0

    # GIVEN a saved dataclass item
    user = User(pk=pk, sk="PROFILE", name="John", age=30)
    await user.save()

    # WHEN we update it
    await user.update(name="Jane", age=31)

    # THEN changes are persisted
    retrieved = await User.get(pk=pk, sk="PROFILE")
    assert retrieved.name == "Jane"
    assert retrieved.age == 31


@pytest.mark.asyncio
async def test_dataclass_delete(dynamo):
    """Delete a dataclass item."""
    pk = f"DC_TEST#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", partition_key="pk", sort_key="sk", client=dynamo)
    @dataclass
    class User:
        pk: str
        sk: str
        name: str

    # GIVEN a saved dataclass item
    user = User(pk=pk, sk="PROFILE", name="John")
    await user.save()
    assert await User.get(pk=pk, sk="PROFILE") is not None

    # WHEN we delete it
    await user.delete()

    # THEN it's gone
    assert await User.get(pk=pk, sk="PROFILE") is None


@pytest.mark.asyncio
async def test_dataclass_get_not_found(dynamo):
    """Get returns None for non-existent item."""
    pk = f"DC_TEST#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", partition_key="pk", sort_key="sk", client=dynamo)
    @dataclass
    class User:
        pk: str
        sk: str
        name: str

    result = await User.get(pk=pk, sk="NONEXISTENT")
    assert result is None


@pytest.mark.asyncio
async def test_dataclass_with_complex_types(dynamo):
    """Dataclass with list and dict fields."""
    pk = f"DC_TEST#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", partition_key="pk", sort_key="sk", client=dynamo)
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

    # WHEN we save and retrieve it
    await item.save()
    retrieved = await ComplexItem.get(pk=pk, sk="COMPLEX")

    # THEN complex types are preserved
    assert retrieved.tags == ["tag1", "tag2"]
    assert retrieved.metadata == {"key": "value", "count": 42}
