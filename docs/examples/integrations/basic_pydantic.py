"""Basic Pydantic integration example."""

from pydantic import BaseModel
from pydynox import DynamoDBClient, dynamodb_model

# Create a client
client = DynamoDBClient(region="us-east-1")


# Define your Pydantic model with the decorator
@dynamodb_model(table="users", hash_key="pk", range_key="sk", client=client)
class User(BaseModel):
    pk: str
    sk: str
    name: str
    age: int = 0


# Create and save
user = User(pk="USER#1", sk="PROFILE", name="John", age=30)
user.save()

# Get by key
user = User.get(pk="USER#1", sk="PROFILE")
print(user.name)  # John

# Update
user.update(name="Jane", age=31)

# Delete
user.delete()
