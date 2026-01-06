"""Example: update_by_key and delete_by_key operations."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(hash_key=True)
    sk = StringAttribute(range_key=True)
    name = StringAttribute()
    age = NumberAttribute()


# Update without fetching first - single DynamoDB call
User.update_by_key(pk="USER#123", sk="PROFILE", name="Jane", age=31)

# Delete without fetching first - single DynamoDB call
User.delete_by_key(pk="USER#123", sk="PROFILE")

# Compare with traditional approach (2 calls):
# user = User.get(pk="USER#123", sk="PROFILE")  # Call 1
# user.update(name="Jane")                       # Call 2
