"""Setting a default client for all models."""

from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import StringAttribute

# Create and set default client once at app startup
client = DynamoDBClient(region="us-east-1", profile="prod")
set_default_client(client)


# All models use the default client automatically
class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()


class Order(Model):
    model_config = ModelConfig(table="orders")
    pk = StringAttribute(hash_key=True)
    total = StringAttribute()


# No need to pass client to each model
user = User(pk="USER#1", name="John")
user.save()  # Uses the default client
