"""GSI pagination - limit vs page_size behavior."""

import asyncio

from pydynox import Model, ModelConfig, get_default_client
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.indexes import GlobalSecondaryIndex

client = get_default_client()


class User(Model):
    """User model with status GSI."""

    model_config = ModelConfig(table="users_gsi_pagination")

    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    email = StringAttribute()
    status = StringAttribute()
    created_at = StringAttribute()
    age = NumberAttribute()

    status_index = GlobalSecondaryIndex(
        index_name="status-index",
        partition_key="status",
        sort_key="created_at",
    )


async def main():
    # Create table with GSI
    if not await client.table_exists("users_gsi_pagination"):
        await client.create_table(
            "users_gsi_pagination",
            partition_key=("pk", "S"),
            sort_key=("sk", "S"),
            global_secondary_indexes=[
                {
                    "index_name": "status-index",
                    "hash_key": ("status", "S"),
                    "range_key": ("created_at", "S"),
                    "projection": "ALL",
                }
            ],
        )

    # Create 25 active users
    for i in range(25):
        await User(
            pk=f"USER#{i:03d}",
            sk="PROFILE",
            email=f"user{i}@example.com",
            status="active",
            created_at=f"2024-01-{i + 1:02d}",
            age=20 + i,
        ).save()

    # limit = total items to return (stops after N items)
    # page_size = items per DynamoDB request (controls pagination)

    # Example 1: Get exactly 10 active users
    users = [u async for u in User.status_index.query(status="active", limit=10)]
    print(f"limit=10: Got {len(users)} users")

    # Example 2: Get all active users, fetching 5 per page
    count = 0
    async for user in User.status_index.query(status="active", page_size=5):
        count += 1
    print(f"page_size=5 (no limit): Got {count} users")

    # Example 3: Get 15 active users, fetching 5 per page (3 requests)
    users = [
        u
        async for u in User.status_index.query(
            status="active",
            limit=15,
            page_size=5,
        )
    ]
    print(f"limit=15, page_size=5: Got {len(users)} users")

    # Example 4: Manual pagination for "load more" UI
    result = User.status_index.query(status="active", limit=10, page_size=10)
    first_page = [u async for u in result]
    print(f"First page: {len(first_page)} items")

    if result.last_evaluated_key:
        result = User.status_index.query(
            status="active",
            limit=10,
            page_size=10,
            last_evaluated_key=result.last_evaluated_key,
        )
        second_page = [u async for u in result]
        print(f"Second page: {len(second_page)} items")


asyncio.run(main())
