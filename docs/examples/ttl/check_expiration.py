"""Check expiration status."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute, TTLAttribute


class Session(Model):
    model_config = ModelConfig(table="sessions")
    pk = StringAttribute(partition_key=True)
    expires_at = TTLAttribute()


async def main():
    session = await Session.get(pk="SESSION#123")

    if session:
        # Check if expired
        if session.is_expired:
            print("Session has expired")
        else:
            # Get time remaining
            remaining = session.expires_in
            if remaining:
                hours = remaining.total_seconds() / 3600
                print(f"Session expires in {hours:.1f} hours")


asyncio.run(main())
