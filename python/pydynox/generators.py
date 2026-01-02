"""Auto-generate strategies for attribute values.

Use these strategies to auto-generate IDs and timestamps on save.

Example:
    >>> from pydynox import Model, ModelConfig
    >>> from pydynox.attributes import StringAttribute
    >>> from pydynox.generators import AutoGenerate
    >>>
    >>> class Order(Model):
    ...     model_config = ModelConfig(table="orders")
    ...     pk = StringAttribute(hash_key=True, default=AutoGenerate.ULID)
    ...     created_at = StringAttribute(default=AutoGenerate.ISO8601)
    >>>
    >>> order = Order()
    >>> order.save()
    >>> print(order.pk)  # "01ARZ3NDEKTSV4RRFFQ69G5FAV"
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydynox import pydynox_core


class AutoGenerate(Enum):
    """Auto-generate strategies for attribute values.

    Values are generated on save() if the attribute is None.

    Strategies:
        UUID4: Random UUID v4 string.
            Example: "550e8400-e29b-41d4-a716-446655440000"

        ULID: Universally Unique Lexicographically Sortable Identifier.
            Sortable by time. Good for partition keys.
            Example: "01ARZ3NDEKTSV4RRFFQ69G5FAV"

        KSUID: K-Sortable Unique Identifier.
            Sortable by time. 27 characters.
            Example: "0ujsswThIGTUYm2K8FjOOfXtY1K"

        EPOCH: Unix timestamp in seconds.
            Example: 1704067200

        EPOCH_MS: Unix timestamp in milliseconds.
            Example: 1704067200000

        ISO8601: ISO 8601 formatted timestamp.
            Example: "2024-01-01T00:00:00Z"

    Example:
        >>> from pydynox import Model, ModelConfig
        >>> from pydynox.attributes import StringAttribute, NumberAttribute
        >>> from pydynox.generators import AutoGenerate
        >>>
        >>> class Event(Model):
        ...     model_config = ModelConfig(table="events")
        ...     pk = StringAttribute(hash_key=True, default=AutoGenerate.ULID)
        ...     sk = StringAttribute(range_key=True, default=AutoGenerate.UUID4)
        ...     timestamp = NumberAttribute(default=AutoGenerate.EPOCH_MS)
        ...     created_at = StringAttribute(default=AutoGenerate.ISO8601)
        >>>
        >>> event = Event()
        >>> event.save()
        >>> # pk, sk, timestamp, created_at are all auto-generated
    """

    UUID4 = "uuid4"
    ULID = "ulid"
    KSUID = "ksuid"
    EPOCH = "epoch"
    EPOCH_MS = "epoch_ms"
    ISO8601 = "iso8601"


def generate_value(strategy: AutoGenerate) -> Any:
    """Generate a value using the given strategy.

    This is called internally by Model.save() when an attribute
    has an AutoGenerate default and the value is None.

    Args:
        strategy: The auto-generate strategy to use.

    Returns:
        The generated value (string or int depending on strategy).

    Raises:
        ValueError: If strategy is unknown.
    """
    if strategy == AutoGenerate.UUID4:
        return pydynox_core.generate_uuid4()
    elif strategy == AutoGenerate.ULID:
        return pydynox_core.generate_ulid()
    elif strategy == AutoGenerate.KSUID:
        return pydynox_core.generate_ksuid()
    elif strategy == AutoGenerate.EPOCH:
        return pydynox_core.generate_epoch()
    elif strategy == AutoGenerate.EPOCH_MS:
        return pydynox_core.generate_epoch_ms()
    elif strategy == AutoGenerate.ISO8601:
        return pydynox_core.generate_iso8601()
    else:
        raise ValueError(f"Unknown auto-generate strategy: {strategy}")


def is_auto_generate(value: Any) -> bool:
    """Check if a value is an AutoGenerate strategy.

    Args:
        value: The value to check.

    Returns:
        True if value is an AutoGenerate enum member.
    """
    return isinstance(value, AutoGenerate)
