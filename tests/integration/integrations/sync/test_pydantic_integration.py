"""Sync integration tests for Pydantic integration with real DynamoDB."""

import uuid

from pydantic import BaseModel, Field
from pydynox import dynamodb_model


def test_sync_pydantic_save_and_get(dynamo):
    """Sync save and retrieve a Pydantic model."""
    pk = f"SYNC_PYD#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", hash_key="pk", range_key="sk", client=dynamo)
    class User(BaseModel):
        pk: str
        sk: str
        name: str
        age: int = 0

    # GIVEN a Pydantic model instance
    user = User(pk=pk, sk="PROFILE", name="John", age=30)

    # WHEN we save and retrieve it (sync)
    user.sync_save()
    retrieved = User.sync_get(pk=pk, sk="PROFILE")

    # THEN all fields are preserved
    assert retrieved is not None
    assert retrieved.pk == pk
    assert retrieved.name == "John"
    assert retrieved.age == 30


def test_sync_pydantic_update(dynamo):
    """Sync update a Pydantic model."""
    pk = f"SYNC_PYD#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", hash_key="pk", range_key="sk", client=dynamo)
    class User(BaseModel):
        pk: str
        sk: str
        name: str
        age: int = 0

    # GIVEN a saved Pydantic model
    user = User(pk=pk, sk="PROFILE", name="John", age=30)
    user.sync_save()

    # WHEN we update it (sync)
    user.sync_update(name="Jane", age=31)

    # THEN changes are persisted
    retrieved = User.sync_get(pk=pk, sk="PROFILE")
    assert retrieved.name == "Jane"
    assert retrieved.age == 31


def test_sync_pydantic_delete(dynamo):
    """Sync delete a Pydantic model."""
    pk = f"SYNC_PYD#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", hash_key="pk", range_key="sk", client=dynamo)
    class User(BaseModel):
        pk: str
        sk: str
        name: str

    # GIVEN a saved Pydantic model
    user = User(pk=pk, sk="PROFILE", name="John")
    user.sync_save()
    assert User.sync_get(pk=pk, sk="PROFILE") is not None

    # WHEN we delete it (sync)
    user.sync_delete()

    # THEN it's gone
    assert User.sync_get(pk=pk, sk="PROFILE") is None


def test_sync_pydantic_validation_on_save(dynamo):
    """Pydantic validates data before sync save."""
    pk = f"SYNC_PYD#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", hash_key="pk", range_key="sk", client=dynamo)
    class User(BaseModel):
        pk: str
        sk: str
        age: int = Field(ge=0, le=150)

    user = User(pk=pk, sk="PROFILE", age=30)
    user.sync_save()

    retrieved = User.sync_get(pk=pk, sk="PROFILE")
    assert retrieved.age == 30


def test_sync_pydantic_with_optional_fields(dynamo):
    """Sync Pydantic model with optional fields."""
    pk = f"SYNC_PYD#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", hash_key="pk", range_key="sk", client=dynamo)
    class User(BaseModel):
        pk: str
        sk: str
        name: str
        email: str | None = None

    user = User(pk=pk, sk="PROFILE", name="John")
    user.sync_save()

    retrieved = User.sync_get(pk=pk, sk="PROFILE")
    assert retrieved.name == "John"
    assert retrieved.email is None


def test_sync_pydantic_with_complex_types(dynamo):
    """Sync Pydantic model with list and dict fields."""
    pk = f"SYNC_PYD#{uuid.uuid4().hex[:8]}"

    @dynamodb_model(table="test_table", hash_key="pk", range_key="sk", client=dynamo)
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

    # WHEN we save and retrieve it (sync)
    item.sync_save()
    retrieved = ComplexItem.sync_get(pk=pk, sk="COMPLEX")

    # THEN complex types are preserved
    assert retrieved.tags == ["tag1", "tag2"]
    assert retrieved.metadata == {"count": 42, "score": 100}
