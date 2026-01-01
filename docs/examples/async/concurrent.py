import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    age = NumberAttribute()


async def sequential():
    # Sequential - slow (100ms + 100ms + 100ms = 300ms)
    user1 = await User.async_get(pk="USER#1", sk="PROFILE")
    user2 = await User.async_get(pk="USER#2", sk="PROFILE")
    user3 = await User.async_get(pk="USER#3", sk="PROFILE")
    return user1, user2, user3


async def concurrent():
    # Concurrent - fast (~100ms total)
    user1, user2, user3 = await asyncio.gather(
        User.async_get(pk="USER#1", sk="PROFILE"),
        User.async_get(pk="USER#2", sk="PROFILE"),
        User.async_get(pk="USER#3", sk="PROFILE"),
    )
    return user1, user2, user3
