"""Limit vs page_size examples (async - default)."""

import asyncio

from pydynox import Model, ModelConfig, get_default_client
from pydynox.attributes import NumberAttribute, StringAttribute

client = get_default_client()

CUSTOMER_PK = "CUSTOMER#123"


class Order(Model):
    model_config = ModelConfig(table="orders_limit")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    total = NumberAttribute()
    status = StringAttribute()


async def main():
    # Setup: create table and data
    if not await client.table_exists("orders_limit"):
        await client.create_table(
            "orders_limit",
            hash_key=("pk", "S"),
            range_key=("sk", "S"),
        )

    # Create 50 orders
    for i in range(50):
        await Order(
            pk=CUSTOMER_PK,
            sk=f"ORDER#{i:03d}",
            total=100 + i,
            status="pending",
        ).save()

    # limit = total items to return (stops after N items)
    # page_size = items per DynamoDB request (controls pagination)

    # Example 1: Get exactly 10 items total
    orders = [order async for order in Order.query(hash_key=CUSTOMER_PK, limit=10)]
    print(f"Example 1: Got {len(orders)} orders")

    # Example 2: Get all items, but fetch 25 per page
    count = 0
    async for order in Order.query(hash_key=CUSTOMER_PK, page_size=25):
        count += 1
    print(f"Example 2: Got {count} orders")

    # Example 3: Get 20 items total, fetching 5 per page
    orders = [
        order
        async for order in Order.query(
            hash_key=CUSTOMER_PK,
            limit=20,
            page_size=5,
        )
    ]
    print(f"Example 3: Got {len(orders)} orders")

    # Example 4: Manual pagination with page_size
    result = Order.query(hash_key=CUSTOMER_PK, limit=10, page_size=10)
    first_page = [order async for order in result]
    print(f"Example 4: First page: {len(first_page)} items")

    if result.last_evaluated_key:
        result = Order.query(
            hash_key=CUSTOMER_PK,
            limit=10,
            page_size=10,
            last_evaluated_key=result.last_evaluated_key,
        )
        second_page = [order async for order in result]
        print(f"Example 4: Second page: {len(second_page)} items")


asyncio.run(main())
