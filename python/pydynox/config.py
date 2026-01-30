"""Model configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pydynox.client import DynamoDBClient


# Global default client
_default_client: DynamoDBClient | None = None


def set_default_client(client: "DynamoDBClient") -> None:
    """Set the default client for all models.

    Call this once at app startup. All models without an explicit client
    will use this one.

    Args:
        client: The DynamoDBClient to use as default.

    Example:
        >>> from pydynox import DynamoDBClient, set_default_client
        >>> client = DynamoDBClient(region="us-east-1", profile="prod")
        >>> set_default_client(client)
    """
    global _default_client
    _default_client = client


def get_default_client() -> DynamoDBClient | None:
    """Get the default client.

    Returns:
        The default client if set, None otherwise.

    Example:
        >>> from pydynox import get_default_client
        >>> client = get_default_client()
        >>> if client:
        ...     print(client.get_region())
    """
    return _default_client


def clear_default_client() -> None:
    """Clear the default client.

    Useful for testing to reset state between tests.
    """
    global _default_client
    _default_client = None


@dataclass
class ModelConfig:
    """Type-safe model configuration.

    Use this instead of class Meta for better IDE support and type checking.

    Args:
        table: DynamoDB table name (required).
        client: DynamoDBClient to use. If None, uses the default client.
        skip_hooks: Skip lifecycle hooks by default (default: False).
        max_size: Max item size in bytes. If set, validates before save.
        consistent_read: Use strongly consistent reads by default (default: False).
            Strongly consistent reads cost 2x RCU but always return latest data.
        hot_partition_writes: Override writes threshold for hot partition detection.
            If set, overrides the client's detector threshold for this model.
        hot_partition_reads: Override reads threshold for hot partition detection.
            If set, overrides the client's detector threshold for this model.

    Example:
        >>> from pydynox import DynamoDBClient, Model, ModelConfig
        >>> from pydynox.attributes import StringAttribute
        >>>
        >>> client = DynamoDBClient(region="us-east-1")
        >>>
        >>> class User(Model):
        ...     model_config = ModelConfig(
        ...         table="users",
        ...         client=client,
        ...     )
        ...     pk = StringAttribute(partition_key=True)
        ...     name = StringAttribute()
        >>>
        >>> # Model with higher hot partition thresholds (high traffic expected)
        >>> class Event(Model):
        ...     model_config = ModelConfig(
        ...         table="events",
        ...         hot_partition_writes=2000,
        ...         hot_partition_reads=5000,
        ...     )
        ...     pk = StringAttribute(partition_key=True)
    """

    table: str
    client: DynamoDBClient | None = field(default=None)
    skip_hooks: bool = field(default=False)
    max_size: int | None = field(default=None)
    consistent_read: bool = field(default=False)
    hot_partition_writes: int | None = field(default=None)
    hot_partition_reads: int | None = field(default=None)
