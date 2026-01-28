"""Consistent read examples (async - default)."""

import asyncio

from pydynox import DynamoDBClient, Model, ModelConfig
from pydynox.attributes import StringAttribute

client = DynamoDBClient(region="us-east-1")


# Option 1: Per-operation (highest priority)
class User(Model):
    model_config = ModelConfig(table="users", client=client)

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()


# Option 2: Model-level default
class Order(Model):
    model_config = ModelConfig(
        table="orders",
        client=client,
        consistent_read=True,  # All reads are strongly consistent
    )

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)


async def main():
    # Eventually consistent (default)
    _user = await User.get(pk="USER#123", sk="PROFILE")

    # Strongly consistent
    _user = await User.get(pk="USER#123", sk="PROFILE", consistent_read=True)

    # Uses strongly consistent read (from model_config)
    _order = await Order.get(pk="ORDER#456", sk="ITEM#1")

    # Override to eventually consistent for this call
    _order = await Order.get(pk="ORDER#456", sk="ITEM#1", consistent_read=False)


if __name__ == "__main__":
    asyncio.run(main())
