"""Example: Inverted index for bidirectional queries."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute
from pydynox.indexes import GlobalSecondaryIndex


class UserOrder(Model):
    model_config = ModelConfig(table="app")

    # Main table: pk=USER#123, sk=ORDER#456
    pk = StringAttribute(partition_key=True, template="USER#{user_id}")
    sk = StringAttribute(sort_key=True, template="ORDER#{order_id}")
    user_id = StringAttribute()
    order_id = StringAttribute()
    status = StringAttribute()

    # Inverted index: sk becomes hash key, pk becomes sort key
    by_order = GlobalSecondaryIndex(
        index_name="inverted",
        partition_key="sk",
        sort_key="pk",
    )


async def main():
    # Create orders
    order1 = UserOrder(user_id="alice", order_id="001", status="shipped")
    order2 = UserOrder(user_id="alice", order_id="002", status="pending")
    order3 = UserOrder(user_id="bob", order_id="003", status="shipped")
    await order1.save()
    await order2.save()
    await order3.save()

    # Query by user (main table)
    print("Alice's orders:")
    async for order in UserOrder.query(user_id="alice"):
        print(f"  {order.order_id}: {order.status}")

    # Query by order (inverted index)
    print("\nWho made order 003?")
    async for result in UserOrder.by_order.query(order_id="003"):
        print(f"  User: {result.user_id}")

    # Cleanup
    await order1.delete()
    await order2.delete()
    await order3.delete()


if __name__ == "__main__":
    asyncio.run(main())
