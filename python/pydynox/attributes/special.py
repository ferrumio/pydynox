"""Special attribute types (JSON, Enum, Datetime)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, TypeVar

from pydynox.attributes.base import Attribute

E = TypeVar("E", bound=Enum)


class JSONAttribute(Attribute[dict[str, Any] | list[Any]]):
    """Store dict/list as JSON string.

    Different from MapAttribute which uses DynamoDB's native Map type.
    JSONAttribute stores data as a string, which can be useful when you
    need to store complex nested structures or when you want to avoid
    DynamoDB's map limitations.

    Example:
        >>> from pydynox import Model, ModelConfig
        >>> from pydynox.attributes import StringAttribute, JSONAttribute
        >>>
        >>> class Config(Model):
        ...     model_config = ModelConfig(table="configs")
        ...     pk = StringAttribute(partition_key=True)
        ...     settings = JSONAttribute()
        >>>
        >>> config = Config(pk="CFG#1", settings={"theme": "dark", "notifications": True})
        >>> config.save()
        >>> # Stored as string '{"theme": "dark", "notifications": true}'
    """

    attr_type = "S"

    def serialize(self, value: dict[str, Any] | list[Any] | None) -> str | None:
        """Convert dict/list to JSON string.

        Args:
            value: Dict or list to serialize.

        Returns:
            JSON string or None.
        """
        if value is None:
            return None
        return json.dumps(value)

    def deserialize(self, value: Any) -> dict[str, Any] | list[Any] | None:
        """Convert JSON string back to dict/list.

        Args:
            value: JSON string from DynamoDB.

        Returns:
            Parsed dict/list or None.
        """
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return value
        result: dict[str, Any] | list[Any] = json.loads(value)
        return result


class EnumAttribute(Attribute[E], Generic[E]):
    """Store Python enum as string.

    Stores the enum's value (not name) in DynamoDB. On load, converts
    back to the enum type.

    Args:
        enum_class: The Enum class to use.
        partition_key: True if this is the partition key.
        sort_key: True if this is the sort key.
        default: Default enum value.
        required: Whether this field is required.

    Example:
        >>> from enum import Enum
        >>> from pydynox import Model, ModelConfig
        >>> from pydynox.attributes import StringAttribute, EnumAttribute
        >>>
        >>> class Status(Enum):
        ...     PENDING = "pending"
        ...     ACTIVE = "active"
        >>>
        >>> class User(Model):
        ...     model_config = ModelConfig(table="users")
        ...     pk = StringAttribute(partition_key=True)
        ...     status = EnumAttribute(Status, default=Status.PENDING)
        >>>
        >>> user = User(pk="USER#1", status=Status.ACTIVE)
        >>> user.save()
        >>> # Stored as "active", loaded as Status.ACTIVE
    """

    attr_type = "S"

    def __init__(
        self,
        enum_class: type[E],
        partition_key: bool = False,
        sort_key: bool = False,
        default: E | None = None,
        required: bool = False,
        alias: str | None = None,
    ):
        """Create an enum attribute.

        Args:
            enum_class: The Enum class to use.
            partition_key: True if this is the partition key.
            sort_key: True if this is the sort key.
            default: Default enum value.
            required: Whether this field is required.
            alias: DynamoDB attribute name override.
        """
        super().__init__(
            partition_key=partition_key,
            sort_key=sort_key,
            default=default,
            required=required,
            alias=alias,
        )
        self.enum_class = enum_class

    def serialize(self, value: E | None) -> str | None:
        """Convert enum to its string value.

        Args:
            value: Enum member.

        Returns:
            The enum's value as string.
        """
        if value is None:
            return None
        return str(value.value)

    def deserialize(self, value: Any) -> E | None:
        """Convert string back to enum.

        Args:
            value: String value from DynamoDB.

        Returns:
            Enum member.
        """
        if value is None:
            return None
        return self.enum_class(value)


class DatetimeAttribute(Attribute[datetime]):
    """Store datetime as ISO 8601 string.

    Stores datetime in ISO format which is sortable as a string.
    Naive datetimes (without timezone) are treated as UTC.

    Example:
        >>> from datetime import datetime, timezone
        >>> from pydynox import Model, ModelConfig
        >>> from pydynox.attributes import StringAttribute, DatetimeAttribute
        >>>
        >>> class Event(Model):
        ...     model_config = ModelConfig(table="events")
        ...     pk = StringAttribute(partition_key=True)
        ...     created_at = DatetimeAttribute()
        >>>
        >>> event = Event(pk="EVT#1", created_at=datetime.now(timezone.utc))
        >>> event.save()
        >>> # Stored as "2024-01-15T10:30:00+00:00"

    Note:
        For auto-set timestamps, use hooks:

        >>> from pydynox.hooks import before_save
        >>>
        >>> class Event(Model):
        ...     model_config = ModelConfig(table="events")
        ...     pk = StringAttribute(partition_key=True)
        ...     created_at = DatetimeAttribute(required=False)
        ...
        ...     @before_save
        ...     def set_created_at(self):
        ...         if self.created_at is None:
        ...             self.created_at = datetime.now(timezone.utc)
    """

    attr_type = "S"

    def serialize(self, value: datetime | None) -> str | None:
        """Convert datetime to ISO 8601 string.

        Args:
            value: datetime object.

        Returns:
            ISO format string.
        """
        if value is None:
            return None
        # Treat naive datetime as UTC
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()

    def deserialize(self, value: Any) -> datetime | None:
        """Convert ISO string back to datetime.

        Args:
            value: ISO format string from DynamoDB.

        Returns:
            datetime object.
        """
        if value is None:
            return None
        return datetime.fromisoformat(value)
