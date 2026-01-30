"""Count items in a table (async - default)."""

import asyncio

from pydynox import DynamoDBClient, Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute

client = DynamoDBClient()


class User(Model):
    model_config = ModelConfig(table="users", client=client)
    pk = StringAttribute(partition_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)
    status = StringAttribute(default="active")


async def main():
    # Count all users
    count, metrics = await User.count()
    print(f"Total users: {count}")
    print(f"Duration: {metrics.duration_ms:.2f}ms")
    print(f"RCU consumed: {metrics.consumed_rcu}")

    # Count with filter
    active_count, _ = await User.count(filter_condition=User.status == "active")
    print(f"Active users: {active_count}")

    # Count adults
    adult_count, _ = await User.count(filter_condition=User.age >= 18)
    print(f"Adults: {adult_count}")


asyncio.run(main())
