"""Example: Create tables with client (async version)."""

import asyncio

from pydynox import DynamoDBClient

client = DynamoDBClient()


async def main():
    # Simple table with hash key only
    if not await client.table_exists("example_users"):
        await client.create_table(
            "example_users",
            partition_key=("pk", "S"),
            wait=True,
        )

    # Table with hash key and range key
    if not await client.table_exists("example_orders"):
        await client.create_table(
            "example_orders",
            partition_key=("pk", "S"),
            sort_key=("sk", "S"),
            wait=True,
        )

    # Verify tables exist
    assert await client.table_exists("example_users")
    assert await client.table_exists("example_orders")

    # Cleanup
    await client.delete_table("example_users")
    await client.delete_table("example_orders")


if __name__ == "__main__":
    asyncio.run(main())
