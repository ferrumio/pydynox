"""pydynox: Get item from DynamoDB."""

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()


user = User.get(pk="USER#123", sk="PROFILE")

if user:
    print(f"Name: {user.name}")
