"""Async PartiQL example."""

import asyncio

from pydynox import DynamoDBClient


async def main():
    client = DynamoDBClient()

    result = await client.execute_statement(
        "SELECT * FROM users WHERE pk = ?",
        parameters=["USER#123"],
    )

    for item in result:
        print(item["name"])

    print(f"Duration: {result.metrics.duration_ms}ms")


asyncio.run(main())
