import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class Order(Model):
    model_config = ModelConfig(table="orders")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    total = NumberAttribute()
    status = StringAttribute()


async def main():
    # Async iteration
    async for order in Order.async_query(hash_key="CUSTOMER#123"):
        print(f"Order: {order.sk}")

    # Get first result
    first = await Order.async_query(hash_key="CUSTOMER#123").first()
    if first:
        print(f"First order: {first.sk}")

    # Collect all results
    orders = [order async for order in Order.async_query(hash_key="CUSTOMER#123")]
    print(f"Found {len(orders)} orders")

    # With conditions
    shipped = [
        order
        async for order in Order.async_query(
            hash_key="CUSTOMER#123",
            filter_condition=Order.status == "shipped",
        )
    ]
    print(f"Found {len(shipped)} shipped orders")


asyncio.run(main())
