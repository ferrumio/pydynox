"""Example: Delete a table and wait until it is gone (async version)."""

import asyncio

from pydynox import DynamoDBClient

client = DynamoDBClient()


async def main():
    await client.create_table("example_temp", partition_key=("pk", "S"), wait=True)

    # Returns after the table no longer exists
    await client.delete_table("example_temp", wait=True, timeout_seconds=60)
    assert not await client.table_exists("example_temp")

    # The name is free again, so the table can be recreated
    await client.create_table("example_temp", partition_key=("pk", "S"), wait=True)

    # Cleanup
    await client.delete_table("example_temp", wait=True)


asyncio.run(main())
