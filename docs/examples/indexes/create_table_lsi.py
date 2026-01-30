"""Create table with LSI using DynamoDBClient."""

import asyncio

from pydynox import DynamoDBClient

client = DynamoDBClient()


async def main():
    # Create table with LSI (skip if already exists)
    if not await client.table_exists("orders_with_lsi"):
        await client.create_table(
            "orders_with_lsi",
            partition_key=("customer_id", "S"),
            sort_key=("order_id", "S"),
            local_secondary_indexes=[
                {
                    "index_name": "status-index",
                    "range_key": ("status", "S"),
                    "projection": "ALL",
                },
                {
                    "index_name": "created-index",
                    "range_key": ("created_at", "S"),
                    "projection": "KEYS_ONLY",
                },
            ],
        )


asyncio.run(main())
