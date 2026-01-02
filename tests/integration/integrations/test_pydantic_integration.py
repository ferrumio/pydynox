"""Integration tests for Pydantic integration with real DynamoDB."""

import uuid

from pydantic import BaseModel, Field
from pydynox import dynamodb_model


def test_pydantic_save_and_get(dynamo):
    """Save and retrieve a Pydantic model."""
    pk = f"PYD_TEST#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", hash_key="pk", range_key="sk", client=dynamo)
    class User(BaseModel):
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


def test_pydantic_update(dynamo):
    """Update a Pydantic model."""
    pk = f"PYD_TEST#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", hash_key="pk", range_key="sk", client=dynamo)
    class User(BaseModel):
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


def test_pydantic_delete(dynamo):
    """Delete a Pydantic model."""
    pk = f"PYD_TEST#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", hash_key="pk", range_key="sk", client=dynamo)
    class User(BaseModel):
        pk: str
        sk: str
        name: str

    user = User(pk=pk, sk="PROFILE", name="John")
    user.save()

    assert User.get(pk=pk, sk="PROFILE") is not None

    user.delete()

    assert User.get(pk=pk, sk="PROFILE") is None


def test_pydantic_validation_on_save(dynamo):
    """Pydantic validates data before save."""
    pk = f"PYD_TEST#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", hash_key="pk", range_key="sk", client=dynamo)
    class User(BaseModel):
        pk: str
        sk: str
        age: int = Field(ge=0, le=150)

    user = User(pk=pk, sk="PROFILE", age=30)
    user.save()

    retrieved = User.get(pk=pk, sk="PROFILE")
    assert retrieved.age == 30


def test_pydantic_with_optional_fields(dynamo):
    """Pydantic model with optional fields."""
    pk = f"PYD_TEST#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", hash_key="pk", range_key="sk", client=dynamo)
    class User(BaseModel):
        pk: str
        sk: str
        name: str
        email: str | None = None

    user = User(pk=pk, sk="PROFILE", name="John")
    user.save()

    retrieved = User.get(pk=pk, sk="PROFILE")
    assert retrieved.name == "John"
    assert retrieved.email is None


def test_pydantic_with_complex_types(dynamo):
    """Pydantic model with list and dict fields."""
    pk = f"PYD_TEST#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", hash_key="pk", range_key="sk", client=dynamo)
    class ComplexItem(BaseModel):
        pk: str
        sk: str
        tags: list[str]
        metadata: dict[str, int]

    item = ComplexItem(
        pk=pk,
        sk="COMPLEX",
        tags=["tag1", "tag2"],
        metadata={"count": 42, "score": 100},
    )
    item.save()

    retrieved = ComplexItem.get(pk=pk, sk="COMPLEX")
    assert retrieved.tags == ["tag1", "tag2"]
    assert retrieved.metadata == {"count": 42, "score": 100}
