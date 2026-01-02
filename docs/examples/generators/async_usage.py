import asyncio

from pydynox import AutoGenerate, Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class Order(Model):
    model_config = ModelConfig(table="orders")

    pk = StringAttribute(hash_key=True, default=AutoGenerate.ULID)
    sk = StringAttribute(range_key=True)
    total = NumberAttribute()


async def create_orders():
    """Create multiple orders concurrently. Each gets a unique ID."""
    tasks = []
    for i in range(10):
        order = Order(sk=f"ORDER#{i}", total=i * 10)
        tasks.append(order.async_save())

    await asyncio.gather(*tasks)
    print("Created 10 orders with unique ULIDs")


asyncio.run(create_orders())
