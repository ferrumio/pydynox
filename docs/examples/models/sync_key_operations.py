"""Example: update_by_key and delete_by_key operations (sync - use sync_ prefix)."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    name = StringAttribute()
    age = NumberAttribute()


# Update without fetching first - single DynamoDB call
User.sync_update_by_key(pk="USER#123", sk="PROFILE", name="Jane", age=31)

# Delete without fetching first - single DynamoDB call
User.sync_delete_by_key(pk="USER#123", sk="PROFILE")

# Compare with traditional approach (2 calls):
# user = User.sync_get(pk="USER#123", sk="PROFILE")  # Call 1
# user.sync_update(name="Jane")                       # Call 2
