"""Basic scan example - scan all items in a table (async - default)."""

import asyncio

from pydynox import DynamoDBClient, Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute

client = DynamoDBClient()


class User(Model):
    model_config = ModelConfig(table="users", client=client)
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)


async def main():
    # Scan all users
    async for user in User.scan():
        print(f"{user.name} is {user.age} years old")


asyncio.run(main())
