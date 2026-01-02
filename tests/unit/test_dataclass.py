"""Tests for dataclass integration."""

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest
from pydynox.integrations.dataclass import from_dataclass
from pydynox.integrations.functions import dynamodb_model


def test_decorator_adds_metadata():
    """Decorator adds pydynox metadata to the class."""

    @dynamodb_model(table="users", hash_key="pk", range_key="sk")
    @dataclass
    class User:
        pk: str
        sk: str
        name: str

    assert User._pydynox_table == "users"
    assert User._pydynox_hash_key == "pk"
    assert User._pydynox_range_key == "sk"


def test_decorator_adds_methods():
    """Decorator adds CRUD methods to the class."""

    @dynamodb_model(table="users", hash_key="pk")
    @dataclass
    class User:
        pk: str
        name: str

    assert hasattr(User, "get")
    assert hasattr(User, "save")
    assert hasattr(User, "delete")
    assert hasattr(User, "update")
    assert hasattr(User, "_get_key")
    assert hasattr(User, "_set_client")


def test_dataclass_still_works():
    """Dataclass still works normally."""

    @dynamodb_model(table="users", hash_key="pk", range_key="sk")
    @dataclass
    class User:
        pk: str
        sk: str
        name: str
        age: int = 0

    user = User(pk="USER#1", sk="PROFILE", name="John", age=30)

    assert user.pk == "USER#1"
    assert user.name == "John"
    assert user.age == 30


def test_get_key_returns_hash_and_range():
    """_get_key returns both hash and range key."""

    @dynamodb_model(table="users", hash_key="pk", range_key="sk")
    @dataclass
    class User:
        pk: str
        sk: str
        name: str

    user = User(pk="USER#1", sk="PROFILE", name="John")
    key = user._get_key()

    assert key == {"pk": "USER#1", "sk": "PROFILE"}


def test_get_fetches_from_dynamodb():
    """get() fetches item from DynamoDB and returns dataclass."""
    mock_client = MagicMock()
    mock_client.get_item.return_value = {
        "pk": "USER#1",
        "sk": "PROFILE",
        "name": "John",
        "age": 30,
    }

    @dynamodb_model(table="users", hash_key="pk", range_key="sk", client=mock_client)
    @dataclass
    class User:
        pk: str
        sk: str
        name: str
        age: int = 0

    user = User.get(pk="USER#1", sk="PROFILE")

    assert user is not None
    assert isinstance(user, User)
    assert user.pk == "USER#1"
    assert user.name == "John"
    mock_client.get_item.assert_called_once_with("users", {"pk": "USER#1", "sk": "PROFILE"})


def test_get_returns_none_when_not_found():
    """get() returns None when item not found."""
    mock_client = MagicMock()
    mock_client.get_item.return_value = None

    @dynamodb_model(table="users", hash_key="pk", range_key="sk", client=mock_client)
    @dataclass
    class User:
        pk: str
        sk: str
        name: str

    user = User.get(pk="USER#1", sk="PROFILE")

    assert user is None


def test_save_puts_to_dynamodb():
    """save() puts item to DynamoDB."""
    mock_client = MagicMock()

    @dynamodb_model(table="users", hash_key="pk", range_key="sk", client=mock_client)
    @dataclass
    class User:
        pk: str
        sk: str
        name: str
        age: int = 0

    user = User(pk="USER#1", sk="PROFILE", name="John", age=30)
    user.save()

    mock_client.put_item.assert_called_once_with(
        "users", {"pk": "USER#1", "sk": "PROFILE", "name": "John", "age": 30}
    )


def test_delete_removes_from_dynamodb():
    """delete() removes item from DynamoDB."""
    mock_client = MagicMock()

    @dynamodb_model(table="users", hash_key="pk", range_key="sk", client=mock_client)
    @dataclass
    class User:
        pk: str
        sk: str
        name: str

    user = User(pk="USER#1", sk="PROFILE", name="John")
    user.delete()

    mock_client.delete_item.assert_called_once_with("users", {"pk": "USER#1", "sk": "PROFILE"})


def test_update_updates_dynamodb():
    """update() updates item in DynamoDB."""
    mock_client = MagicMock()

    @dynamodb_model(table="users", hash_key="pk", range_key="sk", client=mock_client)
    @dataclass
    class User:
        pk: str
        sk: str
        name: str
        age: int = 0

    user = User(pk="USER#1", sk="PROFILE", name="John", age=30)
    user.update(name="Jane", age=31)

    # Local instance updated
    assert user.name == "Jane"
    assert user.age == 31

    # DynamoDB updated
    mock_client.update_item.assert_called_once_with(
        "users", {"pk": "USER#1", "sk": "PROFILE"}, updates={"name": "Jane", "age": 31}
    )


def test_from_dataclass_creates_model():
    """from_dataclass() creates a DynamoDB-enabled dataclass."""

    @dataclass
    class Product:
        pk: str
        name: str
        price: float

    ProductDB = from_dataclass(Product, table="products", hash_key="pk")

    assert ProductDB._pydynox_table == "products"
    assert ProductDB._pydynox_hash_key == "pk"
    assert hasattr(ProductDB, "save")


def test_decorator_requires_dataclass_or_pydantic():
    """Decorator raises error if class is not a dataclass or Pydantic model."""
    with pytest.raises(TypeError, match="must be a dataclass or Pydantic BaseModel"):

        @dynamodb_model(table="test", hash_key="id")
        class NotSupported:
            id: str


def test_hash_key_only_model():
    """Model with only hash key (no range key) works."""

    @dynamodb_model(table="simple", hash_key="id")
    @dataclass
    class SimpleModel:
        id: str
        data: str

    item = SimpleModel(id="123", data="test")
    key = item._get_key()

    assert key == {"id": "123"}


def test_set_client_after_creation():
    """_set_client() allows setting client after model creation."""

    @dynamodb_model(table="users", hash_key="pk")
    @dataclass
    class User:
        pk: str
        name: str

    mock_client = MagicMock()
    mock_client.get_item.return_value = {"pk": "USER#1", "name": "John"}

    User._set_client(mock_client)
    user = User.get(pk="USER#1")

    assert user is not None
    assert user.name == "John"


def test_no_client_raises_error():
    """Operations without client raise RuntimeError."""

    @dynamodb_model(table="users", hash_key="pk")
    @dataclass
    class User:
        pk: str
        name: str

    user = User(pk="USER#1", name="John")

    with pytest.raises(RuntimeError, match="No client set"):
        user.save()


def test_invalid_hash_key_raises_error():
    """Invalid hash_key raises ValueError."""
    with pytest.raises(ValueError, match="hash_key 'invalid' not found"):

        @dynamodb_model(table="test", hash_key="invalid")
        @dataclass
        class Model:
            pk: str


def test_invalid_range_key_raises_error():
    """Invalid range_key raises ValueError."""
    with pytest.raises(ValueError, match="range_key 'invalid' not found"):

        @dynamodb_model(table="test", hash_key="pk", range_key="invalid")
        @dataclass
        class Model:
            pk: str


def test_update_invalid_attribute_raises_error():
    """update() with invalid attribute raises AttributeError."""
    mock_client = MagicMock()

    @dynamodb_model(table="users", hash_key="pk", client=mock_client)
    @dataclass
    class User:
        pk: str
        name: str

    user = User(pk="USER#1", name="John")

    with pytest.raises(AttributeError, match="has no attribute 'invalid'"):
        user.update(invalid="value")
