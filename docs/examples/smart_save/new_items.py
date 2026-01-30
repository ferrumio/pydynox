"""New items always use PutItem, then smart save kicks in."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    name = StringAttribute()


async def main():
    # New item - uses PutItem
    user = User(pk="USER#new", sk="PROFILE", name="John")
    await user.save()  # PutItem

    # After save, tracking is enabled
    user.name = "Jane"
    await user.save()  # UpdateItem (smart save)

    # Cleanup
    await user.delete()


if __name__ == "__main__":
    asyncio.run(main())
