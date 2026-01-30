"""Base functionality for integrations.

Shared code between Pydantic and dataclass integrations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, TypeVar

if TYPE_CHECKING:
    from pydynox.client import DynamoDBClient

T = TypeVar("T")


def add_dynamodb_methods(
    cls: type[T],
    table: str,
    partition_key: str,
    sort_key: str | None,
    client: DynamoDBClient | None,
    to_dict: Callable[[T], dict[str, Any]],
    from_dict: Callable[[type[T], dict[str, Any]], T],
    validate_update: Callable[[T, dict[str, Any]], dict[str, Any]] | None = None,
) -> type[T]:
    """Add DynamoDB methods to a class.

    Args:
        cls: The class to enhance.
        table: DynamoDB table name.
        partition_key: Name of the hash key attribute.
        sort_key: Name of the range key attribute (optional).
        client: DynamoDBClient instance (optional).
        to_dict: Function to convert instance to dict.
        from_dict: Function to create instance from dict.
        validate_update: Optional function to validate updates (for Pydantic).

    Returns:
        The class with DynamoDB methods added.
    """
    # Store metadata
    cls._pydynox_table = table  # type: ignore
    cls._pydynox_partition_key = partition_key  # type: ignore
    cls._pydynox_sort_key = sort_key  # type: ignore
    cls._pydynox_client = client  # type: ignore
    cls._pydynox_to_dict = staticmethod(to_dict)  # type: ignore
    cls._pydynox_from_dict = staticmethod(from_dict)  # type: ignore
    cls._pydynox_validate_update = staticmethod(validate_update) if validate_update else None  # type: ignore

    # Add methods - async-first pattern
    cls._get_client = classmethod(_get_client_method)  # type: ignore
    cls._set_client = classmethod(_set_client_method)  # type: ignore
    cls._get_key = _get_key_method  # type: ignore

    # Async methods (default)
    cls.get = classmethod(_get_method)  # type: ignore
    cls.save = _save_method  # type: ignore
    cls.delete = _delete_method  # type: ignore
    cls.update = _update_method  # type: ignore

    # Sync methods (prefixed)
    cls.sync_get = classmethod(_sync_get_method)  # type: ignore
    cls.sync_save = _sync_save_method  # type: ignore
    cls.sync_delete = _sync_delete_method  # type: ignore
    cls.sync_update = _sync_update_method  # type: ignore

    return cls


def _get_client_method(cls: type[T]) -> "DynamoDBClient":
    """Get the DynamoDB client."""
    if cls._pydynox_client is None:  # type: ignore
        raise RuntimeError(
            f"No client set for {cls.__name__}. "
            "Pass client= to dynamodb_model() or call _set_client()."
        )
    return cls._pydynox_client  # type: ignore


def _set_client_method(cls: type[T], client: "DynamoDBClient") -> None:
    """Set the DynamoDB client."""
    cls._pydynox_client = client  # type: ignore


async def _get_method(cls: type[T], **keys: Any) -> T | None:
    """Get an item from DynamoDB by its key (async)."""
    client = cls._get_client()  # type: ignore
    item = await client.get_item(cls._pydynox_table, keys)  # type: ignore
    if item is None:
        return None
    return cls._pydynox_from_dict(cls, item)  # type: ignore


def _sync_get_method(cls: type[T], **keys: Any) -> T | None:
    """Get an item from DynamoDB by its key (sync)."""
    client = cls._get_client()  # type: ignore
    item = client.sync_get_item(cls._pydynox_table, keys)  # type: ignore
    if item is None:
        return None
    return cls._pydynox_from_dict(cls, item)  # type: ignore


async def _save_method(self: T) -> None:
    """Save to DynamoDB (async)."""
    client = self.__class__._get_client()  # type: ignore
    item = self.__class__._pydynox_to_dict(self)  # type: ignore
    await client.put_item(self.__class__._pydynox_table, item)  # type: ignore


def _sync_save_method(self: T) -> None:
    """Save to DynamoDB (sync)."""
    client = self.__class__._get_client()  # type: ignore
    item = self.__class__._pydynox_to_dict(self)  # type: ignore
    client.sync_put_item(self.__class__._pydynox_table, item)  # type: ignore


async def _delete_method(self: T) -> None:
    """Delete from DynamoDB (async)."""
    client = self.__class__._get_client()  # type: ignore
    key = self._get_key()  # type: ignore
    await client.delete_item(self.__class__._pydynox_table, key)  # type: ignore


def _sync_delete_method(self: T) -> None:
    """Delete from DynamoDB (sync)."""
    client = self.__class__._get_client()  # type: ignore
    key = self._get_key()  # type: ignore
    client.sync_delete_item(self.__class__._pydynox_table, key)  # type: ignore


async def _update_method(self: T, **kwargs: Any) -> None:
    """Update specific attributes (async)."""
    cls = self.__class__

    # Validate if validator provided (Pydantic)
    if cls._pydynox_validate_update:  # type: ignore
        validated = cls._pydynox_validate_update(self, kwargs)  # type: ignore
        for attr_name, value in kwargs.items():
            setattr(self, attr_name, validated.get(attr_name, value))
    else:
        # Simple update (dataclass)
        for attr_name, value in kwargs.items():
            if not hasattr(self, attr_name):
                raise AttributeError(f"'{cls.__name__}' has no attribute '{attr_name}'")
            setattr(self, attr_name, value)

    # Update in DynamoDB
    client = cls._get_client()  # type: ignore
    key = self._get_key()  # type: ignore
    await client.update_item(cls._pydynox_table, key, updates=kwargs)  # type: ignore


def _sync_update_method(self: T, **kwargs: Any) -> None:
    """Update specific attributes (sync)."""
    cls = self.__class__

    # Validate if validator provided (Pydantic)
    if cls._pydynox_validate_update:  # type: ignore
        validated = cls._pydynox_validate_update(self, kwargs)  # type: ignore
        for attr_name, value in kwargs.items():
            setattr(self, attr_name, validated.get(attr_name, value))
    else:
        # Simple update (dataclass)
        for attr_name, value in kwargs.items():
            if not hasattr(self, attr_name):
                raise AttributeError(f"'{cls.__name__}' has no attribute '{attr_name}'")
            setattr(self, attr_name, value)

    # Update in DynamoDB
    client = cls._get_client()  # type: ignore
    key = self._get_key()  # type: ignore
    client.sync_update_item(cls._pydynox_table, key, updates=kwargs)  # type: ignore


def _get_key_method(self: T) -> dict[str, Any]:
    """Get the key dict for this instance."""
    cls = self.__class__
    key = {cls._pydynox_partition_key: getattr(self, cls._pydynox_partition_key)}  # type: ignore
    if cls._pydynox_sort_key:  # type: ignore
        key[cls._pydynox_sort_key] = getattr(self, cls._pydynox_sort_key)  # type: ignore
    return key
