"""GSI query with filter condition example."""

import asyncio

from pydynox import Model, ModelConfig, get_default_client
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.indexes import GlobalSecondaryIndex

client = get_default_client()


class User(Model):
    model_config = ModelConfig(table="users_gsi_filter")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    status = StringAttribute()
    name = StringAttribute()
    age = NumberAttribute()

    status_index = GlobalSecondaryIndex("status-index", hash_key="status")


async def main():
    # Setup: create table with GSI
    if not await client.table_exists("users_gsi_filter"):
        await client.create_table(
            "users_gsi_filter",
            hash_key=("pk", "S"),
            range_key=("sk", "S"),
            global_secondary_indexes=[
                {"index_name": "status-index", "hash_key": ("status", "S")},
            ],
        )

    # Create users with different ages
    await User(pk="USER#1", sk="PROFILE", status="active", name="John", age=30).save()
    await User(pk="USER#2", sk="PROFILE", status="active", name="Jane", age=25).save()
    await User(pk="USER#3", sk="PROFILE", status="active", name="Bob", age=35).save()
    await User(pk="USER#4", sk="PROFILE", status="inactive", name="Alice", age=40).save()

    # Query active users over 30
    print("Active users age >= 30:")
    async for user in User.status_index.query(
        status="active",
        filter_condition=User.age >= 30,
    ):
        print(f"  {user.name} (age={user.age})")


asyncio.run(main())
