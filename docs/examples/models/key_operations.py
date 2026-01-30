"""Example: update_by_key and delete_by_key operations (async - default)."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    name = StringAttribute()
    age = NumberAttribute()


async def main():
    # Update without fetching first - single DynamoDB call
    await User.update_by_key(pk="USER#123", sk="PROFILE", name="Jane", age=31)

    # Delete without fetching first - single DynamoDB call
    await User.delete_by_key(pk="USER#123", sk="PROFILE")

    # Compare with traditional approach (2 calls):
    # user = await User.get(pk="USER#123", sk="PROFILE")  # Call 1
    # await user.update(name="Jane")                       # Call 2


if __name__ == "__main__":
    asyncio.run(main())
