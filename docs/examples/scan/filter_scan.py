"""Scan with filter condition (async - default)."""

import asyncio

from pydynox import DynamoDBClient, Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute

client = DynamoDBClient()


class User(Model):
    model_config = ModelConfig(table="users", client=client)
    pk = StringAttribute(partition_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)
    status = StringAttribute(default="active")


async def main():
    # Filter by status
    async for user in User.scan(filter_condition=User.status == "active"):
        print(f"Active user: {user.name}")

    # Filter by age
    async for user in User.scan(filter_condition=User.age >= 18):
        print(f"Adult: {user.name}")

    # Complex filter
    async for user in User.scan(filter_condition=(User.status == "active") & (User.age >= 21)):
        print(f"Active adult: {user.name}")


asyncio.run(main())
