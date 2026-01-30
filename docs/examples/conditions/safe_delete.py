"""Safe delete - only delete if conditions are met."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class Order(Model):
    model_config = ModelConfig(table="orders")

    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    status = StringAttribute()
    total = NumberAttribute()


async def main():
    # Create an order first
    order = Order(pk="ORDER#123", sk="DETAILS", status="draft", total=100)
    await order.save()

    # Only delete if order is in "draft" status
    await order.delete(condition=Order.status == "draft")

    # Can't delete orders that are already processed


asyncio.run(main())
