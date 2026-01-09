"""TTL (Time To Live) helpers."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from pydynox.attributes.ttl import TTLAttribute

if TYPE_CHECKING:
    from pydynox.model import Model


def _get_ttl_attr_name(self: Model) -> str | None:
    """Get the name of the TTL attribute if defined."""
    for attr_name, attr in self._attributes.items():
        if isinstance(attr, TTLAttribute):
            return attr_name
    return None


def is_expired(self: Model) -> bool:
    """Check if the TTL has passed."""
    ttl_attr = self._get_ttl_attr_name()
    if ttl_attr is None:
        return False

    expires_at: datetime | None = getattr(self, ttl_attr, None)
    if expires_at is None:
        return False

    return bool(datetime.now(timezone.utc) > expires_at)


def expires_in(self: Model) -> timedelta | None:
    """Get time remaining until expiration."""
    ttl_attr = self._get_ttl_attr_name()
    if ttl_attr is None:
        return None

    expires_at: datetime | None = getattr(self, ttl_attr, None)
    if expires_at is None:
        return None

    remaining: timedelta = expires_at - datetime.now(timezone.utc)
    if remaining.total_seconds() < 0:
        return None

    return remaining


def extend_ttl(self: Model, new_expiration: datetime) -> None:
    """Extend the TTL to a new expiration time."""
    ttl_attr = self._get_ttl_attr_name()
    if ttl_attr is None:
        raise ValueError(f"Model {self.__class__.__name__} has no TTLAttribute")

    setattr(self, ttl_attr, new_expiration)

    client = self._get_client()
    table = self._get_table()
    key = self._get_key()
    # Serialize datetime to epoch timestamp for DynamoDB
    ttl_timestamp = int(new_expiration.timestamp())
    client.update_item(table, key, updates={ttl_attr: ttl_timestamp})
