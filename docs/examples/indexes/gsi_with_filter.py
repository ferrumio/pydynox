"""GSI with filter condition - query with additional filtering."""

import asyncio

from pydynox import Model, ModelConfig, get_default_client
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.indexes import GlobalSecondaryIndex

client = get_default_client()


class User(Model):
    """User model with status GSI."""

    model_config = ModelConfig(table="users_filter")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    email = StringAttribute()
    status = StringAttribute()
    name = StringAttribute()
    age = NumberAttribute()

    status_index = GlobalSecondaryIndex(
        index_name="status-index",
        hash_key="status",
        range_key="pk",
    )


async def main():
    # Create table
    if not await client.table_exists("users_filter"):
        await client.create_table(
            "users_filter",
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

    # Create users
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
        status="active",
        name="Bob",
        age=35,
    ).save()

    # Query active users over 30
    print("Active users age >= 30:")
    async for user in User.status_index.query(
        status="active",
        filter_condition=User.age >= 30,
    ):
        print(f"  {user.name} (age={user.age})")

    # Note: Filter runs AFTER the query.
    # DynamoDB still reads all active users, then filters.
    # You pay RCU for all items read, not just the filtered results.


asyncio.run(main())
