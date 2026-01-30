import asyncio

from pydynox import AutoGenerate, Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class Event(Model):
    model_config = ModelConfig(table="events")

    # String IDs
    pk = StringAttribute(partition_key=True, default=AutoGenerate.ULID)
    event_id = StringAttribute(default=AutoGenerate.UUID4)
    trace_id = StringAttribute(default=AutoGenerate.KSUID)

    # Timestamps
    created_at = StringAttribute(default=AutoGenerate.ISO8601)
    timestamp = NumberAttribute(default=AutoGenerate.EPOCH)
    timestamp_ms = NumberAttribute(default=AutoGenerate.EPOCH_MS)

    sk = StringAttribute(sort_key=True)
    name = StringAttribute()


async def main():
    event = Event(sk="EVENT#DATA", name="UserSignup")
    await event.save()

    print(event.pk)  # "01HX5K3M2N4P5Q6R7S8T9UVWXY"
    print(event.event_id)  # "550e8400-e29b-41d4-a716-446655440000"
    print(event.trace_id)  # "2NxK3M4P5Q6R7S8T9UVWXYZabc"
    print(event.created_at)  # "2024-01-15T10:30:00Z"
    print(event.timestamp)  # 1705315800
    print(event.timestamp_ms)  # 1705315800123


asyncio.run(main())
