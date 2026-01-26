import asyncio

from pydynox import DynamoDBClient

client = DynamoDBClient()


async def get_order_details():
    items = await client.transact_get(
        [
            {"table": "users", "key": {"pk": "USER#1", "sk": "PROFILE"}},
            {"table": "orders", "key": {"pk": "ORDER#1", "sk": "DETAILS"}},
        ]
    )

    user, order = items
    print(f"User: {user}, Order: {order}")


asyncio.run(get_order_details())
