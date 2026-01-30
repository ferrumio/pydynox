"""Unified dynamodb_model decorator for pydynox.

Works with both Pydantic models and dataclasses.

Example:
    >>> from pydynox import DynamoDBClient, dynamodb_model
    >>> from dataclasses import dataclass
    >>> from pydantic import BaseModel
    >>>
    >>> client = DynamoDBClient(region="us-east-1")
    >>>
    >>> # With dataclass
    >>> @dynamodb_model(table="users", partition_key="pk", client=client)
    ... @dataclass
    ... class User:
    ...     pk: str
    ...     name: str
    >>>
    >>> # With Pydantic
    >>> @dynamodb_model(table="products", partition_key="pk", client=client)
    ... class Product(BaseModel):
    ...     pk: str
    ...     name: str
"""

from __future__ import annotations

from dataclasses import is_dataclass
from typing import TYPE_CHECKING, Any, TypeVar

if TYPE_CHECKING:
    from pydynox.client import DynamoDBClient

T = TypeVar("T")

__all__ = ["dynamodb_model"]


def dynamodb_model(
    table: str,
    partition_key: str,
    sort_key: str | None = None,
    client: DynamoDBClient | None = None,
) -> Any:
    """Decorator to add DynamoDB operations to a Pydantic model or dataclass.

    Automatically detects whether the class is a Pydantic model or dataclass
    and applies the right integration.

    Args:
        table: DynamoDB table name.
        partition_key: Name of the hash key attribute.
        sort_key: Name of the range key attribute (optional).
        client: DynamoDBClient instance (optional for Pydantic, required for dataclass).

    Returns:
        A decorator that adds DynamoDB methods to the class.

    Example:
        >>> from pydynox import DynamoDBClient, dynamodb_model
        >>> from dataclasses import dataclass
        >>>
        >>> client = DynamoDBClient(region="us-east-1")
        >>>
        >>> @dynamodb_model(table="users", partition_key="pk", client=client)
        ... @dataclass
        ... class User:
        ...     pk: str
        ...     name: str
        >>>
        >>> user = User(pk="USER#1", name="John")
        >>> user.save()
        >>>
        >>> user = User.get(pk="USER#1")
    """

    def decorator(cls: type[T]) -> type[T]:
        if is_dataclass(cls):
            from pydynox.integrations.dataclass import from_dataclass

            return from_dataclass(cls, table, partition_key, sort_key, client)

        # Check if Pydantic model
        try:
            from pydantic import BaseModel

            if issubclass(cls, BaseModel):
                from pydynox.integrations.pydantic import from_pydantic

                return from_pydantic(cls, table, partition_key, sort_key, client)
        except ImportError:
            pass

        raise TypeError(
            f"{cls.__name__} must be a dataclass or Pydantic BaseModel. "
            "Use @dataclass decorator or inherit from BaseModel."
        )

    return decorator
