"""Basic Collection usage - query multiple entity types in one call."""

import asyncio

from pydynox import Collection, Model, ModelConfig
from pydynox.attributes import StringAttribute


class User(Model):
    model_config = ModelConfig(table="app")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    _type = StringAttribute(discriminator=True)
    name = StringAttribute()


class Order(Model):
    model_config = ModelConfig(table="app")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    _type = StringAttribute(discriminator=True)
    total = StringAttribute()


async def main():
    # Create collection
    collection = Collection([User, Order])

    # Query all entities for a user
    result = await collection.query(pk="USER#123")

    # Access results by type
    for user in result.users:
        print(f"User: {user.name}")

    for order in result.orders:
        print(f"Order total: {order.total}")

    # Or use get() for explicit type
    _users: list[User] = result.get(User)
    _orders: list[Order] = result.get(Order)


if __name__ == "__main__":
    asyncio.run(main())
