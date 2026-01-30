"""Example: CRUD operations (async - default)."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)


async def main():
    # Create
    user = User(pk="USER#123", sk="PROFILE", name="John", age=30)
    await user.save()

    # Read
    user = await User.get(pk="USER#123", sk="PROFILE")
    if user:
        print(user.name)  # John

    # Update - full
    user.name = "Jane"
    await user.save()

    # Update - partial
    await user.update(name="Jane", age=31)

    # Delete
    await user.delete()


if __name__ == "__main__":
    asyncio.run(main())
