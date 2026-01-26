"""Tests for Model base class."""

from unittest.mock import MagicMock

import pytest
from pydynox import Model, ModelConfig, clear_default_client, set_default_client
from pydynox.attributes import NumberAttribute, StringAttribute


@pytest.fixture(autouse=True)
def reset_state():
    """Reset default client before and after each test."""
    clear_default_client()
    yield
    clear_default_client()


@pytest.fixture
def mock_client():
    """Create a mock DynamoDB client."""
    return MagicMock()


@pytest.fixture
def user_model(mock_client):
    """Create a User model with mock client."""

    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(hash_key=True)
        sk = StringAttribute(range_key=True)
        name = StringAttribute()
        age = NumberAttribute()

    User._client_instance = None
    return User


def test_model_collects_attributes(user_model):
    """Model metaclass collects all attributes."""
    # GIVEN a User model with pk, sk, name, and age attributes

    # WHEN we check the collected attributes
    attributes = user_model._attributes

    # THEN all attributes should be present
    assert "pk" in attributes
    assert "sk" in attributes
    assert "name" in attributes
    assert "age" in attributes


def test_model_identifies_keys(user_model):
    """Model metaclass identifies hash and range keys."""
    # GIVEN a User model with pk as hash_key and sk as range_key

    # THEN the model should correctly identify the keys
    assert user_model._hash_key == "pk"
    assert user_model._range_key == "sk"


def test_model_init_sets_attributes(user_model):
    """Model init sets attribute values."""
    # GIVEN attribute values for a user

    # WHEN we create a user instance
    user = user_model(pk="USER#1", sk="PROFILE", name="John", age=30)

    # THEN all attributes should be set correctly
    assert user.pk == "USER#1"
    assert user.sk == "PROFILE"
    assert user.name == "John"
    assert user.age == 30


def test_model_init_sets_defaults(user_model):
    """Model init uses default values for missing attributes."""
    # GIVEN only required key attributes

    # WHEN we create a user without optional attributes
    user = user_model(pk="USER#1", sk="PROFILE")

    # THEN keys should be set and optional attributes should be None
    assert user.pk == "USER#1"
    assert user.name is None
    assert user.age is None


def test_model_to_dict(user_model):
    """to_dict returns all non-None attributes."""
    # GIVEN a user with all attributes set
    user = user_model(pk="USER#1", sk="PROFILE", name="John", age=30)

    # WHEN we convert to dict
    result = user.to_dict()

    # THEN all attributes should be in the dict
    assert result == {"pk": "USER#1", "sk": "PROFILE", "name": "John", "age": 30}


def test_model_to_dict_excludes_none(user_model):
    """to_dict excludes None values."""
    # GIVEN a user with age not set
    user = user_model(pk="USER#1", sk="PROFILE", name="John")

    # WHEN we convert to dict
    result = user.to_dict()

    # THEN age should not be in the dict
    assert result == {"pk": "USER#1", "sk": "PROFILE", "name": "John"}
    assert "age" not in result


def test_model_from_dict(user_model):
    """from_dict creates a model instance."""
    # GIVEN a dict with user data
    data = {"pk": "USER#1", "sk": "PROFILE", "name": "John", "age": 30}

    # WHEN we create a user from dict
    user = user_model.from_dict(data)

    # THEN all attributes should be set correctly
    assert user.pk == "USER#1"
    assert user.sk == "PROFILE"
    assert user.name == "John"
    assert user.age == 30


def test_model_get_key(user_model):
    """_get_key returns the primary key dict."""
    # GIVEN a user instance
    user = user_model(pk="USER#1", sk="PROFILE", name="John")

    # WHEN we get the key
    key = user._get_key()

    # THEN it should contain only pk and sk
    assert key == {"pk": "USER#1", "sk": "PROFILE"}


def test_model_repr(user_model):
    """__repr__ returns a readable string."""
    # GIVEN a user instance
    user = user_model(pk="USER#1", sk="PROFILE", name="John")

    # WHEN we get the repr
    result = repr(user)

    # THEN it should contain class name and key attributes
    assert "User" in result
    assert "pk='USER#1'" in result
    assert "name='John'" in result


def test_model_equality(user_model):
    """Models are equal if they have the same key."""
    # GIVEN three users with different keys/names
    user1 = user_model(pk="USER#1", sk="PROFILE", name="John")
    user2 = user_model(pk="USER#1", sk="PROFILE", name="Jane")
    user3 = user_model(pk="USER#2", sk="PROFILE", name="John")

    # THEN users with same key should be equal, different key should not
    assert user1 == user2  # Same key, different name
    assert user1 != user3  # Different key


def test_model_get(user_model, mock_client):
    """Model.get fetches item from DynamoDB."""
    # GIVEN a mock client that returns user data
    mock_client.get_item.return_value = {
        "pk": "USER#1",
        "sk": "PROFILE",
        "name": "John",
        "age": 30,
    }

    # WHEN we call get
    user = user_model.get(pk="USER#1", sk="PROFILE")

    # THEN the user should be returned with correct data
    assert user is not None
    assert user.pk == "USER#1"
    assert user.name == "John"
    mock_client.get_item.assert_called_once_with(
        "users", {"pk": "USER#1", "sk": "PROFILE"}, consistent_read=False
    )


def test_model_get_not_found(user_model, mock_client):
    """Model.get returns None when item not found."""
    # GIVEN a mock client that returns None
    mock_client.get_item.return_value = None

    # WHEN we call get for a non-existent user
    user = user_model.get(pk="USER#1", sk="PROFILE")

    # THEN None should be returned
    assert user is None


def test_model_save(user_model, mock_client):
    """Model.save puts item to DynamoDB."""
    # GIVEN a user instance
    user = user_model(pk="USER#1", sk="PROFILE", name="John", age=30)

    # WHEN we save the user
    user.save()

    # THEN put_item should be called with correct data
    mock_client.put_item.assert_called_once_with(
        "users", {"pk": "USER#1", "sk": "PROFILE", "name": "John", "age": 30}
    )


def test_model_delete(user_model, mock_client):
    """Model.delete removes item from DynamoDB."""
    # GIVEN a user instance
    user = user_model(pk="USER#1", sk="PROFILE", name="John")

    # WHEN we delete the user
    user.delete()

    # THEN delete_item should be called with the key
    mock_client.delete_item.assert_called_once_with("users", {"pk": "USER#1", "sk": "PROFILE"})


def test_model_update(user_model, mock_client):
    """Model.update updates specific attributes."""
    # GIVEN a user instance
    user = user_model(pk="USER#1", sk="PROFILE", name="John", age=30)

    # WHEN we update name and age
    user.update(name="Jane", age=31)

    # THEN local instance should be updated
    assert user.name == "Jane"
    assert user.age == 31

    # AND DynamoDB should be updated
    mock_client.update_item.assert_called_once_with(
        "users", {"pk": "USER#1", "sk": "PROFILE"}, updates={"name": "Jane", "age": 31}
    )


def test_model_update_unknown_attribute(user_model):
    """Model.update raises error for unknown attributes."""
    # GIVEN a user instance
    user = user_model(pk="USER#1", sk="PROFILE", name="John")

    # WHEN we try to update an unknown attribute
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="Unknown attribute"):
        user.update(unknown_field="value")


def test_model_with_default_client(mock_client):
    """Model works with default client."""
    # GIVEN a default client is set
    set_default_client(mock_client)
    mock_client.get_item.return_value = {"pk": "USER#1", "name": "John"}

    class User(Model):
        model_config = ModelConfig(table="users")
        pk = StringAttribute(hash_key=True)
        name = StringAttribute()

    User._client_instance = None

    # WHEN we call get
    user = User.get(pk="USER#1")

    # THEN the default client should be used
    assert user is not None
    assert user.name == "John"
    mock_client.get_item.assert_called_once()


# ========== update_by_key / delete_by_key tests ==========


def test_update_by_key(user_model, mock_client):
    """update_by_key updates item without fetching it first."""
    # GIVEN a model class with mock client

    # WHEN we call update_by_key
    user_model.update_by_key(pk="USER#1", sk="PROFILE", name="Jane", age=31)

    # THEN update_item should be called with correct params
    mock_client.update_item.assert_called_once_with(
        "users",
        {"pk": "USER#1", "sk": "PROFILE"},
        updates={"name": "Jane", "age": 31},
    )


def test_update_by_key_missing_hash_key(user_model):
    """update_by_key raises error when hash_key is missing."""
    # GIVEN a model that requires pk as hash_key

    # WHEN we call update_by_key without pk
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="Missing required hash_key"):
        user_model.update_by_key(sk="PROFILE", name="Jane")


def test_update_by_key_missing_range_key(user_model):
    """update_by_key raises error when range_key is missing."""
    # GIVEN a model that requires sk as range_key

    # WHEN we call update_by_key without sk
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="Missing required range_key"):
        user_model.update_by_key(pk="USER#1", name="Jane")


def test_update_by_key_unknown_attribute(user_model):
    """update_by_key raises error for unknown attributes."""
    # GIVEN a model with known attributes

    # WHEN we try to update an unknown attribute
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="Unknown attribute"):
        user_model.update_by_key(pk="USER#1", sk="PROFILE", unknown_field="value")


def test_update_by_key_no_updates(user_model, mock_client):
    """update_by_key does nothing when no updates provided."""
    # GIVEN a model class

    # WHEN we call update_by_key with only keys
    user_model.update_by_key(pk="USER#1", sk="PROFILE")

    # THEN update_item should not be called
    mock_client.update_item.assert_not_called()


def test_delete_by_key(user_model, mock_client):
    """delete_by_key deletes item without fetching it first."""
    # GIVEN a model class with mock client

    # WHEN we call delete_by_key
    user_model.delete_by_key(pk="USER#1", sk="PROFILE")

    # THEN delete_item should be called with the key
    mock_client.delete_item.assert_called_once_with("users", {"pk": "USER#1", "sk": "PROFILE"})


def test_delete_by_key_missing_hash_key(user_model):
    """delete_by_key raises error when hash_key is missing."""
    # GIVEN a model that requires pk as hash_key

    # WHEN we call delete_by_key without pk
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="Missing required hash_key"):
        user_model.delete_by_key(sk="PROFILE")


def test_delete_by_key_missing_range_key(user_model):
    """delete_by_key raises error when range_key is missing."""
    # GIVEN a model that requires sk as range_key

    # WHEN we call delete_by_key without sk
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="Missing required range_key"):
        user_model.delete_by_key(pk="USER#1")


@pytest.mark.asyncio
async def test_async_update_by_key(user_model, mock_client):
    """async_update_by_key updates item without fetching it first."""
    import asyncio

    # GIVEN a mock async client
    mock_client.async_update_item.return_value = asyncio.Future()
    mock_client.async_update_item.return_value.set_result(None)

    # WHEN we call async_update_by_key
    await user_model.async_update_by_key(pk="USER#1", sk="PROFILE", name="Jane")

    # THEN async_update_item should be called with correct params
    mock_client.async_update_item.assert_called_once_with(
        "users",
        {"pk": "USER#1", "sk": "PROFILE"},
        updates={"name": "Jane"},
    )


@pytest.mark.asyncio
async def test_async_delete_by_key(user_model, mock_client):
    """async_delete_by_key deletes item without fetching it first."""
    import asyncio

    # GIVEN a mock async client
    mock_client.async_delete_item.return_value = asyncio.Future()
    mock_client.async_delete_item.return_value.set_result(None)

    # WHEN we call async_delete_by_key
    await user_model.async_delete_by_key(pk="USER#1", sk="PROFILE")

    # THEN async_delete_item should be called with the key
    mock_client.async_delete_item.assert_called_once_with(
        "users", {"pk": "USER#1", "sk": "PROFILE"}
    )


# ========== as_dict tests ==========


def test_get_as_dict_true_returns_dict(user_model, mock_client):
    """get(as_dict=True) returns plain dict."""
    # GIVEN a mock client that returns user data
    mock_client.get_item.return_value = {
        "pk": "USER#1",
        "sk": "PROFILE",
        "name": "Alice",
        "age": 30,
    }

    # WHEN we call get with as_dict=True
    user = user_model.get(pk="USER#1", sk="PROFILE", as_dict=True)

    # THEN a plain dict should be returned
    assert isinstance(user, dict)
    assert user["name"] == "Alice"


def test_get_as_dict_false_returns_model_instance(user_model, mock_client):
    """get(as_dict=False) returns Model instance."""
    # GIVEN a mock client that returns user data
    mock_client.get_item.return_value = {
        "pk": "USER#1",
        "sk": "PROFILE",
        "name": "Alice",
        "age": 30,
    }

    # WHEN we call get with as_dict=False
    user = user_model.get(pk="USER#1", sk="PROFILE", as_dict=False)

    # THEN a Model instance should be returned
    assert isinstance(user, user_model)
    assert user.name == "Alice"


def test_get_as_dict_returns_none_when_not_found(user_model, mock_client):
    """get(as_dict=True) returns None when item not found."""
    # GIVEN a mock client that returns None
    mock_client.get_item.return_value = None

    # WHEN we call get with as_dict=True for non-existent item
    user = user_model.get(pk="USER#1", sk="PROFILE", as_dict=True)

    # THEN None should be returned
    assert user is None


# ========== sync_batch_get tests ==========


def test_sync_batch_get_returns_model_instances(user_model, mock_client):
    """sync_batch_get returns Model instances by default."""
    # GIVEN a mock client that returns multiple users
    mock_client.sync_batch_get.return_value = [
        {"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 30},
        {"pk": "USER#2", "sk": "PROFILE", "name": "Bob", "age": 25},
    ]

    keys = [
        {"pk": "USER#1", "sk": "PROFILE"},
        {"pk": "USER#2", "sk": "PROFILE"},
    ]

    # WHEN we call sync_batch_get
    users = user_model.sync_batch_get(keys)

    # THEN Model instances should be returned
    assert len(users) == 2
    assert isinstance(users[0], user_model)
    assert isinstance(users[1], user_model)
    assert users[0].name == "Alice"
    assert users[1].name == "Bob"


def test_sync_batch_get_as_dict_true_returns_dicts(user_model, mock_client):
    """sync_batch_get(as_dict=True) returns plain dicts."""
    # GIVEN a mock client that returns multiple users
    mock_client.sync_batch_get.return_value = [
        {"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 30},
        {"pk": "USER#2", "sk": "PROFILE", "name": "Bob", "age": 25},
    ]

    keys = [
        {"pk": "USER#1", "sk": "PROFILE"},
        {"pk": "USER#2", "sk": "PROFILE"},
    ]

    # WHEN we call sync_batch_get with as_dict=True
    users = user_model.sync_batch_get(keys, as_dict=True)

    # THEN plain dicts should be returned
    assert len(users) == 2
    assert isinstance(users[0], dict)
    assert isinstance(users[1], dict)
    assert users[0]["name"] == "Alice"
    assert users[1]["name"] == "Bob"


def test_sync_batch_get_empty_keys_returns_empty_list(user_model, mock_client):
    """sync_batch_get with empty keys returns empty list."""
    # GIVEN an empty list of keys

    # WHEN we call sync_batch_get with empty keys
    users = user_model.sync_batch_get([])

    # THEN empty list should be returned without calling the client
    assert users == []
    mock_client.sync_batch_get.assert_not_called()
