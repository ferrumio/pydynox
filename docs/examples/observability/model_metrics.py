"""Model metrics example - using class methods."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    age = NumberAttribute()


# Reset metrics before starting
User.reset_metrics()

# Do some operations
user = User(pk="USER#1", sk="PROFILE", name="John", age=30)
user.save()

# Get metrics from last operation
last = User.get_last_metrics()
print(f"Save took {last.duration_ms}ms")
print(f"Consumed {last.consumed_wcu} WCU")

# Do more operations
User.get(pk="USER#1", sk="PROFILE")
User.get(pk="USER#2", sk="PROFILE")

# Get total metrics
total = User.get_total_metrics()
print(f"Total operations: {total.operation_count}")
print(f"Total RCU: {total.total_rcu}")
print(f"Total WCU: {total.total_wcu}")
print(f"Gets: {total.get_count}, Puts: {total.put_count}")
