"""Example: Multiple entity types in same table."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute


class User(Model):
    model_config = ModelConfig(table="app")
    pk = StringAttribute(partition_key=True, template="USER#{user_id}")
    sk = StringAttribute(sort_key=True, template="PROFILE")
    user_id = StringAttribute()
    name = StringAttribute()


class Order(Model):
    model_config = ModelConfig(table="app")
    pk = StringAttribute(partition_key=True, template="USER#{user_id}")
    sk = StringAttribute(sort_key=True, template="ORDER#{order_id}")
    user_id = StringAttribute()
    order_id = StringAttribute()
    total = StringAttribute()


async def main():
    # Create user and orders - all in the same table
    user = User(user_id="alice", name="Alice")
    order1 = Order(user_id="alice", order_id="001", total="100")
    order2 = Order(user_id="alice", order_id="002", total="200")
    await user.save()
    await order1.save()
    await order2.save()

    # Get user profile
    found = await User.get(pk="USER#alice", sk="PROFILE")
    if found:
        print(f"User: {found.name}")

    # Get orders - filter by sk prefix to exclude the profile
    print("Orders:")
    async for order in Order.query(
        user_id="alice",
        sort_key_condition=Order.sk.begins_with("ORDER#"),
    ):
        print(f"  {order.order_id}: ${order.total}")

    # Cleanup
    await user.delete()
    await order1.delete()
    await order2.delete()


if __name__ == "__main__":
    asyncio.run(main())
