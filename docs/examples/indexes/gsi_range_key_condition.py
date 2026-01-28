"""GSI query with range key condition example."""

import asyncio

from pydynox import Model, ModelConfig, get_default_client
from pydynox.attributes import StringAttribute
from pydynox.indexes import GlobalSecondaryIndex

client = get_default_client()


class User(Model):
    model_config = ModelConfig(table="users_gsi_range")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    status = StringAttribute()
    name = StringAttribute()

    # GSI with status as hash key and pk as range key
    status_index = GlobalSecondaryIndex("status-index", hash_key="status", range_key="pk")


async def main():
    # Setup: create table with GSI
    if not await client.table_exists("users_gsi_range"):
        await client.create_table(
            "users_gsi_range",
            hash_key=("pk", "S"),
            range_key=("sk", "S"),
            global_secondary_indexes=[
                {
                    "index_name": "status-index",
                    "hash_key": ("status", "S"),
                    "range_key": ("pk", "S"),
                },
            ],
        )

    # Create users
    await User(pk="USER#001", sk="PROFILE", status="active", name="John").save()
    await User(pk="USER#050", sk="PROFILE", status="active", name="Jane").save()
    await User(pk="USER#100", sk="PROFILE", status="active", name="Bob").save()
    await User(pk="ADMIN#001", sk="PROFILE", status="active", name="Admin").save()

    # Query active users with pk starting with "USER#"
    print("Active users (pk starts with USER#):")
    async for user in User.status_index.query(
        status="active",
        range_key_condition=User.pk.begins_with("USER#"),
    ):
        print(f"  {user.name} ({user.pk})")

    # Query with comparison
    print("\nActive users (pk >= USER#050):")
    async for user in User.status_index.query(
        status="active",
        range_key_condition=User.pk >= "USER#050",
    ):
        print(f"  {user.name} ({user.pk})")


asyncio.run(main())
