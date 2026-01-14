"""Testing TTL with pydynox_memory_backend."""

from datetime import datetime, timedelta, timezone

from pydynox import Model, ModelConfig
from pydynox.attributes import ExpiresIn, StringAttribute, TTLAttribute


class Session(Model):
    model_config = ModelConfig(table="sessions")
    pk = StringAttribute(hash_key=True)
    user_id = StringAttribute()
    expires_at = TTLAttribute()


def test_create_session_with_ttl(pydynox_memory_backend):
    """Test creating a session with TTL."""
    session = Session(
        pk="SESSION#123",
        user_id="USER#1",
        expires_at=ExpiresIn.hours(1),
    )
    session.save()

    found = Session.get(pk="SESSION#123")
    assert found is not None
    assert found.user_id == "USER#1"
    assert found.expires_at is not None


def test_session_not_expired(pydynox_memory_backend):
    """Test that session is not expired."""
    session = Session(
        pk="SESSION#123",
        user_id="USER#1",
        expires_at=ExpiresIn.hours(1),
    )
    session.save()

    found = Session.get(pk="SESSION#123")
    assert not found.is_expired


def test_session_expired(pydynox_memory_backend):
    """Test that session is expired."""
    # Create session that expired 1 hour ago
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    session = Session(
        pk="SESSION#123",
        user_id="USER#1",
        expires_at=past,
    )
    session.save()

    found = Session.get(pk="SESSION#123")
    assert found.is_expired


def test_expires_in_helper(pydynox_memory_backend):
    """Test ExpiresIn helper methods."""
    now = datetime.now(timezone.utc)

    # Test various durations
    assert ExpiresIn.seconds(30) > now
    assert ExpiresIn.minutes(5) > now
    assert ExpiresIn.hours(1) > now
    assert ExpiresIn.days(7) > now
    assert ExpiresIn.weeks(2) > now
