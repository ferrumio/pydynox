import asyncio

from pydynox import DynamoDBClient


async def main():
    client = DynamoDBClient()

    # put_item returns OperationMetrics directly
    metrics = await client.put_item("users", {"pk": "USER#1", "sk": "PROFILE", "name": "John"})

    print(metrics.duration_ms)  # 8.2
    print(metrics.consumed_wcu)  # 1.0

    # Same for delete_item and update_item
    metrics = await client.delete_item("users", {"pk": "USER#1", "sk": "PROFILE"})
    print(metrics.duration_ms)


asyncio.run(main())
