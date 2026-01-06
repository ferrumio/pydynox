"""Integration tests for update_by_key and delete_by_key operations."""

import uuid

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.exceptions import ConditionCheckFailedError


@pytest.fixture
def user_model(dynamo):
    """Create a User model with the test client."""

    class User(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        name = StringAttribute()
        age = NumberAttribute()

    User._client_instance = None
    return User


def test_update_by_key_updates_item(user_model):
    """update_by_key updates an existing item."""
    uid = str(uuid.uuid4())
    pk = f"USER#{uid}"

    # Create item first
    user = user_model(pk=pk, sk="PROFILE", name="John", age=30)
    user.save()

    # Update by key without fetching
    user_model.update_by_key(pk=pk, sk="PROFILE", name="Jane", age=31)

    # Verify update
    result = user_model.get(pk=pk, sk="PROFILE")
    assert result is not None
    assert result.name == "Jane"
    assert result.age == 31


def test_update_by_key_partial_update(user_model):
    """update_by_key only updates specified fields."""
    uid = str(uuid.uuid4())
    pk = f"USER#{uid}"

    user = user_model(pk=pk, sk="PROFILE", name="John", age=30)
    user.save()

    # Update only name
    user_model.update_by_key(pk=pk, sk="PROFILE", name="Jane")

    result = user_model.get(pk=pk, sk="PROFILE")
    assert result.name == "Jane"
    assert result.age == 30  # Unchanged


def test_update_by_key_creates_item_if_not_exists(user_model):
    """update_by_key creates item if it doesn't exist (DynamoDB behavior)."""
    uid = str(uuid.uuid4())
    pk = f"USER#{uid}"

    # Update non-existent item
    user_model.update_by_key(pk=pk, sk="PROFILE", name="NewUser")

    # Item should be created
    result = user_model.get(pk=pk, sk="PROFILE")
    assert result is not None
    assert result.name == "NewUser"


def test_update_by_key_with_condition_success(user_model):
    """update_by_key with condition that passes."""
    uid = str(uuid.uuid4())
    pk = f"USER#{uid}"

    user = user_model(pk=pk, sk="PROFILE", name="John", age=30)
    user.save()

    # Update with condition
    user_model.update_by_key(
        pk=pk,
        sk="PROFILE",
        name="Jane",
        condition=user_model.age == 30,
    )

    result = user_model.get(pk=pk, sk="PROFILE")
    assert result.name == "Jane"


def test_update_by_key_with_condition_fails(user_model):
    """update_by_key with condition that fails raises error."""
    uid = str(uuid.uuid4())
    pk = f"USER#{uid}"

    user = user_model(pk=pk, sk="PROFILE", name="John", age=30)
    user.save()

    with pytest.raises(ConditionCheckFailedError):
        user_model.update_by_key(
            pk=pk,
            sk="PROFILE",
            name="Jane",
            condition=user_model.age == 99,  # Wrong age
        )

    # Item unchanged
    result = user_model.get(pk=pk, sk="PROFILE")
    assert result.name == "John"


def test_delete_by_key_deletes_item(user_model):
    """delete_by_key removes an existing item."""
    uid = str(uuid.uuid4())
    pk = f"USER#{uid}"

    user = user_model(pk=pk, sk="PROFILE", name="John", age=30)
    user.save()

    # Delete by key without fetching
    user_model.delete_by_key(pk=pk, sk="PROFILE")

    # Verify deletion
    result = user_model.get(pk=pk, sk="PROFILE")
    assert result is None


def test_delete_by_key_nonexistent_item_no_error(user_model):
    """delete_by_key on non-existent item doesn't raise error."""
    uid = str(uuid.uuid4())
    pk = f"USER#{uid}"

    # Should not raise
    user_model.delete_by_key(pk=pk, sk="PROFILE")


def test_delete_by_key_with_condition_success(user_model):
    """delete_by_key with condition that passes."""
    uid = str(uuid.uuid4())
    pk = f"USER#{uid}"

    user = user_model(pk=pk, sk="PROFILE", name="John", age=30)
    user.save()

    user_model.delete_by_key(
        pk=pk,
        sk="PROFILE",
        condition=user_model.name == "John",
    )

    result = user_model.get(pk=pk, sk="PROFILE")
    assert result is None


def test_delete_by_key_with_condition_fails(user_model):
    """delete_by_key with condition that fails raises error."""
    uid = str(uuid.uuid4())
    pk = f"USER#{uid}"

    user = user_model(pk=pk, sk="PROFILE", name="John", age=30)
    user.save()

    with pytest.raises(ConditionCheckFailedError):
        user_model.delete_by_key(
            pk=pk,
            sk="PROFILE",
            condition=user_model.name == "Jane",  # Wrong name
        )

    # Item still exists
    result = user_model.get(pk=pk, sk="PROFILE")
    assert result is not None


@pytest.mark.asyncio
async def test_async_update_by_key(user_model):
    """async_update_by_key updates an existing item."""
    uid = str(uuid.uuid4())
    pk = f"USER#{uid}"

    user = user_model(pk=pk, sk="PROFILE", name="John", age=30)
    await user.async_save()

    await user_model.async_update_by_key(pk=pk, sk="PROFILE", name="Jane")

    result = await user_model.async_get(pk=pk, sk="PROFILE")
    assert result.name == "Jane"


@pytest.mark.asyncio
async def test_async_delete_by_key(user_model):
    """async_delete_by_key removes an existing item."""
    uid = str(uuid.uuid4())
    pk = f"USER#{uid}"

    user = user_model(pk=pk, sk="PROFILE", name="John", age=30)
    await user.async_save()

    await user_model.async_delete_by_key(pk=pk, sk="PROFILE")

    result = await user_model.async_get(pk=pk, sk="PROFILE")
    assert result is None
