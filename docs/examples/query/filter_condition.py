"""Filter condition examples (async - default)."""

import asyncio

from pydynox import Model, ModelConfig, get_default_client
from pydynox.attributes import NumberAttribute, StringAttribute

client = get_default_client()

CUSTOMER_PK = "CUSTOMER#123"


class Order(Model):
    model_config = ModelConfig(table="orders_filter")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    total = NumberAttribute()
    status = StringAttribute()


async def main():
    # Setup: create table and data
    if not await client.table_exists("orders_filter"):
        await client.create_table(
            "orders_filter",
            partition_key=("pk", "S"),
            sort_key=("sk", "S"),
        )

    # Create orders with different statuses and totals
    statuses = ["pending", "shipped", "delivered", "shipped", "pending"]
    for i, status in enumerate(statuses):
        await Order(
            pk=CUSTOMER_PK,
            sk=f"ORDER#{i:03d}",
            total=50 + i * 30,
            status=status,
        ).save()

    # Filter by status
    async for order in Order.query(
        partition_key=CUSTOMER_PK,
        filter_condition=Order.status == "shipped",
    ):
        print(f"Shipped order: {order.sk}")

    # Filter by total amount
    async for order in Order.query(
        partition_key=CUSTOMER_PK,
        filter_condition=Order.total >= 100,
    ):
        print(f"Large order: {order.sk}, Total: {order.total}")

    # Combine multiple filters with & (AND)
    async for order in Order.query(
        partition_key=CUSTOMER_PK,
        filter_condition=(Order.status == "shipped") & (Order.total > 50),
    ):
        print(f"Shipped large order: {order.sk}")

    # Combine filters with | (OR)
    async for order in Order.query(
        partition_key=CUSTOMER_PK,
        filter_condition=(Order.status == "shipped") | (Order.status == "delivered"),
    ):
        print(f"Completed order: {order.sk}")


asyncio.run(main())
