"""Extend TTL example."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import ExpiresIn, StringAttribute, TTLAttribute


class Session(Model):
    model_config = ModelConfig(table="sessions")
    pk = StringAttribute(hash_key=True)
    expires_at = TTLAttribute()


async def main():
    session = await Session.get(pk="SESSION#123")

    if session and not session.is_expired:
        # Extend by 1 hour from now (sync method)
        session.extend_ttl(ExpiresIn.hours(1))
        print("Session extended")


asyncio.run(main())
