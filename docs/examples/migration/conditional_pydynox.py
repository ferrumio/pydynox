"""pydynox: Conditional write to DynamoDB."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute
from pydynox.exceptions import ConditionalCheckFailedException


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    name = StringAttribute()


async def main():
    try:
        user = User(pk="USER#123", sk="PROFILE", name="John")
        await user.save(condition=User.pk.not_exists())
        print("User created")
    except ConditionalCheckFailedException:
        print("User already exists")


asyncio.run(main())
