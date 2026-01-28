"""Setting a default client for all models."""

import asyncio
import os

from pydynox import DynamoDBClient, Model, ModelConfig, set_default_client
from pydynox.attributes import StringAttribute

# Create and set default client once at app startup
# Uses environment variables or default credential chain
client = DynamoDBClient(
    endpoint_url=os.environ.get("AWS_ENDPOINT_URL"),
)
set_default_client(client)


# All models use the default client automatically
class User(Model):
    model_config = ModelConfig(table="users")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()


class Order(Model):
    model_config = ModelConfig(table="orders")
    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    total = StringAttribute()


async def main():
    # No need to pass client to each model
    user = User(pk="USER#1", sk="PROFILE", name="John")
    await user.save()  # Uses the default client


if __name__ == "__main__":
    asyncio.run(main())
