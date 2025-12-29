"""Attribute types for Model definitions."""

from datetime import datetime, timedelta, timezone
from typing import Any, Generic, Optional, TypeVar

T = TypeVar("T")

__all__ = [
    "Attribute",
    "StringAttribute",
    "NumberAttribute",
    "BooleanAttribute",
    "BinaryAttribute",
    "ListAttribute",
    "MapAttribute",
    "TTLAttribute",
    "ExpiresIn",
]


class Attribute(Generic[T]):
    """Base attribute class for Model fields.

    Attributes define the schema of a DynamoDB item. They can be marked
    as hash_key or range_key to define the table's primary key.

    Example:
        >>> class User(Model):
        ...     pk = StringAttribute(hash_key=True)
        ...     sk = StringAttribute(range_key=True)
        ...     name = StringAttribute()
        ...     age = NumberAttribute()
    """

    attr_type: str = "S"  # Default to string

    def __init__(
        self,
        hash_key: bool = False,
        range_key: bool = False,
        default: Optional[T] = None,
        null: bool = True,
    ):
        """Create an attribute.

        Args:
            hash_key: True if this is the partition key.
            range_key: True if this is the sort key.
            default: Default value when not provided.
            null: Whether None is allowed.
        """
        self.hash_key = hash_key
        self.range_key = range_key
        self.default = default
        self.null = null
        self.attr_name: Optional[str] = None

    def serialize(self, value: T) -> Any:
        """Convert Python value to DynamoDB format."""
        return value

    def deserialize(self, value: Any) -> T:
        """Convert DynamoDB value to Python format."""
        return value


class StringAttribute(Attribute[str]):
    """String attribute (DynamoDB type S)."""

    attr_type = "S"


class NumberAttribute(Attribute[float]):
    """Number attribute (DynamoDB type N).

    Stores both int and float values.
    """

    attr_type = "N"


class BooleanAttribute(Attribute[bool]):
    """Boolean attribute (DynamoDB type BOOL)."""

    attr_type = "BOOL"


class BinaryAttribute(Attribute[bytes]):
    """Binary attribute (DynamoDB type B)."""

    attr_type = "B"


class ListAttribute(Attribute[list]):
    """List attribute (DynamoDB type L)."""

    attr_type = "L"


class MapAttribute(Attribute[dict]):
    """Map attribute (DynamoDB type M)."""

    attr_type = "M"


class ExpiresIn:
    """Helper class to create TTL datetime values.

    Makes it easy to set expiration times without manual datetime math.

    Example:
        >>> from pydynox.attributes import ExpiresIn
        >>> expires = ExpiresIn.hours(1)  # 1 hour from now
        >>> expires = ExpiresIn.days(7)   # 7 days from now
    """

    @staticmethod
    def seconds(n: int) -> datetime:
        """Return datetime n seconds from now.

        Args:
            n: Number of seconds.

        Returns:
            datetime in UTC.
        """
        return datetime.now(timezone.utc) + timedelta(seconds=n)

    @staticmethod
    def minutes(n: int) -> datetime:
        """Return datetime n minutes from now.

        Args:
            n: Number of minutes.

        Returns:
            datetime in UTC.
        """
        return datetime.now(timezone.utc) + timedelta(minutes=n)

    @staticmethod
    def hours(n: int) -> datetime:
        """Return datetime n hours from now.

        Args:
            n: Number of hours.

        Returns:
            datetime in UTC.
        """
        return datetime.now(timezone.utc) + timedelta(hours=n)

    @staticmethod
    def days(n: int) -> datetime:
        """Return datetime n days from now.

        Args:
            n: Number of days.

        Returns:
            datetime in UTC.
        """
        return datetime.now(timezone.utc) + timedelta(days=n)

    @staticmethod
    def weeks(n: int) -> datetime:
        """Return datetime n weeks from now.

        Args:
            n: Number of weeks.

        Returns:
            datetime in UTC.
        """
        return datetime.now(timezone.utc) + timedelta(weeks=n)


class TTLAttribute(Attribute[datetime]):
    """TTL attribute for DynamoDB Time-To-Live.

    Stores datetime as epoch timestamp (number). DynamoDB uses this
    to auto-delete expired items.

    Example:
        >>> from pydynox import Model
        >>> from pydynox.attributes import StringAttribute, TTLAttribute, ExpiresIn
        >>>
        >>> class Session(Model):
        ...     class Meta:
        ...         table = "sessions"
        ...     pk = StringAttribute(hash_key=True)
        ...     expires_at = TTLAttribute()
        >>>
        >>> session = Session(pk="SESSION#123", expires_at=ExpiresIn.hours(1))
        >>> session.save()
    """

    attr_type = "N"

    def serialize(self, value: datetime) -> int:
        """Convert datetime to epoch timestamp.

        Args:
            value: datetime object.

        Returns:
            Unix timestamp as integer.
        """
        return int(value.timestamp())

    def deserialize(self, value: Any) -> datetime:
        """Convert epoch timestamp to datetime.

        Args:
            value: Unix timestamp (int or float).

        Returns:
            datetime object in UTC.
        """
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
