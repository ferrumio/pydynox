"""Tests for Pydantic integration."""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel, Field

from pydynox import dynamodb_model, from_pydantic


@dynamodb_model(table="users", hash_key="pk", range_key="sk")
class User(BaseModel):
    """Test model for users."""

    pk: str
    sk: str
    name: str
    age: int = 0


def test_decorator_adds_metadata():
    """Decorator adds pydynox metadata to the class."""
    assert User._pydynox_table == "users"
    assert User._pydynox_hash_key == "pk"
    assert User._pydynox_range_key == "sk"


def test_decorator_adds_methods():
    """Decorator adds CRUD methods to the class."""
    assert hasattr(User, "get")
    assert hasattr(User, "save")
    assert hasattr(User, "delete")
    assert hasattr(User, "update")
    assert hasattr(User, "_get_key")


def test_model_still_works_as_pydantic():
    """Model still works as a normal Pydantic model."""
    user = User(pk="USER#1", sk="PROFILE", name="John", age=30)

    assert user.pk == "USER#1"
    assert user.name == "John"
    assert user.age == 30

    # Pydantic methods still work
    data = user.model_dump()
    assert data == {"pk": "USER#1", "sk": "PROFILE", "name": "John", "age": 30}


def test_model_validates_with_pydantic():
    """Model validates data with Pydantic."""
    # age must be int
    with pytest.raises(Exception):  # Pydantic ValidationError
        User(pk="USER#1", sk="PROFILE", name="John", age="not a number")


def test_get_key_returns_hash_and_range():
    """_get_key returns both hash and range key."""
    user = User(pk="USER#1", sk="PROFILE", name="John")

    key = user._get_key()

    assert key == {"pk": "USER#1", "sk": "PROFILE"}


@patch("pydynox.pydantic_integration.DynamoDBClient")
def test_get_fetches_from_dynamodb(mock_client_class):
    """get() fetches item from DynamoDB and returns Pydantic model."""
    mock_client = MagicMock()
    mock_client.get_item.return_value = {
        "pk": "USER#1",
        "sk": "PROFILE",
        "name": "John",
        "age": 30,
    }
    mock_client_class.return_value = mock_client
    User._pydynox_client = None

    user = User.get(pk="USER#1", sk="PROFILE")

    assert user is not None
    assert isinstance(user, User)
    assert user.pk == "USER#1"
    assert user.name == "John"
    mock_client.get_item.assert_called_once_with("users", {"pk": "USER#1", "sk": "PROFILE"})


@patch("pydynox.pydantic_integration.DynamoDBClient")
def test_get_returns_none_when_not_found(mock_client_class):
    """get() returns None when item not found."""
    mock_client = MagicMock()
    mock_client.get_item.return_value = None
    mock_client_class.return_value = mock_client
    User._pydynox_client = None

    user = User.get(pk="USER#1", sk="PROFILE")

    assert user is None


@patch("pydynox.pydantic_integration.DynamoDBClient")
def test_save_puts_to_dynamodb(mock_client_class):
    """save() puts item to DynamoDB."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    User._pydynox_client = None

    user = User(pk="USER#1", sk="PROFILE", name="John", age=30)
    user.save()

    mock_client.put_item.assert_called_once_with(
        "users", {"pk": "USER#1", "sk": "PROFILE", "name": "John", "age": 30}
    )


@patch("pydynox.pydantic_integration.DynamoDBClient")
def test_delete_removes_from_dynamodb(mock_client_class):
    """delete() removes item from DynamoDB."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    User._pydynox_client = None

    user = User(pk="USER#1", sk="PROFILE", name="John")
    user.delete()

    mock_client.delete_item.assert_called_once_with("users", {"pk": "USER#1", "sk": "PROFILE"})


@patch("pydynox.pydantic_integration.DynamoDBClient")
def test_update_updates_dynamodb(mock_client_class):
    """update() updates item in DynamoDB."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    User._pydynox_client = None

    user = User(pk="USER#1", sk="PROFILE", name="John", age=30)
    user.update(name="Jane", age=31)

    # Local instance updated
    assert user.name == "Jane"
    assert user.age == 31

    # DynamoDB updated
    mock_client.update_item.assert_called_once_with(
        "users", {"pk": "USER#1", "sk": "PROFILE"}, updates={"name": "Jane", "age": 31}
    )


def test_from_pydantic_creates_model():
    """from_pydantic() creates a DynamoDB-enabled model."""

    class Product(BaseModel):
        pk: str
        name: str
        price: float

    ProductDB = from_pydantic(Product, table="products", hash_key="pk")

    assert ProductDB._pydynox_table == "products"
    assert ProductDB._pydynox_hash_key == "pk"
    assert hasattr(ProductDB, "save")


def test_decorator_requires_basemodel():
    """Decorator raises error if class is not a BaseModel."""
    with pytest.raises(TypeError, match="must be a Pydantic BaseModel"):

        @dynamodb_model(table="test", hash_key="id")
        class NotAModel:
            id: str


def test_hash_key_only_model():
    """Model with only hash key (no range key) works."""

    @dynamodb_model(table="simple", hash_key="id")
    class SimpleModel(BaseModel):
        id: str
        data: str

    item = SimpleModel(id="123", data="test")
    key = item._get_key()

    assert key == {"id": "123"}


def test_pydantic_field_validation():
    """Pydantic Field validation still works."""

    @dynamodb_model(table="validated", hash_key="id")
    class ValidatedModel(BaseModel):
        id: str
        age: int = Field(ge=0, le=150)

    # Valid
    item = ValidatedModel(id="1", age=30)
    assert item.age == 30

    # Invalid - age too high
    with pytest.raises(Exception):
        ValidatedModel(id="1", age=200)
