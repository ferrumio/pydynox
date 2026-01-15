from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute

# For Model-level metrics, use class methods


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()


# After operations, access metrics via class methods
user = User.get(pk="USER#1", sk="PROFILE")

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
