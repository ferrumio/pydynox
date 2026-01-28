"""Managing user tags with list operations."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import ListAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    tags = ListAttribute()


async def main():
    # Create user with initial tags
    user = User(pk="USER#123", sk="PROFILE", tags=["member"])
    await user.save()

    # Add tags to the end
    await user.update(atomic=[User.tags.append(["premium", "verified"])])
    # tags: ["member", "premium", "verified"]

    # Add tags to the beginning
    await user.update(atomic=[User.tags.prepend(["vip"])])
    # tags: ["vip", "member", "premium", "verified"]


asyncio.run(main())
