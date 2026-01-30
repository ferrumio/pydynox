import asyncio

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute

# For Model-level metrics, use class methods


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    name = StringAttribute()


async def main():
    # After operations, access metrics via class methods
    await User.get(pk="USER#1", sk="PROFILE")

    # Get last operation metrics
    last = User.get_last_metrics()
    if last:
        print(last.duration_ms)  # 12.1
        print(last.consumed_rcu)  # 0.5

    # Get total metrics across all operations
    total = User.get_total_metrics()
    print(total.total_rcu)  # 5.0
    print(total.get_count)  # 3

    # Reset metrics
    User.reset_metrics()


asyncio.run(main())
