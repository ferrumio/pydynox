"""Basic query examples (async - default)."""

import asyncio

from pydynox import Model, ModelConfig, get_default_client
from pydynox.attributes import NumberAttribute, StringAttribute

client = get_default_client()


class Order(Model):
    model_config = ModelConfig(table="orders")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    total = NumberAttribute()
    status = StringAttribute()


async def main():
    # Setup: create table and data
    if not await client.table_exists("orders"):
        await client.create_table(
            "orders",
            hash_key=("pk", "S"),
            range_key=("sk", "S"),
        )

    # Create some orders
    for i in range(3):
        await Order(
            pk="CUSTOMER#123",
            sk=f"ORDER#{i:03d}",
            total=100 + i * 50,
            status="pending",
        ).save()

    # Query all orders for a customer
    async for order in Order.query(hash_key="CUSTOMER#123"):
        print(f"Order: {order.sk}, Total: {order.total}")

    # Get first result only
    first_order = await Order.query(hash_key="CUSTOMER#123").first()
    if first_order:
        print(f"First order: {first_order.sk}")

    # Collect all results into a list
    orders = [order async for order in Order.query(hash_key="CUSTOMER#123")]
    print(f"Found {len(orders)} orders")


asyncio.run(main())
