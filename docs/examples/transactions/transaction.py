import asyncio

from pydynox import DynamoDBClient, Transaction

client = DynamoDBClient()


async def create_order():
    async with Transaction(client) as tx:
        tx.put("users", {"pk": "USER#1", "sk": "PROFILE", "name": "John"})
        tx.put("orders", {"pk": "ORDER#1", "sk": "DETAILS", "user": "USER#1"})


asyncio.run(create_order())
