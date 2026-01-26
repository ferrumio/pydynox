import asyncio

from pydynox import DynamoDBClient

client = DynamoDBClient()


async def create_user_and_order():
    operations = [
        {
            "type": "put",
            "table": "users",
            "item": {"pk": "USER#1", "sk": "PROFILE", "name": "John"},
        },
        {
            "type": "put",
            "table": "orders",
            "item": {"pk": "ORDER#1", "sk": "DETAILS", "user": "USER#1", "total": 100},
        },
    ]
    await client.transact_write(operations)


asyncio.run(create_user_and_order())
