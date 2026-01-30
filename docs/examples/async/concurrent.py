"""Concurrent async operations (async is default - no prefix needed)."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    name = StringAttribute()
    age = NumberAttribute()


async def sequential():
    # Sequential - slow (100ms + 100ms + 100ms = 300ms)
    user1 = await User.get(pk="USER#1", sk="PROFILE")
    user2 = await User.get(pk="USER#2", sk="PROFILE")
    user3 = await User.get(pk="USER#3", sk="PROFILE")
    return user1, user2, user3


async def concurrent():
    # Concurrent - fast (~100ms total)
    user1, user2, user3 = await asyncio.gather(
        User.get(pk="USER#1", sk="PROFILE"),
        User.get(pk="USER#2", sk="PROFILE"),
        User.get(pk="USER#3", sk="PROFILE"),
    )
    return user1, user2, user3
