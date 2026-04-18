"""Special attribute types (JSON, Enum, Datetime)."""

from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Generic, TypeVar, overload

from pydynox.attributes.base import Attribute

E = TypeVar("E", bound=Enum)
J = TypeVar("J")


class JSONAttribute(Attribute[J], Generic[J]):
    """Store dict/list or typed model as JSON string.

    When used without a model class, stores plain dict/list as JSON.
    When used with a Pydantic model or dataclass, automatically handles
    serialization and deserialization to the typed model.

    Example:
        >>> from pydynox import Model, ModelConfig
        >>> from pydynox.attributes import StringAttribute, JSONAttribute
        >>>
        >>> # Plain dict/list (existing behavior)
        >>> class Config(Model):
        ...     model_config = ModelConfig(table="configs")
        ...     pk = StringAttribute(partition_key=True)
        ...     settings = JSONAttribute()
        >>>
        >>> # Typed with Pydantic model
        >>> from pydantic import BaseModel
        >>>
        >>> class Payload(BaseModel):
        ...     region: str
        ...     score: float
        >>>
        >>> class MyModel(Model):
        ...     model_config = ModelConfig(table="my_table")
        ...     pk = StringAttribute(partition_key=True)
        ...     payload = JSONAttribute(Payload)
    """

    attr_type = "S"

    @overload
    def __init__(
        self: JSONAttribute[dict[str, Any] | list[Any]],
        *,
        partition_key: bool = False,
        sort_key: bool = False,
        default: Any | None = None,
        required: bool = False,
        alias: str | None = None,
    ) -> None: ...

    @overload
    def __init__(
        self,
        model_class: type[J],
        *,
        partition_key: bool = False,
        sort_key: bool = False,
        default: J | None = None,
        required: bool = False,
        alias: str | None = None,
    ) -> None: ...

    def __init__(
        self,
        model_class: type[J] | None = None,
        *,
        partition_key: bool = False,
        sort_key: bool = False,
        default: Any | None = None,
        required: bool = False,
        alias: str | None = None,
    ):
        super().__init__(
            partition_key=partition_key,
            sort_key=sort_key,
            default=default,
            required=required,
            alias=alias,
        )
        self.model_class = model_class
        self._is_pydantic = model_class is not None and hasattr(model_class, "model_validate")
        self._is_dataclass = model_class is not None and dataclasses.is_dataclass(model_class)

    def _to_dict(self, value: Any) -> dict[str, Any] | list[Any]:
        """Convert a typed model instance to a dict for JSON serialization."""
        if self._is_pydantic:
            return value.model_dump()
        if self._is_dataclass:
            return dataclasses.asdict(value)
        return value

    def _from_dict(self, data: dict[str, Any]) -> Any:
        """Convert a dict to a typed model instance."""
        model_class = self.model_class
        if model_class is None:
            return data
        if self._is_pydantic:
            return model_class.model_validate(data)  # ty: ignore[unresolved-attribute]
        return model_class(**data)

    def serialize(self, value: Any | None) -> str | None:
        """Convert value to JSON string.

        For typed models, calls model_dump() or dataclasses.asdict() first.

        Args:
            value: Dict, list, or typed model instance to serialize.

        Returns:
            JSON string or None.
        """
        if value is None:
            return None
        if self.model_class is not None:
            return json.dumps(self._to_dict(value))
        return json.dumps(value)

    def deserialize(self, value: Any) -> Any | None:
        """Convert JSON string back to dict/list or typed model.

        For typed models, calls model_validate() or constructs from dict.

        Args:
            value: JSON string from DynamoDB.

        Returns:
            Parsed dict/list, typed model instance, or None.
        """
        if value is None:
            return None
        if isinstance(value, str):
            data = json.loads(value)
        elif isinstance(value, (dict, list)):
            data = value
        else:
            data = value
        if self.model_class is not None and isinstance(data, dict):
            return self._from_dict(data)
        return data


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
