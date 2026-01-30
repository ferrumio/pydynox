"""Sorting and limit examples (async - default)."""

import asyncio

from pydynox import Model, ModelConfig, get_default_client
from pydynox.attributes import NumberAttribute, StringAttribute

client = get_default_client()

CUSTOMER_PK = "CUSTOMER#123"


class Order(Model):
    model_config = ModelConfig(table="orders_sort")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    total = NumberAttribute()
    status = StringAttribute()


async def main():
    # Setup: create table and data
    if not await client.table_exists("orders_sort"):
        await client.create_table(
            "orders_sort",
            partition_key=("pk", "S"),
            sort_key=("sk", "S"),
        )

    # Create 10 orders
    for i in range(10):
        await Order(
            pk=CUSTOMER_PK,
            sk=f"ORDER#{i:03d}",
            total=100 + i * 10,
            status="pending",
        ).save()

    # Ascending order (default)
    print("Ascending:")
    async for order in Order.query(
        partition_key=CUSTOMER_PK,
        scan_index_forward=True,
    ):
        print(f"  {order.sk}")

    # Descending order
    print("Descending:")
    async for order in Order.query(
        partition_key=CUSTOMER_PK,
        scan_index_forward=False,
    ):
        print(f"  {order.sk}")

    # Get the 5 most recent orders (descending)
    print("5 most recent:")
    recent_orders = [
        order
        async for order in Order.query(
            partition_key=CUSTOMER_PK,
            scan_index_forward=False,
            limit=5,
        )
    ]

    for order in recent_orders:
        print(f"  {order.sk}")


asyncio.run(main())
