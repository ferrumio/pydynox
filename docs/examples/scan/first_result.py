"""Get first result from scan."""

from pydynox import DynamoDBClient, Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute

client = DynamoDBClient()


class User(Model):
    model_config = ModelConfig(table="users", client=client)
    pk = StringAttribute(hash_key=True)
    name = StringAttribute()
    age = NumberAttribute()


# Get first user (any user)
user = User.scan().first()
if user:
    print(f"Found: {user.name}")
else:
    print("No users found")

# Get first user matching filter
admin = User.scan(filter_condition=User.name == "admin").first()
if admin:
    print(f"Admin found: {admin.pk}")
