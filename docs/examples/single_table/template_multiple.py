"""Example: Multiple placeholders in template."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute


class Order(Model):
    model_config = ModelConfig(table="app")

    pk = StringAttribute(hash_key=True, template="USER#{user_id}")
    sk = StringAttribute(range_key=True, template="ORDER#{order_id}#{date}")
    user_id = StringAttribute()
    order_id = StringAttribute()
    date = StringAttribute()
    status = StringAttribute()


async def main():
    order = Order(user_id="123", order_id="456", date="2024-01-15", status="pending")
    print(order.pk)  # "USER#123"
    print(order.sk)  # "ORDER#456#2024-01-15"

    await order.save()

    # Query using placeholder
    async for o in Order.query(user_id="123"):
        print(f"{o.order_id}: {o.status}")

    # Cleanup
    await order.delete()


if __name__ == "__main__":
    asyncio.run(main())
