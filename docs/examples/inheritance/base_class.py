import asyncio
from datetime import datetime, timezone

from pydynox import Model, ModelConfig
from pydynox.attributes import DatetimeAttribute, StringAttribute


# Base class with shared attributes
class TimestampBase:
    created_at = DatetimeAttribute()
    updated_at = DatetimeAttribute()


# Models inherit from both Model and the base class
class User(Model, TimestampBase):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    name = StringAttribute()


class Product(Model, TimestampBase):
    model_config = ModelConfig(table="products")
    pk = StringAttribute(partition_key=True)
    title = StringAttribute()


async def main():
    now = datetime.now(timezone.utc)

    # User has created_at and updated_at from TimestampBase
    user = User(pk="USER#1", name="John", created_at=now, updated_at=now)
    await user.save()

    loaded = await User.get(pk="USER#1")
    if loaded:
        assert loaded.created_at == now
        assert loaded.name == "John"


if __name__ == "__main__":
    asyncio.run(main())
