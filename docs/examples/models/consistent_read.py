"""Consistent read examples."""

from pydynox import DynamoDBClient, Model, ModelConfig, StringAttribute

client = DynamoDBClient(region="us-east-1")


# Option 1: Per-operation (highest priority)
class User(Model):
    model_config = ModelConfig(table="users", client=client)

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()


# Eventually consistent (default)
user = User.get(pk="USER#123", sk="PROFILE")

# Strongly consistent
user = User.get(pk="USER#123", sk="PROFILE", consistent_read=True)


# Option 2: Model-level default
class Order(Model):
    model_config = ModelConfig(
        table="orders",
        client=client,
        consistent_read=True,  # All reads are strongly consistent
    )

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)


# Uses strongly consistent read (from model_config)
order = Order.get(pk="ORDER#456", sk="ITEM#1")

# Override to eventually consistent for this call
order = Order.get(pk="ORDER#456", sk="ITEM#1", consistent_read=False)
