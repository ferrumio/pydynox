"""Force full replace using PutItem instead of UpdateItem."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    name = StringAttribute()


async def main():
    user = await User.get(pk="USER#1", sk="PROFILE")
    if user:
        user.name = "New Name"

        # Forces PutItem with all fields
        await user.save(full_replace=True)


if __name__ == "__main__":
    asyncio.run(main())
