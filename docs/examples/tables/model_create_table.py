"""Example: Create table from Model schema (sync version)."""

import asyncio

from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import NumberAttribute, StringAttribute
from pydynox.indexes import GlobalSecondaryIndex

# Setup client
client = DynamoDBClient()
set_default_client(client)


class User(Model):
    """User model with GSI for email lookup."""

    model_config = ModelConfig(table="example_model_users")

    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    email = StringAttribute()
    status = StringAttribute()
    age = NumberAttribute()

    # GSI for querying by email
    email_index = GlobalSecondaryIndex(
        index_name="email-index",
        partition_key="email",
    )


async def main():
    # Create table from model schema (includes hash key, range key, and GSIs)
    if not await User.table_exists():
        await User.create_table(wait=True)

    # Verify table exists
    assert await User.table_exists()

    # Save and query to verify GSI works
    user = User(pk="USER#1", sk="PROFILE", email="test@example.com", status="active", age=30)
    await user.save()

    # Query by GSI
    results = [u async for u in User.email_index.query(email="test@example.com")]
    assert len(results) == 1
    assert results[0].pk == "USER#1"

    # Cleanup
    await User.delete_table()


asyncio.run(main())
