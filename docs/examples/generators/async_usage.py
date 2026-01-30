import asyncio

from pydynox import AutoGenerate, Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class Order(Model):
    model_config = ModelConfig(table="orders")

    pk = StringAttribute(partition_key=True, default=AutoGenerate.ULID)
    sk = StringAttribute(sort_key=True)
    total = NumberAttribute()


async def main():
    """Create multiple orders concurrently. Each gets a unique ID."""
    tasks = []
    for i in range(10):
        order = Order(sk=f"ORDER#{i}", total=i * 10)
        tasks.append(order.save())  # save() is async

    await asyncio.gather(*tasks)
    print("Created 10 orders with unique ULIDs")


asyncio.run(main())
