from uuid import uuid4

from pydynox import Model, ModelConfig
from pydynox.attributes import ExpiresIn, StringAttribute, TTLAttribute


class Session(Model):
    model_config = ModelConfig(table="sessions")

    pk = StringAttribute(hash_key=True)
    user_id = StringAttribute()
    expires_at = TTLAttribute()


def create_session(user_id: str) -> Session:
    """Create a session that expires in 24 hours."""
    session = Session(
        pk=f"SESSION#{uuid4()}",
        user_id=user_id,
        expires_at=ExpiresIn.hours(24),
    )
    session.save()
    return session


def validate_session(session_id: str) -> bool:
    """Check if session is valid."""
    session = Session.get(pk=session_id)
    if not session or session.is_expired:
        return False
    return True


def refresh_session(session_id: str) -> None:
    """Extend session by 24 hours."""
    session = Session.get(pk=session_id)
    if session and not session.is_expired:
        session.extend_ttl(ExpiresIn.hours(24))
