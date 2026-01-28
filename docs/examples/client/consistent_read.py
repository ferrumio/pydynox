"""Consistent read with low-level client."""

import asyncio

from pydynox import DynamoDBClient


async def main():
    client = DynamoDBClient(region="us-east-1")

    # get_item with consistent read
    item = await client.get_item(
        "users",
        {"pk": "USER#123", "sk": "PROFILE"},
        consistent_read=True,
    )

    # query with consistent read
    async for item in client.query(
        "users",
        key_condition_expression="#pk = :pk",
        expression_attribute_names={"#pk": "pk"},
        expression_attribute_values={":pk": "USER#123"},
        consistent_read=True,
    ):
        print(item)


asyncio.run(main())
