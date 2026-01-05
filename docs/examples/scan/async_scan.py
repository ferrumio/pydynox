"""Async scan example."""

import asyncio

from pydynox import DynamoDBClient, Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute

client = DynamoDBClient()


class User(Model):
    model_config = ModelConfig(table="users", client=client)
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    age = NumberAttribute()
    status = StringAttribute()


async def scan_all_users() -> None:
    """Scan all users asynchronously."""
    async for user in User.async_scan():
        print(f"{user.name}")


async def scan_active_users() -> None:
    """Scan with filter asynchronously."""
    async for user in User.async_scan(filter_condition=User.status == "active"):
        print(f"Active: {user.name}")


async def count_users() -> None:
    """Count users asynchronously."""
    count, metrics = await User.async_count()
    print(f"Total: {count}, Duration: {metrics.duration_ms:.2f}ms")


async def main() -> None:
    await scan_all_users()
    await scan_active_users()
    await count_users()


if __name__ == "__main__":
    asyncio.run(main())
