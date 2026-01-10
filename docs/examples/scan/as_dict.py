"""Scan returning dicts instead of Model instances."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute(null=True)
    age = NumberAttribute(null=True)


# Return dicts instead of Model instances
for user in User.scan(as_dict=True):
    # user is a plain dict, not a User instance
    print(user.get("pk"), user.get("name"))

# Parallel scan with as_dict
users, metrics = User.parallel_scan(total_segments=4, as_dict=True)
print(f"Found {len(users)} users as dicts")
