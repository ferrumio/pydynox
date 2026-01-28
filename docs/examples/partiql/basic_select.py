"""Basic PartiQL SELECT example."""

import asyncio

from pydynox import DynamoDBClient


async def main():
    client = DynamoDBClient()

    # Select all items for a partition key
    result = await client.execute_statement(
        "SELECT * FROM users WHERE pk = ?",
        parameters=["USER#123"],
    )

    for item in result:
        print(item["name"])

    # Access metrics
    print(f"Duration: {result.metrics.duration_ms}ms")
    print(f"Items: {result.metrics.items_count}")


asyncio.run(main())
