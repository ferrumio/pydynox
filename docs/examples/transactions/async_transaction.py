import asyncio

from pydynox import AsyncTransaction, DynamoDBClient

client = DynamoDBClient()


async def create_order():
    # Async transaction - same API as sync
    async with AsyncTransaction(client) as tx:
        tx.put("users", {"pk": "USER#1", "sk": "PROFILE", "name": "John"})
        tx.put("orders", {"pk": "ORDER#1", "sk": "DETAILS", "user": "USER#1"})


asyncio.run(create_order())
