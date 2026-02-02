"""Collection with model inheritance."""

import asyncio

from pydynox import Collection, Model, ModelConfig
from pydynox.attributes import StringAttribute


# Base class with shared attributes
class BaseEntity(Model):
    model_config = ModelConfig(table="app")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    _type = StringAttribute(discriminator=True)


class User(BaseEntity):
    name = StringAttribute()
    email = StringAttribute()


class Order(BaseEntity):
    total = StringAttribute()
    status = StringAttribute()


class Address(BaseEntity):
    street = StringAttribute()
    city = StringAttribute()


async def main():
    # All models share the same table and discriminator
    collection = Collection([User, Order, Address])

    result = await collection.query(pk="USER#123")

    # Results are typed correctly
    user: User = result.users[0]
    print(f"User: {user.name} ({user.email})")

    for order in result.orders:
        print(f"Order: ${order.total} - {order.status}")

    for addr in result.addresss:
        print(f"Address: {addr.street}, {addr.city}")


if __name__ == "__main__":
    asyncio.run(main())
