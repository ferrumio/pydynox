from pydynox import Model
from pydynox.attributes import ExpiresIn, StringAttribute, TTLAttribute


class Session(Model):
    class Meta:
        table = "sessions"

    pk = StringAttribute(hash_key=True)
    user_id = StringAttribute()
    expires_at = TTLAttribute()


# Create session that expires in 1 hour
session = Session(
    pk="SESSION#123",
    user_id="USER#456",
    expires_at=ExpiresIn.hours(1),
)
session.save()

# Check if expired
if session.is_expired:
    print("Session expired")

# Get time remaining
remaining = session.expires_in
if remaining:
    print(f"Expires in {remaining.total_seconds()} seconds")

# Extend by 1 hour
session.extend_ttl(ExpiresIn.hours(1))
