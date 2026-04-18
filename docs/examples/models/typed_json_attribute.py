"""Typed JSONAttribute example - store Pydantic or dataclass as JSON."""

import asyncio
import dataclasses

from pydynox import Model, ModelConfig
from pydynox.attributes import JSONAttribute, StringAttribute


@dataclasses.dataclass
class Payload:
    region: str
    score: float


class Event(Model):
    model_config = ModelConfig(table="events")

    pk = StringAttribute(partition_key=True)
    payload = JSONAttribute(Payload)


async def main():
    # Save with a typed model
    event = Event(pk="EVT#1", payload=Payload(region="us-east-1", score=0.95))
    await event.save()
    # Stored as '{"region": "us-east-1", "score": 0.95}'

    # Load it back - returns the dataclass, not a dict
    loaded = await Event.get(pk="EVT#1")
    print(loaded.payload.region)  # "us-east-1"
    print(loaded.payload.score)  # 0.95

    # In-place mutations are detected on save
    loaded.payload.score = 0.99
    await loaded.save()  # Detects change and saves


asyncio.run(main())
