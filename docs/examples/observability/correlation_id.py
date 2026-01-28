"""Correlation ID example for Lambda."""

import asyncio

from pydynox import DynamoDBClient, set_correlation_id

client = DynamoDBClient()


async def handler_async(event: dict, request_id: str) -> dict:
    # Set correlation ID from Lambda context
    set_correlation_id(request_id)

    # All pydynox logs will include this ID
    await client.put_item("users", {"pk": "USER#1", "sk": "PROFILE", "name": "John"})
    # INFO:pydynox:put_item table=users duration_ms=8.2 wcu=1.0 correlation_id=abc-123

    return {"statusCode": 200}


asyncio.run(handler_async({}, "abc-123"))
