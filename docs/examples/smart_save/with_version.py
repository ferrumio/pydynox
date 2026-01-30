"""Smart save works with optimistic locking (version attribute)."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute, VersionAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    name = StringAttribute()
    version = VersionAttribute()


async def main():
    user = await User.get(pk="USER#1", sk="PROFILE")
    if user:
        user.name = "New Name"

        # UpdateItem with version check
        await user.save()


if __name__ == "__main__":
    asyncio.run(main())
