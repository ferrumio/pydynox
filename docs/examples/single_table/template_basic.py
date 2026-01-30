"""Example: Basic template keys."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute


class User(Model):
    model_config = ModelConfig(table="app")

    pk = StringAttribute(partition_key=True, template="USER#{email}")
    sk = StringAttribute(sort_key=True, template="PROFILE")
    email = StringAttribute()
    name = StringAttribute()


async def main():
    # Keys are built automatically from the template
    user = User(email="john@example.com", name="John")
    print(user.pk)  # "USER#john@example.com"
    print(user.sk)  # "PROFILE"

    await user.save()

    # Get by built keys
    found = await User.get(pk="USER#john@example.com", sk="PROFILE")
    if found:
        print(found.name)  # "John"

    # Cleanup
    await user.delete()


if __name__ == "__main__":
    asyncio.run(main())
