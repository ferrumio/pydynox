"""Each Model class has isolated metrics."""

import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute
from pydynox.testing import MemoryBackend


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    name = StringAttribute()


class Order(Model):
    model_config = ModelConfig(table="orders")
    pk = StringAttribute(partition_key=True)
    total = StringAttribute()


async def main():
    with MemoryBackend():
        # Reset both
        User.reset_metrics()
        Order.reset_metrics()

        # Operations on User
        await User(pk="USER#1", name="John").save()
        await User.get(pk="USER#1")

        # Operations on Order
        await Order(pk="ORDER#1", total="100").save()

        # Metrics are isolated per class
        print(f"User: {User.get_total_metrics().operation_count} ops")  # 2
        print(f"Order: {Order.get_total_metrics().operation_count} ops")  # 1


asyncio.run(main())
