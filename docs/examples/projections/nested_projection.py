"""Nested attribute projection example."""

import asyncio

from pydynox import DynamoDBClient

client = DynamoDBClient()


async def main():
    # Nested attributes use dot notation
    item = await client.get_item(
        "users",
        {"pk": "USER#1"},
        projection=["name", "address.city", "address.zip"],
    )
    # Returns: {"pk": "USER#1", "name": "John", "address": {"city": "NYC", "zip": "10001"}}
    print(item)


asyncio.run(main())
