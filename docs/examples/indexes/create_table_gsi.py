"""Create table with GSI using DynamoDBClient."""

import asyncio

from pydynox import DynamoDBClient

client = DynamoDBClient()


async def main():
    # Create table with GSI (skip if already exists)
    if not await client.table_exists("users_with_gsi"):
        await client.create_table(
            "users_with_gsi",
            partition_key=("pk", "S"),
            sort_key=("sk", "S"),
            global_secondary_indexes=[
                {
                    "index_name": "email-index",
                    "hash_key": ("email", "S"),
                    "projection": "ALL",
                },
                {
                    "index_name": "status-index",
                    "hash_key": ("status", "S"),
                    "range_key": ("pk", "S"),
                    "projection": "ALL",
                },
            ],
        )


asyncio.run(main())
