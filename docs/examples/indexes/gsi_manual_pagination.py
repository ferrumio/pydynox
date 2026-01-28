"""Manual pagination with GSI - for 'load more' buttons."""

import asyncio

from pydynox import Model, ModelConfig, get_default_client
from pydynox.attributes import StringAttribute
from pydynox.indexes import GlobalSecondaryIndex

client = get_default_client()


class User(Model):
    model_config = ModelConfig(table="users_manual_pagination")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    email = StringAttribute()
    status = StringAttribute()
    name = StringAttribute()

    status_index = GlobalSecondaryIndex("status-index", hash_key="status", range_key="pk")


async def main():
    # Create table with GSI
    if not await client.table_exists("users_manual_pagination"):
        await client.create_table(
            "users_manual_pagination",
            hash_key=("pk", "S"),
            range_key=("sk", "S"),
            global_secondary_indexes=[
                {
                    "index_name": "status-index",
                    "hash_key": ("status", "S"),
                    "range_key": ("pk", "S"),
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
            name=f"User {i}",
        ).save()

    # First page
    result = User.status_index.query(status="active", limit=10, page_size=10)

    print("First page:")
    async for user in result:
        print(f"  {user.email}")

    # Check if there are more results
    if result.last_evaluated_key:
        print("\n--- Loading more ---\n")

        # Next page using last_evaluated_key
        next_result = User.status_index.query(
            status="active",
            limit=10,
            page_size=10,
            last_evaluated_key=result.last_evaluated_key,
        )

        print("Second page:")
        async for user in next_result:
            print(f"  {user.email}")


asyncio.run(main())
