"""Pydantic integration for pydynox.

Use Pydantic models directly with DynamoDB without redefining your schema.

Example:
    >>> from pydynox import dynamodb_model
    >>> from pydantic import BaseModel
    >>>
    >>> @dynamodb_model(table="users", hash_key="pk", range_key="sk")
    ... class User(BaseModel):
    ...     pk: str
    ...     sk: str
    ...     name: str
    ...     age: int = 0
    >>>
    >>> user = User(pk="USER#1", sk="PROFILE", name="John", age=30)
    >>> user.save()
    >>>
    >>> user = User.get(pk="USER#1", sk="PROFILE")
"""

from typing import Any, Optional, Type, TypeVar

try:
    from pydantic import BaseModel
except ImportError:
    BaseModel = None  # type: ignore

from .client import DynamoDBClient

T = TypeVar("T")


def _check_pydantic() -> None:
    """Check if pydantic is installed."""
    if BaseModel is None:
        raise ImportError(
            "pydantic is required for this feature. Install it with: pip install pydynox[pydantic]"
        )


def dynamodb_model(
    table: str,
    hash_key: str,
    range_key: Optional[str] = None,
    region: Optional[str] = None,
    endpoint_url: Optional[str] = None,
):
    """Decorator to add DynamoDB operations to a Pydantic model.

    Args:
        table: DynamoDB table name.
        hash_key: Name of the hash key attribute.
        range_key: Name of the range key attribute (optional).
        region: AWS region (optional).
        endpoint_url: Custom endpoint URL for local testing (optional).

    Returns:
        A decorator that adds DynamoDB methods to the class.

    Example:
        >>> @dynamodb_model(table="users", hash_key="pk", range_key="sk")
        ... class User(BaseModel):
        ...     pk: str
        ...     sk: str
        ...     name: str
        ...     age: int = 0
        >>>
        >>> user = User(pk="USER#1", sk="PROFILE", name="John")
        >>> user.save()
        >>>
        >>> user = User.get(pk="USER#1", sk="PROFILE")
    """
    _check_pydantic()

    def decorator(cls: Type[T]) -> Type[T]:
        if not issubclass(cls, BaseModel):
            raise TypeError(f"{cls.__name__} must be a Pydantic BaseModel subclass")

        # Store metadata
        cls._pydynox_table = table  # type: ignore
        cls._pydynox_hash_key = hash_key  # type: ignore
        cls._pydynox_range_key = range_key  # type: ignore
        cls._pydynox_region = region  # type: ignore
        cls._pydynox_endpoint_url = endpoint_url  # type: ignore
        cls._pydynox_client = None  # type: ignore

        # Add methods
        cls._get_client = classmethod(_get_client_method)  # type: ignore
        cls.get = classmethod(_get_method)  # type: ignore
        cls.save = _save_method
        cls.delete = _delete_method
        cls.update = _update_method
        cls._get_key = _get_key_method

        return cls

    return decorator


def _get_client_method(cls: Type[T]) -> DynamoDBClient:
    """Get or create the DynamoDB client."""
    if cls._pydynox_client is None:  # type: ignore
        cls._pydynox_client = DynamoDBClient(  # type: ignore
            region=cls._pydynox_region,  # type: ignore
            endpoint_url=cls._pydynox_endpoint_url,  # type: ignore
        )
    return cls._pydynox_client  # type: ignore


def _get_method(cls: Type[T], **keys: Any) -> Optional[T]:
    """Get an item from DynamoDB by its key.

    Args:
        **keys: The key attributes (hash_key and optional range_key).

    Returns:
        The model instance if found, None otherwise.
    """
    client = cls._get_client()  # type: ignore
    item = client.get_item(cls._pydynox_table, keys)  # type: ignore
    if item is None:
        return None
    return cls.model_validate(item)


def _save_method(self: T) -> None:
    """Save the model to DynamoDB.

    Validates with Pydantic before saving.
    """
    client = self.__class__._get_client()  # type: ignore
    item = self.model_dump()  # type: ignore
    client.put_item(self.__class__._pydynox_table, item)  # type: ignore


def _delete_method(self: T) -> None:
    """Delete the model from DynamoDB."""
    client = self.__class__._get_client()  # type: ignore
    key = self._get_key()  # type: ignore
    client.delete_item(self.__class__._pydynox_table, key)  # type: ignore


def _update_method(self: T, **kwargs: Any) -> None:
    """Update specific attributes on the model.

    Updates both the local instance and DynamoDB.

    Args:
        **kwargs: Attribute values to update.
    """
    # Validate new values with Pydantic
    current_data = self.model_dump()  # type: ignore
    current_data.update(kwargs)
    validated = self.__class__.model_validate(current_data)  # type: ignore

    # Update local instance
    for attr_name, value in kwargs.items():
        setattr(self, attr_name, getattr(validated, attr_name))

    # Update in DynamoDB
    client = self.__class__._get_client()  # type: ignore
    key = self._get_key()  # type: ignore
    client.update_item(self.__class__._pydynox_table, key, updates=kwargs)  # type: ignore


def _get_key_method(self: T) -> dict[str, Any]:
    """Get the key dict for this instance."""
    cls = self.__class__
    key = {cls._pydynox_hash_key: getattr(self, cls._pydynox_hash_key)}  # type: ignore
    if cls._pydynox_range_key:  # type: ignore
        key[cls._pydynox_range_key] = getattr(self, cls._pydynox_range_key)  # type: ignore
    return key


def from_pydantic(
    model_class: Type[T],
    table: str,
    hash_key: str,
    range_key: Optional[str] = None,
    region: Optional[str] = None,
    endpoint_url: Optional[str] = None,
) -> Type[T]:
    """Create a DynamoDB-enabled model from a Pydantic model.

    This is an alternative to the @dynamodb_model decorator.

    Args:
        model_class: The Pydantic model class.
        table: DynamoDB table name.
        hash_key: Name of the hash key attribute.
        range_key: Name of the range key attribute (optional).
        region: AWS region (optional).
        endpoint_url: Custom endpoint URL for local testing (optional).

    Returns:
        The model class with DynamoDB methods added.

    Example:
        >>> class User(BaseModel):
        ...     pk: str
        ...     sk: str
        ...     name: str
        >>>
        >>> UserDB = from_pydantic(User, table="users", hash_key="pk", range_key="sk")
        >>> user = UserDB(pk="USER#1", sk="PROFILE", name="John")
        >>> user.save()
    """
    return dynamodb_model(
        table=table,
        hash_key=hash_key,
        range_key=range_key,
        region=region,
        endpoint_url=endpoint_url,
    )(model_class)
