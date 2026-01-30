"""Tests for TTL helper classes."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import ExpiresIn, StringAttribute, TTLAttribute


@pytest.fixture
def mock_client():
    """Create a mock DynamoDB client."""
    return MagicMock()


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

    with patch("pydynox.attributes.ttl.datetime") as mock_dt:
        mock_dt.now.return_value = now
        mock_dt.fromtimestamp = datetime.fromtimestamp

        result = getattr(ExpiresIn, method)(**kwargs)

    expected = now + expected_delta
    assert result == expected


def test_expires_in_returns_utc():
    """ExpiresIn returns datetime with UTC timezone."""
    # WHEN calling ExpiresIn.hours
    result = ExpiresIn.hours(1)

    # THEN result has UTC timezone
    assert result.tzinfo == timezone.utc


# --- TTLAttribute tests ---


def test_ttl_attribute_type():
    """TTLAttribute has Number type for DynamoDB."""
    # WHEN creating a TTLAttribute
    attr = TTLAttribute()

    # THEN it has Number type
    assert attr.attr_type == "N"


def test_ttl_serialize():
    """TTLAttribute serializes datetime to epoch timestamp."""
    # GIVEN a TTLAttribute and a datetime
    attr = TTLAttribute()
    dt = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

    # WHEN serializing
    result = attr.serialize(dt)

    # THEN it returns an integer epoch timestamp
    assert result == int(dt.timestamp())
    assert isinstance(result, int)


def test_ttl_deserialize():
    """TTLAttribute deserializes epoch timestamp to datetime."""
    # GIVEN a TTLAttribute and an epoch timestamp
    attr = TTLAttribute()
    timestamp = 1750075200  # 2025-06-16 12:00:00 UTC

    # WHEN deserializing
    result = attr.deserialize(timestamp)

    # THEN it returns a UTC datetime
    assert isinstance(result, datetime)
    assert result.tzinfo == timezone.utc
    assert int(result.timestamp()) == timestamp


def test_ttl_roundtrip():
    """TTLAttribute serialize/deserialize roundtrip preserves value."""
    # GIVEN a TTLAttribute and a datetime
    attr = TTLAttribute()
    original = datetime(2025, 6, 15, 12, 30, 45, tzinfo=timezone.utc)

    # WHEN serializing and deserializing
    serialized = attr.serialize(original)
    deserialized = attr.deserialize(serialized)

    # THEN value is preserved (microseconds are lost in epoch conversion)
    assert deserialized.replace(microsecond=0) == original.replace(microsecond=0)


# --- Model TTL integration tests ---


def test_model_is_expired_true(mock_client):
    """is_expired returns True when TTL has passed."""

    # GIVEN a model with TTL in the past
    class Session(Model):
        model_config = ModelConfig(table="sessions", client=mock_client)
        pk = StringAttribute(partition_key=True)
        expires_at = TTLAttribute()

    past = datetime.now(timezone.utc) - timedelta(hours=1)
    session = Session(pk="SESSION#1", expires_at=past)

    # THEN is_expired returns True
    assert session.is_expired is True


def test_model_is_expired_false(mock_client):
    """is_expired returns False when TTL has not passed."""

    # GIVEN a model with TTL in the future
    class Session(Model):
        model_config = ModelConfig(table="sessions", client=mock_client)
        pk = StringAttribute(partition_key=True)
        expires_at = TTLAttribute()

    future = datetime.now(timezone.utc) + timedelta(hours=1)
    session = Session(pk="SESSION#1", expires_at=future)

    # THEN is_expired returns False
    assert session.is_expired is False


def test_model_is_expired_no_ttl_attr(mock_client):
    """is_expired returns False when model has no TTLAttribute."""

    # GIVEN a model without TTLAttribute
    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(partition_key=True)

    user = User(pk="USER#1")

    # THEN is_expired returns False
    assert user.is_expired is False


def test_model_is_expired_none_value(mock_client):
    """is_expired returns False when TTL value is None."""

    # GIVEN a model with TTL set to None
    class Session(Model):
        model_config = ModelConfig(table="sessions", client=mock_client)
        pk = StringAttribute(partition_key=True)
        expires_at = TTLAttribute()

    session = Session(pk="SESSION#1", expires_at=None)

    # THEN is_expired returns False
    assert session.is_expired is False


def test_model_expires_in_returns_timedelta(mock_client):
    """expires_in returns timedelta until expiration."""

    # GIVEN a model with TTL 1 hour in the future
    class Session(Model):
        model_config = ModelConfig(table="sessions", client=mock_client)
        pk = StringAttribute(partition_key=True)
        expires_at = TTLAttribute()

    future = datetime.now(timezone.utc) + timedelta(hours=1)
    session = Session(pk="SESSION#1", expires_at=future)

    # WHEN getting expires_in
    result = session.expires_in

    # THEN it returns a timedelta of about 1 hour
    assert isinstance(result, timedelta)
    # Allow 1 second tolerance for test execution time
    assert 3599 <= result.total_seconds() <= 3601


def test_model_expires_in_none_when_expired(mock_client):
    """expires_in returns None when already expired."""

    # GIVEN a model with TTL in the past
    class Session(Model):
        model_config = ModelConfig(table="sessions", client=mock_client)
        pk = StringAttribute(partition_key=True)
        expires_at = TTLAttribute()

    past = datetime.now(timezone.utc) - timedelta(hours=1)
    session = Session(pk="SESSION#1", expires_at=past)

    # THEN expires_in returns None
    assert session.expires_in is None


def test_model_expires_in_none_when_no_ttl(mock_client):
    """expires_in returns None when model has no TTLAttribute."""

    # GIVEN a model without TTLAttribute
    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(partition_key=True)

    user = User(pk="USER#1")

    # THEN expires_in returns None
    assert user.expires_in is None


def test_model_extend_ttl_raises_without_ttl_attr(mock_client):
    """extend_ttl raises ValueError when model has no TTLAttribute."""

    # GIVEN a model without TTLAttribute
    class User(Model):
        model_config = ModelConfig(table="users", client=mock_client)
        pk = StringAttribute(partition_key=True)

    user = User(pk="USER#1")

    # WHEN calling extend_ttl
    # THEN ValueError is raised
    with pytest.raises(ValueError, match="has no TTLAttribute"):
        user.extend_ttl(ExpiresIn.hours(1))


def test_model_to_dict_serializes_ttl(mock_client):
    """to_dict serializes TTL datetime to epoch timestamp."""

    # GIVEN a model with TTL datetime
    class Session(Model):
        model_config = ModelConfig(table="sessions", client=mock_client)
        pk = StringAttribute(partition_key=True)
        expires_at = TTLAttribute()

    dt = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
    session = Session(pk="SESSION#1", expires_at=dt)

    # WHEN calling to_dict
    result = session.to_dict()

    # THEN TTL is serialized to epoch timestamp
    assert result["expires_at"] == int(dt.timestamp())


def test_model_from_dict_deserializes_ttl(mock_client):
    """from_dict deserializes epoch timestamp to datetime."""

    # GIVEN a dict with epoch timestamp
    class Session(Model):
        model_config = ModelConfig(table="sessions", client=mock_client)
        pk = StringAttribute(partition_key=True)
        expires_at = TTLAttribute()

    timestamp = 1750075200
    data = {"pk": "SESSION#1", "expires_at": timestamp}

    # WHEN calling from_dict
    session = Session.from_dict(data)

    # THEN TTL is deserialized to datetime
    assert isinstance(session.expires_at, datetime)
    assert int(session.expires_at.timestamp()) == timestamp
