"""Using boto3 and pydynox together during migration."""

import asyncio

import boto3
from pydynox import Model, ModelConfig
from pydynox.attributes import StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()


def legacy_function(data: dict) -> None:
    """Existing code that expects a dict."""
    print(f"As dict: {data}")


async def main():
    # boto3 client for legacy code
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("users")

    # Read with boto3, use as pydynox Model
    response = table.get_item(Key={"pk": "USER#123", "sk": "PROFILE"})
    if item := response.get("Item"):
        user = User(**item)  # boto3 dict -> pydynox Model
        print(f"Loaded from boto3: {user.name}")

    # Read with pydynox, pass to legacy code expecting dict
    user = await User.get(pk="USER#123", sk="PROFILE")
    if user:
        legacy_function(user.to_dict())  # pydynox Model -> dict


asyncio.run(main())
