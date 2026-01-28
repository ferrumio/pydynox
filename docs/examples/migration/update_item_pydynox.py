"""pydynox: Update item in DynamoDB."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    email = StringAttribute()


async def main():
    user = await User.get(pk="USER#123", sk="PROFILE")
    if user:
        await user.update(name="Jane Doe", email="jane@example.com")


asyncio.run(main())
