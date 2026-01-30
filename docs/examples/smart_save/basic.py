"""Basic smart save example - only changed fields are sent to DynamoDB."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    name = StringAttribute()
    email = StringAttribute()
    bio = StringAttribute()


async def main():
    # Load a 4KB item with 20 fields
    user = await User.get(pk="USER#1", sk="PROFILE")
    if user:
        # Change one field
        user.name = "New Name"

        # Only sends 'name' to DynamoDB (not all 4KB)
        await user.save()


if __name__ == "__main__":
    asyncio.run(main())
