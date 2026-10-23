"""Batch get with projection example."""

import asyncio

from pydynox import DynamoDBClient, Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute

client = DynamoDBClient()


class User(Model):
    model_config = ModelConfig(table="users", client=client)
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    name = StringAttribute()
    email = StringAttribute()
    age = NumberAttribute(default=0)


async def main():
    keys = [
        {"pk": "USER#1", "sk": "PROFILE"},
        {"pk": "USER#2", "sk": "PROFILE"},
    ]

    # Client-level: return only these attributes ("name" is a reserved word, that is fine)
    items = await client.batch_get("users", keys, projection=["pk", "name"])
    for item in items:
        print(item["name"])

    # Model-level: fields you did not ask for are not loaded
    users = await User.batch_get(keys, projection=["pk", "sk", "name"])
    for user in users:
        print(user.name)

    # Nested attributes use dot notation
    items = await client.batch_get("users", keys, projection=["address.city"])

    # Sync versions
    items = client.sync_batch_get("users", keys, projection=["name"])
    users = User.sync_batch_get(keys, projection=["pk", "sk", "name"])


asyncio.run(main())
