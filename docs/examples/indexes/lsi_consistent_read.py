"""LSI with consistent read - LSIs support strongly consistent reads."""

import asyncio

from pydynox import Model, ModelConfig, get_default_client
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.indexes import LocalSecondaryIndex

client = get_default_client()


class Order(Model):
    """Order model with LSI."""

    model_config = ModelConfig(table="orders_consistent")

    customer_id = StringAttribute(hash_key=True)
    order_id = StringAttribute(range_key=True)
    status = StringAttribute()
    total = NumberAttribute()

    status_index = LocalSecondaryIndex(
        index_name="status-index",
        range_key="status",
    )


async def main():
    # Create table
    if not await client.table_exists("orders_consistent"):
        await client.create_table(
            "orders_consistent",
            hash_key=("customer_id", "S"),
            range_key=("order_id", "S"),
            local_secondary_indexes=[
                {
                    "index_name": "status-index",
                    "range_key": ("status", "S"),
                    "projection": "ALL",
                }
            ],
        )

    # Create an order
    Order(
        customer_id="CUST#1",
        order_id="ORD#001",
        status="pending",
        total=100,
    ).save()

    # Query with consistent read (LSI-specific feature)
    # GSIs do NOT support consistent reads, but LSIs do!
    results = list(
        Order.status_index.query(
            customer_id="CUST#1",
            consistent_read=True,  # Strongly consistent read
        )
    )

    print(f"Found {len(results)} orders with consistent read")


asyncio.run(main())
