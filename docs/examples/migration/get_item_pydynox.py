"""pydynox: Get item from DynamoDB."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    name = StringAttribute()


async def main():
    user = await User.get(pk="USER#123", sk="PROFILE")

    if user:
        print(f"Name: {user.name}")


asyncio.run(main())
