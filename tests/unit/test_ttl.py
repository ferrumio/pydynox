"""Tests for TTL helper classes."""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from pydynox import Model, ModelConfig
from pydynox.attributes import ExpiresIn, StringAttribute, TTLAttribute
from pydynox.testing import MemoryBackend


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


# --- extend_ttl alias and failure-path tests ---


def test_extend_ttl_aliased_ttl(mock_client):
    """extend_ttl writes to the DynamoDB alias and updates the instance."""

    # GIVEN a model with an aliased TTL attribute
    class Session(Model):
        model_config = ModelConfig(table="sessions", client=mock_client)
        pk = StringAttribute(partition_key=True)
        expires_at = TTLAttribute(alias="ttl")

    original_expiry = datetime(2030, 1, 1, tzinfo=timezone.utc)
    new_expiry = datetime(2031, 1, 1, tzinfo=timezone.utc)
    session = Session(pk="S1", expires_at=original_expiry)

    # WHEN extending the TTL
    session.extend_ttl(new_expiry)

    # THEN the update uses the alias and the instance holds the new value
    mock_client.sync_update_item.assert_called_once()
    updates = mock_client.sync_update_item.call_args.kwargs["updates"]
    assert updates == {"ttl": int(new_expiry.timestamp())}
    assert session.expires_at == new_expiry


def test_extend_ttl_aliased_key_and_ttl(mock_client):
    """extend_ttl maps both the aliased partition key and the aliased TTL field."""

    # GIVEN a model with aliased key and TTL attributes
    class Session(Model):
        model_config = ModelConfig(table="sessions", client=mock_client)
        session_id = StringAttribute(partition_key=True, alias="sid")
        expires_at = TTLAttribute(alias="ttl")

    new_expiry = datetime(2031, 1, 1, tzinfo=timezone.utc)
    session = Session(
        session_id="S1",
        expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
    )

    # WHEN extending the TTL
    session.extend_ttl(new_expiry)

    # THEN the key and the update both use their DynamoDB aliases
    mock_client.sync_update_item.assert_called_once()
    call = mock_client.sync_update_item.call_args
    assert call.args[0] == "sessions"
    assert call.args[1] == {"sid": "S1"}
    assert call.kwargs["updates"] == {"ttl": int(new_expiry.timestamp())}


def test_extend_ttl_unaliased(mock_client):
    """extend_ttl keeps the Python name when no alias is defined."""

    # GIVEN a model with an unaliased TTL attribute
    class Session(Model):
        model_config = ModelConfig(table="sessions", client=mock_client)
        pk = StringAttribute(partition_key=True)
        expires_at = TTLAttribute()

    new_expiry = datetime(2031, 1, 1, tzinfo=timezone.utc)
    session = Session(pk="S1", expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc))

    # WHEN extending the TTL
    session.extend_ttl(new_expiry)

    # THEN the update uses the Python name and the instance holds the new value
    mock_client.sync_update_item.assert_called_once()
    updates = mock_client.sync_update_item.call_args.kwargs["updates"]
    assert updates == {"expires_at": int(new_expiry.timestamp())}
    assert session.expires_at == new_expiry


def test_extend_ttl_failure_does_not_update_instance(mock_client):
    """extend_ttl leaves the instance unchanged when the write fails."""

    # GIVEN a model whose update call will fail
    class Session(Model):
        model_config = ModelConfig(table="sessions", client=mock_client)
        pk = StringAttribute(partition_key=True)
        expires_at = TTLAttribute(alias="ttl")

    original_expiry = datetime(2030, 1, 1, tzinfo=timezone.utc)
    new_expiry = datetime(2031, 1, 1, tzinfo=timezone.utc)
    session = Session(pk="S1", expires_at=original_expiry)
    mock_client.sync_update_item.side_effect = RuntimeError("boom")

    # WHEN the write fails
    # THEN the error propagates and the instance keeps the old value
    with pytest.raises(RuntimeError, match="boom"):
        session.extend_ttl(new_expiry)

    assert session.expires_at == original_expiry


def test_extend_ttl_issue_repro():
    """extend_ttl updates the aliased TTL field stored in the backend."""

    # GIVEN a saved model with an aliased TTL attribute
    class Session(Model):
        model_config = ModelConfig(table="sessions")
        pk = StringAttribute(partition_key=True)
        expires_at = TTLAttribute(alias="ttl")

    with MemoryBackend() as backend:
        original_expiry = datetime(2030, 1, 1, tzinfo=timezone.utc)
        session = Session(pk="SESSION#1", expires_at=original_expiry)
        session.sync_save()

        # WHEN extending the TTL
        new_expiry = datetime(2031, 1, 1, tzinfo=timezone.utc)
        session.extend_ttl(new_expiry)

        # THEN the stored aliased field holds the new timestamp
        stored = backend.client.sync_get_item("sessions", {"pk": "SESSION#1"})

    assert stored["ttl"] == int(new_expiry.timestamp())
    assert "expires_at" not in stored


def test_extend_ttl_roundtrip():
    """extend_ttl persists the aliased field and the model reads it back."""

    # GIVEN a saved model with an aliased TTL attribute
    class Session(Model):
        model_config = ModelConfig(table="sessions")
        pk = StringAttribute(partition_key=True)
        expires_at = TTLAttribute(alias="ttl")

    with MemoryBackend() as backend:
        original_expiry = datetime(2030, 1, 1, tzinfo=timezone.utc)
        session = Session(pk="S1", expires_at=original_expiry)
        session.sync_save()

        # WHEN extending the TTL
        new_expiry = datetime(2031, 1, 1, tzinfo=timezone.utc)
        session.extend_ttl(new_expiry)

        # THEN the raw stored field is the aliased one with the new timestamp
        stored = backend.client.sync_get_item("sessions", {"pk": "S1"})
        assert stored["ttl"] == int(new_expiry.timestamp())
        assert "expires_at" not in stored

        # AND the model reads the new value back
        loaded = Session.sync_get(pk="S1")

    assert loaded is not None
    assert loaded.expires_at == new_expiry


def test_extend_ttl_naive_datetime_matches_timestamp(mock_client):
    """extend_ttl serializes naive datetimes exactly like int(dt.timestamp())."""

    # GIVEN a model with an aliased TTL attribute and a naive datetime
    class Session(Model):
        model_config = ModelConfig(table="sessions", client=mock_client)
        pk = StringAttribute(partition_key=True)
        expires_at = TTLAttribute(alias="ttl")

    naive_expiry = datetime(2031, 1, 1, 12, 0, 0)
    session = Session(pk="S1", expires_at=datetime(2030, 1, 1, tzinfo=timezone.utc))

    # WHEN extending the TTL with the naive datetime
    session.extend_ttl(naive_expiry)

    # THEN the serialized value matches the old int(dt.timestamp()) behavior
    updates = mock_client.sync_update_item.call_args.kwargs["updates"]
    assert list(updates.values()) == [int(naive_expiry.timestamp())]
