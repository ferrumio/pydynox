"""EnumAttribute example - store Python enum as string."""

import asyncio
from enum import Enum

from pydynox import Model, ModelConfig
from pydynox.attributes import EnumAttribute, StringAttribute


class Status(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    INACTIVE = "inactive"


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    status = EnumAttribute(Status, default=Status.PENDING)


async def main():
    # Create with enum value
    user = User(pk="USER#ENUM", sk="PROFILE", status=Status.ACTIVE)
    await user.save()
    # Stored as "active" in DynamoDB

    # Load it back - returns the enum
    loaded = await User.get(pk="USER#ENUM", sk="PROFILE")
    print(loaded.status)  # Status.ACTIVE
    print(loaded.status == Status.ACTIVE)  # True

    # Default value works
    user2 = User(pk="USER#ENUM2", sk="PROFILE")
    print(user2.status)  # Status.PENDING


asyncio.run(main())
