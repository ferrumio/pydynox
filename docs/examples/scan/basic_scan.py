"""Basic scan example - scan all items in a table."""

from pydynox import DynamoDBClient, Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute

client = DynamoDBClient()


class User(Model):
    model_config = ModelConfig(table="users", client=client)
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    age = NumberAttribute()


# Scan all users
for user in User.scan():
    print(f"{user.name} is {user.age} years old")
