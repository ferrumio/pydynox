"""Parallel scan example - scan large tables fast."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    """User model."""

    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    age = NumberAttribute()
    status = StringAttribute()


# Parallel scan with 4 segments - much faster for large tables
users, metrics = User.parallel_scan(total_segments=4)
print(f"Found {len(users)} users in {metrics.duration_ms:.2f}ms")

# With filter
active_users, metrics = User.parallel_scan(
    total_segments=4, filter_condition=User.status == "active"
)
print(f"Found {len(active_users)} active users")
