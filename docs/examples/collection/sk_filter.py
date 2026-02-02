"""Collection with sort key filter."""

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
    collection = Collection([User, Order])

    # Get only orders (filter by sk prefix)
    result = await collection.query(pk="USER#123", sk_begins_with="ORDER#")

    # Only orders returned
    print(f"Orders: {len(result.orders)}")
    print(f"Users: {len(result.users)}")  # 0


if __name__ == "__main__":
    asyncio.run(main())
