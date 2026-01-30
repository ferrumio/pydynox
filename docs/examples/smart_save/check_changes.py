"""Check if item changed using is_dirty and changed_fields."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    name = StringAttribute()
    email = StringAttribute()


async def main():
    user = await User.get(pk="USER#1", sk="PROFILE")
    if user:
        print(user.is_dirty)  # False

        user.name = "New Name"
        print(user.is_dirty)  # True
        print(user.changed_fields)  # ["name"]

        user.email = "new@example.com"
        print(user.changed_fields)  # ["name", "email"]


if __name__ == "__main__":
    asyncio.run(main())
