"""Dataclass integration for pydynox.

Use Python dataclasses directly with DynamoDB.

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
"""

from __future__ import annotations

from dataclasses import asdict, fields, is_dataclass
from typing import TYPE_CHECKING, Any, TypeVar

from pydynox.integrations._base import add_dynamodb_methods

if TYPE_CHECKING:
    from pydynox.client import DynamoDBClient

T = TypeVar("T")

__all__ = ["from_dataclass"]


def from_dataclass(
    cls: type[T],
    table: str,
    partition_key: str,
    sort_key: str | None = None,
    client: DynamoDBClient | None = None,
) -> type[T]:
    """Add DynamoDB operations to a dataclass.

    Args:
        cls: The dataclass to enhance.
        table: DynamoDB table name.
        partition_key: Name of the hash key attribute.
        sort_key: Name of the range key attribute (optional).
        client: DynamoDBClient instance (optional).

    Returns:
        The dataclass with DynamoDB methods added.
    """
    if not is_dataclass(cls):
        raise TypeError(f"{cls.__name__} must be a dataclass")

    # Validate keys exist
    field_names = {f.name for f in fields(cls)}
    if partition_key not in field_names:
        raise ValueError(f"partition_key '{partition_key}' not found in dataclass fields")
    if sort_key and sort_key not in field_names:
        raise ValueError(f"sort_key '{sort_key}' not found in dataclass fields")

    def to_dict(instance: T) -> dict[str, Any]:
        return asdict(instance)  # type: ignore

    def from_dict(klass: type[T], data: dict[str, Any]) -> T:
        return klass(**data)

    return add_dynamodb_methods(cls, table, partition_key, sort_key, client, to_dict, from_dict)
