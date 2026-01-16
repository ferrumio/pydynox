"""pydynox: Put item to DynamoDB."""

from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    email = StringAttribute()


user = User(pk="USER#123", sk="PROFILE", name="John Doe", email="john@example.com")
user.save()
