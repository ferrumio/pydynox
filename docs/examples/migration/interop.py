"""Using boto3 and pydynox together during migration."""

import boto3
from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()


# Convert boto3 response to pydynox Model
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table("users")

response = table.get_item(Key={"pk": "USER#123", "sk": "PROFILE"})
if item := response.get("Item"):
    user = User(**item)
    print(f"Loaded from boto3: {user.name}")

# Convert pydynox Model to dict for legacy code
user = User.get(pk="USER#123", sk="PROFILE")
if user:
    data = user.to_dict()
    print(f"As dict: {data}")
