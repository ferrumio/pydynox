"""Tests for Model base class."""

from unittest.mock import MagicMock, patch

import pytest
from pydynox import Model  # noqa: I001
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    """Test model for users."""

    class Meta:
        table = "users"
        region = "us-east-1"

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    age = NumberAttribute()


def test_model_collects_attributes():
    """Model metaclass collects all attributes."""
    assert "pk" in User._attributes
    assert "sk" in User._attributes
    assert "name" in User._attributes
    assert "age" in User._attributes


def test_model_identifies_keys():
    """Model metaclass identifies hash and range keys."""
    assert User._hash_key == "pk"
    assert User._range_key == "sk"


def test_model_init_sets_attributes():
    """Model init sets attribute values."""
    user = User(pk="USER#1", sk="PROFILE", name="John", age=30)

    assert user.pk == "USER#1"
    assert user.sk == "PROFILE"
    assert user.name == "John"
    assert user.age == 30


def test_model_init_sets_defaults():
    """Model init uses default values for missing attributes."""
    user = User(pk="USER#1", sk="PROFILE")

    assert user.pk == "USER#1"
    assert user.name is None
    assert user.age is None


def test_model_to_dict():
    """to_dict returns all non-None attributes."""
    user = User(pk="USER#1", sk="PROFILE", name="John", age=30)

    result = user.to_dict()

    assert result == {"pk": "USER#1", "sk": "PROFILE", "name": "John", "age": 30}


def test_model_to_dict_excludes_none():
    """to_dict excludes None values."""
    user = User(pk="USER#1", sk="PROFILE", name="John")

    result = user.to_dict()

    assert result == {"pk": "USER#1", "sk": "PROFILE", "name": "John"}
    assert "age" not in result


def test_model_from_dict():
    """from_dict creates a model instance."""
    data = {"pk": "USER#1", "sk": "PROFILE", "name": "John", "age": 30}

    user = User.from_dict(data)

    assert user.pk == "USER#1"
    assert user.sk == "PROFILE"
    assert user.name == "John"
    assert user.age == 30


def test_model_get_key():
    """_get_key returns the primary key dict."""
    user = User(pk="USER#1", sk="PROFILE", name="John")

    key = user._get_key()

    assert key == {"pk": "USER#1", "sk": "PROFILE"}


def test_model_repr():
    """__repr__ returns a readable string."""
    user = User(pk="USER#1", sk="PROFILE", name="John")

    result = repr(user)

    assert "User" in result
    assert "pk='USER#1'" in result
    assert "name='John'" in result


def test_model_equality():
    """Models are equal if they have the same key."""
    user1 = User(pk="USER#1", sk="PROFILE", name="John")
    user2 = User(pk="USER#1", sk="PROFILE", name="Jane")
    user3 = User(pk="USER#2", sk="PROFILE", name="John")

    assert user1 == user2  # Same key, different name
    assert user1 != user3  # Different key


@patch("pydynox.model.DynamoDBClient")
def test_model_get(mock_client_class):
    """Model.get fetches item from DynamoDB."""
    mock_client = MagicMock()
    mock_client.get_item.return_value = {
        "pk": "USER#1",
        "sk": "PROFILE",
        "name": "John",
        "age": 30,
    }
    mock_client_class.return_value = mock_client
    User._client = None  # Reset cached client

    user = User.get(pk="USER#1", sk="PROFILE")

    assert user is not None
    assert user.pk == "USER#1"
    assert user.name == "John"
    mock_client.get_item.assert_called_once_with("users", {"pk": "USER#1", "sk": "PROFILE"})


@patch("pydynox.model.DynamoDBClient")
def test_model_get_not_found(mock_client_class):
    """Model.get returns None when item not found."""
    mock_client = MagicMock()
    mock_client.get_item.return_value = None
    mock_client_class.return_value = mock_client
    User._client = None

    user = User.get(pk="USER#1", sk="PROFILE")

    assert user is None


@patch("pydynox.model.DynamoDBClient")
def test_model_save(mock_client_class):
    """Model.save puts item to DynamoDB."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    User._client = None

    user = User(pk="USER#1", sk="PROFILE", name="John", age=30)
    user.save()

    mock_client.put_item.assert_called_once_with(
        "users", {"pk": "USER#1", "sk": "PROFILE", "name": "John", "age": 30}
    )


@patch("pydynox.model.DynamoDBClient")
def test_model_delete(mock_client_class):
    """Model.delete removes item from DynamoDB."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    User._client = None

    user = User(pk="USER#1", sk="PROFILE", name="John")
    user.delete()

    mock_client.delete_item.assert_called_once_with("users", {"pk": "USER#1", "sk": "PROFILE"})


@patch("pydynox.model.DynamoDBClient")
def test_model_update(mock_client_class):
    """Model.update updates specific attributes."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    User._client = None

    user = User(pk="USER#1", sk="PROFILE", name="John", age=30)
    user.update(name="Jane", age=31)

    # Local instance updated
    assert user.name == "Jane"
    assert user.age == 31

    # DynamoDB updated
    mock_client.update_item.assert_called_once_with(
        "users", {"pk": "USER#1", "sk": "PROFILE"}, updates={"name": "Jane", "age": 31}
    )


@patch("pydynox.model.DynamoDBClient")
def test_model_update_unknown_attribute(mock_client_class):
    """Model.update raises error for unknown attributes."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    User._client = None

    user = User(pk="USER#1", sk="PROFILE", name="John")

    with pytest.raises(ValueError, match="Unknown attribute"):
        user.update(unknown_field="value")
