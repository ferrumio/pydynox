"""TTL (Time-To-Live) attribute types."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from pydynox.attributes.base import Attribute


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
        >>> from pydynox import Model, ModelConfig
        >>> from pydynox.attributes import StringAttribute, TTLAttribute, ExpiresIn
        >>>
        >>> class Session(Model):
        ...     model_config = ModelConfig(table="sessions")
        ...     pk = StringAttribute(partition_key=True)
        ...     expires_at = TTLAttribute()
        >>>
        >>> session = Session(pk="SESSION#123", expires_at=ExpiresIn.hours(1))
        >>> session.save()
    """

    attr_type = "N"

    def serialize(self, value: datetime | None) -> int | None:
        """Convert datetime to epoch timestamp.

        Args:
            value: datetime object.

        Returns:
            Unix timestamp as integer.
        """
        if value is None:
            return None
        return int(value.timestamp())

    def deserialize(self, value: Any) -> datetime:
        """Convert epoch timestamp to datetime.

        Args:
            value: Unix timestamp (int or float).

        Returns:
            datetime object in UTC.
        """
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
