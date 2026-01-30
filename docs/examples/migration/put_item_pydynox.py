"""pydynox: Put item to DynamoDB."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    name = StringAttribute()
    email = StringAttribute()


async def main():
    user = User(pk="USER#123", sk="PROFILE", name="John Doe", email="john@example.com")
    await user.save()


asyncio.run(main())
