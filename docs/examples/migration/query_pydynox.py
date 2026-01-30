"""pydynox: Query items from DynamoDB."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class Order(Model):
    model_config = ModelConfig(table="orders")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    amount = NumberAttribute()


async def main():
    orders = Order.query(
        partition_key="CUSTOMER#123",
        sort_key_condition=Order.sk.begins_with("ORDER#"),
        filter_condition=Order.amount > 100,
    )

    async for order in orders:
        print(f"Order: {order.sk}, Amount: {order.amount}")


asyncio.run(main())
