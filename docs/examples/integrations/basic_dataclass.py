"""Basic dataclass integration example."""

import asyncio
from dataclasses import dataclass

from pydynox import DynamoDBClient, dynamodb_model

# Create a client
client = DynamoDBClient(region="us-east-1")


# Define your dataclass with the decorator
@dynamodb_model(table="users", hash_key="pk", range_key="sk", client=client)
@dataclass
class User:
    pk: str
    sk: str
    name: str
    age: int = 0


async def main():
    # Create and save
    user = User(pk="USER#1", sk="PROFILE", name="John", age=30)
    await user.save()

    # Get by key
    user = await User.get(pk="USER#1", sk="PROFILE")
    print(user.name)  # John

    # Update
    await user.update(name="Jane", age=31)

    # Delete
    await user.delete()


asyncio.run(main())
