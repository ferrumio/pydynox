"""Query returning dicts instead of Model instances (async - default)."""

import asyncio

from pydynox import Model, ModelConfig, get_default_client
from pydynox.attributes import NumberAttribute, StringAttribute

client = get_default_client()

CUSTOMER_PK = "CUSTOMER#123"


class Order(Model):
    model_config = ModelConfig(table="orders_dict")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    total = NumberAttribute()
    status = StringAttribute()


async def main():
    # Setup: create table and data
    if not await client.table_exists("orders_dict"):
        await client.create_table(
            "orders_dict",
            partition_key=("pk", "S"),
            sort_key=("sk", "S"),
        )

    # Create some orders
    for i in range(5):
        await Order(
            pk=CUSTOMER_PK,
            sk=f"ORDER#{i:03d}",
            total=100 + i * 10,
            status="pending",
        ).save()

    # Return dicts instead of Model instances
    async for order in Order.query(partition_key=CUSTOMER_PK, as_dict=True):
        # order is a plain dict, not an Order instance
        print(order.get("sk"), order.get("total"))

    # Useful for read-only operations where you don't need Model methods
    orders = [order async for order in Order.query(partition_key=CUSTOMER_PK, as_dict=True)]
    print(f"Found {len(orders)} orders as dicts")


asyncio.run(main())
