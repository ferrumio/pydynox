"""Tests for Pydantic integration."""

from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel, Field
from pydynox.integrations.pydantic import dynamodb_model, from_pydantic


def test_decorator_adds_metadata():
    """Decorator adds pydynox metadata to the class."""

    # GIVEN a Pydantic model decorated with dynamodb_model
    @dynamodb_model(table="users", hash_key="pk", range_key="sk")
    class User(BaseModel):
        pk: str
        sk: str
        name: str

    # THEN pydynox metadata should be added
    assert User._pydynox_table == "users"
    assert User._pydynox_hash_key == "pk"
    assert User._pydynox_range_key == "sk"


def test_decorator_adds_methods():
    """Decorator adds CRUD methods to the class."""

    # GIVEN a decorated Pydantic model
    @dynamodb_model(table="users", hash_key="pk")
    class User(BaseModel):
        pk: str
        name: str

    # THEN CRUD methods should be added
    assert hasattr(User, "get")
    assert hasattr(User, "save")
    assert hasattr(User, "delete")
    assert hasattr(User, "update")
    assert hasattr(User, "_get_key")
    assert hasattr(User, "_set_client")


def test_model_still_works_as_pydantic():
    """Model still works as a normal Pydantic model."""

    # GIVEN a decorated Pydantic model
    @dynamodb_model(table="users", hash_key="pk", range_key="sk")
    class User(BaseModel):
        pk: str
        sk: str
        name: str
        age: int = 0

    # WHEN we create an instance
    user = User(pk="USER#1", sk="PROFILE", name="John", age=30)

    # THEN Pydantic behavior should work normally
    assert user.pk == "USER#1"
    assert user.name == "John"
    assert user.age == 30

    # AND Pydantic methods still work
    data = user.model_dump()
    assert data == {"pk": "USER#1", "sk": "PROFILE", "name": "John", "age": 30}


def test_model_validates_with_pydantic():
    """Model validates data with Pydantic."""

    # GIVEN a decorated Pydantic model with int field
    @dynamodb_model(table="users", hash_key="pk", range_key="sk")
    class User(BaseModel):
        pk: str
        sk: str
        name: str
        age: int = 0

    # WHEN we try to create with invalid type
    # THEN Pydantic ValidationError should be raised
    with pytest.raises(Exception):
        User(pk="USER#1", sk="PROFILE", name="John", age="not a number")


def test_get_key_returns_hash_and_range():
    """_get_key returns both hash and range key."""

    # GIVEN a decorated model with hash and range key
    @dynamodb_model(table="users", hash_key="pk", range_key="sk")
    class User(BaseModel):
        pk: str
        sk: str
        name: str

    user = User(pk="USER#1", sk="PROFILE", name="John")

    # WHEN we get the key
    key = user._get_key()

    # THEN both keys should be returned
    assert key == {"pk": "USER#1", "sk": "PROFILE"}


def test_get_fetches_from_dynamodb():
    """get() fetches item from DynamoDB and returns Pydantic model."""
    # GIVEN a mock client that returns user data
    mock_client = MagicMock()
    mock_client.get_item.return_value = {
        "pk": "USER#1",
        "sk": "PROFILE",
        "name": "John",
        "age": 30,
    }

    @dynamodb_model(table="users", hash_key="pk", range_key="sk", client=mock_client)
    class User(BaseModel):
        pk: str
        sk: str
        name: str
        age: int = 0

    # WHEN we call get
    user = User.get(pk="USER#1", sk="PROFILE")

    # THEN a Pydantic model instance should be returned
    assert user is not None
    assert isinstance(user, User)
    assert user.pk == "USER#1"
    assert user.name == "John"
    mock_client.get_item.assert_called_once_with("users", {"pk": "USER#1", "sk": "PROFILE"})


def test_get_returns_none_when_not_found():
    """get() returns None when item not found."""
    # GIVEN a mock client that returns None
    mock_client = MagicMock()
    mock_client.get_item.return_value = None

    @dynamodb_model(table="users", hash_key="pk", range_key="sk", client=mock_client)
    class User(BaseModel):
        pk: str
        sk: str
        name: str

    # WHEN we call get for non-existent item
    user = User.get(pk="USER#1", sk="PROFILE")

    # THEN None should be returned
    assert user is None


def test_save_puts_to_dynamodb():
    """save() puts item to DynamoDB."""
    # GIVEN a mock client
    mock_client = MagicMock()

    @dynamodb_model(table="users", hash_key="pk", range_key="sk", client=mock_client)
    class User(BaseModel):
        pk: str
        sk: str
        name: str
        age: int = 0

    user = User(pk="USER#1", sk="PROFILE", name="John", age=30)

    # WHEN we save
    user.save()

    # THEN put_item should be called with correct data
    mock_client.put_item.assert_called_once_with(
        "users", {"pk": "USER#1", "sk": "PROFILE", "name": "John", "age": 30}
    )


def test_delete_removes_from_dynamodb():
    """delete() removes item from DynamoDB."""
    # GIVEN a mock client
    mock_client = MagicMock()

    @dynamodb_model(table="users", hash_key="pk", range_key="sk", client=mock_client)
    class User(BaseModel):
        pk: str
        sk: str
        name: str

    user = User(pk="USER#1", sk="PROFILE", name="John")

    # WHEN we delete
    user.delete()

    # THEN delete_item should be called with the key
    mock_client.delete_item.assert_called_once_with("users", {"pk": "USER#1", "sk": "PROFILE"})


def test_update_updates_dynamodb():
    """update() updates item in DynamoDB."""
    # GIVEN a mock client
    mock_client = MagicMock()

    @dynamodb_model(table="users", hash_key="pk", range_key="sk", client=mock_client)
    class User(BaseModel):
        pk: str
        sk: str
        name: str
        age: int = 0

    user = User(pk="USER#1", sk="PROFILE", name="John", age=30)

    # WHEN we update
    user.update(name="Jane", age=31)

    # THEN local instance should be updated
    assert user.name == "Jane"
    assert user.age == 31

    # AND DynamoDB should be updated
    mock_client.update_item.assert_called_once_with(
        "users", {"pk": "USER#1", "sk": "PROFILE"}, updates={"name": "Jane", "age": 31}
    )


def test_from_pydantic_creates_model():
    """from_pydantic() creates a DynamoDB-enabled model."""

    # GIVEN a plain Pydantic model
    class Product(BaseModel):
        pk: str
        name: str
        price: float

    # WHEN we call from_pydantic
    ProductDB = from_pydantic(Product, table="products", hash_key="pk")

    # THEN a DynamoDB-enabled class should be created
    assert ProductDB._pydynox_table == "products"
    assert ProductDB._pydynox_hash_key == "pk"
    assert hasattr(ProductDB, "save")


def test_decorator_requires_basemodel():
    """Decorator raises error if class is not a BaseModel."""
    # WHEN we try to decorate a non-BaseModel class
    # THEN TypeError should be raised
    with pytest.raises(TypeError, match="must be a Pydantic BaseModel"):

        @dynamodb_model(table="test", hash_key="id")
        class NotAModel:
            id: str


def test_hash_key_only_model():
    """Model with only hash key (no range key) works."""

    # GIVEN a model with only hash key
    @dynamodb_model(table="simple", hash_key="id")
    class SimpleModel(BaseModel):
        id: str
        data: str

    item = SimpleModel(id="123", data="test")

    # WHEN we get the key
    key = item._get_key()

    # THEN only hash key should be returned
    assert key == {"id": "123"}


def test_pydantic_field_validation():
    """Pydantic Field validation still works."""

    # GIVEN a model with Field validation
    @dynamodb_model(table="validated", hash_key="id")
    class ValidatedModel(BaseModel):
        id: str
        age: int = Field(ge=0, le=150)

    # WHEN we create with valid data
    item = ValidatedModel(id="1", age=30)
    assert item.age == 30

    # THEN invalid data should raise
    with pytest.raises(Exception):
        ValidatedModel(id="1", age=200)


def test_set_client_after_creation():
    """_set_client() allows setting client after model creation."""

    # GIVEN a model without client
    @dynamodb_model(table="users", hash_key="pk")
    class User(BaseModel):
        pk: str
        name: str

    mock_client = MagicMock()
    mock_client.get_item.return_value = {"pk": "USER#1", "name": "John"}

    # WHEN we set the client
    User._set_client(mock_client)
    user = User.get(pk="USER#1")

    # THEN operations should work
    assert user is not None
    assert user.name == "John"


def test_no_client_raises_error():
    """Operations without client raise RuntimeError."""

    # GIVEN a model without client
    @dynamodb_model(table="users", hash_key="pk")
    class User(BaseModel):
        pk: str
        name: str

    user = User(pk="USER#1", name="John")

    # WHEN we try to save without client
    # THEN RuntimeError should be raised
    with pytest.raises(RuntimeError, match="No client set"):
        user.save()
