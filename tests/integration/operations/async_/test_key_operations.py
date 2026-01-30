"""Integration tests for update_by_key and delete_by_key operations."""

import uuid

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.exceptions import ConditionalCheckFailedException


@pytest.fixture
def user_model(dynamo):
    """Create a User model with the test client."""

    class User(Model):
        model_config = ModelConfig(table="test_table", client=dynamo)
        pk = StringAttribute(partition_key=True)
        sk = StringAttribute(sort_key=True)
        name = StringAttribute()
        age = NumberAttribute()

    User._client_instance = None
    return User


@pytest.mark.asyncio
async def test_update_by_key_updates_item(user_model):
    """update_by_key updates an existing item."""
    uid = str(uuid.uuid4())
    pk = f"USER#{uid}"

    # GIVEN an existing item
    user = user_model(pk=pk, sk="PROFILE", name="John", age=30)
    await user.save()

    # WHEN we update by key without fetching
    await user_model.update_by_key(pk=pk, sk="PROFILE", name="Jane", age=31)

    # THEN the update is applied
    result = await user_model.get(pk=pk, sk="PROFILE")
    assert result is not None
    assert result.name == "Jane"
    assert result.age == 31


@pytest.mark.asyncio
async def test_update_by_key_partial_update(user_model):
    """update_by_key only updates specified fields."""
    uid = str(uuid.uuid4())
    pk = f"USER#{uid}"

    user = user_model(pk=pk, sk="PROFILE", name="John", age=30)
    await user.save()

    # Update only name
    await user_model.update_by_key(pk=pk, sk="PROFILE", name="Jane")

    result = await user_model.get(pk=pk, sk="PROFILE")
    assert result.name == "Jane"
    assert result.age == 30  # Unchanged


@pytest.mark.asyncio
async def test_update_by_key_creates_item_if_not_exists(user_model):
    """update_by_key creates item if it doesn't exist (DynamoDB behavior)."""
    uid = str(uuid.uuid4())
    pk = f"USER#{uid}"

    # Update non-existent item
    await user_model.update_by_key(pk=pk, sk="PROFILE", name="NewUser")

    # Item should be created
    result = await user_model.get(pk=pk, sk="PROFILE")
    assert result is not None
    assert result.name == "NewUser"


@pytest.mark.asyncio
async def test_update_by_key_with_condition_success(user_model):
    """update_by_key with condition that passes."""
    uid = str(uuid.uuid4())
    pk = f"USER#{uid}"

    user = user_model(pk=pk, sk="PROFILE", name="John", age=30)
    await user.save()

    # Build condition separately to avoid any parsing issues
    age_condition = user_model.age == 30

    # Update with condition
    await user_model.update_by_key(
        pk=pk,
        sk="PROFILE",
        name="Jane",
        condition=age_condition,
    )

    result = await user_model.get(pk=pk, sk="PROFILE")
    assert result.name == "Jane"


@pytest.mark.asyncio
async def test_update_by_key_with_condition_fails(user_model):
    """update_by_key with condition that fails raises error."""
    uid = str(uuid.uuid4())
    pk = f"USER#{uid}"

    user = user_model(pk=pk, sk="PROFILE", name="John", age=30)
    await user.save()

    # Build condition separately
    age_condition = user_model.age == 99  # Wrong age

    with pytest.raises(ConditionalCheckFailedException):
        await user_model.update_by_key(
            pk=pk,
            sk="PROFILE",
            name="Jane",
            condition=age_condition,
        )

    # Item unchanged
    result = await user_model.get(pk=pk, sk="PROFILE")
    assert result.name == "John"


@pytest.mark.asyncio
async def test_delete_by_key_deletes_item(user_model):
    """delete_by_key removes an existing item."""
    uid = str(uuid.uuid4())
    pk = f"USER#{uid}"

    # GIVEN an existing item
    user = user_model(pk=pk, sk="PROFILE", name="John", age=30)
    await user.save()

    # WHEN we delete by key without fetching
    await user_model.delete_by_key(pk=pk, sk="PROFILE")

    # THEN the item is deleted
    result = await user_model.get(pk=pk, sk="PROFILE")
    assert result is None


@pytest.mark.asyncio
async def test_delete_by_key_nonexistent_item_no_error(user_model):
    """delete_by_key on non-existent item doesn't raise error."""
    uid = str(uuid.uuid4())
    pk = f"USER#{uid}"

    # Should not raise
    await user_model.delete_by_key(pk=pk, sk="PROFILE")


@pytest.mark.asyncio
async def test_delete_by_key_with_condition_success(user_model):
    """delete_by_key with condition that passes."""
    uid = str(uuid.uuid4())
    pk = f"USER#{uid}"

    user = user_model(pk=pk, sk="PROFILE", name="John", age=30)
    await user.save()

    # Build condition separately
    name_condition = user_model.name == "John"

    await user_model.delete_by_key(
        pk=pk,
        sk="PROFILE",
        condition=name_condition,
    )

    result = await user_model.get(pk=pk, sk="PROFILE")
    assert result is None


@pytest.mark.asyncio
async def test_delete_by_key_with_condition_fails(user_model):
    """delete_by_key with condition that fails raises error."""
    uid = str(uuid.uuid4())
    pk = f"USER#{uid}"

    user = user_model(pk=pk, sk="PROFILE", name="John", age=30)
    await user.save()

    # Build condition separately
    name_condition = user_model.name == "Jane"  # Wrong name

    with pytest.raises(ConditionalCheckFailedException):
        await user_model.delete_by_key(
            pk=pk,
            sk="PROFILE",
            condition=name_condition,
        )

    # Item still exists
    result = await user_model.get(pk=pk, sk="PROFILE")
    assert result is not None


# ========== SYNC TESTS ==========


def test_sync_update_by_key(user_model):
    """sync_update_by_key updates an existing item."""
    uid = str(uuid.uuid4())
    pk = f"USER#{uid}"

    user = user_model(pk=pk, sk="PROFILE", name="John", age=30)
    user.sync_save()

    user_model.sync_update_by_key(pk=pk, sk="PROFILE", name="Jane")

    result = user_model.sync_get(pk=pk, sk="PROFILE")
    assert result.name == "Jane"


def test_sync_delete_by_key(user_model):
    """sync_delete_by_key removes an existing item."""
    uid = str(uuid.uuid4())
    pk = f"USER#{uid}"

    user = user_model(pk=pk, sk="PROFILE", name="John", age=30)
    user.sync_save()

    user_model.sync_delete_by_key(pk=pk, sk="PROFILE")

    result = user_model.sync_get(pk=pk, sk="PROFILE")
    assert result is None


# ========== as_dict tests ==========


@pytest.mark.asyncio
async def test_get_as_dict_returns_dict(user_model):
    """Model.get(as_dict=True) returns plain dict."""
    uid = str(uuid.uuid4())
    pk = f"USER#{uid}"

    # GIVEN an existing item
    user = user_model(pk=pk, sk="PROFILE", name="Alice", age=25)
    await user.save()

    # WHEN we get with as_dict=True
    result = await user_model.get(pk=pk, sk="PROFILE", as_dict=True)

    # THEN a plain dict is returned
    assert result is not None
    assert isinstance(result, dict)
    assert result["name"] == "Alice"
    assert result["age"] == 25


@pytest.mark.asyncio
async def test_get_as_dict_false_returns_model(user_model):
    """Model.get(as_dict=False) returns Model instance."""
    uid = str(uuid.uuid4())
    pk = f"USER#{uid}"

    user = user_model(pk=pk, sk="PROFILE", name="Bob", age=30)
    await user.save()

    result = await user_model.get(pk=pk, sk="PROFILE", as_dict=False)

    assert result is not None
    assert isinstance(result, user_model)
    assert result.name == "Bob"


@pytest.mark.asyncio
async def test_get_as_dict_not_found_returns_none(user_model):
    """Model.get(as_dict=True) returns None when not found."""
    uid = str(uuid.uuid4())
    pk = f"USER#{uid}"

    result = await user_model.get(pk=pk, sk="PROFILE", as_dict=True)

    assert result is None
