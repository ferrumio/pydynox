"""Scan returning dicts instead of Model instances (async - default)."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)


async def main():
    # Return dicts instead of Model instances
    async for user in User.scan(as_dict=True):
        # user is a plain dict, not a User instance
        print(user.get("pk"), user.get("name"))

    # Parallel scan with as_dict
    users, metrics = await User.parallel_scan(total_segments=4, as_dict=True)
    print(f"Found {len(users)} users as dicts")


asyncio.run(main())
