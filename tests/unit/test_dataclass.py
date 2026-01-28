"""Tests for dataclass integration."""

from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest
from pydynox.integrations.dataclass import from_dataclass
from pydynox.integrations.functions import dynamodb_model


def test_decorator_adds_metadata():
    """Decorator adds pydynox metadata to the class."""

    # GIVEN a dataclass decorated with dynamodb_model
    @dynamodb_model(table="users", hash_key="pk", range_key="sk")
    @dataclass
    class User:
        pk: str
        sk: str
        name: str

    # THEN pydynox metadata should be added
    assert User._pydynox_table == "users"
    assert User._pydynox_hash_key == "pk"
    assert User._pydynox_range_key == "sk"


def test_decorator_adds_methods():
    """Decorator adds CRUD methods to the class."""

    # GIVEN a dataclass decorated with dynamodb_model
    @dynamodb_model(table="users", hash_key="pk")
    @dataclass
    class User:
        pk: str
        name: str

    # THEN CRUD methods should be added
    assert hasattr(User, "get")
    assert hasattr(User, "save")
    assert hasattr(User, "delete")
    assert hasattr(User, "update")
    assert hasattr(User, "_get_key")
    assert hasattr(User, "_set_client")


def test_dataclass_still_works():
    """Dataclass still works normally."""

    # GIVEN a decorated dataclass
    @dynamodb_model(table="users", hash_key="pk", range_key="sk")
    @dataclass
    class User:
        pk: str
        sk: str
        name: str
        age: int = 0

    # WHEN we create an instance
    user = User(pk="USER#1", sk="PROFILE", name="John", age=30)

    # THEN dataclass behavior should work normally
    assert user.pk == "USER#1"
    assert user.name == "John"
    assert user.age == 30


def test_get_key_returns_hash_and_range():
    """_get_key returns both hash and range key."""

    # GIVEN a decorated dataclass with hash and range key
    @dynamodb_model(table="users", hash_key="pk", range_key="sk")
    @dataclass
    class User:
        pk: str
        sk: str
        name: str

    user = User(pk="USER#1", sk="PROFILE", name="John")

    # WHEN we get the key
    key = user._get_key()

    # THEN both keys should be returned
    assert key == {"pk": "USER#1", "sk": "PROFILE"}


def test_get_fetches_from_dynamodb():
    """sync_get() fetches item from DynamoDB and returns dataclass."""
    # GIVEN a mock client that returns user data
    mock_client = MagicMock()
    mock_client.sync_get_item.return_value = {
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

    # WHEN we call sync_get
    user = User.sync_get(pk="USER#1", sk="PROFILE")

    # THEN a dataclass instance should be returned with correct data
    assert user is not None
    assert isinstance(user, User)
    assert user.pk == "USER#1"
    assert user.name == "John"
    mock_client.sync_get_item.assert_called_once_with("users", {"pk": "USER#1", "sk": "PROFILE"})


def test_get_returns_none_when_not_found():
    """sync_get() returns None when item not found."""
    # GIVEN a mock client that returns None
    mock_client = MagicMock()
    mock_client.sync_get_item.return_value = None

    @dynamodb_model(table="users", hash_key="pk", range_key="sk", client=mock_client)
    @dataclass
    class User:
        pk: str
        sk: str
        name: str

    # WHEN we call sync_get for non-existent item
    user = User.sync_get(pk="USER#1", sk="PROFILE")

    # THEN None should be returned
    assert user is None


def test_save_puts_to_dynamodb():
    """sync_save() puts item to DynamoDB."""
    # GIVEN a mock client
    mock_client = MagicMock()

    @dynamodb_model(table="users", hash_key="pk", range_key="sk", client=mock_client)
    @dataclass
    class User:
        pk: str
        sk: str
        name: str
        age: int = 0

    user = User(pk="USER#1", sk="PROFILE", name="John", age=30)

    # WHEN we sync_save
    user.sync_save()

    # THEN sync_put_item should be called with correct data
    mock_client.sync_put_item.assert_called_once_with(
        "users", {"pk": "USER#1", "sk": "PROFILE", "name": "John", "age": 30}
    )


def test_delete_removes_from_dynamodb():
    """sync_delete() removes item from DynamoDB."""
    # GIVEN a mock client
    mock_client = MagicMock()

    @dynamodb_model(table="users", hash_key="pk", range_key="sk", client=mock_client)
    @dataclass
    class User:
        pk: str
        sk: str
        name: str

    user = User(pk="USER#1", sk="PROFILE", name="John")

    # WHEN we sync_delete
    user.sync_delete()

    # THEN sync_delete_item should be called with the key
    mock_client.sync_delete_item.assert_called_once_with("users", {"pk": "USER#1", "sk": "PROFILE"})


def test_update_updates_dynamodb():
    """sync_update() updates item in DynamoDB."""
    # GIVEN a mock client
    mock_client = MagicMock()

    @dynamodb_model(table="users", hash_key="pk", range_key="sk", client=mock_client)
    @dataclass
    class User:
        pk: str
        sk: str
        name: str
        age: int = 0

    user = User(pk="USER#1", sk="PROFILE", name="John", age=30)

    # WHEN we sync_update
    user.sync_update(name="Jane", age=31)

    # THEN local instance should be updated
    assert user.name == "Jane"
    assert user.age == 31

    # AND DynamoDB should be updated
    mock_client.sync_update_item.assert_called_once_with(
        "users", {"pk": "USER#1", "sk": "PROFILE"}, updates={"name": "Jane", "age": 31}
    )


def test_from_dataclass_creates_model():
    """from_dataclass() creates a DynamoDB-enabled dataclass."""

    # GIVEN a plain dataclass
    @dataclass
    class Product:
        pk: str
        name: str
        price: float

    # WHEN we call from_dataclass
    ProductDB = from_dataclass(Product, table="products", hash_key="pk")

    # THEN a DynamoDB-enabled class should be created
    assert ProductDB._pydynox_table == "products"
    assert ProductDB._pydynox_hash_key == "pk"
    assert hasattr(ProductDB, "save")


def test_decorator_requires_dataclass_or_pydantic():
    """Decorator raises error if class is not a dataclass or Pydantic model."""
    # WHEN we try to decorate a plain class
    # THEN TypeError should be raised
    with pytest.raises(TypeError, match="must be a dataclass or Pydantic BaseModel"):

        @dynamodb_model(table="test", hash_key="id")
        class NotSupported:
            id: str


def test_hash_key_only_model():
    """Model with only hash key (no range key) works."""

    # GIVEN a model with only hash key
    @dynamodb_model(table="simple", hash_key="id")
    @dataclass
    class SimpleModel:
        id: str
        data: str

    item = SimpleModel(id="123", data="test")

    # WHEN we get the key
    key = item._get_key()

    # THEN only hash key should be returned
    assert key == {"id": "123"}


def test_set_client_after_creation():
    """_set_client() allows setting client after model creation."""

    # GIVEN a model without client
    @dynamodb_model(table="users", hash_key="pk")
    @dataclass
    class User:
        pk: str
        name: str

    mock_client = MagicMock()
    mock_client.sync_get_item.return_value = {"pk": "USER#1", "name": "John"}

    # WHEN we set the client
    User._set_client(mock_client)
    user = User.sync_get(pk="USER#1")

    # THEN operations should work
    assert user is not None
    assert user.name == "John"


def test_no_client_raises_error():
    """Operations without client raise RuntimeError."""

    # GIVEN a model without client
    @dynamodb_model(table="users", hash_key="pk")
    @dataclass
    class User:
        pk: str
        name: str

    user = User(pk="USER#1", name="John")

    # WHEN we try to sync_save without client
    # THEN RuntimeError should be raised
    with pytest.raises(RuntimeError, match="No client set"):
        user.sync_save()


def test_invalid_hash_key_raises_error():
    """Invalid hash_key raises ValueError."""
    # WHEN we try to create a model with invalid hash_key
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="hash_key 'invalid' not found"):

        @dynamodb_model(table="test", hash_key="invalid")
        @dataclass
        class Model:
            pk: str


def test_invalid_range_key_raises_error():
    """Invalid range_key raises ValueError."""
    # WHEN we try to create a model with invalid range_key
    # THEN ValueError should be raised
    with pytest.raises(ValueError, match="range_key 'invalid' not found"):

        @dynamodb_model(table="test", hash_key="pk", range_key="invalid")
        @dataclass
        class Model:
            pk: str


def test_update_invalid_attribute_raises_error():
    """sync_update() with invalid attribute raises AttributeError."""
    # GIVEN a model with known attributes
    mock_client = MagicMock()

    @dynamodb_model(table="users", hash_key="pk", client=mock_client)
    @dataclass
    class User:
        pk: str
        name: str

    user = User(pk="USER#1", name="John")

    # WHEN we try to sync_update an invalid attribute
    # THEN AttributeError should be raised
    with pytest.raises(AttributeError, match="has no attribute 'invalid'"):
        user.sync_update(invalid="value")
