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
