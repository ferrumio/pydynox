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
    assert "pk" in user_model._attributes
    assert "sk" in user_model._attributes
    assert "name" in user_model._attributes
    assert "age" in user_model._attributes


def test_model_identifies_keys(user_model):
    """Model metaclass identifies hash and range keys."""
    assert user_model._hash_key == "pk"
    assert user_model._range_key == "sk"


def test_model_init_sets_attributes(user_model):
    """Model init sets attribute values."""
    user = user_model(pk="USER#1", sk="PROFILE", name="John", age=30)

    assert user.pk == "USER#1"
    assert user.sk == "PROFILE"
    assert user.name == "John"
    assert user.age == 30


def test_model_init_sets_defaults(user_model):
    """Model init uses default values for missing attributes."""
    user = user_model(pk="USER#1", sk="PROFILE")

    assert user.pk == "USER#1"
    assert user.name is None
    assert user.age is None


def test_model_to_dict(user_model):
    """to_dict returns all non-None attributes."""
    user = user_model(pk="USER#1", sk="PROFILE", name="John", age=30)

    result = user.to_dict()

    assert result == {"pk": "USER#1", "sk": "PROFILE", "name": "John", "age": 30}


def test_model_to_dict_excludes_none(user_model):
    """to_dict excludes None values."""
    user = user_model(pk="USER#1", sk="PROFILE", name="John")

    result = user.to_dict()

    assert result == {"pk": "USER#1", "sk": "PROFILE", "name": "John"}
    assert "age" not in result


def test_model_from_dict(user_model):
    """from_dict creates a model instance."""
    data = {"pk": "USER#1", "sk": "PROFILE", "name": "John", "age": 30}

    user = user_model.from_dict(data)

    assert user.pk == "USER#1"
    assert user.sk == "PROFILE"
    assert user.name == "John"
    assert user.age == 30


def test_model_get_key(user_model):
    """_get_key returns the primary key dict."""
    user = user_model(pk="USER#1", sk="PROFILE", name="John")

    key = user._get_key()

    assert key == {"pk": "USER#1", "sk": "PROFILE"}


def test_model_repr(user_model):
    """__repr__ returns a readable string."""
    user = user_model(pk="USER#1", sk="PROFILE", name="John")

    result = repr(user)

    assert "User" in result
    assert "pk='USER#1'" in result
    assert "name='John'" in result


def test_model_equality(user_model):
    """Models are equal if they have the same key."""
    user1 = user_model(pk="USER#1", sk="PROFILE", name="John")
    user2 = user_model(pk="USER#1", sk="PROFILE", name="Jane")
    user3 = user_model(pk="USER#2", sk="PROFILE", name="John")

    assert user1 == user2  # Same key, different name
    assert user1 != user3  # Different key


def test_model_get(user_model, mock_client):
    """Model.get fetches item from DynamoDB."""
    mock_client.get_item.return_value = {
        "pk": "USER#1",
        "sk": "PROFILE",
        "name": "John",
        "age": 30,
    }

    user = user_model.get(pk="USER#1", sk="PROFILE")

    assert user is not None
    assert user.pk == "USER#1"
    assert user.name == "John"
    mock_client.get_item.assert_called_once_with(
        "users", {"pk": "USER#1", "sk": "PROFILE"}, consistent_read=False
    )


def test_model_get_not_found(user_model, mock_client):
    """Model.get returns None when item not found."""
    mock_client.get_item.return_value = None

    user = user_model.get(pk="USER#1", sk="PROFILE")

    assert user is None


def test_model_save(user_model, mock_client):
    """Model.save puts item to DynamoDB."""
    user = user_model(pk="USER#1", sk="PROFILE", name="John", age=30)
    user.save()

    mock_client.put_item.assert_called_once_with(
        "users", {"pk": "USER#1", "sk": "PROFILE", "name": "John", "age": 30}
    )


def test_model_delete(user_model, mock_client):
    """Model.delete removes item from DynamoDB."""
    user = user_model(pk="USER#1", sk="PROFILE", name="John")
    user.delete()

    mock_client.delete_item.assert_called_once_with("users", {"pk": "USER#1", "sk": "PROFILE"})


def test_model_update(user_model, mock_client):
    """Model.update updates specific attributes."""
    user = user_model(pk="USER#1", sk="PROFILE", name="John", age=30)
    user.update(name="Jane", age=31)

    # Local instance updated
    assert user.name == "Jane"
    assert user.age == 31

    # DynamoDB updated
    mock_client.update_item.assert_called_once_with(
        "users", {"pk": "USER#1", "sk": "PROFILE"}, updates={"name": "Jane", "age": 31}
    )


def test_model_update_unknown_attribute(user_model):
    """Model.update raises error for unknown attributes."""
    user = user_model(pk="USER#1", sk="PROFILE", name="John")

    with pytest.raises(ValueError, match="Unknown attribute"):
        user.update(unknown_field="value")


def test_model_with_default_client(mock_client):
    """Model works with default client."""
    set_default_client(mock_client)
    mock_client.get_item.return_value = {"pk": "USER#1", "name": "John"}

    class User(Model):
        model_config = ModelConfig(table="users")
        pk = StringAttribute(hash_key=True)
        name = StringAttribute()

    User._client_instance = None

    user = User.get(pk="USER#1")

    assert user is not None
    assert user.name == "John"
    mock_client.get_item.assert_called_once()


# ========== update_by_key / delete_by_key tests ==========


def test_update_by_key(user_model, mock_client):
    """update_by_key updates item without fetching it first."""
    user_model.update_by_key(pk="USER#1", sk="PROFILE", name="Jane", age=31)

    mock_client.update_item.assert_called_once_with(
        "users",
        {"pk": "USER#1", "sk": "PROFILE"},
        updates={"name": "Jane", "age": 31},
    )


def test_update_by_key_missing_hash_key(user_model):
    """update_by_key raises error when hash_key is missing."""
    with pytest.raises(ValueError, match="Missing required hash_key"):
        user_model.update_by_key(sk="PROFILE", name="Jane")


def test_update_by_key_missing_range_key(user_model):
    """update_by_key raises error when range_key is missing."""
    with pytest.raises(ValueError, match="Missing required range_key"):
        user_model.update_by_key(pk="USER#1", name="Jane")


def test_update_by_key_unknown_attribute(user_model):
    """update_by_key raises error for unknown attributes."""
    with pytest.raises(ValueError, match="Unknown attribute"):
        user_model.update_by_key(pk="USER#1", sk="PROFILE", unknown_field="value")


def test_update_by_key_no_updates(user_model, mock_client):
    """update_by_key does nothing when no updates provided."""
    user_model.update_by_key(pk="USER#1", sk="PROFILE")

    mock_client.update_item.assert_not_called()


def test_delete_by_key(user_model, mock_client):
    """delete_by_key deletes item without fetching it first."""
    user_model.delete_by_key(pk="USER#1", sk="PROFILE")

    mock_client.delete_item.assert_called_once_with("users", {"pk": "USER#1", "sk": "PROFILE"})


def test_delete_by_key_missing_hash_key(user_model):
    """delete_by_key raises error when hash_key is missing."""
    with pytest.raises(ValueError, match="Missing required hash_key"):
        user_model.delete_by_key(sk="PROFILE")


def test_delete_by_key_missing_range_key(user_model):
    """delete_by_key raises error when range_key is missing."""
    with pytest.raises(ValueError, match="Missing required range_key"):
        user_model.delete_by_key(pk="USER#1")


@pytest.mark.asyncio
async def test_async_update_by_key(user_model, mock_client):
    """async_update_by_key updates item without fetching it first."""
    import asyncio

    mock_client.async_update_item.return_value = asyncio.Future()
    mock_client.async_update_item.return_value.set_result(None)

    await user_model.async_update_by_key(pk="USER#1", sk="PROFILE", name="Jane")

    mock_client.async_update_item.assert_called_once_with(
        "users",
        {"pk": "USER#1", "sk": "PROFILE"},
        updates={"name": "Jane"},
    )


@pytest.mark.asyncio
async def test_async_delete_by_key(user_model, mock_client):
    """async_delete_by_key deletes item without fetching it first."""
    import asyncio

    mock_client.async_delete_item.return_value = asyncio.Future()
    mock_client.async_delete_item.return_value.set_result(None)

    await user_model.async_delete_by_key(pk="USER#1", sk="PROFILE")

    mock_client.async_delete_item.assert_called_once_with(
        "users", {"pk": "USER#1", "sk": "PROFILE"}
    )


# ========== as_dict tests ==========


def test_get_as_dict_true_returns_dict(user_model, mock_client):
    """get(as_dict=True) returns plain dict."""
    mock_client.get_item.return_value = {
        "pk": "USER#1",
        "sk": "PROFILE",
        "name": "Alice",
        "age": 30,
    }

    user = user_model.get(pk="USER#1", sk="PROFILE", as_dict=True)

    assert isinstance(user, dict)
    assert user["name"] == "Alice"


def test_get_as_dict_false_returns_model_instance(user_model, mock_client):
    """get(as_dict=False) returns Model instance."""
    mock_client.get_item.return_value = {
        "pk": "USER#1",
        "sk": "PROFILE",
        "name": "Alice",
        "age": 30,
    }

    user = user_model.get(pk="USER#1", sk="PROFILE", as_dict=False)

    assert isinstance(user, user_model)
    assert user.name == "Alice"


def test_get_as_dict_returns_none_when_not_found(user_model, mock_client):
    """get(as_dict=True) returns None when item not found."""
    mock_client.get_item.return_value = None

    user = user_model.get(pk="USER#1", sk="PROFILE", as_dict=True)

    assert user is None


# ========== batch_get tests ==========


def test_batch_get_returns_model_instances(user_model, mock_client):
    """batch_get returns Model instances by default."""
    mock_client.batch_get.return_value = [
        {"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 30},
        {"pk": "USER#2", "sk": "PROFILE", "name": "Bob", "age": 25},
    ]

    keys = [
        {"pk": "USER#1", "sk": "PROFILE"},
        {"pk": "USER#2", "sk": "PROFILE"},
    ]
    users = user_model.batch_get(keys)

    assert len(users) == 2
    assert isinstance(users[0], user_model)
    assert isinstance(users[1], user_model)
    assert users[0].name == "Alice"
    assert users[1].name == "Bob"


def test_batch_get_as_dict_true_returns_dicts(user_model, mock_client):
    """batch_get(as_dict=True) returns plain dicts."""
    mock_client.batch_get.return_value = [
        {"pk": "USER#1", "sk": "PROFILE", "name": "Alice", "age": 30},
        {"pk": "USER#2", "sk": "PROFILE", "name": "Bob", "age": 25},
    ]

    keys = [
        {"pk": "USER#1", "sk": "PROFILE"},
        {"pk": "USER#2", "sk": "PROFILE"},
    ]
    users = user_model.batch_get(keys, as_dict=True)

    assert len(users) == 2
    assert isinstance(users[0], dict)
    assert isinstance(users[1], dict)
    assert users[0]["name"] == "Alice"
    assert users[1]["name"] == "Bob"


def test_batch_get_empty_keys_returns_empty_list(user_model, mock_client):
    """batch_get with empty keys returns empty list."""
    users = user_model.batch_get([])

    assert users == []
    mock_client.batch_get.assert_not_called()
