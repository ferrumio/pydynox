"""DatetimeAttribute example - store datetime as ISO string."""

import asyncio
from datetime import datetime, timezone

from pydynox import Model, ModelConfig
from pydynox.attributes import DatetimeAttribute, StringAttribute


class Event(Model):
    model_config = ModelConfig(table="events")

    pk = StringAttribute(hash_key=True)
    created_at = DatetimeAttribute()


async def main():
    # Save with datetime
    event = Event(pk="EVT#1", created_at=datetime.now(timezone.utc))
    await event.save()
    # Stored as "2024-01-15T10:30:00+00:00"

    # Load it back - returns datetime object
    loaded = await Event.get(pk="EVT#1")
    print(loaded.created_at)  # datetime object
    print(loaded.created_at.year)  # 2024


asyncio.run(main())
