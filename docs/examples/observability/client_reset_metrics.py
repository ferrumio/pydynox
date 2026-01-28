"""Reset metrics per request - important for long-running processes."""

import asyncio

from pydynox import DynamoDBClient

client = DynamoDBClient()


async def handle_request(user_id: str) -> dict:
    # Reset at start of each request
    client.reset_metrics()

    # Do operations
    await client.put_item("users", {"pk": user_id, "sk": "PROFILE", "name": "John"})
    item = await client.get_item("users", {"pk": user_id, "sk": "PROFILE"})

    # Check total for this request
    total = client.get_total_metrics()
    print(f"Request used {total.total_rcu} RCU, {total.total_wcu} WCU")

    return item or {}


asyncio.run(handle_request("USER#1"))
