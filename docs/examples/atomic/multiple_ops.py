"""Multiple atomic operations in one request."""

import asyncio
from datetime import datetime

from pydynox import Model, ModelConfig
from pydynox.attributes import (
    ListAttribute,
    NumberAttribute,
    StringAttribute,
)


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    login_count = NumberAttribute()
    last_login = StringAttribute()
    badges = ListAttribute()
    temp_token = StringAttribute()


async def main():
    user = User(
        pk="USER#123",
        sk="PROFILE",
        login_count=0,
        badges=[],
        temp_token="abc123",
    )
    await user.save()

    # Multiple operations in one request
    await user.update(
        atomic=[
            User.login_count.add(1),
            User.last_login.set(datetime.now().isoformat()),
            User.badges.append(["first_login"]),
            User.temp_token.remove(),
        ]
    )

    # Result:
    # login_count: 1
    # last_login: "2024-01-15T10:30:00"
    # badges: ["first_login"]
    # temp_token: None (removed)


asyncio.run(main())
