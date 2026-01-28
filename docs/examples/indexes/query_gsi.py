"""Query a GSI example."""

import asyncio

from pydynox import Model, ModelConfig, get_default_client
from pydynox.attributes import StringAttribute
from pydynox.indexes import GlobalSecondaryIndex

client = get_default_client()


class User(Model):
    model_config = ModelConfig(table="users_gsi")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    email = StringAttribute()
    status = StringAttribute()
    name = StringAttribute()

    # Define GSIs
    email_index = GlobalSecondaryIndex("email-index", hash_key="email")
    status_index = GlobalSecondaryIndex("status-index", hash_key="status")


async def main():
    # Setup: create table with GSIs
    if not await client.table_exists("users_gsi"):
        await client.create_table(
            "users_gsi",
            hash_key=("pk", "S"),
            range_key=("sk", "S"),
            global_secondary_indexes=[
                {"index_name": "email-index", "hash_key": ("email", "S")},
                {"index_name": "status-index", "hash_key": ("status", "S")},
            ],
        )

    # Create some users
    await User(
        pk="USER#1", sk="PROFILE", email="john@example.com", status="active", name="John"
    ).save()
    await User(
        pk="USER#2", sk="PROFILE", email="jane@example.com", status="active", name="Jane"
    ).save()

    # Query by email
    async for user in User.email_index.query(email="john@example.com"):
        print(f"By email: {user.name}")

    # Query by status
    async for user in User.status_index.query(status="active"):
        print(f"Active: {user.name}")


asyncio.run(main())
