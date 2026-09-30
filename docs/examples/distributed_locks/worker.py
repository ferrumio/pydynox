"""Async workers coordinate customer work through one lock table."""

import asyncio

from pydynox import DynamoDBClient
from pydynox.lock import distributed_lock

client = DynamoDBClient()

# Deployment setup. Normally provision the table outside the application.
if not client.sync_table_exists("worker_locks"):
    client.sync_create_table("worker_locks", partition_key=("key", "S"), wait=True)


@distributed_lock(client, table="worker_locks", key="customer:{customer_id}", wait_timeout=2)
async def synchronize_customer(customer_id: str) -> str:
    await asyncio.sleep(0.01)  # Replace with the customer's import or repair work.
    return f"Updated {customer_id}"


async def main():
    # Same customer waits; different customers can proceed independently.
    results = await asyncio.gather(
        synchronize_customer("123"),
        synchronize_customer(customer_id="123"),
        synchronize_customer("456"),
    )
    assert results == ["Updated 123", "Updated 123", "Updated 456"]


asyncio.run(main())
