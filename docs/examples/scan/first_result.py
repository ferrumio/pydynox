"""Get first result from scan (async - default)."""

import asyncio

from pydynox import DynamoDBClient, Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute

client = DynamoDBClient()


class User(Model):
    model_config = ModelConfig(table="users", client=client)
    pk = StringAttribute(partition_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)


async def main():
    # Get first user (any user)
    user = await User.scan().first()
    if user:
        print(f"Found: {user.name}")
    else:
        print("No users found")

    # Get first user matching filter
    admin = await User.scan(filter_condition=User.name == "admin").first()
    if admin:
        print(f"Admin found: {admin.pk}")


asyncio.run(main())
