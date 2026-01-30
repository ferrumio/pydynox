"""Prevent overwriting existing items."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    email = StringAttribute()
    name = StringAttribute()
    age = NumberAttribute()


async def main():
    # Only save if the item doesn't exist yet
    user = User(pk="USER#NEW", sk="PROFILE", email="john@example.com", name="John", age=30)
    await user.save(condition=User.pk.not_exists())

    # If USER#NEW already exists, this raises ConditionalCheckFailedException


asyncio.run(main())
