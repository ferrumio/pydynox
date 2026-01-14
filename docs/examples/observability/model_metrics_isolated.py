"""Each Model class has isolated metrics."""

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute
from pydynox.testing import MemoryBackend


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()


class Order(Model):
    model_config = ModelConfig(table="orders")
    pk = StringAttribute(hash_key=True)
    total = StringAttribute()


with MemoryBackend():
    # Reset both
    User.reset_metrics()
    Order.reset_metrics()

    # Operations on User
    User(pk="USER#1", name="John").save()
    User.get(pk="USER#1")

    # Operations on Order
    Order(pk="ORDER#1", total="100").save()

    # Metrics are isolated per class
    print(f"User: {User.get_total_metrics().operation_count} ops")  # 2
    print(f"Order: {Order.get_total_metrics().operation_count} ops")  # 1
