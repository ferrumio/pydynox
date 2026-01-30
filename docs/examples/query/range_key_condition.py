"""Range key condition examples (async - default)."""

import asyncio

from pydynox import Model, ModelConfig, get_default_client
from pydynox.attributes import NumberAttribute, StringAttribute

client = get_default_client()

CUSTOMER_PK = "CUSTOMER#123"


class Order(Model):
    model_config = ModelConfig(table="orders_range")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    total = NumberAttribute()
    status = StringAttribute()


async def main():
    # Setup: create table and data
    if not await client.table_exists("orders_range"):
        await client.create_table(
            "orders_range",
            partition_key=("pk", "S"),
            sort_key=("sk", "S"),
        )

    # Create orders with different sort keys
    for i in range(15):
        await Order(
            pk=CUSTOMER_PK,
            sk=f"ORDER#{i:03d}",
            total=100 + i * 10,
            status="pending",
        ).save()

    # Query orders that start with "ORDER#"
    async for order in Order.query(
        partition_key=CUSTOMER_PK,
        sort_key_condition=Order.sk.begins_with("ORDER#"),
    ):
        print(f"Order: {order.sk}")

    # Query orders between two sort keys
    async for order in Order.query(
        partition_key=CUSTOMER_PK,
        sort_key_condition=Order.sk.between("ORDER#001", "ORDER#010"),
    ):
        print(f"Between: {order.sk}")

    # Query orders greater than a sort key
    async for order in Order.query(
        partition_key=CUSTOMER_PK,
        sort_key_condition=Order.sk > "ORDER#010",
    ):
        print(f"Greater: {order.sk}")


asyncio.run(main())
