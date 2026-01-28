import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import ExpiresIn, StringAttribute, TTLAttribute


class Session(Model):
    model_config = ModelConfig(table="sessions")

    pk = StringAttribute(hash_key=True)
    user_id = StringAttribute()
    expires_at = TTLAttribute()


async def main():
    # Create session that expires in 1 hour
    session = Session(
        pk="SESSION#123",
        user_id="USER#456",
        expires_at=ExpiresIn.hours(1),
    )
    await session.save()

    # Check if expired
    if session.is_expired:
        print("Session expired")

    # Get time remaining
    remaining = session.expires_in
    if remaining:
        print(f"Expires in {remaining.total_seconds()} seconds")

    # Extend by 1 hour (sync method - updates TTL in DynamoDB)
    session.extend_ttl(ExpiresIn.hours(1))


asyncio.run(main())
