"""Example: CRUD operations (sync - use sync_ prefix)."""

from pydynox import Model, ModelConfig
from pydynox.attributes import NumberAttribute, StringAttribute


class User(Model):
    model_config = ModelConfig(table="users")

    pk = StringAttribute(partition_key=True)
    sk = StringAttribute(sort_key=True)
    name = StringAttribute()
    age = NumberAttribute(default=0)


# Create
user = User(pk="USER#123", sk="PROFILE", name="John", age=30)
user.sync_save()

# Read
user = User.sync_get(pk="USER#123", sk="PROFILE")
if user:
    print(user.name)  # John

# Update - full
user.name = "Jane"
user.sync_save()

# Update - partial
user.sync_update(name="Jane", age=31)

# Delete
user.sync_delete()
