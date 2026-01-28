import asyncio

from pydynox import DynamoDBClient


async def main():
    client = DynamoDBClient()

    # get_item returns a plain dict
    item = await client.get_item("users", {"pk": "USER#1", "sk": "PROFILE"})

    if item:
        print(item["name"])  # Works like a normal dict

    # Access metrics via client.get_last_metrics()
    metrics = client.get_last_metrics()
    print(metrics.duration_ms)  # 12.1
    print(metrics.consumed_rcu)  # 0.5


asyncio.run(main())
