import asyncio

from pydynox import DynamoDBClient

client = DynamoDBClient()


async def get_order_details():
    # Read multiple items atomically (async is default, no prefix)
    items = await client.transact_get(
        [
            {"table": "users", "key": {"pk": "USER#1", "sk": "PROFILE"}},
            {"table": "orders", "key": {"pk": "ORDER#1", "sk": "DETAILS"}},
        ]
    )

    user, order = items
    return {"user": user, "order": order}


result = asyncio.run(get_order_details())
