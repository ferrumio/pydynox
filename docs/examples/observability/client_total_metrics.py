import asyncio

from pydynox import DynamoDBClient

client = DynamoDBClient()


async def main():
    # Do some operations
    await client.put_item("users", {"pk": "USER#1", "sk": "PROFILE", "name": "John"})
    await client.put_item("users", {"pk": "USER#2", "sk": "PROFILE", "name": "Jane"})
    await client.get_item("users", {"pk": "USER#1", "sk": "PROFILE"})

    # Get total metrics
    total = client.get_total_metrics()
    print(total.total_rcu)  # 0.5
    print(total.total_wcu)  # 2.0
    print(total.operation_count)  # 3
    print(total.put_count)  # 2
    print(total.get_count)  # 1


asyncio.run(main())
