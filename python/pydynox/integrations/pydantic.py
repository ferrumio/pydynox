"""Pydantic integration for pydynox.

Use Pydantic models directly with DynamoDB.

Example:
    >>> from pydynox import DynamoDBClient, dynamodb_model
    >>> from pydantic import BaseModel
    >>>
    >>> client = DynamoDBClient(region="us-east-1")
    >>>
    >>> @dynamodb_model(table="users", partition_key="pk", client=client)
    ... class User(BaseModel):
    ...     pk: str
    ...     name: str
    >>>
    >>> user = User(pk="USER#1", name="John")
    >>> user.save()
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar

from pydynox.integrations._base import add_dynamodb_methods

if TYPE_CHECKING:
    from pydynox.client import DynamoDBClient

try:
    from pydantic import BaseModel
except ImportError:
    BaseModel = None  # type: ignore

T = TypeVar("T")

__all__ = ["dynamodb_model", "from_pydantic"]


def _check_pydantic() -> None:
    """Check if pydantic is installed."""
    if BaseModel is None:
        raise ImportError(
            "pydantic is required for this feature. Install it with: pip install pydynox[pydantic]"
        )


def dynamodb_model(
    table: str,
    partition_key: str,
    sort_key: str | None = None,
    client: DynamoDBClient | None = None,
) -> Any:
    """Decorator to add DynamoDB operations to a Pydantic model.

    Args:
        table: DynamoDB table name.
        partition_key: Name of the hash key attribute.
        sort_key: Name of the range key attribute (optional).
        client: DynamoDBClient instance (optional).

    Returns:
        A decorator that adds DynamoDB methods to the class.
    """
    _check_pydantic()

    def decorator(cls: type[T]) -> type[T]:
        return from_pydantic(cls, table, partition_key, sort_key, client)

    return decorator


def from_pydantic(
    cls: type[T],
    table: str,
    partition_key: str,
    sort_key: str | None = None,
    client: DynamoDBClient | None = None,
) -> type[T]:
    """Add DynamoDB operations to a Pydantic model.

    Args:
        cls: The Pydantic model class.
        table: DynamoDB table name.
        partition_key: Name of the hash key attribute.
        sort_key: Name of the range key attribute (optional).
        client: DynamoDBClient instance (optional).

    Returns:
        The model class with DynamoDB methods added.
    """
    _check_pydantic()

    if not issubclass(cls, BaseModel):
        raise TypeError(f"{cls.__name__} must be a Pydantic BaseModel subclass")

    def to_dict(instance: T) -> dict[str, Any]:
        return instance.model_dump()  # type: ignore

    def from_dict(klass: type[T], data: dict[str, Any]) -> T:
        return klass.model_validate(data)  # type: ignore

    def validate_update(instance: T, updates: dict[str, Any]) -> dict[str, Any]:
        current = instance.model_dump()  # type: ignore
        current.update(updates)
        validated = instance.__class__.model_validate(current)  # type: ignore
        return {k: getattr(validated, k) for k in updates}

    return add_dynamodb_methods(
        cls, table, partition_key, sort_key, client, to_dict, from_dict, validate_update
    )
