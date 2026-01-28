"""GSI with range key - query users by status with sorting."""

import asyncio

from pydynox import Model, ModelConfig, get_default_client
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.indexes import GlobalSecondaryIndex

client = get_default_client()


class User(Model):
    """User model with status GSI that has a range key."""

    model_config = ModelConfig(table="users_status")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    email = StringAttribute()
    status = StringAttribute()
    name = StringAttribute()
    age = NumberAttribute()

    # GSI with range key for sorting
    status_index = GlobalSecondaryIndex(
        index_name="status-index",
        hash_key="status",
        range_key="pk",  # Sort by pk within each status
    )


async def main():
    # Create table with GSI
    if not await client.table_exists("users_status"):
        await client.create_table(
            "users_status",
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

    # Create users with different statuses
    await User(
        pk="USER#1",
        sk="PROFILE",
        email="john@example.com",
        status="active",
        name="John",
        age=30,
    ).save()
    await User(
        pk="USER#2",
        sk="PROFILE",
        email="jane@example.com",
        status="active",
        name="Jane",
        age=25,
    ).save()
    await User(
        pk="USER#3",
        sk="PROFILE",
        email="bob@example.com",
        status="inactive",
        name="Bob",
        age=35,
    ).save()
    await User(
        pk="ADMIN#1",
        sk="PROFILE",
        email="admin@example.com",
        status="active",
        name="Admin",
        age=40,
    ).save()

    # Query all active users
    print("All active users:")
    async for user in User.status_index.query(status="active"):
        print(f"  {user.name} (pk={user.pk})")

    # Query active users with pk starting with "USER#"
    print("\nActive users (not admins):")
    async for user in User.status_index.query(
        status="active",
        range_key_condition=User.pk.begins_with("USER#"),
    ):
        print(f"  {user.name} (pk={user.pk})")

    # Query in descending order
    print("\nActive users (descending by pk):")
    async for user in User.status_index.query(status="active", scan_index_forward=False):
        print(f"  {user.name} (pk={user.pk})")


asyncio.run(main())
