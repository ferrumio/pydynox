"""Integration tests for Pydantic integration with real DynamoDB."""

import uuid

import pytest
from pydantic import BaseModel, Field
from pydynox import dynamodb_model


@pytest.mark.asyncio
async def test_pydantic_save_and_get(dynamo):
    """Save and retrieve a Pydantic model."""
    pk = f"PYD_TEST#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", partition_key="pk", sort_key="sk", client=dynamo)
    class User(BaseModel):
        pk: str
        sk: str
        name: str
        age: int = 0

    # GIVEN a Pydantic model instance
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
async def test_pydantic_update(dynamo):
    """Update a Pydantic model."""
    pk = f"PYD_TEST#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", partition_key="pk", sort_key="sk", client=dynamo)
    class User(BaseModel):
        pk: str
        sk: str
        name: str
        age: int = 0

    # GIVEN a saved Pydantic model
    user = User(pk=pk, sk="PROFILE", name="John", age=30)
    await user.save()

    # WHEN we update it
    await user.update(name="Jane", age=31)

    # THEN changes are persisted
    retrieved = await User.get(pk=pk, sk="PROFILE")
    assert retrieved.name == "Jane"
    assert retrieved.age == 31


@pytest.mark.asyncio
async def test_pydantic_delete(dynamo):
    """Delete a Pydantic model."""
    pk = f"PYD_TEST#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", partition_key="pk", sort_key="sk", client=dynamo)
    class User(BaseModel):
        pk: str
        sk: str
        name: str

    # GIVEN a saved Pydantic model
    user = User(pk=pk, sk="PROFILE", name="John")
    await user.save()
    assert await User.get(pk=pk, sk="PROFILE") is not None

    # WHEN we delete it
    await user.delete()

    # THEN it's gone
    assert await User.get(pk=pk, sk="PROFILE") is None


@pytest.mark.asyncio
async def test_pydantic_validation_on_save(dynamo):
    """Pydantic validates data before save."""
    pk = f"PYD_TEST#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", partition_key="pk", sort_key="sk", client=dynamo)
    class User(BaseModel):
        pk: str
        sk: str
        age: int = Field(ge=0, le=150)

    user = User(pk=pk, sk="PROFILE", age=30)
    await user.save()

    retrieved = await User.get(pk=pk, sk="PROFILE")
    assert retrieved.age == 30


@pytest.mark.asyncio
async def test_pydantic_with_optional_fields(dynamo):
    """Pydantic model with optional fields."""
    pk = f"PYD_TEST#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", partition_key="pk", sort_key="sk", client=dynamo)
    class User(BaseModel):
        pk: str
        sk: str
        name: str
        email: str | None = None

    user = User(pk=pk, sk="PROFILE", name="John")
    await user.save()

    retrieved = await User.get(pk=pk, sk="PROFILE")
    assert retrieved.name == "John"
    assert retrieved.email is None


@pytest.mark.asyncio
async def test_pydantic_with_complex_types(dynamo):
    """Pydantic model with list and dict fields."""
    pk = f"PYD_TEST#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", partition_key="pk", sort_key="sk", client=dynamo)
    class ComplexItem(BaseModel):
        pk: str
        sk: str
        tags: list[str]
        metadata: dict[str, int]

    # GIVEN a Pydantic model with complex types
    item = ComplexItem(
        pk=pk,
        sk="COMPLEX",
        tags=["tag1", "tag2"],
        metadata={"count": 42, "score": 100},
    )

    # WHEN we save and retrieve it
    await item.save()
    retrieved = await ComplexItem.get(pk=pk, sk="COMPLEX")

    # THEN complex types are preserved
    assert retrieved.tags == ["tag1", "tag2"]
    assert retrieved.metadata == {"count": 42, "score": 100}
