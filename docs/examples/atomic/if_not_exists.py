"""Using if_not_exists for default values."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    login_count = NumberAttribute()
    score = NumberAttribute()


async def main():
    # User without login_count
    user = User(pk="USER#123", sk="PROFILE")
    await user.save()

    # Set default value only if attribute doesn't exist
    await user.update(atomic=[User.login_count.if_not_exists(0)])
    # login_count: 0

    # Now increment it
    await user.update(atomic=[User.login_count.add(1)])
    # login_count: 1

    # if_not_exists won't overwrite existing value
    await user.update(atomic=[User.login_count.if_not_exists(999)])
    # login_count: still 1

    # Combine with add for "increment or initialize"
    await user.update(
        atomic=[
            User.score.if_not_exists(0),  # Initialize if missing
        ]
    )
    await user.update(atomic=[User.score.add(10)])  # Then increment
    # score: 10


asyncio.run(main())
