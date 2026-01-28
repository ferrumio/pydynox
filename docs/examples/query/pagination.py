"""Pagination examples (async - default)."""

import asyncio

from pydynox import Model, ModelConfig, get_default_client
from pydynox.attributes import NumberAttribute, StringAttribute

client = get_default_client()

CUSTOMER_PK = "CUSTOMER#123"


class Order(Model):
    model_config = ModelConfig(table="orders_page")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    total = NumberAttribute()
    status = StringAttribute()


async def main():
    # Setup: create table and data
    if not await client.table_exists("orders_page"):
        await client.create_table(
            "orders_page",
            hash_key=("pk", "S"),
            range_key=("sk", "S"),
        )

    # Create 25 orders
    for i in range(25):
        await Order(
            pk=CUSTOMER_PK,
            sk=f"ORDER#{i:03d}",
            total=100 + i,
            status="pending",
        ).save()

    # Automatic pagination - iterator fetches all pages
    print("All orders:")
    async for order in Order.query(hash_key=CUSTOMER_PK):
        print(f"  {order.sk}")

    # Manual pagination - control page size
    result = Order.query(hash_key=CUSTOMER_PK, limit=10)

    # Process first page
    page_count = 0
    async for order in result:
        print(f"Page 1: {order.sk}")
        page_count += 1
        if page_count >= 10:
            break

    # Check if there are more pages
    if result.last_evaluated_key:
        print("More pages available")

        # Fetch next page
        next_result = Order.query(
            hash_key=CUSTOMER_PK,
            limit=10,
            last_evaluated_key=result.last_evaluated_key,
        )
        async for order in next_result:
            print(f"Page 2: {order.sk}")


asyncio.run(main())
