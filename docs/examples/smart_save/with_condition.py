"""Smart save works with conditions."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    status = StringAttribute()


async def main():
    user = await User.get(pk="USER#1", sk="PROFILE")
    if user:
        user.status = "active"

        # UpdateItem with condition
        try:
            await user.save(condition=User.status == "pending")
        except Exception:
            # Condition failed - status was not "pending"
            pass


if __name__ == "__main__":
    asyncio.run(main())
