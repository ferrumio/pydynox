"""Scan with filter condition."""

from pydynox import DynamoDBClient, Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute

client = DynamoDBClient()


class User(Model):
    model_config = ModelConfig(table="users", client=client)
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    age = NumberAttribute()
    status = StringAttribute()


# Filter by status
for user in User.scan(filter_condition=User.status == "active"):
    print(f"Active user: {user.name}")

# Filter by age
for user in User.scan(filter_condition=User.age >= 18):
    print(f"Adult: {user.name}")

# Complex filter
for user in User.scan(filter_condition=(User.status == "active") & (User.age >= 21)):
    print(f"Active adult: {user.name}")
