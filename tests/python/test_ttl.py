"""Tests for TTL helper classes."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from pydynox.attributes import ExpiresIn, StringAttribute, TTLAttribute
from pydynox.model import Model

# --- ExpiresIn tests ---


@pytest.mark.parametrize(
    "method,kwargs,expected_delta",
    [
        pytest.param("seconds", {"n": 30}, timedelta(seconds=30), id="30_seconds"),
        pytest.param("minutes", {"n": 15}, timedelta(minutes=15), id="15_minutes"),
        pytest.param("hours", {"n": 1}, timedelta(hours=1), id="1_hour"),
        pytest.param("days", {"n": 7}, timedelta(days=7), id="7_days"),
        pytest.param("weeks", {"n": 2}, timedelta(weeks=2), id="2_weeks"),
    ],
)
def test_expires_in_methods(method, kwargs, expected_delta):
    """ExpiresIn methods return correct datetime offset."""
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    with patch("pydynox.attributes.datetime") as mock_dt:
        mock_dt.now.return_value = now
        mock_dt.fromtimestamp = datetime.fromtimestamp

        result = getattr(ExpiresIn, method)(**kwargs)

    expected = now + expected_delta
    assert result == expected


def test_expires_in_returns_utc():
    """ExpiresIn returns datetime with UTC timezone."""
    result = ExpiresIn.hours(1)

    assert result.tzinfo == timezone.utc


# --- TTLAttribute tests ---


def test_ttl_attribute_type():
    """TTLAttribute has Number type for DynamoDB."""
    attr = TTLAttribute()

    assert attr.attr_type == "N"


def test_ttl_serialize():
    """TTLAttribute serializes datetime to epoch timestamp."""
    attr = TTLAttribute()
    dt = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

    result = attr.serialize(dt)

    assert result == int(dt.timestamp())
    assert isinstance(result, int)


def test_ttl_deserialize():
    """TTLAttribute deserializes epoch timestamp to datetime."""
    attr = TTLAttribute()
    timestamp = 1750075200  # 2025-06-16 12:00:00 UTC

    result = attr.deserialize(timestamp)

    assert isinstance(result, datetime)
    assert result.tzinfo == timezone.utc
    assert int(result.timestamp()) == timestamp


def test_ttl_roundtrip():
    """TTLAttribute serialize/deserialize roundtrip preserves value."""
    attr = TTLAttribute()
    original = datetime(2025, 6, 15, 12, 30, 45, tzinfo=timezone.utc)

    serialized = attr.serialize(original)
    deserialized = attr.deserialize(serialized)

    # Microseconds are lost in epoch conversion
    assert deserialized.replace(microsecond=0) == original.replace(microsecond=0)


# --- Model TTL integration tests ---


class Session(Model):
    """Test model with TTL."""

    class Meta:
        table = "sessions"

    pk = StringAttribute(hash_key=True)
    expires_at = TTLAttribute()


def test_model_is_expired_true():
    """is_expired returns True when TTL has passed."""
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    session = Session(pk="SESSION#1", expires_at=past)

    assert session.is_expired is True


def test_model_is_expired_false():
    """is_expired returns False when TTL has not passed."""
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    session = Session(pk="SESSION#1", expires_at=future)

    assert session.is_expired is False


def test_model_is_expired_no_ttl_attr():
    """is_expired returns False when model has no TTLAttribute."""

    class User(Model):
        class Meta:
            table = "users"

        pk = StringAttribute(hash_key=True)

    user = User(pk="USER#1")

    assert user.is_expired is False


def test_model_is_expired_none_value():
    """is_expired returns False when TTL value is None."""
    session = Session(pk="SESSION#1", expires_at=None)

    assert session.is_expired is False


def test_model_expires_in_returns_timedelta():
    """expires_in returns timedelta until expiration."""
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    session = Session(pk="SESSION#1", expires_at=future)

    result = session.expires_in

    assert isinstance(result, timedelta)
    # Allow 1 second tolerance for test execution time
    assert 3599 <= result.total_seconds() <= 3601


def test_model_expires_in_none_when_expired():
    """expires_in returns None when already expired."""
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    session = Session(pk="SESSION#1", expires_at=past)

    assert session.expires_in is None


def test_model_expires_in_none_when_no_ttl():
    """expires_in returns None when model has no TTLAttribute."""

    class User(Model):
        class Meta:
            table = "users"

        pk = StringAttribute(hash_key=True)

    user = User(pk="USER#1")

    assert user.expires_in is None


def test_model_extend_ttl_raises_without_ttl_attr():
    """extend_ttl raises ValueError when model has no TTLAttribute."""

    class User(Model):
        class Meta:
            table = "users"

        pk = StringAttribute(hash_key=True)

    user = User(pk="USER#1")

    with pytest.raises(ValueError, match="has no TTLAttribute"):
        user.extend_ttl(ExpiresIn.hours(1))


def test_model_to_dict_serializes_ttl():
    """to_dict serializes TTL datetime to epoch timestamp."""
    dt = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    session = Session(pk="SESSION#1", expires_at=dt)

    result = session.to_dict()

    assert result["expires_at"] == int(dt.timestamp())


def test_model_from_dict_deserializes_ttl():
    """from_dict deserializes epoch timestamp to datetime."""
    timestamp = 1750075200
    data = {"pk": "SESSION#1", "expires_at": timestamp}

    session = Session.from_dict(data)

    assert isinstance(session.expires_at, datetime)
    assert int(session.expires_at.timestamp()) == timestamp
